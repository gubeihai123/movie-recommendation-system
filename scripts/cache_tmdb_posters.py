import argparse
import json
import os
import re
import time
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

import mysql.connector
from dotenv import load_dotenv
from PIL import Image, ImageFile, ImageOps


ROOT = Path(__file__).resolve().parents[1]
POSTER_DIR = ROOT / "static" / "posters"
REAL_MOVIES_PATH = ROOT / "data" / "real_movies.json"
USER_AGENT = "Mozilla/5.0 MovieMindCF/1.0 (academic course project)"
OG_IMAGE_PATTERNS = [
    re.compile(r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)["\']', re.I),
    re.compile(r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']og:image["\']', re.I),
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


def request_bytes(url: str, timeout: int) -> tuple[bytes, str, str]:
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept-Language": "en-US,en;q=0.9",
        },
    )
    with urllib.request.urlopen(req, timeout=timeout) as response:
        return response.read(), response.headers.get("Content-Type", ""), response.geturl()


def request_json(url: str, timeout: int = 60) -> dict[str, Any]:
    data, _content_type, _final_url = request_bytes(url, timeout)
    return json.loads(data.decode("utf-8"))


def fetch_missing_movies() -> list[dict[str, Any]]:
    real_movies = json.loads(REAL_MOVIES_PATH.read_text(encoding="utf-8"))
    with connect() as conn:
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            """
            SELECT movie_id, title, poster_url
            FROM movies
            WHERE poster_url LIKE 'http%'
            ORDER BY movie_id
            """
        )
        movies = cursor.fetchall()
        cursor.close()

    rows = []
    for movie in movies:
        index = int(movie["movie_id"]) - 1
        if 0 <= index < len(real_movies):
            movie["wikidata_id"] = real_movies[index].get("wikidata_id")
            rows.append(movie)
    return [row for row in rows if row.get("wikidata_id")]


def chunks(rows: list[dict[str, Any]], size: int):
    for index in range(0, len(rows), size):
        yield rows[index:index + size]


def fetch_tmdb_ids(movies: list[dict[str, Any]]) -> dict[str, str]:
    tmdb_ids: dict[str, str] = {}
    for batch in chunks(movies, 80):
        values = " ".join(f"wd:{row['wikidata_id']}" for row in batch)
        query = f"""
SELECT ?film ?tmdb WHERE {{
  VALUES ?film {{ {values} }}
  ?film wdt:P4947 ?tmdb.
}}
"""
        url = "https://query.wikidata.org/sparql?" + urllib.parse.urlencode(
            {"query": query, "format": "json"}
        )
        data = request_json(url, timeout=90)
        for item in data.get("results", {}).get("bindings", []):
            qid = item["film"]["value"].rsplit("/", 1)[-1]
            tmdb_ids[qid] = item["tmdb"]["value"]
        time.sleep(0.6)
    return tmdb_ids


def extract_og_image(html: str) -> str | None:
    for pattern in OG_IMAGE_PATTERNS:
        match = pattern.search(html)
        if match:
            return match.group(1).replace("&amp;", "&")
    return None


def fetch_tmdb_image(tmdb_id: str, timeout: int) -> str:
    data, _content_type, _final_url = request_bytes(f"https://www.themoviedb.org/movie/{tmdb_id}", timeout)
    html = data.decode("utf-8", "ignore")
    image_url = extract_og_image(html)
    if not image_url or "media.themoviedb.org" not in image_url:
        raise ValueError("tmdb_og_image_missing")
    return image_url


def pick_extension(content_type: str, final_url: str) -> str:
    value = content_type.lower()
    if "png" in value:
        return ".png"
    if "webp" in value:
        return ".webp"
    if "jpeg" in value or "jpg" in value:
        return ".jpg"
    match = re.search(r"\.(jpg|jpeg|png|webp)(?:[?#]|$)", final_url.lower())
    if match:
        return ".jpg" if match.group(1) == "jpeg" else f".{match.group(1)}"
    return ".jpg"


def optimize_image(path: Path) -> None:
    ImageFile.LOAD_TRUNCATED_IMAGES = True
    with Image.open(path) as img:
        img = ImageOps.exif_transpose(img)
        img.thumbnail((520, 520), Image.Resampling.LANCZOS)
        if path.suffix.lower() in {".jpg", ".jpeg"}:
            if img.mode not in {"RGB", "L"}:
                img = img.convert("RGB")
            img.save(path, format="JPEG", quality=78, optimize=True, progressive=True)
        elif path.suffix.lower() == ".png":
            img.save(path, format="PNG", optimize=True)
        else:
            img.save(path, format="WEBP", quality=78, method=6)


def download_movie_poster(movie: dict[str, Any], tmdb_id: str, timeout: int) -> tuple[bool, int, str, str]:
    try:
        image_url = fetch_tmdb_image(tmdb_id, timeout)
        data, content_type, final_url = request_bytes(image_url, timeout)
        if "svg" in content_type.lower() or len(data) < 3000:
            raise ValueError("invalid_image")
        ext = pick_extension(content_type, final_url)
        path = POSTER_DIR / f"movie_{int(movie['movie_id']):03d}{ext}"
        path.write_bytes(data)
        optimize_image(path)
        return True, int(movie["movie_id"]), f"/static/posters/{path.name}", "cached_tmdb"
    except Exception as error:
        return False, int(movie["movie_id"]), movie.get("poster_url") or "", type(error).__name__


def update_database(results: list[tuple[bool, int, str, str]]) -> int:
    rows = [(url, movie_id) for ok, movie_id, url, _reason in results if ok]
    if not rows:
        return 0
    with connect() as conn:
        cursor = conn.cursor()
        cursor.executemany("UPDATE movies SET poster_url = %s WHERE movie_id = %s", rows)
        cursor.executemany(
            """
            UPDATE movie_files
            SET file_path = %s, file_name = %s, file_size = 0
            WHERE movie_id = %s AND file_type = 'poster'
            """,
            [(url, Path(url).name, movie_id) for url, movie_id in rows],
        )
        conn.commit()
        cursor.close()
    return len(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description="Cache real posters from TMDb for movies whose Wiki posters failed.")
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--timeout", type=int, default=25)
    args = parser.parse_args()

    POSTER_DIR.mkdir(parents=True, exist_ok=True)
    movies = fetch_missing_movies()
    tmdb_ids = fetch_tmdb_ids(movies)
    targets = [movie for movie in movies if movie["wikidata_id"] in tmdb_ids]

    results: list[tuple[bool, int, str, str]] = []
    with ThreadPoolExecutor(max_workers=max(1, args.workers)) as executor:
        future_map = {
            executor.submit(download_movie_poster, movie, tmdb_ids[movie["wikidata_id"]], args.timeout): movie
            for movie in targets
        }
        for future in as_completed(future_map):
            movie = future_map[future]
            ok, movie_id, url, reason = future.result()
            results.append((ok, movie_id, url, reason))
            status = "->" if ok else "skipped:"
            print(f"{movie_id:03d} {movie['title']} {status} {url if ok else reason}")

    updated = update_database(results)
    failed = len([row for row in results if not row[0]])
    print(f"tmdb ids: {len(tmdb_ids)}, attempted: {len(results)}, cached: {updated}, failed: {failed}")


if __name__ == "__main__":
    main()
