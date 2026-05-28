"""Cache layer for frequent queries and API responses."""

import hashlib
import json
import time
from collections import OrderedDict
from pathlib import Path
from typing import Any, Optional

import config
from core.bot_logger import logger

_CACHE_DIR = config.DATA_DIR / "cache"
_CACHE_DIR.mkdir(parents=True, exist_ok=True)


class LRUCache:
    """In-memory LRU cache with TTL support."""

    def __init__(self, max_size: int = 500, default_ttl: int = 3600) -> None:
        self.max_size = max_size
        self.default_ttl = default_ttl
        self._cache: OrderedDict[str, dict[str, Any]] = OrderedDict()
        self._hits = 0
        self._misses = 0

    def get(self, key: str) -> Optional[Any]:
        """Get value from cache, returns None if expired or missing."""
        if key not in self._cache:
            self._misses += 1
            return None

        entry = self._cache[key]
        if time.time() - entry["timestamp"] > entry.get("ttl", self.default_ttl):
            del self._cache[key]
            self._misses += 1
            return None

        self._cache.move_to_end(key)
        self._hits += 1
        return entry["value"]

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Set value in cache with optional TTL."""
        if key in self._cache:
            self._cache.move_to_end(key)
        self._cache[key] = {
            "value": value,
            "timestamp": time.time(),
            "ttl": ttl or self.default_ttl,
        }
        self._evict_if_needed()

    def invalidate(self, key: str) -> bool:
        """Remove specific key from cache."""
        if key in self._cache:
            del self._cache[key]
            return True
        return False

    def clear(self) -> int:
        """Clear all cache entries."""
        count = len(self._cache)
        self._cache.clear()
        return count

    def _evict_if_needed(self) -> None:
        """Evict oldest entries if cache exceeds max size."""
        while len(self._cache) > self.max_size:
            self._cache.popitem(last=False)

    def stats(self) -> dict[str, Any]:
        """Get cache statistics."""
        total = self._hits + self._misses
        return {
            "size": len(self._cache),
            "max_size": self.max_size,
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": self._hits / max(1, total),
            "default_ttl": self.default_ttl,
        }


class QueryCache:
    """File-based cache for query results with LRU in-memory layer."""

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
        self._lru = LRUCache(max_size=min(500, max_size), default_ttl=default_ttl)

    def _key(self, query: str, params: Optional[dict] = None) -> str:
        raw = query + json.dumps(params or {}, sort_keys=True)
        return hashlib.md5(raw.encode()).hexdigest()

    def _path(self, key: str) -> Path:
        return self.cache_dir / f"{key}.json"

    def get(self, query: str, params: Optional[dict] = None) -> Optional[Any]:
        key = self._key(query, params)

        lru_result = self._lru.get(key)
        if lru_result is not None:
            return lru_result

        path = self._path(key)

        if not path.exists():
            return None

        try:
            data = json.loads(path.read_text())
            if time.time() - data["timestamp"] > data.get("ttl", self.default_ttl):
                path.unlink(missing_ok=True)
                return None
            result = data["result"]
            self._lru.set(key, result, data.get("ttl", self.default_ttl))
            return result
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
            self._lru.set(key, result, ttl or self.default_ttl)
            self._evict_if_needed()
        except Exception as e:
            logger.debug(f"Cache write error: {e}")

    def invalidate(self, query: str, params: Optional[dict] = None) -> bool:
        key = self._key(query, params)
        self._lru.invalidate(key)
        path = self._path(key)
        if path.exists():
            path.unlink()
            return True
        return False

    def clear(self) -> int:
        self._lru.clear()
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

    def stats(self) -> dict[str, Any]:
        files = list(self.cache_dir.glob("*.json"))
        total_size = sum(f.stat().st_size for f in files)
        lru_stats = self._lru.stats()
        return {
            "entries": len(files),
            "total_size_bytes": total_size,
            "max_size": self.max_size,
            "default_ttl": self.default_ttl,
            "lru_cache": lru_stats,
        }


_cache: Optional[QueryCache] = None


def get_cache() -> QueryCache:
    global _cache
    if _cache is None:
        _cache = QueryCache()
    return _cache
