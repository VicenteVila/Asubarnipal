"""Scheduled Research Manager - Schedule research tasks."""

import json
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

import config
from core.bot_logger import logger

SCHEDULES_FILE = config.DATA_DIR / "research_schedules.json"


class ResearchScheduler:
    """Manages scheduled research tasks."""

    def __init__(self) -> None:
        self.schedules: list[dict[str, Any]] = []
        self.running = False
        self._thread: Optional[threading.Thread] = None
        self._load_schedules()

    def _load_schedules(self) -> None:
        """Load schedules from disk."""
        if SCHEDULES_FILE.exists():
            try:
                self.schedules = json.loads(SCHEDULES_FILE.read_text())
                logger.info(f"Loaded {len(self.schedules)} research schedules")
            except Exception as e:
                logger.error(f"Failed to load schedules: {e}")
                self.schedules = []
        else:
            self.schedules = []

    def _save_schedules(self) -> None:
        """Save schedules to disk."""
        try:
            SCHEDULES_FILE.write_text(json.dumps(self.schedules, indent=2))
        except Exception as e:
            logger.error(f"Failed to save schedules: {e}")

    def add_schedule(
        self,
        topic: str,
        interval_minutes: int = 60,
        user_id: Optional[int] = None,
        notify: bool = True,
    ) -> dict[str, Any]:
        """Add a scheduled research task."""
        schedule = {
            "id": len(self.schedules) + 1,
            "topic": topic,
            "interval_minutes": interval_minutes,
            "user_id": user_id,
            "notify": notify,
            "created": datetime.now().isoformat(),
            "last_run": None,
            "run_count": 0,
            "active": True,
        }
        self.schedules.append(schedule)
        self._save_schedules()
        logger.info(f"Added research schedule: {topic} every {interval_minutes}min")
        return schedule

    def remove_schedule(self, schedule_id: int) -> bool:
        """Remove a scheduled research task."""
        for i, s in enumerate(self.schedules):
            if s["id"] == schedule_id:
                removed = self.schedules.pop(i)
                self._save_schedules()
                logger.info(f"Removed research schedule: {removed['topic']}")
                return True
        return False

    def list_schedules(self) -> list[dict[str, Any]]:
        """List all active schedules."""
        return [s for s in self.schedules if s.get("active", True)]

    def toggle_schedule(self, schedule_id: int) -> Optional[dict[str, Any]]:
        """Toggle a schedule active/inactive."""
        for s in self.schedules:
            if s["id"] == schedule_id:
                s["active"] = not s.get("active", True)
                self._save_schedules()
                return s
        return None

    def start(self) -> None:
        """Start the scheduler loop."""
        if self.running:
            return
        self.running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()
        logger.info("Research scheduler started")

    def stop(self) -> None:
        """Stop the scheduler loop."""
        self.running = False
        if self._thread:
            self._thread.join(timeout=5)
        logger.info("Research scheduler stopped")

    def _loop(self) -> None:
        """Main scheduler loop."""
        while self.running:
            now = datetime.now()
            for schedule in self.schedules:
                if not schedule.get("active", True):
                    continue

                last_run = schedule.get("last_run")
                if last_run:
                    last_dt = datetime.fromisoformat(last_run)
                    elapsed = (now - last_dt).total_seconds() / 60
                    if elapsed < schedule["interval_minutes"]:
                        continue

                self._run_schedule(schedule)

            time.sleep(30)

    def _run_schedule(self, schedule: dict[str, Any]) -> None:
        """Execute a scheduled research task."""
        topic = schedule["topic"]
        logger.info(f"Running scheduled research: {topic}")

        try:
            from core.llm_router import LLMRouter
            from brave_search import BraveSearch

            brave = BraveSearch()
            results = brave.search(topic, max_results=5)

            if results:
                summary = "\n".join([r.get("title", "") + ": " + r.get("snippet", "") for r in results[:3]])

                from core.wiki import Wiki
                wiki = Wiki()
                wiki.add(f"Investigacion programada: {topic}", summary, tipo="synthesis")

                schedule["last_run"] = datetime.now().isoformat()
                schedule["run_count"] = schedule.get("run_count", 0) + 1
                self._save_schedules()

                logger.info(f"Scheduled research completed: {topic}")
            else:
                logger.warning(f"No results for scheduled research: {topic}")

        except Exception as e:
            logger.error(f"Scheduled research failed: {topic}: {e}")


_scheduler: Optional[ResearchScheduler] = None


def get_scheduler() -> ResearchScheduler:
    """Get or create the research scheduler."""
    global _scheduler
    if _scheduler is None:
        _scheduler = ResearchScheduler()
    return _scheduler
