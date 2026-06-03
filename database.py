"""SQLite persistence layer for sent news and generated posts."""

from __future__ import annotations

import logging
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger("arabic_tech_news_bot.database")


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


@dataclass
class GeneratedPost:
    title: str
    url: str
    source: str
    arabic_text: str


class Database:
    """Thin wrapper around SQLite with the schema this bot needs."""

    def __init__(self, path: str = "data/bot.db") -> None:
        self.path = path
        # Allow use from the scheduler thread and handlers.
        import os

        directory = os.path.dirname(path)
        if directory:
            os.makedirs(directory, exist_ok=True)
        self._conn = sqlite3.connect(path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._create_tables()

    def _create_tables(self) -> None:
        with self._conn:
            self._conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS sent_news (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    url TEXT NOT NULL UNIQUE,
                    source TEXT NOT NULL,
                    sent_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS generated_posts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    url TEXT NOT NULL,
                    arabic_text TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    sent_status INTEGER NOT NULL DEFAULT 0
                );

                CREATE INDEX IF NOT EXISTS idx_sent_news_url ON sent_news(url);
                """
            )

    # ------------------------------------------------------------------
    # Duplicate detection
    # ------------------------------------------------------------------
    def is_duplicate(self, url: str) -> bool:
        """Return True if a news item with this URL was already sent."""
        cur = self._conn.execute("SELECT 1 FROM sent_news WHERE url = ? LIMIT 1", (url,))
        return cur.fetchone() is not None

    # ------------------------------------------------------------------
    # Writes
    # ------------------------------------------------------------------
    def save_generated_post(self, post: GeneratedPost, sent: bool = False) -> int:
        """Persist a generated post; returns its row id."""
        with self._conn:
            cur = self._conn.execute(
                """
                INSERT INTO generated_posts (title, url, arabic_text, created_at, sent_status)
                VALUES (?, ?, ?, ?, ?)
                """,
                (post.title, post.url, post.arabic_text, _utcnow_iso(), int(sent)),
            )
        return int(cur.lastrowid)

    def mark_post_sent(self, post_id: int) -> None:
        with self._conn:
            self._conn.execute(
                "UPDATE generated_posts SET sent_status = 1 WHERE id = ?", (post_id,)
            )

    def record_sent_news(self, post: GeneratedPost) -> None:
        """Record a successfully sent news item (idempotent on URL)."""
        with self._conn:
            self._conn.execute(
                """
                INSERT OR IGNORE INTO sent_news (title, url, source, sent_at)
                VALUES (?, ?, ?, ?)
                """,
                (post.title, post.url, post.source, _utcnow_iso()),
            )

    # ------------------------------------------------------------------
    # Reads (for /status)
    # ------------------------------------------------------------------
    def last_sent_at(self) -> Optional[str]:
        cur = self._conn.execute("SELECT MAX(sent_at) AS last FROM sent_news")
        row = cur.fetchone()
        return row["last"] if row and row["last"] else None

    def counts(self) -> dict[str, int]:
        sent = self._conn.execute("SELECT COUNT(*) AS c FROM sent_news").fetchone()["c"]
        generated = self._conn.execute(
            "SELECT COUNT(*) AS c FROM generated_posts"
        ).fetchone()["c"]
        return {"sent_news": int(sent), "generated_posts": int(generated)}

    def close(self) -> None:
        try:
            self._conn.close()
        except Exception:  # pragma: no cover - defensive
            logger.debug("Error closing database connection", exc_info=True)
