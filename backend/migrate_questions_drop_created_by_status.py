#!/usr/bin/env python3
"""
一次性数据库迁移脚本：
从 questions 表中移除 created_by / status 两个字段。

当前项目默认使用 SQLite（backend/app/physics.db）。

用法：
  python migrate_questions_drop_created_by_status.py

说明：
  - SQLite 不支持直接 DROP COLUMN，本脚本会通过“新建表 -> 拷贝数据 -> 替换表”的方式迁移。
  - 如果字段不存在，会直接跳过。
"""

from __future__ import annotations

import os
import sqlite3
from typing import List, Tuple


DROP_COLUMNS = {"created_by", "status"}


def _get_questions_columns(conn: sqlite3.Connection) -> List[Tuple]:
    # cid, name, type, notnull, dflt_value, pk
    return conn.execute("PRAGMA table_info(questions);").fetchall()


def _build_create_sql(cols: List[Tuple]) -> str:
    col_defs = []
    for cid, name, col_type, notnull, dflt_value, pk in cols:
        if name in DROP_COLUMNS:
            continue

        # 兼容空类型
        col_type = (col_type or "TEXT").strip()

        if pk:
            # SQLite 主键列通常是 INTEGER PRIMARY KEY
            # 这里保留原类型并加上 PRIMARY KEY
            base = f'"{name}" {col_type} PRIMARY KEY'
        else:
            base = f'"{name}" {col_type}'
            if notnull:
                base += " NOT NULL"
            if dflt_value is not None:
                base += f" DEFAULT {dflt_value}"

        col_defs.append(base)

    return "CREATE TABLE questions_new (\n  " + ",\n  ".join(col_defs) + "\n);"


def migrate_sqlite(db_path: str) -> None:
    if not os.path.exists(db_path):
        raise FileNotFoundError(f"数据库文件不存在: {db_path}")

    conn = sqlite3.connect(db_path)
    try:
        # questions 表不存在则跳过
        row = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='questions';"
        ).fetchone()
        if not row:
            print("[SKIP] questions 表不存在")
            return

        cols = _get_questions_columns(conn)
        col_names = [c[1] for c in cols]

        if not (set(col_names) & DROP_COLUMNS):
            print("[SKIP] questions 表已不包含 created_by/status")
            return

        kept_cols = [c[1] for c in cols if c[1] not in DROP_COLUMNS]

        conn.execute("PRAGMA foreign_keys=OFF;")
        conn.execute("BEGIN;")

        # 1) 新建表
        create_sql = _build_create_sql(cols)
        conn.execute("DROP TABLE IF EXISTS questions_new;")
        conn.execute(create_sql)

        # 2) 拷贝数据
        cols_sql = ", ".join([f'"{c}"' for c in kept_cols])
        conn.execute(
            f"INSERT INTO questions_new ({cols_sql}) SELECT {cols_sql} FROM questions;"
        )

        # 3) 替换表
        conn.execute("DROP TABLE questions;")
        conn.execute("ALTER TABLE questions_new RENAME TO questions;")

        conn.execute("COMMIT;")
        conn.execute("PRAGMA foreign_keys=ON;")
        print("[OK] SQLite questions 表迁移完成")
    except Exception:
        conn.execute("ROLLBACK;")
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    here = os.path.dirname(os.path.abspath(__file__))
    db_path = os.path.join(here, "app", "physics.db")
    migrate_sqlite(db_path)
