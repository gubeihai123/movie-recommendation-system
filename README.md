# 基于协同过滤的电影推荐系统后端

这是课程项目的 Python + MySQL 后端，实现了用户、管理员、电影资产、行为追踪和推荐接口。

## 环境

- Python 3.12
- MySQL 8.0
- 默认数据库连接：`root/root@127.0.0.1:3306`

## 初始化

```powershell
pip install -r requirements.txt
Copy-Item .env.example .env
python scripts/init_db.py --reset
python scripts/seed_data.py
python app.py
```

启动后访问：

```text
http://127.0.0.1:5000/api/health
```

## 默认账号

- 普通用户：`user001` / `password123`
- 管理员：`admin` / `root`

## 真实电影数据

`data/real_movies.json` 保存了真实电影元数据，包含片名、分类、简介、海报 URL 和来源页面。当前数据集包含 300 部真实电影，数据来自 Wikidata、中文 Wikipedia 摘要与 Wikimedia 图片接口，`scripts/seed_data.py` 会从该文件导入真实电影，并生成评分、收藏、浏览等行为数据。

如需重新批量抓取电影数据，可运行：

```powershell
python scripts/fetch_wikidata_movies.py --target 300 --limit 1000 --min-sitelinks 5
python scripts/seed_data.py
```

如果希望扩大电影库数量，可以提高 `--target` 和 `--limit`，例如 `--target 500 --limit 1600`。抓取后必须再次运行 `python scripts/seed_data.py` 才会写入 MySQL。当前前端会按需懒加载远程真实海报，避免首页一次性加载大量图片；若后续想追求更快速度，可以选择运行 `scripts/cache_posters.py` 将远程海报缓存到本地。缓存脚本只下载真实远程图片，不生成替代封面；下载失败的电影会继续保留原远程地址。

如需重新刷新部分中文简介，可运行：

```powershell
python scripts/refresh_zh_metadata.py
python scripts/seed_data.py
```

如需强制重建 ItemCF 相似度，可登录管理员后调用后台重建接口，或访问推荐接口时追加 `rebuild=1`：

```text
GET /api/recommendations?refresh=1&rebuild=1&limit=10
```

## 主要接口

### 认证

- `POST /api/auth/register`
- `POST /api/auth/login`
- `POST /api/auth/admin/login`
- `POST /api/auth/logout`
- `GET /api/auth/me`

### 电影与行为

- `GET /api/categories`
- `GET /api/movies?q=&category_id=&page=&page_size=`
- `GET /api/movies/<movie_id>`
- `POST /api/movies/<movie_id>/browse`
- `POST /api/movies/<movie_id>/rating`
- `DELETE /api/movies/<movie_id>/rating`
- `POST /api/movies/<movie_id>/favorite`
- `DELETE /api/movies/<movie_id>/favorite`
- `GET /api/me/behaviors`

### 推荐

- `GET /api/recommendations/hot`
- `POST /api/recommendations/generate`
- `GET /api/recommendations?refresh=1&limit=10`

### 管理员

- `GET /api/admin/stats`
- `POST /api/admin/categories`
- `PUT /api/admin/categories/<category_id>`
- `POST /api/admin/movies`
- `PUT /api/admin/movies/<movie_id>`
- `DELETE /api/admin/movies/<movie_id>`
- `POST /api/admin/movies/<movie_id>/files`
- `POST /api/admin/rebuild-similarity`

## 数据库对象

`sql/schema.sql` 包含课程验收需要的建库内容：

- 10 张表：`users`、`admins`、`categories`、`movies`、`ratings`、`favorites`、`browse_history`、`recommendations`、`movie_files`、`item_similarity`
- 主键、外键、唯一约束、CHECK 约束
- 复合索引
- 视图：`v_movie_details`、`v_user_behavior_summary`、`v_hot_movies`
- 触发器：评分统计自动刷新、浏览量自动累加
- 函数：交互分数、热门分数
- 存储过程：刷新评分统计、计算 ItemCF 相似度、生成推荐结果

## 云端部署

本项目完整运行需要三部分：

- GitHub Pages：托管静态前端，目录为 `docs/`
- Render：托管 Flask 后端 API
- 云 MySQL：托管数据库

### 1. 准备云 MySQL

创建云 MySQL 后，拿到以下连接信息：

```text
DB_HOST=
DB_PORT=
DB_USER=
DB_PASSWORD=
DB_NAME=movie_recommendation_db
```

本地临时把 `.env` 改成云数据库连接，然后初始化云数据库：

```powershell
python scripts/init_db.py --reset
python scripts/seed_data.py
python scripts/cache_posters.py --workers 4 --timeout 25
```

`cache_posters.py` 只缓存真实远程图片，失败会保留原远程地址，不会生成替代封面。

### 2. 部署后端到 Render

Render Web Service 配置：

```text
Build Command: pip install -r requirements.txt
Start Command: gunicorn app:app
```

Render 环境变量：

```text
DB_HOST=云数据库地址
DB_PORT=云数据库端口
DB_USER=云数据库用户名
DB_PASSWORD=云数据库密码
DB_NAME=movie_recommendation_db
SECRET_KEY=一串长随机字符串
FLASK_DEBUG=0
CORS_ORIGINS=https://你的GitHub用户名.github.io
SESSION_COOKIE_SAMESITE=None
SESSION_COOKIE_SECURE=1
```

部署成功后检查：

```text
https://你的Render服务地址/api/health
```

### 3. 生成 GitHub Pages 前端

先导出静态前端：

```powershell
python scripts/export_pages.py
```

然后编辑：

```text
docs/static/js/config.js
```

把占位地址改成 Render 后端地址：

```js
window.MOVIE_API_BASE = "https://你的Render服务地址";
```

### 4. 开启 GitHub Pages

GitHub 仓库设置：

```text
Settings -> Pages -> Deploy from a branch
Branch: main
Folder: /docs
```

前端访问地址通常是：

```text
https://你的GitHub用户名.github.io/仓库名/
```

### 5. 部署后测试

依次测试：

- `GET /api/health` 能返回 `status: ok`
- GitHub Pages 首页能打开
- 电影库能加载
- 注册、登录能成功
- 评分、收藏、浏览能写入云数据库
- 智能推荐能生成
- 管理员 `admin/root` 能进入后台
