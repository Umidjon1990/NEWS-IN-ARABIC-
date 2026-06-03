"""Unit tests for the news fetcher (no real network access)."""

from __future__ import annotations

import os
import sys
from types import SimpleNamespace

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import news_fetcher  # noqa: E402
from news_fetcher import NewsFetcher, _clean  # noqa: E402
from utils import NewsSource  # noqa: E402


def test_clean_strips_html_and_whitespace():
    assert _clean("<p>Hello&nbsp;&amp; <b>world</b></p>  ") == "Hello & world"
    assert _clean("") == ""


def _fake_feed(entries):
    return SimpleNamespace(bozo=0, bozo_exception=None, entries=entries)


def test_fetch_source_parses_entries(monkeypatch):
    entries = [
        SimpleNamespace(title="AI breakthrough", link="https://ex.com/1", summary="x"),
        SimpleNamespace(title="New chip", link="https://ex.com/2", description="y"),
    ]
    monkeypatch.setattr(news_fetcher.feedparser, "parse", lambda url: _fake_feed(entries))

    fetcher = NewsFetcher([NewsSource("Test", "https://ex.com/feed")])
    items = fetcher._fetch_source(NewsSource("Test", "https://ex.com/feed"))
    assert len(items) == 2
    assert items[0].title == "AI breakthrough"
    assert items[0].url == "https://ex.com/1"


def test_failing_source_does_not_break_others(monkeypatch):
    good = NewsSource("Good", "https://good.com/feed")
    bad = NewsSource("Bad", "https://bad.com/feed")

    def fake_parse(url):
        if "bad" in url:
            raise RuntimeError("network down")
        return _fake_feed(
            [SimpleNamespace(title="OK", link="https://good.com/1", summary="s")]
        )

    monkeypatch.setattr(news_fetcher.feedparser, "parse", fake_parse)

    fetcher = NewsFetcher([bad, good])
    items = fetcher.fetch_all()
    assert len(items) == 1
    assert items[0].source == "Good"


def test_get_fresh_item_skips_duplicates(monkeypatch):
    entries = [
        SimpleNamespace(title="Old", link="https://ex.com/old", summary="s"),
        SimpleNamespace(title="New", link="https://ex.com/new", summary="s"),
    ]
    monkeypatch.setattr(news_fetcher.feedparser, "parse", lambda url: _fake_feed(entries))

    fetcher = NewsFetcher([NewsSource("Test", "https://ex.com/feed")])
    seen = {"https://ex.com/old"}
    item = fetcher.get_fresh_item(lambda url: url in seen)
    assert item is not None
    assert item.url == "https://ex.com/new"


def test_get_fresh_item_returns_none_when_all_duplicates(monkeypatch):
    entries = [SimpleNamespace(title="Old", link="https://ex.com/old", summary="s")]
    monkeypatch.setattr(news_fetcher.feedparser, "parse", lambda url: _fake_feed(entries))

    fetcher = NewsFetcher([NewsSource("Test", "https://ex.com/feed")])
    assert fetcher.get_fresh_item(lambda url: True) is None


def test_entries_without_title_or_url_are_skipped(monkeypatch):
    entries = [
        SimpleNamespace(title="", link="https://ex.com/1", summary="s"),
        SimpleNamespace(title="No link", link="", summary="s"),
    ]
    monkeypatch.setattr(news_fetcher.feedparser, "parse", lambda url: _fake_feed(entries))
    fetcher = NewsFetcher([NewsSource("Test", "https://ex.com/feed")])
    assert fetcher.fetch_all() == []


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))
