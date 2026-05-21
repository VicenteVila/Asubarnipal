"""TurboQuant Base Configuration for CPU."""

from dataclasses import dataclass
from typing import Dict, Optional
import os

@dataclass
class CompressionFormat:
    """Compression format for KV Cache."""
    name: str
    bits: float
    quality: float  # 0-1, quality preservation
    speed: float    # relative speed factor

    @property
    def compression_ratio(self) -> float:
        """Estimated compression ratio vs FP16."""
        return 16 / self.bits


COMPRESSION_FORMATS = {
    "q8_0": CompressionFormat("q8_0", 8.0, 1.0, 0.7),
    "turbo4": CompressionFormat("turbo4", 4.25, 0.95, 0.9),
    "turbo3": CompressionFormat("turbo3", 3.25, 0.88, 1.1),
    "turbo2": CompressionFormat("turbo2", 2.5, 0.82, 1.3),
}


@dataclass
class CPUConfig:
    """CPU configuration based on available memory."""
    name: str
    context: int
    batch: int
    threads: Optional[int] = None

    @classmethod
    def detect(cls) -> 'CPUConfig':
        """Auto-detect CPU config based on available memory."""
        mem_gb = cls._get_available_memory_gb()

        if mem_gb >= 16:
            return cls("high_mem", 65_536, 1024)
        elif mem_gb >= 8:
            return cls("medium_mem", 32_768, 512)
        else:
            return cls("low_mem", 16_384, 256)

    @staticmethod
    def _get_available_memory_gb() -> float:
        """Get available memory in GB."""
        try:
            import psutil
            return psutil.virtual_memory().available / (1024**3)
        except ImportError:
            try:
                import shutil
                return shutil.disk_usage('/').total / (1024**3)
            except:
                return 8.0  # fallback


@dataclass
class ModelConfig:
    """Configuration for a specific model."""
    name: str
    size_gb: float
    context_max: int
    recommended_context: int
    cache_k: str
    cache_v: str
    priority: str  # "speed", "balanced", "quality"


MODEL_CONFIGS = {
    "nemotron-3-nano:4b": ModelConfig(
        name="nemotron-3-nano:4b",
        size_gb=2.8,
        context_max=16_384,
        recommended_context=8_192,
        cache_k="turbo4",
        cache_v="turbo4",
        priority="speed"
    ),
    "qwen3.5:4b": ModelConfig(
        name="qwen3.5:4b",
        size_gb=3.4,
        context_max=128_000,
        recommended_context=32_768,
        cache_k="q8_0",
        cache_v="turbo4",
        priority="balanced"
    ),
    "qwen3:8b": ModelConfig(
        name="qwen3:8b",
        size_gb=5.2,
        context_max=32_768,
        recommended_context=16_384,
        cache_k="q8_0",
        cache_v="q8_0",
        priority="quality"
    ),
    "gemma4:e4b": ModelConfig(
        name="gemma4:e4b",
        size_gb=9.6,
        context_max=32_768,
        recommended_context=16_384,
        cache_k="q8_0",
        cache_v="q8_0",
        priority="quality"
    ),
    "qwen3.5:9b": ModelConfig(
        name="qwen3.5:9b",
        size_gb=6.6,
        context_max=64_000,
        recommended_context=32_768,
        cache_k="turbo4",
        cache_v="turbo3",
        priority="balanced"
    ),
    "llama3.2:latest": ModelConfig(
        name="llama3.2:latest",
        size_gb=2.0,
        context_max=128_000,
        recommended_context=32_768,
        cache_k="turbo2",
        cache_v="turbo3",
        priority="speed"
    ),
}


def get_model_config(model_name: str) -> Optional[ModelConfig]:
    """Get model config by name, with fuzzy matching."""
    if model_name in MODEL_CONFIGS:
        return MODEL_CONFIGS[model_name]

    for key in MODEL_CONFIGS:
        if key.split(":")[0] in model_name.lower():
            return MODEL_CONFIGS[key]

    return None


def estimate_context_limit(model_name: str, available_ram_gb: float = 8) -> int:
    """Estimate max context for a model given available RAM."""
    model_cfg = get_model_config(model_name)

    if not model_cfg:
        return 16_384  # default

    reserved = model_cfg.size_gb * 1.5
    available = available_ram_gb - reserved

    if available <= 0:
        return 8_192

    tokens_per_gb = 4096
    estimated = int(available * tokens_per_gb)

    return min(estimated, model_cfg.context_max)


def get_default_cpu_config() -> CPUConfig:
    """Get default CPU config."""
    return CPUConfig.detect()