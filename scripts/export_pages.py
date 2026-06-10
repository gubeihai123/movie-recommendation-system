import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"


def render_static_index() -> str:
    html = (ROOT / "templates" / "index.html").read_text(encoding="utf-8")
    html = html.replace("{{ url_for('static', filename='css/app.css') }}", "static/css/app.css")
    html = html.replace("{{ url_for('static', filename='js/app.js') }}", "static/js/app.js")
    html = html.replace(
        '<script src="static/js/app.js"></script>',
        '<script src="static/js/config.js"></script>\n  <script src="static/js/app.js"></script>',
    )
    return html


def copy_tree(src: Path, dst: Path) -> None:
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(src, dst)


def main() -> None:
    DOCS.mkdir(exist_ok=True)
    copy_tree(ROOT / "static" / "css", DOCS / "static" / "css")
    copy_tree(ROOT / "static" / "js", DOCS / "static" / "js")
    (DOCS / "index.html").write_text(render_static_index(), encoding="utf-8")
    (DOCS / "static" / "js" / "config.js").write_text(
        """// GitHub Pages 前端配置：部署 Render 后端后，把这里改成你的后端公网地址。
window.MOVIE_API_BASE = "https://YOUR_RENDER_SERVICE.onrender.com";
""",
        encoding="utf-8",
    )
    print(f"exported GitHub Pages frontend -> {DOCS}")


if __name__ == "__main__":
    main()
