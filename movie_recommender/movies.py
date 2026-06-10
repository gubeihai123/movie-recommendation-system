from flask import Blueprint, jsonify, request
from mysql.connector import IntegrityError

from .db import execute, fetch_all, fetch_one
from .security import current_user_id, login_required


bp = Blueprint("movies", __name__, url_prefix="/api")


@bp.get("/categories")
def categories():
    rows = fetch_all(
        """
        SELECT category_id, category_name, description
        FROM categories
        ORDER BY category_id
        """
    )
    return jsonify({"items": rows})


@bp.get("/movies")
def list_movies():
    page = max(int(request.args.get("page", 1)), 1)
    page_size = min(max(int(request.args.get("page_size", 20)), 1), 100)
    offset = (page - 1) * page_size
    category_id = request.args.get("category_id")
    keyword = (request.args.get("q") or "").strip()

    where = ["m.status = 'online'"]
    params: list[object] = []
    if category_id:
        where.append("m.category_id = %s")
        params.append(category_id)
    if keyword:
        where.append("(m.title LIKE %s OR m.description LIKE %s)")
        params.extend([f"%{keyword}%", f"%{keyword}%"])
    where_sql = " AND ".join(where)

    items = fetch_all(
        f"""
        SELECT m.movie_id, m.title, m.description, m.poster_url,
               m.avg_rating, m.rating_count, m.view_count, m.created_at,
               c.category_id, c.category_name
        FROM movies m
        JOIN categories c ON c.category_id = m.category_id
        WHERE {where_sql}
        ORDER BY m.movie_id ASC
        LIMIT %s OFFSET %s
        """,
        tuple(params + [page_size, offset]),
    )
    total = fetch_one(
        f"""
        SELECT COUNT(*) AS total
        FROM movies m
        WHERE {where_sql}
        """,
        tuple(params),
    )
    return jsonify({"items": items, "page": page, "page_size": page_size, "total": total["total"]})


@bp.get("/movies/<int:movie_id>")
def movie_detail(movie_id: int):
    movie = fetch_one(
        """
        SELECT *
        FROM v_movie_details
        WHERE movie_id = %s
        """,
        (movie_id,),
    )
    if not movie:
        return jsonify({"error": "not_found", "message": "电影不存在"}), 404

    files = fetch_all(
        """
        SELECT file_id, file_name, file_path, file_type, file_size, upload_time
        FROM movie_files
        WHERE movie_id = %s
        ORDER BY file_type, file_id
        """,
        (movie_id,),
    )
    user_id = current_user_id()
    user_state = None
    if user_id:
        execute("INSERT INTO browse_history(user_id, movie_id) VALUES (%s, %s)", (user_id, movie_id))
        user_state = fetch_one(
            """
            SELECT
              (SELECT score FROM ratings WHERE user_id = %s AND movie_id = %s) AS rating_score,
              EXISTS(SELECT 1 FROM favorites WHERE user_id = %s AND movie_id = %s) AS favored
            """,
            (user_id, movie_id, user_id, movie_id),
        )

    return jsonify({"movie": movie, "files": files, "user_state": user_state})


@bp.post("/movies/<int:movie_id>/browse")
@login_required
def record_browse(movie_id: int):
    if not fetch_one("SELECT movie_id FROM movies WHERE movie_id = %s", (movie_id,)):
        return jsonify({"error": "not_found", "message": "电影不存在"}), 404
    execute("INSERT INTO browse_history(user_id, movie_id) VALUES (%s, %s)", (current_user_id(), movie_id))
    return jsonify({"message": "浏览记录已保存"})


@bp.post("/movies/<int:movie_id>/rating")
@login_required
def rate_movie(movie_id: int):
    data = request.get_json(silent=True) or {}
    try:
        score = float(data.get("score"))
    except (TypeError, ValueError):
        return jsonify({"error": "bad_request", "message": "评分必须是 1 到 5 的数字"}), 400
    if score < 1 or score > 5:
        return jsonify({"error": "bad_request", "message": "评分必须在 1 到 5 之间"}), 400

    try:
        execute(
            """
            INSERT INTO ratings(user_id, movie_id, score)
            VALUES (%s, %s, %s)
            ON DUPLICATE KEY UPDATE score = VALUES(score), created_at = CURRENT_TIMESTAMP
            """,
            (current_user_id(), movie_id, score),
        )
    except IntegrityError:
        return jsonify({"error": "not_found", "message": "电影不存在"}), 404
    return jsonify({"message": "评分已保存"})


@bp.delete("/movies/<int:movie_id>/rating")
@login_required
def delete_rating(movie_id: int):
    execute("DELETE FROM ratings WHERE user_id = %s AND movie_id = %s", (current_user_id(), movie_id))
    return jsonify({"message": "评分已删除"})


@bp.post("/movies/<int:movie_id>/favorite")
@login_required
def add_favorite(movie_id: int):
    try:
        execute(
            """
            INSERT IGNORE INTO favorites(user_id, movie_id)
            VALUES (%s, %s)
            """,
            (current_user_id(), movie_id),
        )
    except IntegrityError:
        return jsonify({"error": "not_found", "message": "电影不存在"}), 404
    return jsonify({"message": "已收藏"})


@bp.delete("/movies/<int:movie_id>/favorite")
@login_required
def delete_favorite(movie_id: int):
    execute("DELETE FROM favorites WHERE user_id = %s AND movie_id = %s", (current_user_id(), movie_id))
    return jsonify({"message": "已取消收藏"})


@bp.get("/me/behaviors")
@login_required
def my_behaviors():
    user_id = current_user_id()
    ratings = fetch_all(
        """
        SELECT r.rating_id, r.score, r.created_at, m.movie_id, m.title, m.poster_url
        FROM ratings r
        JOIN movies m ON m.movie_id = r.movie_id
        WHERE r.user_id = %s
        ORDER BY r.created_at DESC
        """,
        (user_id,),
    )
    favorites = fetch_all(
        """
        SELECT f.favorite_id, f.created_at, m.movie_id, m.title, m.poster_url
        FROM favorites f
        JOIN movies m ON m.movie_id = f.movie_id
        WHERE f.user_id = %s
        ORDER BY f.created_at DESC
        """,
        (user_id,),
    )
    browses = fetch_all(
        """
        SELECT b.history_id, b.browse_time, m.movie_id, m.title, m.poster_url
        FROM browse_history b
        JOIN movies m ON m.movie_id = b.movie_id
        WHERE b.user_id = %s
        ORDER BY b.browse_time DESC
        LIMIT 100
        """,
        (user_id,),
    )
    return jsonify({"ratings": ratings, "favorites": favorites, "browses": browses})
