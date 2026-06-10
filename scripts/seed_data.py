import json
import os
import random
from pathlib import Path

import mysql.connector
from dotenv import load_dotenv
from werkzeug.security import generate_password_hash


ROOT = Path(__file__).resolve().parents[1]
REAL_MOVIES_PATH = ROOT / "data" / "real_movies.json"
PNG_HEADER = bytes.fromhex("89504E470D0A1A0A")

CATEGORY_ROWS = [
    ("科幻", "科学幻想、未来科技、太空探索和反乌托邦题材"),
    ("动作", "动作冒险、战争、英雄和高强度冲突题材"),
    ("喜剧", "幽默、讽刺、家庭娱乐和轻喜剧题材"),
    ("剧情", "人物成长、社会议题、犯罪史诗和现实叙事题材"),
    ("爱情", "情感关系、浪漫叙事和经典爱情题材"),
    ("动画", "动画长片、家庭向和奇幻冒险题材"),
    ("悬疑", "犯罪、推理、心理惊悚和悬念题材"),
    ("纪录片", "纪实影像、人物传记、自然和社会议题题材"),
]


def connect():
    load_dotenv(ROOT / ".env")
    return mysql.connector.connect(
        host=os.getenv("DB_HOST", "127.0.0.1"),
        port=int(os.getenv("DB_PORT", "3306")),
        user=os.getenv("DB_USER", "root"),
        password=os.getenv("DB_PASSWORD", "root"),
        database=os.getenv("DB_NAME", "movie_recommendation_db"),
        charset="utf8mb4",
        collation="utf8mb4_0900_ai_ci",
        autocommit=False,
    )


def reset_data(cursor) -> None:
    cursor.execute("SET FOREIGN_KEY_CHECKS = 0")
    for table in [
        "recommendations",
        "item_similarity",
        "movie_files",
        "browse_history",
        "favorites",
        "ratings",
        "movies",
        "categories",
        "admins",
        "users",
    ]:
        cursor.execute(f"TRUNCATE TABLE {table}")
    cursor.execute("SET FOREIGN_KEY_CHECKS = 1")


def seed_categories(cursor) -> dict[str, int]:
    cursor.executemany(
        "INSERT INTO categories(category_name, description) VALUES (%s, %s)",
        CATEGORY_ROWS,
    )
    cursor.execute("SELECT category_id, category_name FROM categories")
    return {name: category_id for category_id, name in cursor.fetchall()}


def seed_users(cursor) -> list[int]:
    user_hash = generate_password_hash("password123")
    users = [
        (f"user{i:03d}", user_hash, f"user{i:03d}@example.com", "active")
        for i in range(1, 201)
    ]
    cursor.executemany(
        """
        INSERT INTO users(username, password_hash, email, status)
        VALUES (%s, %s, %s, %s)
        """,
        users,
    )
    admin_hash = generate_password_hash("root")
    cursor.execute(
        """
        INSERT INTO admins(username, password_hash, role)
        VALUES (%s, %s, %s)
        """,
        ("admin", admin_hash, "super_admin"),
    )
    return list(range(1, 201))


def load_real_movies() -> list[dict]:
    if not REAL_MOVIES_PATH.exists():
        raise FileNotFoundError(f"缺少真实电影数据文件：{REAL_MOVIES_PATH}")
    rows = json.loads(REAL_MOVIES_PATH.read_text(encoding="utf-8"))
    valid_rows = [
        row for row in rows
        if row.get("title") and row.get("description") and row.get("poster_url")
    ]
    if len(valid_rows) < 200:
        raise ValueError("真实电影数据少于 200 条，请先运行 scripts/fetch_wikidata_movies.py")
    return valid_rows


