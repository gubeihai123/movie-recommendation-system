from flask import Blueprint, jsonify, request

from .db import call_procedure, fetch_all, fetch_one
from .security import current_user_id, login_required


bp = Blueprint("recommendations", __name__, url_prefix="/api/recommendations")


@bp.get("/hot")
def hot_movies():
    limit = min(max(int(request.args.get("limit", 10)), 1), 50)
    rows = fetch_all(
        """
        SELECT *
        FROM v_hot_movies
        LIMIT %s
        """,
        (limit,),
    )
    return jsonify({"items": rows})


@bp.post("/generate")
@login_required
def generate():
    limit = min(max(int((request.get_json(silent=True) or {}).get("limit", 10)), 1), 50)
    similarity_count = fetch_one("SELECT COUNT(*) AS total FROM item_similarity")
    if not similarity_count or similarity_count["total"] == 0:
        call_procedure("sp_calculate_item_similarity")
    call_procedure("sp_generate_recommendations", (current_user_id(), limit))
    return jsonify({"message": "推荐结果已生成", "limit": limit})


@bp.get("")
@login_required
def list_recommendations():
    limit = min(max(int(request.args.get("limit", 10)), 1), 50)
    refresh = request.args.get("refresh", "0") == "1"
    rebuild = request.args.get("rebuild", "0") == "1"
    if refresh:
        if rebuild:
            call_procedure("sp_calculate_item_similarity")
        call_procedure("sp_generate_recommendations", (current_user_id(), limit))

    rows = fetch_all(
        """
        SELECT r.rec_id, r.recommend_score, r.algorithm_type, r.rec_reason, r.created_at,
               m.movie_id, m.title, m.description, m.poster_url,
               m.avg_rating, m.rating_count, m.view_count,
               c.category_name
        FROM recommendations r
        JOIN movies m ON m.movie_id = r.movie_id
        JOIN categories c ON c.category_id = m.category_id
        WHERE r.user_id = %s
        ORDER BY r.recommend_score DESC, r.rec_id DESC
        LIMIT %s
        """,
        (current_user_id(), limit),
    )
    if not rows:
        call_procedure("sp_generate_recommendations", (current_user_id(), limit))
        rows = fetch_all(
            """
            SELECT r.rec_id, r.recommend_score, r.algorithm_type, r.rec_reason, r.created_at,
                   m.movie_id, m.title, m.description, m.poster_url,
                   m.avg_rating, m.rating_count, m.view_count,
                   c.category_name
            FROM recommendations r
            JOIN movies m ON m.movie_id = r.movie_id
            JOIN categories c ON c.category_id = m.category_id
            WHERE r.user_id = %s
            ORDER BY r.recommend_score DESC, r.rec_id DESC
            LIMIT %s
            """,
            (current_user_id(), limit),
        )
    return jsonify({"items": rows})
