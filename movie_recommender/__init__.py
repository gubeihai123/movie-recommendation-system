from flask import Flask, jsonify, render_template, request

from .admin import bp as admin_bp
from .auth import bp as auth_bp
from .config import Config
from .movies import bp as movies_bp
from .recommendations import bp as recommendations_bp


def create_app() -> Flask:
    app = Flask(__name__, template_folder="../templates", static_folder="../static")
    app.config.from_object(Config)

    app.register_blueprint(auth_bp)
    app.register_blueprint(movies_bp)
    app.register_blueprint(recommendations_bp)
    app.register_blueprint(admin_bp)

    @app.after_request
    def add_cors_headers(response):
        origin = request.headers.get("Origin", "")
        if origin in app.config["CORS_ORIGINS"]:
            response.headers["Access-Control-Allow-Origin"] = origin
            response.headers["Access-Control-Allow-Credentials"] = "true"
            response.headers["Vary"] = "Origin"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
        response.headers["Access-Control-Allow-Methods"] = "GET,POST,PUT,DELETE,OPTIONS"
        return response

    @app.get("/api/health")
    def health():
        return jsonify({"status": "ok", "database": app.config["DB_NAME"]})

    @app.get("/")
    def frontend():
        return render_template("index.html")

    @app.errorhandler(404)
    def not_found(_error):
        return jsonify({"error": "not_found", "message": "接口不存在"}), 404

    @app.errorhandler(500)
    def internal_error(error):
        app.logger.exception(error)
        return jsonify({"error": "internal_error", "message": "服务器内部错误"}), 500

    return app
