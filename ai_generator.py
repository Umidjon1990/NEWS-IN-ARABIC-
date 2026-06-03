"""Generate the final Arabic Telegram post from a news item using OpenAI."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional

from openai import OpenAI

from news_fetcher import NewsItem
from utils import count_arabic_words

logger = logging.getLogger("arabic_tech_news_bot.ai_generator")

SYSTEM_PROMPT = (
    "You are an Arabic technology news editor.\n"
    "Rewrite the given technology news as a short Telegram post in Modern "
    "Standard Arabic.\n"
    "Add full Arabic harakat/tashkīl to every Arabic word.\n"
    "The post must be 50–70 words.\n"
    "The level must be suitable for A2–B1 Arabic learners.\n"
    "Use simple and clear language.\n"
    "Do not add false information.\n"
    "Avoid politics, religion, adult content, violence, and unsafe content.\n"
    "Return only the final Telegram post.\n\n"
    "Format:\n"
    "📰 العُنْوَانُ:\n"
    "[title with harakat]\n\n"
    "[50–70 Arabic words with full harakat]\n\n"
    "🔗 المَصْدَرُ: [source URL]"
)


@dataclass
class GenerationResult:
    arabic_text: str
    word_count: int


class AIGenerationError(RuntimeError):
    """Raised when the AI fails to return a usable post."""


class AIGenerator:
    """Wraps the OpenAI chat completion call and validates the output."""

    def __init__(
        self,
        api_key: str,
        model: str = "gpt-4o-mini",
        min_words: int = 50,
        max_words: int = 70,
    ) -> None:
        self._client = OpenAI(api_key=api_key)
        self.model = model
        self.min_words = min_words
        self.max_words = max_words

    def _build_user_prompt(self, item: NewsItem) -> str:
        return (
            f"Source name: {item.source}\n"
            f"Source URL: {item.url}\n"
            f"Original title: {item.title}\n"
            f"Original summary: {item.summary}\n\n"
            "Now produce the Arabic Telegram post following the required format. "
            f"Use exactly this URL in the المَصْدَرُ line: {item.url}"
        )

    def _validate(self, text: str, item: NewsItem) -> GenerationResult:
        text = (text or "").strip()
        if not text:
            raise AIGenerationError("AI returned empty content")

        if "📰" not in text or "🔗" not in text:
            raise AIGenerationError("AI output is missing required format markers")

        # The source URL must be present so we never publish a wrong/missing link.
        if item.url not in text:
            logger.warning("AI omitted the source URL; appending it explicitly")
            text = f"{text}\n\n🔗 المَصْدَرُ: {item.url}"

        word_count = count_arabic_words(text)
        # Allow a small tolerance so borderline-good posts are not discarded.
        lower = max(0, self.min_words - 10)
        upper = self.max_words + 15
        if not (lower <= word_count <= upper):
            raise AIGenerationError(
                f"Arabic word count {word_count} is outside acceptable range "
                f"[{lower}, {upper}]"
            )

        return GenerationResult(arabic_text=text, word_count=word_count)

    def generate(self, item: NewsItem) -> GenerationResult:
        """Generate and validate an Arabic post. Raises AIGenerationError on failure."""
        try:
            response = self._client.chat.completions.create(
                model=self.model,
                temperature=0.4,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": self._build_user_prompt(item)},
                ],
            )
        except Exception as exc:  # network / API error
            logger.exception("OpenAI request failed")
            raise AIGenerationError(f"OpenAI request failed: {exc}") from exc

        content: Optional[str] = None
        if response.choices:
            content = response.choices[0].message.content

        result = self._validate(content or "", item)
        logger.info("Generated Arabic post (%d Arabic words)", result.word_count)
        return result
