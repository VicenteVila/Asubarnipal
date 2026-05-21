"""TurboQuant Mode Configurations for /charlar integration."""

from dataclasses import dataclass
from typing import Dict, Optional
from .turboquant_config import COMPRESSION_FORMATS


@dataclass
class ChatModeConfig:
    """TurboQuant configuration for a chat mode."""
    name: str
    emoji: str
    context: int
    cache_k: str
    cache_v: str
    priority: str  # "speed", "balanced", "quality"
    description: str
    model: str = ""  # Ollama model for this mode


CHAT_MODE_TURBO: Dict[str, ChatModeConfig] = {
    "libre": ChatModeConfig(
        name="Charla Libre",
        emoji="💬",
        context=8_192,
        cache_k="turbo4",
        cache_v="turbo4",
        priority="speed",
        description="Conversación natural - velocidad óptima",
        model="nemotron-3-nano:4b"
    ),
    "consultor": ChatModeConfig(
        name="Consultor",
        emoji="🧠",
        context=64_000,
        cache_k="q8_0",
        cache_v="turbo4",
        priority="balanced",
        description="Análisis en 3 fases - balance calidad/velocidad",
        model="qwen3:8b"
    ),
    "devil": ChatModeConfig(
        name="Devil's Advocate",
        emoji="🔥",
        context=16_384,
        cache_k="q8_0",
        cache_v="q8_0",
        priority="quality",
        description="Crítica implacable - máxima calidad",
        model="gemma4:e4b"
    ),
    "socratico": ChatModeConfig(
        name="Maestro Socrático",
        emoji="❓",
        context=48_000,
        cache_k="turbo4",
        cache_v="turbo3",
        priority="balanced",
        description="Preguntas socráticas - balance velocidad/contexto",
        model="qwen3.5:4b"
    ),
    "lateral": ChatModeConfig(
        name="Pensamiento Lateral",
        emoji="🌐",
        context=24_576,
        cache_k="turbo3",
        cache_v="turbo4",
        priority="speed",
        description="Perspectivas alternativas - velocidad alta",
        model="qwen3.5:9b"
    ),
}


def get_mode_config(mode: str) -> Optional[ChatModeConfig]:
    """Get TurboQuant config for a chat mode."""
    return CHAT_MODE_TURBO.get(mode.lower())


def get_all_modes() -> Dict[str, ChatModeConfig]:
    """Get all available mode configurations."""
    return CHAT_MODE_TURBO.copy()


def format_mode_summary(mode: str) -> str:
    """Format a summary string for a mode."""
    cfg = get_mode_config(mode)
    if not cfg:
        return "Modo desconocido"

    k_fmt = COMPRESSION_FORMATS.get(cfg.cache_k)
    v_fmt = COMPRESSION_FORMATS.get(cfg.cache_v)

    k_ratio = k_fmt.compression_ratio if k_fmt else 0
    v_ratio = v_fmt.compression_ratio if v_fmt else 0

    return (
        f"{cfg.emoji} *{cfg.name}*\n"
        f"   🤖 Modelo: `{cfg.model}`\n"
        f"   📏 Contexto: {cfg.context // 1024}K tokens\n"
        f"   💾 Cache K: {cfg.cache_k} ({k_ratio:.1f}x compr.)\n"
        f"   💾 Cache V: {cfg.cache_v} ({v_ratio:.1f}x compr.)\n"
        f"   ⚡ Prioridad: {cfg.priority}"
    )


def get_mode_for_priority(priority: str) -> str:
    """Get recommended mode based on priority preference."""
    priority_map = {
        "speed": ["libre", "lateral"],
        "balanced": ["consultor", "socratico"],
        "quality": ["devil"]
    }
    return priority_map.get(priority, ["consultor"])[0]