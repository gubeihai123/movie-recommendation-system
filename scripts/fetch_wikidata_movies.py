import argparse
import json
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_PATH = ROOT / "data" / "real_movies.json"
USER_AGENT = "MovieMindCF/1.0 (academic course project)"

BANNED_KEYWORDS = {
    "成人", "情色", "色情", "性爱", "av", "porn", "pornographic",
    "erotic", "hentai", "sexploitation", "softcore",
}

CATEGORY_KEYWORDS = [
    ("纪录片", ["纪录", "documentary", "docudrama"]),
    ("动画", ["动画", "anime", "animation", "animated", "儿童", "children"]),
    ("悬疑", ["悬疑", "推理", "犯罪", "惊悚", "thriller", "mystery", "crime", "noir", "detective", "slasher", "horror"]),
    ("科幻", ["科幻", "science fiction", "cyberpunk", "space", "superhero"]),
    ("动作", ["动作", "冒险", "战争", "武侠", "action", "adventure", "war", "martial"]),
    ("爱情", ["爱情", "浪漫", "romance", "romantic"]),
    ("喜剧", ["喜剧", "幽默", "comedy", "comic", "satire"]),
    ("剧情", ["剧情", "drama", "historical", "biographical", "epic"]),
]


def request_json(url: str, timeout: int = 60) -> dict:
    last_error: Exception | None = None
    for attempt in range(5):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(req, timeout=timeout) as response:
                return json.load(response)
        except urllib.error.HTTPError as error:
            last_error = error
            if error.code not in {429, 500, 502, 503, 504}:
                raise
            time.sleep(2.0 * (attempt + 1))
        except Exception as error:
            last_error = error
            time.sleep(1.0 * (attempt + 1))
    raise last_error or RuntimeError("request failed")


def fetch_wikidata_candidates(limit: int, min_sitelinks: int) -> list[dict]:
    query = f"""
SELECT ?film ?filmLabel ?filmDescription ?article (SAMPLE(?image) AS ?image)
       (GROUP_CONCAT(DISTINCT ?genreLabel; separator="|") AS ?genres)
       ?sitelinks WHERE {{
  ?film wdt:P31/wdt:P279* wd:Q11424;
        wdt:P18 ?image;
        wikibase:sitelinks ?sitelinks.
  ?article schema:about ?film;
           schema:isPartOf <https://zh.wikipedia.org/>.
  FILTER(?sitelinks >= {min_sitelinks})
  OPTIONAL {{
    ?film wdt:P136 ?genre.
    ?genre rdfs:label ?genreLabel
    FILTER(LANG(?genreLabel) IN ("zh", "en"))
  }}
  SERVICE wikibase:label {{ bd:serviceParam wikibase:language "zh,en". }}
}}
GROUP BY ?film ?filmLabel ?filmDescription ?article ?sitelinks
ORDER BY DESC(?sitelinks)
LIMIT {limit}
"""
    url = "https://query.wikidata.org/sparql?" + urllib.parse.urlencode(
        {"query": query, "format": "json"}
    )
    data = request_json(url, timeout=90)
    rows = []
    for item in data["results"]["bindings"]:
        article_url = item["article"]["value"]
        page_title = urllib.parse.unquote(article_url.rsplit("/", 1)[-1]).replace("_", " ")
        image_url = item["image"]["value"].replace("http://", "https://")
        row = {
            "wikidata_id": item["film"]["value"].rsplit("/", 1)[-1],
            "source_title": page_title,
            "title": item["filmLabel"]["value"],
            "wikidata_description": item.get("filmDescription", {}).get("value", ""),
            "article_title": page_title,
            "source_url": article_url,
            "poster_url": image_url,
            "genres": item.get("genres", {}).get("value", ""),
            "sitelinks": int(item["sitelinks"]["value"]),
        }
        text = f"{row['title']} {row['genres']}".lower()
        if any(keyword in text for keyword in BANNED_KEYWORDS):
            continue
        rows.append(row)
    return rows


def chunks(rows: list[dict], size: int):
    for index in range(0, len(rows), size):
        yield rows[index:index + size]


