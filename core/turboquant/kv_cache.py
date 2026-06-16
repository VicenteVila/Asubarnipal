"""KV Cache with eviction policies for transformer inference.

Implements LRU and LFU eviction policies for key-value cache
with configurable memory limits.
"""

import time
import logging
from typing import Dict, Optional, List, Tuple, Any
from collections import OrderedDict, defaultdict
from dataclasses import dataclass, field
from enum import Enum

import torch

logger = logging.getLogger(__name__)


class EvictionPolicy(Enum):
    LRU = "lru"
    LFU = "lfu"


@dataclass
class KVCacheEntry:
    """Entry in the KV cache."""
    key: torch.Tensor
    value: torch.Tensor
    last_access: float = 0.0
    access_count: int = 0
    size_bytes: int = 0

    def __post_init__(self):
        if self.size_bytes == 0:
            self.size_bytes = (
                self.key.element_size() * self.key.nelement()
                + self.value.element_size() * self.value.nelement()
            )


@dataclass
class KVCacheStats:
    """Statistics for KV cache."""
    num_entries: int = 0
    memory_used_mb: float = 0.0
    max_memory_mb: float = 0.0
    hit_count: int = 0
    miss_count: int = 0
    eviction_count: int = 0
    hit_rate: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "num_entries": self.num_entries,
            "memory_used_mb": round(self.memory_used_mb, 2),
            "max_memory_mb": round(self.max_memory_mb, 2),
            "memory_usage_pct": round(
                (self.memory_used_mb / self.max_memory_mb * 100) if self.max_memory_mb > 0 else 0, 1
            ),
            "hit_count": self.hit_count,
            "miss_count": self.miss_count,
            "eviction_count": self.eviction_count,
            "hit_rate": round(self.hit_rate, 3),
        }


class KVCache:
    """Key-Value cache with configurable eviction policy and memory limit.

    Args:
        max_memory_mb: Maximum memory in MB (default: 4096 = 4GB).
        policy: Eviction policy ('lru' or 'lfu', default: 'lru').
        device: Device for stored tensors.
    """

    def __init__(
        self,
        max_memory_mb: float = 4096.0,
        policy: str = "lru",
        device: str = "cpu",
    ):
        self.max_memory_bytes = int(max_memory_mb * 1024 * 1024)
        self.policy = EvictionPolicy(policy.lower())
        self.device = device
        self._cache: Dict[str, KVCacheEntry] = OrderedDict()
        self._hit_count = 0
        self._miss_count = 0
        self._eviction_count = 0

    def get(self, key: str) -> Optional[Tuple[torch.Tensor, torch.Tensor]]:
        """Get entry from cache.

        Args:
            key: Cache key.

        Returns:
            (key_tensor, value_tensor) or None if not found.
        """
        entry = self._cache.get(key)
        if entry is not None:
            self._hit_count += 1
            entry.last_access = time.time()
            entry.access_count += 1
            if self.policy == EvictionPolicy.LRU:
                self._cache.move_to_end(key)
            return entry.key, entry.value

        self._miss_count += 1
        return None

    def put(self, key: str, key_tensor: torch.Tensor, value_tensor: torch.Tensor):
        """Store entry in cache.

        Args:
            key: Cache key.
            key_tensor: Key tensor (from attention).
            value_tensor: Value tensor (from attention).
        """
        entry = KVCacheEntry(
            key=key_tensor.to(self.device),
            value=value_tensor.to(self.device),
            last_access=time.time(),
            access_count=1,
        )

        self._ensure_space(entry.size_bytes)
        self._cache[key] = entry

        if self.policy == EvictionPolicy.LRU:
            self._cache.move_to_end(key)

    def get_many(self, keys: List[str]) -> Dict[str, Tuple[torch.Tensor, torch.Tensor]]:
        """Get multiple entries at once."""
        results = {}
        for key in keys:
            result = self.get(key)
            if result is not None:
                results[key] = result
        return results

    def evict(self, count: int = 1):
        """Evict entries based on policy.

        Args:
            count: Number of entries to evict.
        """
        for _ in range(count):
            if not self._cache:
                break

            if self.policy == EvictionPolicy.LRU:
                self._cache.popitem(last=False)
            elif self.policy == EvictionPolicy.LFU:
                min_key = min(self._cache, key=lambda k: self._cache[k].access_count)
                del self._cache[min_key]

            self._eviction_count += 1

    def clear(self):
        """Clear all cache entries."""
        self._cache.clear()
        logger.info("KV cache cleared")

    def contains(self, key: str) -> bool:
        """Check if key exists in cache."""
        return key in self._cache

    def get_stats(self) -> KVCacheStats:
        """Get cache statistics."""
        total = self._hit_count + self._miss_count
        hit_rate = self._hit_count / total if total > 0 else 0.0
        memory_used = sum(e.size_bytes for e in self._cache.values())

        return KVCacheStats(
            num_entries=len(self._cache),
            memory_used_mb=memory_used / (1024 * 1024),
            max_memory_mb=self.max_memory_bytes / (1024 * 1024),
            hit_count=self._hit_count,
            miss_count=self._miss_count,
            eviction_count=self._eviction_count,
            hit_rate=hit_rate,
        )

    def get_memory_usage(self) -> int:
        """Get current memory usage in bytes."""
        return sum(e.size_bytes for e in self._cache.values())

    def _ensure_space(self, needed_bytes: int):
        """Evict entries until enough space is available."""
        while self.get_memory_usage() + needed_bytes > self.max_memory_bytes and self._cache:
            self.evict(1)
