"""Tests for core/research_scheduler.py."""

import json
import os
import unittest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path


class TestResearchScheduler(unittest.TestCase):
    """Test research scheduler module."""

    def setUp(self):
        """Set up test fixtures."""
        from core.research_scheduler import ResearchScheduler, SCHEDULES_FILE

        self.test_file = Path("/tmp/test_schedules.json")
        if self.test_file.exists():
            self.test_file.unlink()

    def tearDown(self):
        """Clean up test files."""
        if self.test_file.exists():
            self.test_file.unlink()

    def test_add_schedule(self):
        """Test adding a new schedule."""
        from core.research_scheduler import ResearchScheduler

        with patch("core.research_scheduler.SCHEDULES_FILE", self.test_file):
            scheduler = ResearchScheduler()
            schedule = scheduler.add_schedule("AI news", interval_minutes=30)

            self.assertEqual(schedule["topic"], "AI news")
            self.assertEqual(schedule["interval_minutes"], 30)
            self.assertEqual(schedule["id"], 1)
            self.assertTrue(schedule["active"])
            self.assertEqual(schedule["run_count"], 0)

    def test_remove_schedule(self):
        """Test removing a schedule."""
        from core.research_scheduler import ResearchScheduler

        with patch("core.research_scheduler.SCHEDULES_FILE", self.test_file):
            scheduler = ResearchScheduler()
            scheduler.add_schedule("AI news")
            scheduler.add_schedule("ML updates")

            self.assertTrue(scheduler.remove_schedule(1))
            self.assertEqual(len(scheduler.list_schedules()), 1)

            self.assertFalse(scheduler.remove_schedule(999))

    def test_list_schedules(self):
        """Test listing active schedules."""
        from core.research_scheduler import ResearchScheduler

        with patch("core.research_scheduler.SCHEDULES_FILE", self.test_file):
            scheduler = ResearchScheduler()
            scheduler.add_schedule("AI news")
            scheduler.add_schedule("ML updates")

            schedules = scheduler.list_schedules()
            self.assertEqual(len(schedules), 2)

    def test_toggle_schedule(self):
        """Test toggling schedule active state."""
        from core.research_scheduler import ResearchScheduler

        with patch("core.research_scheduler.SCHEDULES_FILE", self.test_file):
            scheduler = ResearchScheduler()
            scheduler.add_schedule("AI news")

            result = scheduler.toggle_schedule(1)
            self.assertFalse(result["active"])

            result = scheduler.toggle_schedule(1)
            self.assertTrue(result["active"])

            result = scheduler.toggle_schedule(999)
            self.assertIsNone(result)

    def test_load_schedules_from_file(self):
        """Test loading schedules from existing file."""
        from core.research_scheduler import ResearchScheduler

        test_data = [
            {"id": 1, "topic": "AI news", "interval_minutes": 60, "active": True}
        ]
        self.test_file.write_text(json.dumps(test_data))

        with patch("core.research_scheduler.SCHEDULES_FILE", self.test_file):
            scheduler = ResearchScheduler()
            self.assertEqual(len(scheduler.schedules), 1)
            self.assertEqual(scheduler.schedules[0]["topic"], "AI news")

    def test_load_schedules_invalid_file(self):
        """Test loading schedules from corrupted file."""
        from core.research_scheduler import ResearchScheduler

        self.test_file.write_text("invalid json{{{")

        with patch("core.research_scheduler.SCHEDULES_FILE", self.test_file):
            scheduler = ResearchScheduler()
            self.assertEqual(len(scheduler.schedules), 0)

    def test_load_schedules_no_file(self):
        """Test loading schedules when file doesn't exist."""
        from core.research_scheduler import ResearchScheduler

        if self.test_file.exists():
            self.test_file.unlink()

        with patch("core.research_scheduler.SCHEDULES_FILE", self.test_file):
            scheduler = ResearchScheduler()
            self.assertEqual(len(scheduler.schedules), 0)

    def test_get_scheduler_singleton(self):
        """Test get_scheduler returns singleton."""
        from core.research_scheduler import get_scheduler, _scheduler

        scheduler1 = get_scheduler()
        scheduler2 = get_scheduler()

        self.assertIs(scheduler1, scheduler2)


if __name__ == "__main__":
    unittest.main()
