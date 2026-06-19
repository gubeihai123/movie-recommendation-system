import os
import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"


def render_static_index() -> str:
    html = (ROOT / "templates" / "index.html").read_text(encoding="utf-8")
    html = html.replace("{{ url_for('static', filename='css/app.css') }}", "static/css/app.css")
    html = html.replace("{{ url_for('static', filename='js/tsparticles.bundle.min.js') }}", "static/js/tsparticles.bundle.min.js")
    html = html.replace("{{ url_for('static', filename='js/app.js') }}", "static/js/app.js")
    html = html.replace('<script src="static/js/app.js', '<script src="static/js/config.js"></script>\n  <script src="static/js/app.js')
    return html


def copy_tree(src: Path, dst: Path) -> None:
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(src, dst)


def main() -> None:
    DOCS.mkdir(exist_ok=True)
    config_path = DOCS / "static" / "js" / "config.js"
    existing_config = config_path.read_text(encoding="utf-8") if config_path.exists() else ""
    api_base = os.getenv("MOVIE_API_BASE")
    copy_tree(ROOT / "static" / "css", DOCS / "static" / "css")
    copy_tree(ROOT / "static" / "js", DOCS / "static" / "js")
    if (ROOT / "static" / "images").exists():
        copy_tree(ROOT / "static" / "images", DOCS / "static" / "images")
    (DOCS / "index.html").write_text(render_static_index(), encoding="utf-8")
    if api_base:
        config = f'// GitHub Pages 前端配置：部署 Render 后端后，把这里改成你的后端公网地址。\nwindow.MOVIE_API_BASE = "{api_base.rstrip("/")}";\n'
    else:
        config = existing_config or '// GitHub Pages 前端配置：部署 Render 后端后，把这里改成你的后端公网地址。\nwindow.MOVIE_API_BASE = "https://YOUR_RENDER_SERVICE.onrender.com";\n'
    config_path.write_text(config, encoding="utf-8")
    print(f"exported GitHub Pages frontend -> {DOCS}")


if __name__ == "__main__":
    main()
