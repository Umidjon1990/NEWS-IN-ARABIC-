"""Shared helpers: logging, configuration loading, environment validation."""

from __future__ import annotations

import logging
import os
import re
from dataclasses import dataclass, field
from typing import Any

import yaml
from dotenv import load_dotenv


def setup_logging(level: int = logging.INFO) -> logging.Logger:
    """Configure root logging once and return a module logger."""
    logging.basicConfig(
        level=level,
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    # Silence overly chatty third-party loggers.
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("apscheduler").setLevel(logging.WARNING)
    return logging.getLogger("arabic_tech_news_bot")


logger = logging.getLogger("arabic_tech_news_bot")


class ConfigError(RuntimeError):
    """Raised when environment variables or config files are invalid."""


@dataclass
class NewsSource:
    name: str
    url: str


@dataclass
class Settings:
    """Strongly typed view over `.env` + `config.yaml`."""

    # From .env
    bot_token: str
    channel_id: str
    admin_ids: list[int]
    openai_api_key: str
    timezone: str

    # From config.yaml
    schedule_hour: int
    schedule_minute: int
    max_items_to_check: int
    sources: list[NewsSource] = field(default_factory=list)
    min_words: int = 50
    max_words: int = 70
    add_harakat: bool = True
    level: str = "A2-B1"
    language: str = "Arabic"


def _parse_admin_ids(raw: str) -> list[int]:
    ids: list[int] = []
    for piece in raw.split(","):
        piece = piece.strip()
        if not piece:
            continue
        if not re.fullmatch(r"-?\d+", piece):
            raise ConfigError(f"ADMIN_IDS contains a non-numeric value: {piece!r}")
        ids.append(int(piece))
    return ids


def load_config(path: str = "config.yaml") -> dict[str, Any]:
    """Load YAML configuration from disk."""
    if not os.path.exists(path):
        raise ConfigError(f"Config file not found: {path}")
    with open(path, "r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    if not isinstance(data, dict):
        raise ConfigError("config.yaml must contain a mapping at the top level")
    return data


def load_settings(
    config_path: str = "config.yaml", env_path: str | None = ".env"
) -> Settings:
    """Validate `.env` and `config.yaml`, returning a combined Settings object.

    Raises ConfigError with a clear message if anything required is missing.
    """
    if env_path and os.path.exists(env_path):
        load_dotenv(env_path)
    else:
        load_dotenv()  # fall back to process environment

    bot_token = os.getenv("BOT_TOKEN", "").strip()
    channel_id = os.getenv("CHANNEL_ID", "").strip()
    admin_ids_raw = os.getenv("ADMIN_IDS", "").strip()
    openai_api_key = os.getenv("OPENAI_API_KEY", "").strip()
    timezone = os.getenv("TIMEZONE", "Asia/Tashkent").strip() or "Asia/Tashkent"

    missing = [
        name
        for name, value in (
            ("BOT_TOKEN", bot_token),
            ("CHANNEL_ID", channel_id),
            ("ADMIN_IDS", admin_ids_raw),
            ("OPENAI_API_KEY", openai_api_key),
        )
        if not value
    ]
    if missing:
        raise ConfigError(
            "Missing required environment variables: "
            + ", ".join(missing)
            + ". Copy .env.example to .env and fill it in."
        )

    # Reject obvious placeholder values copied from .env.example.
    placeholders = {
        "your_telegram_bot_token",
        "@your_channel_username_or_channel_id",
        "your_openai_api_key",
    }
    for name, value in (
        ("BOT_TOKEN", bot_token),
        ("CHANNEL_ID", channel_id),
        ("OPENAI_API_KEY", openai_api_key),
    ):
        if value in placeholders:
            raise ConfigError(
                f"{name} still has the placeholder value from .env.example. "
                "Replace it with a real value."
            )

    admin_ids = _parse_admin_ids(admin_ids_raw)
    if not admin_ids:
        raise ConfigError("ADMIN_IDS must contain at least one numeric Telegram user ID")

    cfg = load_config(config_path)
    schedule = cfg.get("schedule", {}) or {}
    news = cfg.get("news", {}) or {}
    post = cfg.get("post", {}) or {}

    raw_sources = news.get("sources", []) or []
    sources: list[NewsSource] = []
    for item in raw_sources:
        if not isinstance(item, dict) or "name" not in item or "url" not in item:
            raise ConfigError(f"Invalid news source entry: {item!r}")
        sources.append(NewsSource(name=str(item["name"]), url=str(item["url"])))
    if not sources:
        raise ConfigError("config.yaml must define at least one news source")

    # A timezone in config.yaml overrides the .env default when present.
    timezone = str(schedule.get("timezone", timezone)).strip() or timezone

    return Settings(
        bot_token=bot_token,
        channel_id=channel_id,
        admin_ids=admin_ids,
        openai_api_key=openai_api_key,
        timezone=timezone,
        schedule_hour=int(schedule.get("hour", 9)),
        schedule_minute=int(schedule.get("minute", 0)),
        max_items_to_check=int(news.get("max_items_to_check", 10)),
        sources=sources,
        min_words=int(post.get("min_words", 50)),
        max_words=int(post.get("max_words", 70)),
        add_harakat=bool(post.get("add_harakat", True)),
        level=str(post.get("level", "A2-B1")),
        language=str(post.get("language", "Arabic")),
    )


# Arabic Unicode ranges (letters + harakat) used for counting words.
_ARABIC_WORD_RE = re.compile(r"[؀-ۿݐ-ݿ]+")


def count_arabic_words(text: str) -> int:
    """Count Arabic word tokens in the given text."""
    return len(_ARABIC_WORD_RE.findall(text))


def is_within_word_range(text: str, min_words: int, max_words: int) -> bool:
    """Return True if the Arabic word count falls within [min_words, max_words]."""
    return min_words <= count_arabic_words(text) <= max_words
