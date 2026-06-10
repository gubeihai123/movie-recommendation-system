CREATE DATABASE IF NOT EXISTS movie_recommendation_db
  DEFAULT CHARACTER SET utf8mb4
  DEFAULT COLLATE utf8mb4_0900_ai_ci;

USE movie_recommendation_db;

DROP TRIGGER IF EXISTS trg_ratings_after_insert;
DROP TRIGGER IF EXISTS trg_ratings_after_update;
DROP TRIGGER IF EXISTS trg_ratings_after_delete;
DROP TRIGGER IF EXISTS trg_browse_after_insert;

DROP PROCEDURE IF EXISTS sp_refresh_movie_rating_stats;
DROP PROCEDURE IF EXISTS sp_calculate_item_similarity;
DROP PROCEDURE IF EXISTS sp_generate_recommendations;

DROP FUNCTION IF EXISTS fn_user_movie_interaction_score;
DROP FUNCTION IF EXISTS fn_hot_score;

DROP VIEW IF EXISTS v_movie_details;
DROP VIEW IF EXISTS v_user_behavior_summary;
DROP VIEW IF EXISTS v_hot_movies;

CREATE TABLE users (
  user_id BIGINT PRIMARY KEY AUTO_INCREMENT,
  username VARCHAR(50) NOT NULL UNIQUE,
  password_hash VARCHAR(255) NOT NULL,
  email VARCHAR(100) NOT NULL UNIQUE,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  status ENUM('active', 'banned', 'deleted') NOT NULL DEFAULT 'active'
) ENGINE=InnoDB;

