"""Fetch and select fresh technology news from RSS feeds."""

from __future__ import annotations

import html
import logging
import re
from dataclasses import dataclass
from typing import Callable, Optional

import feedparser

from utils import NewsSource

logger = logging.getLogger("arabic_tech_news_bot.news_fetcher")


@dataclass
class NewsItem:
    title: str
    url: str
    source: str
    summary: str


_TAG_RE = re.compile(r"<[^>]+>")


def _clean(text: str) -> str:
    """Strip HTML tags/entities and collapse whitespace."""
    if not text:
        return ""
    text = _TAG_RE.sub(" ", text)
    text = html.unescape(text)
    return re.sub(r"\s+", " ", text).strip()


class NewsFetcher:
    """Fetches RSS feeds and returns the first fresh, non-duplicate item."""

    def __init__(self, sources: list[NewsSource], max_items_to_check: int = 10) -> None:
        self.sources = sources
        self.max_items_to_check = max_items_to_check

    def _fetch_source(self, source: NewsSource) -> list[NewsItem]:
        """Fetch a single feed. Returns [] on any failure (logged)."""
        try:
            parsed = feedparser.parse(source.url)
        except Exception:  # network or parser error
            logger.exception("Failed to fetch source %s (%s)", source.name, source.url)
            return []

        if getattr(parsed, "bozo", 0) and not parsed.entries:
            logger.warning(
                "Source %s returned no usable entries (bozo=%s)",
                source.name,
                getattr(parsed, "bozo_exception", "unknown"),
            )
            return []

        items: list[NewsItem] = []
        for entry in parsed.entries[: self.max_items_to_check]:
            title = _clean(getattr(entry, "title", ""))
            url = getattr(entry, "link", "") or ""
            summary = _clean(
                getattr(entry, "summary", "") or getattr(entry, "description", "")
            )
            if not title or not url:
                continue
            items.append(
                NewsItem(title=title, url=url, source=source.name, summary=summary)
            )
        logger.info("Fetched %d items from %s", len(items), source.name)
        return items

    def fetch_all(self) -> list[NewsItem]:
        """Fetch from every source; a failing source never stops the others."""
        all_items: list[NewsItem] = []
        for source in self.sources:
            all_items.extend(self._fetch_source(source))
        return all_items

    def get_fresh_item(
        self, is_duplicate: Callable[[str], bool]
    ) -> Optional[NewsItem]:
        """Return the first item whose URL is not already in the database.

        `is_duplicate` is typically Database.is_duplicate.
        """
        for item in self.fetch_all():
            try:
                if is_duplicate(item.url):
                    continue
            except Exception:
                logger.exception("Duplicate check failed for %s", item.url)
                continue
            logger.info("Selected fresh item: %s (%s)", item.title, item.source)
            return item
        logger.warning("No fresh (non-duplicate) news items found across all sources")
        return None
