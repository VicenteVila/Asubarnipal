"""Tests for core/backup_manager.py."""

import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


class TestBackupManager(unittest.TestCase):
    """Test automated backup system."""

    def setUp(self):
        import importlib
        import core.backup_manager as bm_mod
        bm_mod._backup_manager = None
        importlib.reload(bm_mod)

        self.test_dir = Path(tempfile.mkdtemp())
        self.backup_dir = self.test_dir / "backups"
        self.backup_dir.mkdir()
        self.meta_file = self.backup_dir / "backup_history.json"

    def tearDown(self):
        import core.backup_manager as bm_mod
        bm_mod._backup_manager = None
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)

    def _make_bm(self, **kwargs):
        from core.backup_manager import BackupManager, BACKUP_META_FILE
        with patch.object(BackupManager, '_load_history', lambda self: setattr(self, '_history', [])):
            bm = BackupManager(backup_dir=self.backup_dir, **kwargs)
            bm._history = []
            return bm

    def test_backup_vault_full(self):
        from core.backup_manager import BackupManager

        with patch("core.backup_manager.config") as mock_config:
            mock_config.DATA_DIR = self.test_dir
            mock_config.WIKI_DIR = self.test_dir / "wiki"
            mock_config.WIKI_DIR.mkdir()
            (mock_config.WIKI_DIR / "test.md").write_text("# Test")

            bm = self._make_bm()
            result = bm.backup_vault()

            self.assertTrue(result["success"])
            self.assertEqual(result["backup"]["vault"], "full")

    def test_list_backups_empty(self):
        bm = self._make_bm()
        self.assertEqual(len(bm.list_backups()), 0)

    def test_list_backups_after_backup(self):
        from core.backup_manager import BackupManager

        with patch("core.backup_manager.config") as mock_config:
            mock_config.DATA_DIR = self.test_dir
            mock_config.WIKI_DIR = self.test_dir / "wiki"
            mock_config.WIKI_DIR.mkdir()

            bm = self._make_bm()
            bm.backup_vault()

            backups = bm.list_backups()
            self.assertEqual(len(backups), 1)

    def test_delete_backup(self):
        from core.backup_manager import BackupManager

        with patch("core.backup_manager.config") as mock_config:
            mock_config.DATA_DIR = self.test_dir
            mock_config.WIKI_DIR = self.test_dir / "wiki"
            mock_config.WIKI_DIR.mkdir()

            bm = self._make_bm()
            result = bm.backup_vault()
            backup_name = result["backup"]["name"]

            delete_result = bm.delete_backup(backup_name)
            self.assertTrue(delete_result["success"])
            self.assertEqual(len(bm.list_backups()), 0)

    def test_restore_backup_not_found(self):
        bm = self._make_bm()
        result = bm.restore_backup("nonexistent")
        self.assertFalse(result["success"])

    def test_backup_rotation(self):
        import time
        from core.backup_manager import BackupManager

        with patch("core.backup_manager.config") as mock_config:
            mock_config.DATA_DIR = self.test_dir
            mock_config.WIKI_DIR = self.test_dir / "wiki"
            mock_config.WIKI_DIR.mkdir()

            bm = self._make_bm(max_backups=3)

            for i in range(5):
                bm.backup_vault()
                time.sleep(1.1)

            self.assertEqual(len(bm.list_backups()), 3)

    def test_stats(self):
        from core.backup_manager import BackupManager

        with patch("core.backup_manager.config") as mock_config:
            mock_config.DATA_DIR = self.test_dir
            mock_config.WIKI_DIR = self.test_dir / "wiki"
            mock_config.WIKI_DIR.mkdir()

            bm = self._make_bm(max_backups=5, auto_backup_interval=3600)
            bm.backup_vault()

            stats = bm.stats()
            self.assertEqual(stats["total_backups"], 1)
            self.assertEqual(stats["max_backups"], 5)
            self.assertEqual(stats["auto_backup_interval"], 3600)

    def test_should_auto_backup_when_no_history(self):
        bm = self._make_bm(auto_backup_interval=1)
        self.assertTrue(bm.should_auto_backup())

    def test_get_backup_manager_singleton(self):
        from core.backup_manager import get_backup_manager

        bm1 = get_backup_manager()
        bm2 = get_backup_manager()
        self.assertIs(bm1, bm2)


if __name__ == "__main__":
    unittest.main()
