import os
import sqlite3
from typing import List, Optional, Dict, Any, Tuple

DB_NAME = "pinterest_scraper.db"
DB_PATH = os.path.join(os.path.dirname(__file__), DB_NAME)

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS pins (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pin_id TEXT NOT NULL UNIQUE,
    href TEXT,
    title TEXT,
    description TEXT,
    media_type TEXT,
    media_url TEXT,
    file_path TEXT,
    query TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""

INDEXES_SQL = [
    "CREATE INDEX IF NOT EXISTS idx_pins_pin_id ON pins(pin_id)",
    "CREATE INDEX IF NOT EXISTS idx_pins_query ON pins(query)",
]

def get_conn(db_path: Optional[str] = None) -> sqlite3.Connection:
    path = db_path or DB_PATH
    os.makedirs(os.path.dirname(path), exist_ok=True)
    conn = sqlite3.connect(path)
    conn.execute("PRAGMA journal_mode=WAL;")
    return conn


def init_db(db_path: Optional[str] = None) -> str:
    path = db_path or DB_PATH
    with get_conn(path) as conn:
        conn.execute(SCHEMA_SQL)
        for sql in INDEXES_SQL:
            conn.execute(sql)
        conn.commit()
    return path


def upsert_pin(record: Dict[str, Any], db_path: Optional[str] = None) -> None:
    with get_conn(db_path) as conn:
        conn.execute(
            """
            INSERT INTO pins (pin_id, href, title, description, media_type, media_url, file_path, query)
            VALUES (:pin_id, :href, :title, :description, :media_type, :media_url, :file_path, :query)
            ON CONFLICT(pin_id) DO UPDATE SET
                href=excluded.href,
                title=excluded.title,
                description=excluded.description,
                media_type=excluded.media_type,
                media_url=excluded.media_url,
                file_path=COALESCE(excluded.file_path, file_path),
                query=excluded.query
            ;
            """,
            record,
        )
        conn.commit()


def fetch_pins(limit: int = 100, search: Optional[str] = None, db_path: Optional[str] = None) -> List[Tuple]:
    sql = "SELECT id, pin_id, href, title, description, media_type, media_url, file_path, query, created_at FROM pins"
    params: Tuple[Any, ...] = tuple()
    if search:
        sql += " WHERE pin_id LIKE ? OR title LIKE ? OR description LIKE ? OR query LIKE ?"
        like = f"%{search}%"
        params = (like, like, like, like)
    sql += " ORDER BY id DESC LIMIT ?"
    params = params + (limit,)
    with get_conn(db_path) as conn:
        cur = conn.execute(sql, params)
        return cur.fetchall()


def update_file_path(pin_id: str, file_path: str, db_path: Optional[str] = None) -> None:
    with get_conn(db_path) as conn:
        conn.execute("UPDATE pins SET file_path=? WHERE pin_id=?", (file_path, pin_id))
        conn.commit()
