import argparse
import os
import shutil
import subprocess
from pathlib import Path

from dotenv import load_dotenv


ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "sql" / "schema.sql"
KNOWN_MYSQL_CLIENTS = [
    Path(r"D:\mysql-8.0.27-winx64\bin\mysql.exe"),
    Path(r"C:\Program Files\MySQL\MySQL Workbench 8.0 CE\mysql.exe"),
]


def find_mysql_client() -> str:
    env_client = os.getenv("MYSQL_CLIENT")
    if env_client and Path(env_client).exists():
        return env_client
    path_client = shutil.which("mysql")
    if path_client:
        return path_client
    for candidate in KNOWN_MYSQL_CLIENTS:
        if candidate.exists():
            return str(candidate)
    raise FileNotFoundError("未找到 mysql.exe，请设置 MYSQL_CLIENT 环境变量")


def main() -> None:
    parser = argparse.ArgumentParser(description="Initialize MySQL database schema.")
    parser.add_argument("--reset", action="store_true", help="Drop database before creating schema.")
    args = parser.parse_args()

    load_dotenv(ROOT / ".env")
    host = os.getenv("DB_HOST", "127.0.0.1")
    port = os.getenv("DB_PORT", "3306")
    user = os.getenv("DB_USER", "root")
    password = os.getenv("DB_PASSWORD", "root")
    database = os.getenv("DB_NAME", "movie_recommendation_db")

    sql = SCHEMA_PATH.read_text(encoding="utf-8")
    if database != "movie_recommendation_db":
        sql = sql.replace("movie_recommendation_db", database)
    if args.reset:
        sql = f"DROP DATABASE IF EXISTS `{database}`;\n" + sql

    cmd = [
        find_mysql_client(),
        "--default-character-set=utf8mb4",
        "-h",
        host,
        "-P",
        port,
        "-u",
        user,
        f"-p{password}",
    ]
    result = subprocess.run(cmd, input=sql, text=True, encoding="utf-8", cwd=ROOT)
    if result.returncode != 0:
        raise SystemExit(result.returncode)
    print(f"数据库结构已初始化：{database}")


if __name__ == "__main__":
    main()
