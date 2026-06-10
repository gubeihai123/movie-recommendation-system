from functools import wraps

from flask import jsonify, session
from werkzeug.security import check_password_hash, generate_password_hash


def hash_password(password: str) -> str:
    return generate_password_hash(password)


def verify_password(password_hash: str, password: str) -> bool:
    return check_password_hash(password_hash, password)


def current_user_id() -> int | None:
    return session.get("user_id")


def current_admin_id() -> int | None:
    return session.get("admin_id")


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