def seed_movies(cursor, category_ids: dict[str, int]) -> list[int]:
    real_movies = load_real_movies()
    rows = []
    for row in real_movies:
        category_name = row.get("category") or "剧情"
        category_id = category_ids.get(category_name, category_ids["剧情"])
        rows.append(
            (
                category_id,
                row["title"][:100],
                row["description"],
                row["poster_url"][:255],
                "online",
            )
        )

    cursor.executemany(
        """
        INSERT INTO movies(category_id, title, description, poster_url, status)
        VALUES (%s, %s, %s, %s, %s)
        """,
        rows,
    )

    cursor.execute("SELECT movie_id, poster_url FROM movies ORDER BY movie_id")
    movie_rows = cursor.fetchall()
    movie_files = [
        (
            movie_id,
            f"movie_{movie_id:03d}_poster.jpg",
            poster_url,
            "poster",
            len(PNG_HEADER),
            PNG_HEADER,
        )
        for movie_id, poster_url in movie_rows
    ]
    cursor.executemany(
        """
        INSERT INTO movie_files(movie_id, file_name, file_path, file_type, file_size, file_data)
        VALUES (%s, %s, %s, %s, %s, %s)
        """,
        movie_files,
    )
    return [movie_id for movie_id, _poster_url in movie_rows]


def seed_behaviors(cursor, user_ids: list[int], movie_ids: list[int]) -> None:
    random.seed(20260609)

    rating_pairs = set()
    ratings = []
    target_ratings = min(2500, len(user_ids) * len(movie_ids) // 5)
    while len(ratings) < target_ratings:
        user_id = random.choice(user_ids)
        movie_id = random.choice(movie_ids)
        if (user_id, movie_id) in rating_pairs:
            continue
        rating_pairs.add((user_id, movie_id))
        score = random.choices([1, 2, 3, 4, 5], weights=[3, 7, 20, 36, 34])[0]
        ratings.append((user_id, movie_id, score))
    cursor.executemany(
        "INSERT INTO ratings(user_id, movie_id, score) VALUES (%s, %s, %s)",
        ratings,
    )

    favorites = set()
    target_favorites = min(900, len(user_ids) * len(movie_ids) // 12)
    while len(favorites) < target_favorites:
        favorites.add((random.choice(user_ids), random.choice(movie_ids)))
    cursor.executemany(
        "INSERT IGNORE INTO favorites(user_id, movie_id) VALUES (%s, %s)",
        list(favorites),
    )

    browses = [
        (random.choice(user_ids), random.choice(movie_ids))
        for _ in range(min(3500, len(user_ids) * len(movie_ids) // 3))
    ]
    cursor.executemany(
        "INSERT INTO browse_history(user_id, movie_id) VALUES (%s, %s)",
        browses,
    )


def build_recommendations(cursor, user_count: int) -> None:
    cursor.callproc("sp_calculate_item_similarity")
    for result in cursor.stored_results():
        result.fetchall()
    for user_id in range(1, min(user_count, 20) + 1):
        cursor.callproc("sp_generate_recommendations", (user_id, 10))
        for result in cursor.stored_results():
            result.fetchall()


def print_counts(cursor) -> None:
    for table in [
        "users",
        "admins",
        "categories",
        "movies",
        "ratings",
        "favorites",
        "browse_history",
        "movie_files",
        "item_similarity",
        "recommendations",
    ]:
        cursor.execute(f"SELECT COUNT(*) FROM {table}")
        print(f"{table}: {cursor.fetchone()[0]}")


def main() -> None:
    conn = connect()
    cursor = conn.cursor()
    try:
        reset_data(cursor)
        category_ids = seed_categories(cursor)
        user_ids = seed_users(cursor)
        movie_ids = seed_movies(cursor, category_ids)
        seed_behaviors(cursor, user_ids, movie_ids)
        conn.commit()
        build_recommendations(cursor, len(user_ids))
        conn.commit()
        print_counts(cursor)
        print("真实电影数据已导入。普通用户 user001/password123，管理员 admin/root。")
    except Exception:
        conn.rollback()
        raise
    finally:
        cursor.close()
        conn.close()


if __name__ == "__main__":
    main()
