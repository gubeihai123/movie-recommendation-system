import os
from urllib.parse import urlsplit

from dotenv import load_dotenv


load_dotenv()


def _normalize_origin(origin: str) -> str:
    parsed = urlsplit(origin.strip())
    if parsed.scheme and parsed.netloc:
        return f"{parsed.scheme}://{parsed.netloc}"
    return origin.strip().rstrip("/")


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-movie-recommendation-secret")
    DB_HOST = os.getenv("DB_HOST", "127.0.0.1")
    DB_PORT = int(os.getenv("DB_PORT", "3306"))
    DB_USER = os.getenv("DB_USER", "root")
    DB_PASSWORD = os.getenv("DB_PASSWORD", "root")
    DB_NAME = os.getenv("DB_NAME", "movie_recommendation_db")
    CORS_ORIGINS = sorted({
        _normalize_origin(origin)
        for origin in os.getenv("CORS_ORIGINS", "http://127.0.0.1:5000,http://localhost:5000").split(",")
        if origin.strip()
    })
    SESSION_COOKIE_SAMESITE = os.getenv("SESSION_COOKIE_SAMESITE", "Lax")
    SESSION_COOKIE_SECURE = os.getenv("SESSION_COOKIE_SECURE", "0") == "1"
    JSON_AS_ASCII = False
