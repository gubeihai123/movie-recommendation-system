import json
import time
import urllib.parse
import urllib.request
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / "data" / "real_movies.json"
HEADERS = {"User-Agent": "MovieMindCF/1.0 (academic course project)"}

ZH_TITLE_BY_SOURCE = {
    "Dune (2021 film)": "沙丘 (2021年电影)",
    "The Martian (film)": "火星救援",
    "Arrival (film)": "降临 (电影)",
    "Mad Max: Fury Road": "疯狂的麦克斯：狂暴之路",
    "Gladiator (2000 film)": "角斗士 (电影)",
    "John Wick (film)": "疾速追杀",
    "Top Gun: Maverick": "壮志凌云：独行侠",
    "Raiders of the Lost Ark": "夺宝奇兵",
    "The Grand Budapest Hotel": "布达佩斯大饭店",
    "Titanic (1997 film)": "泰坦尼克号 (1997年电影)",
    "Casablanca (film)": "北非谍影",
    "Spirited Away": "千与千寻",
    "Coco (2017 film)": "寻梦环游记",
    "Inside Out (2015 film)": "头脑特工队",
    "Up (2009 film)": "飞屋环游记",
    "Finding Nemo": "海底总动员",
    "Frozen (2013 film)": "冰雪奇缘",
    "Spider-Man: Into the Spider-Verse": "蜘蛛侠：平行宇宙",
    "Se7en": "七宗罪 (电影)",
    "Shutter Island": "禁闭岛",
    "Memento (film)": "记忆碎片",
    "Gone Girl (film)": "消失的爱人",
    "The Silence of the Lambs (film)": "沉默的羔羊 (电影)",
    "Knives Out": "利刃出鞘",
}


def fetch_summary(title: str) -> dict | None:
    url = "https://zh.wikipedia.org/api/rest_v1/page/summary/" + urllib.parse.quote(title)
    for attempt in range(3):
        try:
            request = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(request, timeout=14) as response:
                return json.load(response)
        except Exception:
            time.sleep(0.6 * (attempt + 1))
    return None


def main() -> None:
    rows = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    updated = 0
    for row in rows:
        zh_title = ZH_TITLE_BY_SOURCE.get(row["source_title"])
        if not zh_title:
            continue
        data = fetch_summary(zh_title)
        if not data or not data.get("extract"):
            continue
        row["title"] = data.get("title") or row["title"]
        row["description"] = data["extract"].strip().replace("\n", " ")[:420]
        row["poster_url"] = (
            data.get("thumbnail", {}).get("source")
            or data.get("originalimage", {}).get("source")
            or row["poster_url"]
        )
        row["source_url"] = (
            data.get("content_urls", {}).get("desktop", {}).get("page")
            or row.get("source_url", "")
        )
        updated += 1
    DATA_PATH.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"updated: {updated}")


if __name__ == "__main__":
    main()