def fetch_wikipedia_extracts(candidates: list[dict]) -> dict[str, dict]:
    page_data: dict[str, dict] = {}
    for batch in chunks(candidates, 25):
        titles = "|".join(row["article_title"] for row in batch)
        params = {
            "action": "query",
            "format": "json",
            "prop": "extracts|pageimages|info",
            "exintro": "1",
            "explaintext": "1",
            "pithumbsize": "600",
            "inprop": "url",
            "redirects": "1",
            "titles": titles,
            "origin": "*",
        }
        url = "https://zh.wikipedia.org/w/api.php?" + urllib.parse.urlencode(params)
        try:
            data = request_json(url, timeout=60)
        except Exception as error:
            print(f"skip wikipedia batch: {error}")
            continue
        normalized = {
            item["from"]: item["to"]
            for item in data.get("query", {}).get("normalized", [])
        }
        redirects = {
            item["from"]: item["to"]
            for item in data.get("query", {}).get("redirects", [])
        }
        pages = data.get("query", {}).get("pages", {})
        by_title = {page.get("title"): page for page in pages.values()}
        for row in batch:
            title = row["article_title"]
            resolved = redirects.get(normalized.get(title, title), normalized.get(title, title))
            page = by_title.get(resolved) or by_title.get(title)
            if page:
                page_data[title] = page
        time.sleep(0.8)
    return page_data


def classify_movie(row: dict, extract: str) -> str:
    text = f"{row.get('genres', '')} {row.get('title', '')} {extract[:120]}".lower()
    for category, keywords in CATEGORY_KEYWORDS:
        if any(keyword.lower() in text for keyword in keywords):
            return category
    return "剧情"


def build_dataset(limit: int, min_sitelinks: int, target: int) -> list[dict]:
    candidates = fetch_wikidata_candidates(limit, min_sitelinks)
    pages = fetch_wikipedia_extracts(candidates)
    movies = []
    seen_titles = set()
    for row in candidates:
        page = pages.get(row["article_title"])
        extract = (page.get("extract") or "").strip().replace("\n", " ") if page else ""
        if len(extract) < 60:
            fallback = row.get("wikidata_description", "").strip()
            genres = row.get("genres", "").replace("|", "、")
            if not fallback:
                continue
            extract = f"{row['title']}：{fallback}。类型信息：{genres}。"
        text = f"{row['title']} {row['genres']} {extract[:200]}".lower()
        if any(keyword in text for keyword in BANNED_KEYWORDS):
            continue
        title = page.get("title") if page else row["title"]
        if title in seen_titles:
            continue
        seen_titles.add(title)
        poster_url = (
            (page or {}).get("thumbnail", {}).get("source")
            or row["poster_url"]
        ).replace("http://", "https://")
        movies.append(
            {
                "source_title": row["source_title"],
                "wikidata_id": row["wikidata_id"],
                "title": title,
                "category": classify_movie(row, extract),
                "description": extract[:520],
                "poster_url": poster_url,
                "source_url": (page or {}).get("fullurl") or row["source_url"],
                "genres": row.get("genres", ""),
                "sitelinks": row.get("sitelinks", 0),
            }
        )
        if len(movies) >= target:
            break
    return movies


def main() -> None:
    parser = argparse.ArgumentParser(description="Fetch real movie metadata from Wikidata/Wikipedia.")
    parser.add_argument("--limit", type=int, default=900, help="SPARQL candidate limit.")
    parser.add_argument("--target", type=int, default=320, help="Target imported movie count.")
    parser.add_argument("--min-sitelinks", type=int, default=5, help="Minimum Wikidata sitelinks.")
    args = parser.parse_args()

    OUTPUT_PATH.parent.mkdir(exist_ok=True)
    movies = build_dataset(args.limit, args.min_sitelinks, args.target)
    if len(movies) < min(args.target, 200):
        raise SystemExit(f"只抓到 {len(movies)} 部，低于可用阈值。可降低 --min-sitelinks 或增大 --limit。")
    OUTPUT_PATH.write_text(json.dumps(movies, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"saved: {len(movies)} movies -> {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
