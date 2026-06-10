import base64

from flask import Blueprint, jsonify, request
from mysql.connector import IntegrityError

from .db import call_procedure, execute, fetch_all, fetch_one
from .security import admin_required, hash_password


bp = Blueprint("admin", __name__, url_prefix="/api/admin")


@bp.get("/stats")
@admin_required
def stats():
    table_counts = fetch_all(
        """
        SELECT 'users' AS table_name, COUNT(*) AS total FROM users
        UNION ALL SELECT 'movies', COUNT(*) FROM movies
        UNION ALL SELECT 'ratings', COUNT(*) FROM ratings
        UNION ALL SELECT 'favorites', COUNT(*) FROM favorites
        UNION ALL SELECT 'browse_history', COUNT(*) FROM browse_history
        UNION ALL SELECT 'recommendations', COUNT(*) FROM recommendations
        UNION ALL SELECT 'item_similarity', COUNT(*) FROM item_similarity
        """
    )
    behavior_summary = fetch_all(
        """
        SELECT *
        FROM v_user_behavior_summary
        ORDER BY rating_count DESC, favorite_count DESC, browse_count DESC
        LIMIT 20
        """
    )
    return jsonify({"table_counts": table_counts, "behavior_summary": behavior_summary})


@bp.post("/admins")
@admin_required
def create_admin():
    data = request.get_json(silent=True) or {}
    username = (data.get("username") or "").strip()
    password = data.get("password") or ""
    role = data.get("role") or "content_admin"
    if len(username) < 3 or len(password) < 6:
        return jsonify({"error": "bad_request", "message": "管理员用户名或密码格式不正确"}), 400
    try:
        execute(
            """
            INSERT INTO admins(username, password_hash, role)
            VALUES (%s, %s, %s)
            """,
            (username, hash_password(password), role),
        )
    except IntegrityError:
        return jsonify({"error": "duplicate", "message": "管理员用户名已存在"}), 409
    return jsonify({"message": "管理员已创建"}), 201


@bp.post("/categories")
@admin_required
def create_category():
    data = request.get_json(silent=True) or {}
    name = (data.get("category_name") or "").strip()
    description = data.get("description")
    if not name:
        return jsonify({"error": "bad_request", "message": "分类名不能为空"}), 400
    try:
        execute(
            "INSERT INTO categories(category_name, description) VALUES (%s, %s)",
            (name, description),
        )
    except IntegrityError:
        return jsonify({"error": "duplicate", "message": "分类已存在"}), 409
    return jsonify({"message": "分类已创建"}), 201


@bp.put("/categories/<int:category_id>")
@admin_required
def update_category(category_id: int):
    data = request.get_json(silent=True) or {}
    execute(
        """
        UPDATE categories
        SET category_name = COALESCE(%s, category_name),
            description = COALESCE(%s, description)
        WHERE category_id = %s
        """,
        (data.get("category_name"), data.get("description"), category_id),
    )
    return jsonify({"message": "分类已更新"})


@bp.post("/movies")
@admin_required
def create_movie():
    data = request.get_json(silent=True) or {}
    required = ["category_id", "title"]
    if any(not data.get(key) for key in required):
        return jsonify({"error": "bad_request", "message": "category_id 和 title 必填"}), 400

    execute(
        """
        INSERT INTO movies(category_id, title, description, poster_url, status)
        VALUES (%s, %s, %s, %s, %s)
        """,
        (
            data["category_id"],
            data["title"],
            data.get("description"),
            data.get("poster_url"),
            data.get("status", "online"),
        ),
    )
    movie = fetch_one("SELECT * FROM movies WHERE title = %s ORDER BY movie_id DESC LIMIT 1", (data["title"],))
    return jsonify({"message": "电影已创建", "movie": movie}), 201


@bp.put("/movies/<int:movie_id>")
@admin_required
def update_movie(movie_id: int):
    data = request.get_json(silent=True) or {}
    execute(
        """
        UPDATE movies
        SET category_id = COALESCE(%s, category_id),
            title = COALESCE(%s, title),
            description = COALESCE(%s, description),
            poster_url = COALESCE(%s, poster_url),
            status = COALESCE(%s, status)
        WHERE movie_id = %s
        """,
        (
            data.get("category_id"),
            data.get("title"),
            data.get("description"),
            data.get("poster_url"),
            data.get("status"),
            movie_id,
        ),
    )
    return jsonify({"message": "电影已更新"})


@bp.delete("/movies/<int:movie_id>")
@admin_required
def delete_movie(movie_id: int):
    execute("DELETE FROM movies WHERE movie_id = %s", (movie_id,))
    return jsonify({"message": "电影已删除"})


@bp.post("/movies/<int:movie_id>/files")
@admin_required
def create_movie_file(movie_id: int):
    data = request.get_json(silent=True) or {}
    file_name = (data.get("file_name") or "").strip()
    file_type = data.get("file_type", "poster")
    file_path = data.get("file_path")
    raw_base64 = data.get("file_data_base64")
    binary = base64.b64decode(raw_base64) if raw_base64 else None
    file_size = len(binary) if binary is not None else data.get("file_size", 0)
    if not file_name:
        return jsonify({"error": "bad_request", "message": "file_name 必填"}), 400

    execute(
        """
        INSERT INTO movie_files(movie_id, file_name, file_path, file_type, file_size, file_data)
        VALUES (%s, %s, %s, %s, %s, %s)
        """,
        (movie_id, file_name, file_path, file_type, file_size, binary),
    )
    return jsonify({"message": "电影文件已保存"}), 201


@bp.post("/rebuild-similarity")
@admin_required
def rebuild_similarity():
    call_procedure("sp_calculate_item_similarity")
    count = fetch_one("SELECT COUNT(*) AS total FROM item_similarity")
    return jsonify({"message": "相似度矩阵已重建", "total": count["total"]})

