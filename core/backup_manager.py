"""Automated backup system for vaults and data."""

import json
import shutil
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

import config
from core.bot_logger import logger

BACKUP_DIR = config.DATA_DIR / "backups"
BACKUP_DIR.mkdir(parents=True, exist_ok=True)

BACKUP_META_FILE = BACKUP_DIR / "backup_history.json"


class BackupManager:
    """Automated backup system with rotation."""

    def __init__(
        self,
        backup_dir: Path = BACKUP_DIR,
        max_backups: int = 10,
        auto_backup_interval: int = 86400,
    ) -> None:
        self.backup_dir = backup_dir
        self.max_backups = max_backups
        self.auto_backup_interval = auto_backup_interval
        self._history: list[dict] = []
        self._load_history()

    def _load_history(self) -> None:
        if BACKUP_META_FILE.exists():
            try:
                self._history = json.loads(BACKUP_META_FILE.read_text())
            except Exception:
                self._history = []

    def _save_history(self) -> None:
        BACKUP_META_FILE.write_text(json.dumps(self._history, indent=2))

    def backup_vault(self, vault_name: Optional[str] = None) -> dict:
        """Create a backup of a vault or all data."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"backup_{vault_name or 'full'}_{timestamp}"
        backup_path = self.backup_dir / backup_name

        try:
            if vault_name:
                from core.vault_manager import get_vault_manager

                vm = get_vault_manager()
                vault_config = vm._config.get("vaults", {}).get(vault_name)
                if not vault_config:
                    return {"success": False, "error": f"Vault '{vault_name}' not found"}

                vault_path = Path(vault_config["path"])
                db_path = Path(vault_config.get("db_path", ""))

                backup_path.mkdir(parents=True)

                if vault_path.exists():
                    shutil.copytree(vault_path, backup_path / "wiki")

                if db_path.exists():
                    shutil.copy2(db_path, backup_path / "wiki.db")

                size = sum(f.stat().st_size for f in backup_path.rglob("*") if f.is_file())

            else:
                shutil.copytree(config.DATA_DIR, backup_path, ignore=shutil.ignore_patterns("backups", "*.faiss"))
                size = sum(f.stat().st_size for f in backup_path.rglob("*") if f.is_file())

            record = {
                "name": backup_name,
                "path": str(backup_path),
                "timestamp": datetime.now().isoformat(),
                "vault": vault_name or "full",
                "size_bytes": size,
                "status": "completed",
            }
            self._history.append(record)
            self._save_history()
            self._rotate_backups()

            logger.info(f"Backup created: {backup_name} ({size / 1024:.1f} KB)")
            return {"success": True, "backup": record}

        except Exception as e:
            logger.error(f"Backup failed: {e}")
            return {"success": False, "error": str(e)}

    def list_backups(self) -> list[dict]:
        return sorted(self._history, key=lambda x: x["timestamp"], reverse=True)

    def restore_backup(self, backup_name: str) -> dict:
        """Restore from a backup."""
        backup_path = self.backup_dir / backup_name

        if not backup_path.exists():
            return {"success": False, "error": f"Backup '{backup_name}' not found"}

        try:
            wiki_dir = backup_path / "wiki"
            if wiki_dir.exists():
                target = config.WIKI_DIR
                if target.exists():
                    shutil.rmtree(target)
                shutil.copytree(wiki_dir, target)

            db_file = backup_path / "wiki.db"
            if db_file.exists():
                from core.vault_manager import get_vault_manager

                vm = get_vault_manager()
                active = vm.get_active()
                if active and active.get("db_path"):
                    shutil.copy2(db_file, active["db_path"])

            logger.info(f"Restored from backup: {backup_name}")
            return {"success": True, "restored": backup_name}

        except Exception as e:
            logger.error(f"Restore failed: {e}")
            return {"success": False, "error": str(e)}

    def delete_backup(self, backup_name: str) -> dict:
        backup_path = self.backup_dir / backup_name

        if not backup_path.exists():
            return {"success": False, "error": "Backup not found"}

        try:
            shutil.rmtree(backup_path)
            self._history = [h for h in self._history if h["name"] != backup_name]
            self._save_history()
            return {"success": True}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _rotate_backups(self) -> None:
        if len(self._history) > self.max_backups:
            to_remove = self._history[: len(self._history) - self.max_backups]
            for record in to_remove:
                path = Path(record["path"])
                if path.exists():
                    shutil.rmtree(path)
            self._history = self._history[len(to_remove) :]
            self._save_history()

    def should_auto_backup(self) -> bool:
        if not self._history:
            return True
        last = max(self._history, key=lambda x: x["timestamp"])
        last_time = datetime.fromisoformat(last["timestamp"]).timestamp()
        return (time.time() - last_time) > self.auto_backup_interval

    def auto_backup_if_needed(self) -> Optional[dict]:
        if self.should_auto_backup():
            return self.backup_vault()
        return None

    def stats(self) -> dict:
        total_size = sum(
            sum(f.stat().st_size for f in Path(r["path"]).rglob("*") if f.is_file())
            for r in self._history
            if Path(r["path"]).exists()
        )
        return {
            "total_backups": len(self._history),
            "total_size_bytes": total_size,
            "max_backups": self.max_backups,
            "auto_backup_interval": self.auto_backup_interval,
            "last_backup": self._history[-1]["timestamp"] if self._history else None,
        }


_backup_manager: Optional[BackupManager] = None


def get_backup_manager() -> BackupManager:
    global _backup_manager
    if _backup_manager is None:
        _backup_manager = BackupManager()
    return _backup_manager
