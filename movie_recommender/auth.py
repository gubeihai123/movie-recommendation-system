from flask import Blueprint, jsonify, request, session
from mysql.connector import IntegrityError

from .db import execute, fetch_one
from .security import hash_password, verify_password


bp = Blueprint("auth", __name__, url_prefix="/api/auth")


@bp.post("/register")
def register():
    data = request.get_json(silent=True) or {}
    username = (data.get("username") or "").strip()
    email = (data.get("email") or "").strip()
    password = data.get("password") or ""

    if len(username) < 3 or len(password) < 6 or "@" not in email:
        return jsonify({"error": "bad_request", "message": "用户名、邮箱或密码格式不正确"}), 400

    try:
        execute(
            """
            INSERT INTO users(username, email, password_hash)
            VALUES (%s, %s, %s)
            """,
            (username, email, hash_password(password)),
        )
    except IntegrityError:
        return jsonify({"error": "duplicate", "message": "用户名或邮箱已存在"}), 409

    user = fetch_one("SELECT user_id, username, email, status FROM users WHERE username = %s", (username,))
    session.clear()
    session["user_id"] = user["user_id"]
    return jsonify({"message": "注册成功", "user": user}), 201


@bp.post("/login")
def login():
    data = request.get_json(silent=True) or {}
    username = (data.get("username") or "").strip()
    password = data.get("password") or ""

    user = fetch_one(
        """
        SELECT user_id, username, email, password_hash, status
        FROM users
        WHERE username = %s
        """,
        (username,),
    )
    if not user or not verify_password(user["password_hash"], password):
        return jsonify({"error": "invalid_credentials", "message": "用户名或密码错误"}), 401
    if user["status"] != "active":
        return jsonify({"error": "disabled", "message": "账号不可用"}), 403

    session.clear()
    session["user_id"] = user["user_id"]
    return jsonify(
        {
            "message": "登录成功",
            "user": {
                "user_id": user["user_id"],
                "username": user["username"],
                "email": user["email"],
                "status": user["status"],
            },
        }
    )


@bp.post("/admin/login")
def admin_login():
    data = request.get_json(silent=True) or {}
    username = (data.get("username") or "").strip()
    password = data.get("password") or ""

    admin = fetch_one(
        """
        SELECT admin_id, username, password_hash, role
        FROM admins
        WHERE username = %s
        """,
        (username,),
    )
    if not admin or not verify_password(admin["password_hash"], password):
        return jsonify({"error": "invalid_credentials", "message": "管理员账号或密码错误"}), 401

    session.clear()
    session["admin_id"] = admin["admin_id"]
    return jsonify(
        {
            "message": "管理员登录成功",
            "admin": {
                "admin_id": admin["admin_id"],
                "username": admin["username"],
                "role": admin["role"],
            },
        }
    )


@bp.post("/logout")
def logout():
    session.clear()
    return jsonify({"message": "已退出登录"})


@bp.get("/me")
def me():
    if session.get("user_id"):
        user = fetch_one(
            "SELECT user_id, username, email, status, created_at FROM users WHERE user_id = %s",
            (session["user_id"],),
        )
        return jsonify({"type": "user", "profile": user})
    if session.get("admin_id"):
        admin = fetch_one(
            "SELECT admin_id, username, role, created_at FROM admins WHERE admin_id = %s",
            (session["admin_id"],),
        )
        return jsonify({"type": "admin", "profile": admin})
    return jsonify({"type": "guest", "profile": None})

