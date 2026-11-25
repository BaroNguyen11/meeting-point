import json
import os
import secrets
import sqlite3
import time
from backend.core.config import settings


class SQLiteStorage:
    def __init__(self, db_path: str = settings.SQLITE_DB_PATH):
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self.db_path = db_path
        self._init_tables()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_tables(self) -> None:
        with self._connect() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS poi_enrichment (
                    poi_key TEXT PRIMARY KEY,
                    rating REAL,
                    review_count INTEGER,
                    price_level TEXT,
                    photo_url TEXT,
                    kol_videos_json TEXT,
                    enrichment_json TEXT,
                    updated_at REAL
                )
            """)
            # Tự động bổ sung cột enrichment_json nếu database cũ chưa có
            cols = [r["name"] for r in conn.execute("PRAGMA table_info(poi_enrichment)").fetchall()]
            if "enrichment_json" not in cols:
                conn.execute("ALTER TABLE poi_enrichment ADD COLUMN enrichment_json TEXT")

            conn.execute("""
                CREATE TABLE IF NOT EXISTS shared_rooms (
                    room_id TEXT PRIMARY KEY,
                    payload_json TEXT NOT NULL,
                    created_at REAL NOT NULL
                )
            """)

    def get_poi_enrichment(self, poi_key: str, ttl_seconds: int = 14 * 86400) -> dict | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM poi_enrichment WHERE poi_key = ?", (poi_key,)
            ).fetchone()
            if not row:
                return None
            if time.time() - row["updated_at"] > ttl_seconds:
                return None
            if row["enrichment_json"]:
                return json.loads(row["enrichment_json"])
            return {
                "rating": row["rating"],
                "review_count": row["review_count"],
                "price_level": row["price_level"],
                "photo_url": row["photo_url"],
                "kol_videos": json.loads(row["kol_videos_json"] or "[]"),
            }

    def save_poi_enrichment(self, poi_key: str, data: dict) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO poi_enrichment
                (poi_key, rating, review_count, price_level, photo_url, kol_videos_json, enrichment_json, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    poi_key,
                    data.get("rating"),
                    data.get("review_count"),
                    data.get("price_level"),
                    data.get("photo_url"),
                    json.dumps(data.get("kol_videos", []), ensure_ascii=False),
                    json.dumps(data, ensure_ascii=False),
                    time.time(),
                ),
            )

    def _cleanup_expired_rooms(self, conn: sqlite3.Connection, ttl_seconds: int = 6 * 3600) -> None:
        cutoff = time.time() - ttl_seconds
        conn.execute("DELETE FROM shared_rooms WHERE created_at < ?", (cutoff,))

    def create_room(self, payload: dict, ttl_seconds: int = 6 * 3600) -> str:
        room_id = secrets.token_urlsafe(6)
        with self._connect() as conn:
            self._cleanup_expired_rooms(conn, ttl_seconds)
            conn.execute(
                "INSERT INTO shared_rooms (room_id, payload_json, created_at) VALUES (?, ?, ?)",
                (room_id, json.dumps(payload, ensure_ascii=False), time.time()),
            )
        return room_id

    def get_room(self, room_id: str, ttl_seconds: int = 6 * 3600) -> dict | None:
        with self._connect() as conn:
            self._cleanup_expired_rooms(conn, ttl_seconds)
            row = conn.execute(
                "SELECT payload_json FROM shared_rooms WHERE room_id = ?", (room_id,)
            ).fetchone()
            return json.loads(row["payload_json"]) if row else None


storage = SQLiteStorage()