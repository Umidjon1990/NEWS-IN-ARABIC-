"""APScheduler wrapper that runs the daily post job in Asia/Tashkent time."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Awaitable, Callable, Optional

import pytz
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

logger = logging.getLogger("arabic_tech_news_bot.scheduler")

JobCallback = Callable[[], Awaitable[None]]


class DailyScheduler:
    """Schedules a single async job to run every day at a fixed local time."""

    JOB_ID = "daily_arabic_post"

    def __init__(self, hour: int, minute: int, timezone: str) -> None:
        self.hour = hour
        self.minute = minute
        try:
            self.tz = pytz.timezone(timezone)
        except pytz.UnknownTimeZoneError as exc:
            raise ValueError(f"Unknown timezone: {timezone}") from exc
        self._scheduler = AsyncIOScheduler(timezone=self.tz)

    def start(self, job: JobCallback) -> None:
        trigger = CronTrigger(hour=self.hour, minute=self.minute, timezone=self.tz)
        self._scheduler.add_job(
            job,
            trigger=trigger,
            id=self.JOB_ID,
            replace_existing=True,
            misfire_grace_time=3600,
            coalesce=True,
        )
        self._scheduler.start()
        logger.info(
            "Scheduler started: daily post at %02d:%02d %s",
            self.hour,
            self.minute,
            self.tz,
        )

    def next_run_time(self) -> Optional[datetime]:
        job = self._scheduler.get_job(self.JOB_ID)
        return job.next_run_time if job else None

    def shutdown(self) -> None:
        if self._scheduler.running:
            self._scheduler.shutdown(wait=False)
            logger.info("Scheduler shut down")
