"""Tests for KV Cache and Conversation Compressor modules."""

import torch
import pytest

from core.turboquant.kv_cache import KVCache, EvictionPolicy, KVCacheEntry, KVCacheStats
from core.turboquant.conversation_compressor import (
    ConversationCompressor,
    CompressionResult,
    CRITICAL_KEYWORDS,
)


class TestKVCache:
    def test_put_and_get(self):
        cache = KVCache(max_memory_mb=1024)
        k = torch.randn(1, 4, 64)
        v = torch.randn(1, 4, 64)
        cache.put("test", k, v)
        result = cache.get("test")
        assert result is not None
        retrieved_k, retrieved_v = result
        assert torch.equal(retrieved_k, k)
        assert torch.equal(retrieved_v, v)

    def test_get_missing_key(self):
        cache = KVCache(max_memory_mb=1024)
        result = cache.get("nonexistent")
        assert result is None

    def test_contains(self):
        cache = KVCache(max_memory_mb=1024)
        cache.put("key1", torch.randn(1, 4, 64), torch.randn(1, 4, 64))
        assert cache.contains("key1") is True
        assert cache.contains("key2") is False

    def test_eviction_lru(self):
        cache = KVCache(max_memory_mb=1, policy="lru")
        for i in range(5):
            cache.put(f"key{i}", torch.randn(1, 4, 64), torch.randn(1, 4, 64))
        cache.evict(2)
        assert cache.contains("key0") is False
        assert cache.contains("key1") is False

    def test_eviction_lfu(self):
        cache = KVCache(max_memory_mb=1, policy="lfu")
        for i in range(3):
            cache.put(f"key{i}", torch.randn(1, 4, 64), torch.randn(1, 4, 64))
        cache.get("key0")
        cache.get("key0")
        cache.get("key1")
        cache.evict(1)
        assert cache.contains("key2") is False

    def test_clear(self):
        cache = KVCache(max_memory_mb=1024)
        for i in range(3):
            cache.put(f"key{i}", torch.randn(1, 4, 64), torch.randn(1, 4, 64))
        cache.clear()
        assert cache.get_stats().num_entries == 0

    def test_get_many(self):
        cache = KVCache(max_memory_mb=1024)
        cache.put("a", torch.randn(1, 4, 64), torch.randn(1, 4, 64))
        cache.put("b", torch.randn(1, 4, 64), torch.randn(1, 4, 64))
        results = cache.get_many(["a", "b", "c"])
        assert len(results) == 2
        assert "a" in results
        assert "b" in results

    def test_stats_initial(self):
        cache = KVCache(max_memory_mb=1024)
        stats = cache.get_stats()
        assert stats.num_entries == 0
        assert stats.hit_count == 0
        assert stats.miss_count == 0
        assert stats.hit_rate == 0.0

    def test_stats_hit_rate(self):
        cache = KVCache(max_memory_mb=1024)
        cache.put("k", torch.randn(1, 4, 64), torch.randn(1, 4, 64))
        cache.get("k")
        cache.get("k")
        cache.get("missing")
        stats = cache.get_stats()
        assert stats.hit_count == 2
        assert stats.miss_count == 1
        assert stats.hit_rate == 2 / 3

    def test_max_memory_enforced(self):
        cache = KVCache(max_memory_mb=0.001, policy="lru")
        for i in range(100):
            cache.put(f"key{i}", torch.randn(1, 4, 64), torch.randn(1, 4, 64))
        assert cache.get_stats().num_entries < 20

    def test_device(self):
        cache = KVCache(max_memory_mb=1024, device="cpu")
        assert cache.device == "cpu"

    def test_eviction_policy_enum(self):
        assert EvictionPolicy.LRU.value == "lru"
        assert EvictionPolicy.LFU.value == "lfu"


