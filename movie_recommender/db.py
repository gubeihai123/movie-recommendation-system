from contextlib import contextmanager
from typing import Any

import mysql.connector
from flask import current_app


@contextmanager
def get_connection():
    conn = mysql.connector.connect(
        host=current_app.config["DB_HOST"],
        port=current_app.config["DB_PORT"],
        user=current_app.config["DB_USER"],
        password=current_app.config["DB_PASSWORD"],
        database=current_app.config["DB_NAME"],
        charset="utf8mb4",
        collation="utf8mb4_0900_ai_ci",
        autocommit=False,
    )
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def fetch_all(sql: str, params: tuple[Any, ...] | None = None) -> list[dict[str, Any]]:
    with get_connection() as conn:
        cursor = conn.cursor(dictionary=True)
        cursor.execute(sql, params or ())
        rows = cursor.fetchall()
        cursor.close()
        return rows


def fetch_one(sql: str, params: tuple[Any, ...] | None = None) -> dict[str, Any] | None:
    with get_connection() as conn:
        cursor = conn.cursor(dictionary=True)
        cursor.execute(sql, params or ())
        row = cursor.fetchone()
        cursor.close()
        return row


def execute(sql: str, params: tuple[Any, ...] | None = None) -> int:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(sql, params or ())
        rowcount = cursor.rowcount
        cursor.close()
        return rowcount


def execute_many(sql: str, rows: list[tuple[Any, ...]]) -> int:
    if not rows:
        return 0
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.executemany(sql, rows)
        rowcount = cursor.rowcount
        cursor.close()
        return rowcount


def call_procedure(name: str, args: tuple[Any, ...] = ()) -> None:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.callproc(name, args)
        for result in cursor.stored_results():
            result.fetchall()
        cursor.close()
