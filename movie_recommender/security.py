from functools import wraps

from flask import current_app, jsonify, request, session
from itsdangerous import BadSignature, BadTimeSignature, URLSafeTimedSerializer
from werkzeug.security import check_password_hash, generate_password_hash


def hash_password(password: str) -> str:
    return generate_password_hash(password)


def verify_password(password_hash: str, password: str) -> bool:
    return check_password_hash(password_hash, password)


def _serializer() -> URLSafeTimedSerializer:
    return URLSafeTimedSerializer(current_app.config["SECRET_KEY"], salt="movie-recsys-auth")


def make_auth_token(identity_type: str, identity_id: int) -> str:
    return _serializer().dumps({"type": identity_type, "id": int(identity_id)})


def token_identity() -> dict | None:
    header = request.headers.get("Authorization", "")
    if not header.startswith("Bearer "):
        return None
    token = header.removeprefix("Bearer ").strip()
    if not token:
        return None
    try:
        data = _serializer().loads(token, max_age=60 * 60 * 24 * 14)
    except (BadSignature, BadTimeSignature):
        return None
    if data.get("type") not in {"user", "admin"} or not data.get("id"):
        return None
    return data


def current_user_id() -> int | None:
    if session.get("user_id"):
        return session.get("user_id")
    identity = token_identity()
    if identity and identity["type"] == "user":
        return identity["id"]
    return None


def current_admin_id() -> int | None:
    if session.get("admin_id"):
        return session.get("admin_id")
    identity = token_identity()
    if identity and identity["type"] == "admin":
        return identity["id"]
    return None


def login_required(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if not current_user_id():
            return jsonify({"error": "unauthorized", "message": "请先登录用户账号"}), 401
        return func(*args, **kwargs)

    return wrapper


def admin_required(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if not current_admin_id():
            return jsonify({"error": "forbidden", "message": "需要管理员权限"}), 403
        return func(*args, **kwargs)

    return wrapper