class TestKVCacheEntry:
    def test_size_calculation(self):
        k = torch.randn(1, 4, 64)
        v = torch.randn(1, 4, 64)
        entry = KVCacheEntry(key=k, value=v)
        expected = k.element_size() * k.nelement() + v.element_size() * v.nelement()
        assert entry.size_bytes == expected


class TestKVCacheStats:
    def test_to_dict_keys(self):
        stats = KVCacheStats(
            num_entries=10, memory_used_mb=256.0, max_memory_mb=1024.0,
            hit_count=50, miss_count=10, eviction_count=5, hit_rate=0.833,
        )
        d = stats.to_dict()
        assert d["num_entries"] == 10
        assert d["hit_rate"] == 0.833
        assert "memory_usage_pct" in d


class TestConversationCompressor:
    def test_no_compression_needed(self):
        compressor = ConversationCompressor(max_messages=10)
        messages = [{"role": "user", "content": f"Message {i}"} for i in range(5)]
        result = compressor.compress(messages)
        assert len(result) == 5

    def test_compression_with_old_messages(self):
        compressor = ConversationCompressor(max_messages=5, summary_threshold=3)
        messages = [{"role": "user", "content": f"Message {i}"} for i in range(10)]
        result = compressor.compress(messages)
        assert len(result) < 10

    def test_preserves_critical_messages(self):
        compressor = ConversationCompressor(max_messages=3, summary_threshold=2)
        messages = [
            {"role": "user", "content": "normal message"},
            {"role": "assistant", "content": "decidí implementar X"},
            {"role": "user", "content": "otro normal"},
            {"role": "assistant", "content": "último mensaje"},
        ]
        result = compressor.compress(messages)
        contents = [m["content"] for m in result]
        assert any("decidí" in c for c in contents)

    def test_is_critical_tool_calls(self):
        compressor = ConversationCompressor()
        assert compressor._is_critical({"tool_calls": ["func1"]}) is True
        assert compressor._is_critical({"function_call": "func1"}) is True

    def test_is_critical_role(self):
        compressor = ConversationCompressor()
        assert compressor._is_critical({"role": "tool", "content": "result"}) is True
        assert compressor._is_critical({"role": "function", "content": "result"}) is True

    def test_is_critical_keywords(self):
        compressor = ConversationCompressor()
        assert compressor._is_critical({"role": "assistant", "content": "Decidí implementar"}) is True
        assert compressor._is_critical({"role": "assistant", "content": "la conclusión es"}) is True
        assert compressor._is_critical({"role": "assistant", "content": "mensaje normal"}) is False

    def test_summarize_empty(self):
        compressor = ConversationCompressor()
        assert compressor._summarize([]) == ""

    def test_summarize_short(self):
        compressor = ConversationCompressor()
        messages = [{"role": "user", "content": "Este es un mensaje de prueba con suficiente longitud para ser considerado."}]
        result = compressor._summarize(messages)
        assert len(result) > 0

    def test_extractive_summary(self):
        compressor = ConversationCompressor()
        text = "Primera oración importante. Segunda oración con información clave. Tercera oración con más detalles relevantes. Cuarta oración final."
        result = compressor._extractive_summary(text, max_sentences=2)
        assert "Primera" in result
        assert "final" in result

    def test_compress_too_short_for_summary(self):
        compressor = ConversationCompressor()
        text = "Corto."
        result = compressor._extractive_summary(text)
        assert "Corto" in result

    def test_compress_to_token_budget(self):
        compressor = ConversationCompressor(max_messages=5)
        messages = [{"role": "user", "content": "Mensaje largo " * 50} for _ in range(20)]
        result = compressor.compress_to_token_budget(messages, max_tokens=500)
        assert len(result) <= 20

    def test_compress_to_token_budget_already_within(self):
        compressor = ConversationCompressor()
        messages = [{"role": "user", "content": "short"} for _ in range(3)]
        result = compressor.compress_to_token_budget(messages, max_tokens=10000)
        assert len(result) == 3
