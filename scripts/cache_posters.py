import argparse
import os
import re
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import mysql.connector
from dotenv import load_dotenv


ROOT = Path(__file__).resolve().parents[1]
POSTER_DIR = ROOT / "static" / "posters"
USER_AGENT = "MovieMindCF/1.0 (academic course project)"


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


def safe_filename(movie_id: int, suffix: str) -> str:
    return f"movie_{movie_id:03d}{suffix}"


def pick_extension(content_type: str, fallback_url: str) -> str:
    content_type = (content_type or "").lower()
    if "jpeg" in content_type or "jpg" in content_type:
        return ".jpg"
    if "png" in content_type:
        return ".png"
    if "webp" in content_type:
        return ".webp"
    match = re.search(r"\.(jpg|jpeg|png|webp)(?:[?#]|$)", fallback_url.lower())
    if match:
        return ".jpg" if match.group(1) == "jpeg" else f".{match.group(1)}"
    return ".jpg"


def existing_cached_poster(movie_id: int) -> str | None:
    for ext in (".jpg", ".png", ".webp"):
        path = POSTER_DIR / safe_filename(movie_id, ext)
        if path.exists() and path.stat().st_size >= 3000:
            return f"/static/posters/{path.name}"
    return None


def download_poster(movie: dict, timeout: int) -> tuple[bool, str, str]:
    movie_id = int(movie["movie_id"])
    cached = existing_cached_poster(movie_id)
    if cached:
        return True, cached, "already_cached"

    url = movie.get("poster_url") or ""
    if not url.startswith("http"):
        return False, url, "not_remote"
    try:
        request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(request, timeout=timeout) as response:
            content_type = response.headers.get("Content-Type", "")
            if "svg" in content_type.lower():
                return False, url, "svg"
            data = response.read(2_500_000)
            if len(data) < 3000:
                return False, url, "too_small"
            ext = pick_extension(content_type, response.geturl() or url)
    except Exception as error:
        return False, url, type(error).__name__

    file_name = safe_filename(movie_id, ext)
    path = POSTER_DIR / file_name
    path.write_bytes(data)
    return True, f"/static/posters/{file_name}", "cached"


def main():
    parser = argparse.ArgumentParser(description="Cache real remote movie posters locally without generating fallback covers.")
    parser.add_argument("--workers", type=int, default=12)
    parser.add_argument("--timeout", type=int, default=12)
    args = parser.parse_args()

    POSTER_DIR.mkdir(parents=True, exist_ok=True)
    with connect() as conn:
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            """
            SELECT m.movie_id, m.title, m.poster_url, m.avg_rating, c.category_name
            FROM movies m
            JOIN categories c ON c.category_id = m.category_id
            WHERE m.status = 'online'
            ORDER BY m.movie_id
            """
        )
        movies = cursor.fetchall()

    results = []
    skipped = []
    with ThreadPoolExecutor(max_workers=max(1, args.workers)) as executor:
        future_map = {executor.submit(download_poster, movie, args.timeout): movie for movie in movies}
        for future in as_completed(future_map):
            movie = future_map[future]
            ok, poster_url, reason = future.result()
            if ok:
                results.append((poster_url, int(movie["movie_id"]), movie["title"]))
                print(f"{movie['movie_id']:03d} {movie['title']} -> {poster_url}")
            else:
                skipped.append((int(movie["movie_id"]), movie["title"], reason, poster_url))
                print(f"{movie['movie_id']:03d} {movie['title']} skipped: {reason}")

    if results:
        with connect() as conn:
            cursor = conn.cursor()
            cursor.executemany("UPDATE movies SET poster_url = %s WHERE movie_id = %s", [(url, mid) for url, mid, _ in results])
            cursor.executemany(
                """
                UPDATE movie_files
                SET file_path = %s, file_name = %s, file_size = 0
                WHERE movie_id = %s AND file_type = 'poster'
                """,
                [(url, Path(url).name, mid) for url, mid, _ in results],
            )
            conn.commit()

    print(f"cached: {len(results)} posters, skipped: {len(skipped)}, generated placeholders: 0")


if __name__ == "__main__":
    main()
