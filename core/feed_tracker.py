"""Feed Tracker - Seguimiento de RSS/Atom feeds con alertas."""

import json
import logging
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Self, Optional

import config
import feedparser

logger = logging.getLogger(__name__)


class FeedTracker:
    """跟踪RSS/Atom feeds y detectar actualizaciones."""
    
    def __init__(self) -> None:
        self.subscriptions_file = config.STORAGE_DIR / "feeds.json"
        self.alerts_file = config.STORAGE_DIR / "feed_alerts.json"
        self._load()
    
    def _load(self) -> None:
        """Cargar suscripciones."""
        self.subscriptions = []
        self.last_entries = {}
        
        if self.subscriptions_file.exists():
            try:
                data = json.loads(self.subscriptions_file.read_text())
                self.subscriptions = data.get("subscriptions", [])
                self.last_entries = data.get("last_entries", {})
            except Exception:
                self.subscriptions = []
                self.last_entries = {}
    
    def _save(self) -> None:
        """Guardar suscripciones."""
        config.STORAGE_DIR.mkdir(exist_ok=True)
        self.subscriptions_file.write_text(json.dumps({
            "subscriptions": self.subscriptions,
            "last_entries": self.last_entries,
        }, indent=2), encoding="utf-8")
    
    def subscribe(self, url: str, name: str = "") -> bool:
        """Suscribirse a un feed."""
        if any(s["url"] == url for s in self.subscriptions):
            return False
        
        try:
            feed = feedparser.parse(url)
            if feed.bozo and not feed.entries:
                logger.warning(f"Invalid feed: {url}")
                return False
            
            name = name or feed.feed.get("title", url)
            entry_id = self._get_entry_id(feed.entries[0]) if feed.entries else ""
            
            self.subscriptions.append({
                "url": url,
                "name": name,
                "added": datetime.now().isoformat(),
            })
            self.last_entries[url] = entry_id
            self._save()
            logger.info(f"✅ Subscrito a: {name}")
            return True
        except Exception as e:
            logger.error(f"Error subscripting: {e}")
            return False
    
    def unsubscribe(self, url: str) -> bool:
        """Cancelar suscripción."""
        self.subscriptions = [s for s in self.subscriptions if s["url"] != url]
        self.last_entries.pop(url, None)
        self._save()
        return True
    
    def _get_entry_id(self, entry) -> str:
        """Obtener ID único de entrada."""
        return entry.get("id", entry.get("link", entry.get("title", "")))
    
    def check_updates(self) -> list[dict]:
        """Verificar actualizaciones."""
        updates = []
        
        for sub in self.subscriptions:
            try:
                feed = feedparser.parse(sub["url"], etag=self.last_entries.get(f"etag_{sub['url']}"),
                                  modified=self.last_entries.get(f"modified_{sub['url']}"))
                
                if feed.status == 304:
                    continue
                
                if feed.etag:
                    self.last_entries[f"etag_{sub['url']}"] = feed.etag
                if feed.modified:
                    self.last_entries[f"modified_{sub['url']}"] = feed.modified
                
                last_id = self.last_entries.get(sub["url"], "")
                
                for entry in feed.entries[:5]:
                    entry_id = self._get_entry_id(entry)
                    if entry_id != last_id:
                        updates.append({
                            "feed": sub["name"],
                            "url": sub["url"],
                            "title": entry.get("title", "Sin título"),
                            "link": entry.get("link", ""),
                            "published": entry.get("published", entry.get("updated", "")),
                            "summary": entry.get("summary", entry.get("description", ""))[:200],
                        })
                
                if feed.entries:
                    self.last_entries[sub["url"]] = self._get_entry_id(feed.entries[0])
                
                time.sleep(0.5)
            except Exception as e:
                logger.error(f"Error checking feed: {e}")
        
        if updates:
            self._save_alerts(updates)
        
        return updates
    
    def _save_alerts(self, updates: list[dict[str, Any]]) -> None:
        """Guardar alertas."""
        config.STORAGE_DIR.mkdir(exist_ok=True)
        
        alerts = []
        if self.alerts_file.exists():
            try:
                alerts = json.loads(self.alerts_file.read_text())
            except Exception:
                alerts = []
        
        alerts.extend([{
            **u,
            "timestamp": datetime.now().isoformat(),
            "read": False
        } for u in updates])
        
        alerts = alerts[-100:]
        self.alerts_file.write_text(json.dumps(alerts, indent=2), encoding="utf-8")
    
    def get_subscriptions(self) -> list[dict]:
        """Listar suscripciones."""
        return self.subscriptions
    
    def get_alerts(self, unread_only: bool = False) -> list[dict]:
        """Obtener alertas."""
        if not self.alerts_file.exists():
            return []
        
        try:
            alerts = json.loads(self.alerts_file.read_text())
            if unread_only:
                return [a for a in alerts if not a.get("read", True)]
            return alerts
        except Exception:
            return []
    
    def mark_alert_read(self, index: int = -1) -> None:
        """Marcar alerta como leída."""
        if not self.alerts_file.exists():
            return
        
        try:
            alerts = json.loads(self.alerts_file.read_text())
            if 0 <= index < len(alerts):
                alerts[index]["read"] = True
                self.alerts_file.write_text(json.dumps(alerts, indent=2), encoding="utf-8")
        except Exception:
            pass
    
    def get_unread_count(self) -> int:
        """Contar alertas sin leer."""
        return len(self.get_alerts(unread_only=True))


# Funciones de utilidad para schedulers
def check_all_feeds() -> list[dict[str, Any]]:
    """Verificar todos los feeds (para scheduler)."""
    tracker = FeedTracker()
    updates = tracker.check_updates()
    
    if updates:
        logger.info(f"🔔 {len(updates)} actualizaciones detectadas")
        return updates
    
    return []


if __name__ == "__main__":
    tracker = FeedTracker()
    print("📡 Feeds suscritos:")
    for sub in tracker.subscriptions:
        print(f"  - {sub['name']}: {sub['url']}")
    
    print("\n🔄 Verificando actualizaciones...")
    updates = check_all_feeds()
    print(f"  {len(updates)} actualizaciones")