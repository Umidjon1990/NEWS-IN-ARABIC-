"""Unit tests for the AI generator's validation logic (no real API calls)."""

from __future__ import annotations

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ai_generator import AIGenerationError, AIGenerator  # noqa: E402
from news_fetcher import NewsItem  # noqa: E402
from utils import count_arabic_words  # noqa: E402

ITEM = NewsItem(
    title="New app",
    url="https://example.com/news",
    source="TechCrunch",
    summary="A new app launched.",
)

# ~55 Arabic words with harakat, valid format.
VALID_BODY = " ".join(["تَطْبِيقٌ"] * 55)
VALID_POST = (
    "📰 العُنْوَانُ:\n"
    "تَطْبِيقٌ جَدِيدٌ\n\n"
    f"{VALID_BODY}\n\n"
    "🔗 المَصْدَرُ: https://example.com/news"
)


def _generator():
    # api_key is never used because we never call the real client in these tests.
    return AIGenerator(api_key="test-key", min_words=50, max_words=70)


def test_count_arabic_words():
    assert count_arabic_words("مَرْحَبًا بِكَ") == 2
    assert count_arabic_words("hello world") == 0


def test_validate_accepts_well_formed_post():
    gen = _generator()
    result = gen._validate(VALID_POST, ITEM)
    assert result.word_count >= 50
    assert "🔗" in result.arabic_text


def test_validate_rejects_empty():
    gen = _generator()
    with pytest.raises(AIGenerationError):
        gen._validate("", ITEM)


def test_validate_rejects_missing_format_markers():
    gen = _generator()
    with pytest.raises(AIGenerationError):
        gen._validate("just some plain arabic نَصٌّ", ITEM)


def test_validate_appends_missing_url():
    gen = _generator()
    body = " ".join(["كَلِمَةٌ"] * 55)
    text = f"📰 العُنْوَانُ:\nعُنْوَانٌ\n\n{body}\n\n🔗 المَصْدَرُ:"
    result = gen._validate(text, ITEM)
    assert ITEM.url in result.arabic_text


def test_validate_rejects_too_few_words():
    gen = _generator()
    body = " ".join(["كَلِمَةٌ"] * 5)
    text = f"📰 العُنْوَانُ:\nعُنْوَانٌ\n\n{body}\n\n🔗 المَصْدَرُ: {ITEM.url}"
    with pytest.raises(AIGenerationError):
        gen._validate(text, ITEM)


class _FakeMessage:
    def __init__(self, content):
        self.content = content


class _FakeChoice:
    def __init__(self, content):
        self.message = _FakeMessage(content)


class _FakeResponse:
    def __init__(self, content):
        self.choices = [_FakeChoice(content)]


def test_generate_success(monkeypatch):
    gen = _generator()

    def fake_create(**kwargs):
        return _FakeResponse(VALID_POST)

    monkeypatch.setattr(gen._client.chat.completions, "create", fake_create)
    result = gen.generate(ITEM)
    assert result.word_count >= 50


def test_generate_wraps_api_errors(monkeypatch):
    gen = _generator()

    def boom(**kwargs):
        raise RuntimeError("api down")

    monkeypatch.setattr(gen._client.chat.completions, "create", boom)
    with pytest.raises(AIGenerationError):
        gen.generate(ITEM)


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))
