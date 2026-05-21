"""Cache layer for frequent queries and API responses."""

import hashlib
import json
import time
from pathlib import Path
from typing import Any, Optional

import config
from core.bot_logger import logger

_CACHE_DIR = config.DATA_DIR / "cache"
_CACHE_DIR.mkdir(parents=True, exist_ok=True)


class QueryCache:
    """File-based cache for query results."""

    def __init__(
        self,
        cache_dir: Path = _CACHE_DIR,
        default_ttl: int = 3600,
        max_size: int = 1000,
    ) -> None:
        self.cache_dir = cache_dir
        self.default_ttl = default_ttl
        self.max_size = max_size
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _key(self, query: str, params: Optional[dict] = None) -> str:
        raw = query + json.dumps(params or {}, sort_keys=True)
        return hashlib.md5(raw.encode()).hexdigest()

    def _path(self, key: str) -> Path:
        return self.cache_dir / f"{key}.json"

    def get(self, query: str, params: Optional[dict] = None) -> Optional[Any]:
        key = self._key(query, params)
        path = self._path(key)

        if not path.exists():
            return None

        try:
            data = json.loads(path.read_text())
            if time.time() - data["timestamp"] > data.get("ttl", self.default_ttl):
                path.unlink(missing_ok=True)
                return None
            return data["result"]
        except Exception as e:
            logger.debug(f"Cache read error: {e}")
            return None

    def set(
        self,
        query: str,
        result: Any,
        params: Optional[dict] = None,
        ttl: Optional[int] = None,
    ) -> None:
        key = self._key(query, params)
        path = self._path(key)

        data = {
            "timestamp": time.time(),
            "ttl": ttl or self.default_ttl,
            "result": result,
            "query": query[:200],
        }

        try:
            path.write_text(json.dumps(data, default=str))
            self._evict_if_needed()
        except Exception as e:
            logger.debug(f"Cache write error: {e}")

    def invalidate(self, query: str, params: Optional[dict] = None) -> bool:
        key = self._key(query, params)
        path = self._path(key)
        if path.exists():
            path.unlink()
            return True
        return False

    def clear(self) -> int:
        count = 0
        for f in self.cache_dir.glob("*.json"):
            f.unlink()
            count += 1
        logger.info(f"Cache cleared: {count} entries removed")
        return count

    def _evict_if_needed(self) -> None:
        files = list(self.cache_dir.glob("*.json"))
        if len(files) > self.max_size:
            files.sort(key=lambda f: f.stat().st_mtime)
            to_remove = len(files) - self.max_size
            for f in files[:to_remove]:
                f.unlink()

    def stats(self) -> dict:
        files = list(self.cache_dir.glob("*.json"))
        total_size = sum(f.stat().st_size for f in files)
        return {
            "entries": len(files),
            "total_size_bytes": total_size,
            "max_size": self.max_size,
            "default_ttl": self.default_ttl,
        }


_cache: Optional[QueryCache] = None


def get_cache() -> QueryCache:
    global _cache
    if _cache is None:
        _cache = QueryCache()
    return _cache
