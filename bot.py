"""Entry point: Telegram bot that posts a daily Arabic tech-news summary.

Wires together configuration, the SQLite database, the RSS news fetcher,
the OpenAI-based Arabic generator, and the daily scheduler.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Optional

import pytz
from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import (
    Application,
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
)

from ai_generator import AIGenerationError, AIGenerator
from database import Database, GeneratedPost
from news_fetcher import NewsFetcher, NewsItem
from scheduler import DailyScheduler
from utils import ConfigError, Settings, load_settings, setup_logging

logger = setup_logging()


class ArabicTechNewsBot:
    """Holds shared services and implements the bot's behaviour."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.db = Database()
        self.fetcher = NewsFetcher(
            sources=settings.sources,
            max_items_to_check=settings.max_items_to_check,
        )
        self.generator = AIGenerator(
            api_key=settings.openai_api_key,
            min_words=settings.min_words,
            max_words=settings.max_words,
        )
        self.scheduler = DailyScheduler(
            hour=settings.schedule_hour,
            minute=settings.schedule_minute,
            timezone=settings.timezone,
        )
        self.tz = pytz.timezone(settings.timezone)

    # ------------------------------------------------------------------
    # Core pipeline
    # ------------------------------------------------------------------
    def _build_post(self) -> Optional[tuple[NewsItem, str]]:
        """Fetch a fresh item and generate its Arabic post.

        Returns (item, arabic_text) or None if no content could be produced.
        Never raises — failures are logged and reported as None.
        """
        item = self.fetcher.get_fresh_item(self.db.is_duplicate)
        if item is None:
            return None
        try:
            result = self.generator.generate(item)
        except AIGenerationError:
            logger.exception("AI generation failed; refusing to send broken content")
            return None
        return item, result.arabic_text

    async def _send_post(self, application: Application) -> bool:
        """Generate and send one post to the channel. Returns True on success."""
        built = self._build_post()
        if built is None:
            logger.warning("No post to send (no fresh news or generation failed)")
            return False

        item, arabic_text = built
        post = GeneratedPost(
            title=item.title,
            url=item.url,
            source=item.source,
            arabic_text=arabic_text,
        )
        post_id = self.db.save_generated_post(post, sent=False)
        try:
            await application.bot.send_message(
                chat_id=self.settings.channel_id,
                text=arabic_text,
                parse_mode=None,  # plain text; Arabic + emoji need no markdown
                disable_web_page_preview=False,
            )
        except Exception:
            logger.exception("Failed to send message to channel")
            return False

        self.db.mark_post_sent(post_id)
        self.db.record_sent_news(post)
        logger.info("Posted news to channel: %s", item.title)
        return True

    # ------------------------------------------------------------------
    # Admin helpers
    # ------------------------------------------------------------------
    def _is_admin(self, update: Update) -> bool:
        user = update.effective_user
        return bool(user and user.id in self.settings.admin_ids)

    async def _deny(self, update: Update) -> None:
        if update.effective_message:
            await update.effective_message.reply_text(
                "⛔ This command is restricted to administrators."
            )

    # ------------------------------------------------------------------
    # Command handlers
    # ------------------------------------------------------------------
    async def cmd_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not self._is_admin(update):
            await self._deny(update)
            return
        next_run = self.scheduler.next_run_time()
        next_txt = next_run.strftime("%Y-%m-%d %H:%M %Z") if next_run else "not scheduled"
        await update.effective_message.reply_text(
            "🤖 Arabic Tech News Bot is running.\n"
            f"Channel: {self.settings.channel_id}\n"
            f"Daily post: {self.settings.schedule_hour:02d}:"
            f"{self.settings.schedule_minute:02d} {self.settings.timezone}\n"
            f"Next run: {next_txt}\n\n"
            "Commands: /send_now /latest /status /sources"
        )

    async def cmd_send_now(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not self._is_admin(update):
            await self._deny(update)
            return
        await update.effective_message.reply_text("⏳ Generating and sending a post...")
        ok = await self._send_post(context.application)
        if ok:
            await update.effective_message.reply_text("✅ Sent to the channel.")
        else:
            await update.effective_message.reply_text(
                "⚠️ Could not send: no fresh news or generation failed. Check logs."
            )

    async def cmd_latest(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not self._is_admin(update):
            await self._deny(update)
            return
        await update.effective_message.reply_text("⏳ Generating a preview...")
        built = self._build_post()
        if built is None:
            await update.effective_message.reply_text(
                "⚠️ Could not generate a preview (no fresh news or AI failed)."
            )
            return
        _item, arabic_text = built
        await update.effective_message.reply_text(
            "👁 Preview (not sent):\n\n" + arabic_text
        )

    async def cmd_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not self._is_admin(update):
            await self._deny(update)
            return
        last_sent = self.db.last_sent_at() or "never"
        next_run = self.scheduler.next_run_time()
        next_txt = next_run.strftime("%Y-%m-%d %H:%M %Z") if next_run else "not scheduled"
        counts = self.db.counts()
        now = datetime.now(self.tz).strftime("%Y-%m-%d %H:%M %Z")
        await update.effective_message.reply_text(
            "📊 Status\n"
            f"Now: {now}\n"
            f"Last sent (UTC): {last_sent}\n"
            f"Next scheduled: {next_txt}\n"
            f"DB: {counts['sent_news']} sent, {counts['generated_posts']} generated"
        )

    async def cmd_sources(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not self._is_admin(update):
            await self._deny(update)
            return
        lines = ["🗞 Configured sources:"]
        for src in self.settings.sources:
            lines.append(f"• {src.name} — {src.url}")
        await update.effective_message.reply_text("\n".join(lines))

    # ------------------------------------------------------------------
    # Scheduled job
    # ------------------------------------------------------------------
    def make_daily_job(self, application: Application):
        async def _job() -> None:
            logger.info("Running scheduled daily post job")
            try:
                await self._send_post(application)
            except Exception:
                logger.exception("Unexpected error in daily job")

        return _job

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------
    async def _on_startup(self, application: Application) -> None:
        self.scheduler.start(self.make_daily_job(application))

    async def _on_shutdown(self, application: Application) -> None:
        self.scheduler.shutdown()
        self.db.close()

    def build_application(self) -> Application:
        application = (
            ApplicationBuilder()
            .token(self.settings.bot_token)
            .post_init(self._on_startup)
            .post_shutdown(self._on_shutdown)
            .build()
        )
        application.add_handler(CommandHandler("start", self.cmd_start))
        application.add_handler(CommandHandler("send_now", self.cmd_send_now))
        application.add_handler(CommandHandler("latest", self.cmd_latest))
        application.add_handler(CommandHandler("status", self.cmd_status))
        application.add_handler(CommandHandler("sources", self.cmd_sources))
        return application


def main() -> None:
    try:
        settings = load_settings()
    except ConfigError as exc:
        logger.error("Configuration error: %s", exc)
        raise SystemExit(1) from exc

    bot = ArabicTechNewsBot(settings)
    application = bot.build_application()
    logger.info("Starting bot (polling)...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