CREATE TABLE admins (
  admin_id BIGINT PRIMARY KEY AUTO_INCREMENT,
  username VARCHAR(50) NOT NULL UNIQUE,
  password_hash VARCHAR(255) NOT NULL,
  role ENUM('super_admin', 'content_admin') NOT NULL DEFAULT 'content_admin',
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;

CREATE TABLE categories (
  category_id BIGINT PRIMARY KEY AUTO_INCREMENT,
  category_name VARCHAR(50) NOT NULL UNIQUE,
  description VARCHAR(255)
) ENGINE=InnoDB;

CREATE TABLE movies (
  movie_id BIGINT PRIMARY KEY AUTO_INCREMENT,
  category_id BIGINT NOT NULL,
  title VARCHAR(100) NOT NULL,
  description TEXT,
  poster_url VARCHAR(255),
  avg_rating DECIMAL(3,2) NOT NULL DEFAULT 0,
  rating_count INT NOT NULL DEFAULT 0,
  view_count INT NOT NULL DEFAULT 0,
  status ENUM('online', 'offline') NOT NULL DEFAULT 'online',
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_movies_category
    FOREIGN KEY (category_id) REFERENCES categories(category_id)
    ON UPDATE CASCADE
) ENGINE=InnoDB;

CREATE TABLE ratings (
  rating_id BIGINT PRIMARY KEY AUTO_INCREMENT,
  user_id BIGINT NOT NULL,
  movie_id BIGINT NOT NULL,
  score DECIMAL(2,1) NOT NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT ck_ratings_score CHECK (score BETWEEN 1 AND 5),
  CONSTRAINT uq_ratings_user_movie UNIQUE (user_id, movie_id),
  CONSTRAINT fk_ratings_user
    FOREIGN KEY (user_id) REFERENCES users(user_id)
    ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT fk_ratings_movie
    FOREIGN KEY (movie_id) REFERENCES movies(movie_id)
    ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB;

CREATE TABLE favorites (
  favorite_id BIGINT PRIMARY KEY AUTO_INCREMENT,
  user_id BIGINT NOT NULL,
  movie_id BIGINT NOT NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT uq_favorites_user_movie UNIQUE (user_id, movie_id),
  CONSTRAINT fk_favorites_user
    FOREIGN KEY (user_id) REFERENCES users(user_id)
    ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT fk_favorites_movie
    FOREIGN KEY (movie_id) REFERENCES movies(movie_id)
    ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB;

CREATE TABLE browse_history (
  history_id BIGINT PRIMARY KEY AUTO_INCREMENT,
  user_id BIGINT NOT NULL,
  movie_id BIGINT NOT NULL,
  browse_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_browse_user
    FOREIGN KEY (user_id) REFERENCES users(user_id)
    ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT fk_browse_movie
    FOREIGN KEY (movie_id) REFERENCES movies(movie_id)
    ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB;

CREATE TABLE recommendations (
  rec_id BIGINT PRIMARY KEY AUTO_INCREMENT,
  user_id BIGINT NOT NULL,
  movie_id BIGINT NOT NULL,
  recommend_score DECIMAL(10,4) NOT NULL DEFAULT 0,
  algorithm_type ENUM('itemcf', 'hot', 'hybrid') NOT NULL,
  rec_reason VARCHAR(255),
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT uq_recommendations_user_movie UNIQUE (user_id, movie_id),
  CONSTRAINT fk_recommendations_user
    FOREIGN KEY (user_id) REFERENCES users(user_id)
    ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT fk_recommendations_movie
    FOREIGN KEY (movie_id) REFERENCES movies(movie_id)
    ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB;

CREATE TABLE movie_files (
  file_id BIGINT PRIMARY KEY AUTO_INCREMENT,
  movie_id BIGINT NOT NULL,
  file_name VARCHAR(100) NOT NULL,
  file_path VARCHAR(255),
  file_type ENUM('poster', 'trailer', 'other') NOT NULL DEFAULT 'poster',
  file_size INT NOT NULL DEFAULT 0,
  file_data LONGBLOB,
  upload_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_movie_files_movie
    FOREIGN KEY (movie_id) REFERENCES movies(movie_id)
    ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB;

CREATE TABLE item_similarity (
  movie_id BIGINT NOT NULL,
  similar_movie_id BIGINT NOT NULL,
  similarity DECIMAL(10,6) NOT NULL DEFAULT 0,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (movie_id, similar_movie_id),
  CONSTRAINT fk_item_similarity_movie
    FOREIGN KEY (movie_id) REFERENCES movies(movie_id)
    ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT fk_item_similarity_similar_movie
    FOREIGN KEY (similar_movie_id) REFERENCES movies(movie_id)
    ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB;

CREATE INDEX idx_ratings_user_movie
  ON ratings(user_id, movie_id);

CREATE INDEX idx_ratings_movie_score
  ON ratings(movie_id, score);

CREATE INDEX idx_favorites_user_movie
  ON favorites(user_id, movie_id);

CREATE INDEX idx_browse_user_movie
  ON browse_history(user_id, movie_id);

CREATE INDEX idx_recommendations_user_score
  ON recommendations(user_id, recommend_score);

CREATE INDEX idx_item_similarity_movie_score
  ON item_similarity(movie_id, similarity);

CREATE INDEX idx_movies_category_status
  ON movies(category_id, status);

CREATE OR REPLACE VIEW v_movie_details AS
SELECT
  m.movie_id,
  m.title,
  m.description,
  m.poster_url,
  m.avg_rating,
  m.rating_count,
  m.view_count,
  m.status,
  m.created_at,
  c.category_id,
  c.category_name,
  mf.file_id,
  mf.file_name,
  mf.file_path,
  mf.file_type,
  mf.file_size,
  mf.upload_time
FROM movies m
JOIN categories c ON m.category_id = c.category_id
LEFT JOIN movie_files mf ON m.movie_id = mf.movie_id AND mf.file_type = 'poster';

CREATE OR REPLACE VIEW v_user_behavior_summary AS
SELECT
  u.user_id,
  u.username,
  COUNT(DISTINCT r.rating_id) AS rating_count,
  COUNT(DISTINCT f.favorite_id) AS favorite_count,
  COUNT(DISTINCT b.history_id) AS browse_count
FROM users u
LEFT JOIN ratings r ON u.user_id = r.user_id
LEFT JOIN favorites f ON u.user_id = f.user_id
LEFT JOIN browse_history b ON u.user_id = b.user_id
GROUP BY u.user_id, u.username;

CREATE OR REPLACE VIEW v_hot_movies AS
SELECT
  m.movie_id,
  m.title,
  m.description,
  m.poster_url,
  c.category_name,
  m.avg_rating,
  m.rating_count,
  m.view_count,
  COUNT(f.favorite_id) AS favorite_count,
  ROUND(m.avg_rating * 0.55 + LOG(m.view_count + 1) * 0.25 + LOG(COUNT(f.favorite_id) + 1) * 0.20, 4) AS hot_score
FROM movies m
JOIN categories c ON m.category_id = c.category_id
LEFT JOIN favorites f ON m.movie_id = f.movie_id
WHERE m.status = 'online'
GROUP BY m.movie_id, m.title, m.description, m.poster_url, c.category_name, m.avg_rating, m.rating_count, m.view_count
ORDER BY hot_score DESC;

DELIMITER $$

CREATE PROCEDURE sp_refresh_movie_rating_stats(IN p_movie_id BIGINT)
BEGIN
  UPDATE movies m
  SET
    m.avg_rating = (
      SELECT COALESCE(ROUND(AVG(r.score), 2), 0)
      FROM ratings r
      WHERE r.movie_id = p_movie_id
    ),
    m.rating_count = (
      SELECT COUNT(*)
      FROM ratings r
      WHERE r.movie_id = p_movie_id
    )
  WHERE m.movie_id = p_movie_id;
END$$

CREATE TRIGGER trg_ratings_after_insert
AFTER INSERT ON ratings
FOR EACH ROW
BEGIN
  CALL sp_refresh_movie_rating_stats(NEW.movie_id);
END$$

CREATE TRIGGER trg_ratings_after_update
AFTER UPDATE ON ratings
FOR EACH ROW
BEGIN
  CALL sp_refresh_movie_rating_stats(OLD.movie_id);
  IF OLD.movie_id <> NEW.movie_id THEN
    CALL sp_refresh_movie_rating_stats(NEW.movie_id);
  END IF;
END$$

CREATE TRIGGER trg_ratings_after_delete
AFTER DELETE ON ratings
FOR EACH ROW
BEGIN
  CALL sp_refresh_movie_rating_stats(OLD.movie_id);
END$$

CREATE TRIGGER trg_browse_after_insert
AFTER INSERT ON browse_history
FOR EACH ROW
BEGIN
  UPDATE movies
  SET view_count = view_count + 1
  WHERE movie_id = NEW.movie_id;
END$$

CREATE FUNCTION fn_user_movie_interaction_score(
  p_user_id BIGINT,
  p_movie_id BIGINT
) RETURNS DECIMAL(10,4)
DETERMINISTIC
READS SQL DATA
BEGIN
  DECLARE v_rating_score DECIMAL(10,4) DEFAULT 0;
  DECLARE v_favorite_weight DECIMAL(10,4) DEFAULT 0;
  DECLARE v_view_weight DECIMAL(10,4) DEFAULT 0;

  SELECT COALESCE(MAX(score), 0)
  INTO v_rating_score
  FROM ratings
  WHERE user_id = p_user_id AND movie_id = p_movie_id;

  SELECT IF(COUNT(*) > 0, 4, 0)
  INTO v_favorite_weight
  FROM favorites
  WHERE user_id = p_user_id AND movie_id = p_movie_id;

  SELECT LEAST(COUNT(*) * 0.5, 3)
  INTO v_view_weight
  FROM browse_history
  WHERE user_id = p_user_id AND movie_id = p_movie_id;

  RETURN v_rating_score + v_favorite_weight + v_view_weight;
END$$

CREATE FUNCTION fn_hot_score(p_movie_id BIGINT)
RETURNS DECIMAL(10,4)
DETERMINISTIC
READS SQL DATA
BEGIN
  DECLARE v_avg_rating DECIMAL(10,4) DEFAULT 0;
  DECLARE v_view_count INT DEFAULT 0;
  DECLARE v_favorite_count INT DEFAULT 0;

  SELECT avg_rating, view_count
  INTO v_avg_rating, v_view_count
  FROM movies
  WHERE movie_id = p_movie_id;

  SELECT COUNT(*)
  INTO v_favorite_count
  FROM favorites
  WHERE movie_id = p_movie_id;

  RETURN ROUND(v_avg_rating * 0.55 + LOG(v_view_count + 1) * 0.25 + LOG(v_favorite_count + 1) * 0.20, 4);
END$$

CREATE PROCEDURE sp_calculate_item_similarity()
BEGIN
  DELETE FROM item_similarity;

  INSERT INTO item_similarity(movie_id, similar_movie_id, similarity, updated_at)
  WITH user_movie_pairs AS (
    SELECT user_id, movie_id FROM ratings
    UNION
    SELECT user_id, movie_id FROM favorites
    UNION
    SELECT user_id, movie_id FROM browse_history
  ),
  interaction AS (
    SELECT
      user_id,
      movie_id,
      fn_user_movie_interaction_score(user_id, movie_id) AS interaction_score
    FROM user_movie_pairs
  ),
  norms AS (
    SELECT
      movie_id,
      SQRT(SUM(interaction_score * interaction_score)) AS norm_value
    FROM interaction
    GROUP BY movie_id
  )
  SELECT
    i1.movie_id,
    i2.movie_id AS similar_movie_id,
    ROUND(SUM(i1.interaction_score * i2.interaction_score) / (n1.norm_value * n2.norm_value), 6) AS similarity,
    NOW()
  FROM interaction i1
  JOIN interaction i2
    ON i1.user_id = i2.user_id
   AND i1.movie_id <> i2.movie_id
  JOIN norms n1 ON n1.movie_id = i1.movie_id
  JOIN norms n2 ON n2.movie_id = i2.movie_id
  WHERE n1.norm_value > 0 AND n2.norm_value > 0
  GROUP BY i1.movie_id, i2.movie_id, n1.norm_value, n2.norm_value
  HAVING similarity > 0;
END$$

CREATE PROCEDURE sp_generate_recommendations(
  IN p_user_id BIGINT,
  IN p_limit_num INT
)
BEGIN
  DECLARE v_behavior_count INT DEFAULT 0;
  DECLARE v_existing_count INT DEFAULT 0;
  DECLARE v_remaining_count INT DEFAULT 0;

  DELETE FROM recommendations
  WHERE user_id = p_user_id;

  SELECT COUNT(*)
  INTO v_behavior_count
  FROM (
    SELECT movie_id FROM ratings WHERE user_id = p_user_id
    UNION
    SELECT movie_id FROM favorites WHERE user_id = p_user_id
    UNION
    SELECT movie_id FROM browse_history WHERE user_id = p_user_id
  ) AS behavior_movies;

  IF v_behavior_count > 0 THEN
    INSERT INTO recommendations(
      user_id, movie_id, recommend_score, algorithm_type, rec_reason, created_at
    )
    SELECT
      p_user_id,
      s.similar_movie_id,
      ROUND(SUM(s.similarity * fn_user_movie_interaction_score(p_user_id, s.movie_id)), 4) AS recommend_score,
      'itemcf',
      '基于相似电影和用户历史行为生成',
      NOW()
    FROM item_similarity s
    JOIN movies m ON m.movie_id = s.similar_movie_id AND m.status = 'online'
    WHERE s.movie_id IN (
      SELECT movie_id FROM ratings WHERE user_id = p_user_id
      UNION
      SELECT movie_id FROM favorites WHERE user_id = p_user_id
      UNION
      SELECT movie_id FROM browse_history WHERE user_id = p_user_id
    )
    AND NOT EXISTS (
      SELECT 1
      FROM (
        SELECT movie_id FROM ratings WHERE user_id = p_user_id
        UNION
        SELECT movie_id FROM favorites WHERE user_id = p_user_id
        UNION
        SELECT movie_id FROM browse_history WHERE user_id = p_user_id
      ) AS used_movies
      WHERE used_movies.movie_id = s.similar_movie_id
    )
    GROUP BY s.similar_movie_id
    ORDER BY recommend_score DESC
    LIMIT p_limit_num;
  END IF;

  SELECT COUNT(*)
  INTO v_existing_count
  FROM recommendations
  WHERE user_id = p_user_id;

  SET v_remaining_count = p_limit_num - v_existing_count;

  IF v_existing_count < p_limit_num THEN
    INSERT INTO recommendations(
      user_id, movie_id, recommend_score, algorithm_type, rec_reason, created_at
    )
    SELECT
      p_user_id,
      m.movie_id,
      fn_hot_score(m.movie_id),
      IF(v_behavior_count > 0, 'hybrid', 'hot'),
      IF(v_behavior_count > 0, '个性化候选不足时使用热门电影补齐', '冷启动或行为稀疏场景下的热门推荐'),
      NOW()
    FROM movies m
    WHERE m.status = 'online'
      AND NOT EXISTS (
        SELECT 1 FROM ratings r WHERE r.user_id = p_user_id AND r.movie_id = m.movie_id
      )
      AND NOT EXISTS (
        SELECT 1 FROM favorites f WHERE f.user_id = p_user_id AND f.movie_id = m.movie_id
      )
      AND NOT EXISTS (
        SELECT 1 FROM browse_history b WHERE b.user_id = p_user_id AND b.movie_id = m.movie_id
      )
      AND NOT EXISTS (
        SELECT 1 FROM recommendations rec WHERE rec.user_id = p_user_id AND rec.movie_id = m.movie_id
      )
    ORDER BY fn_hot_score(m.movie_id) DESC
    LIMIT v_remaining_count;
  END IF;
END$$

DELIMITER ;
