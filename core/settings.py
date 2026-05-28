"""Pydantic-based settings with validation."""

from pathlib import Path
from typing import Optional
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class OllamaSettings(BaseSettings):
    """Ollama LLM configuration."""
    base_url: str = Field(default="http://127.0.0.1:11434", description="Ollama API URL")
    model: str = Field(default="qwen3.5:4b", description="Default Ollama model")
    models_path: str = Field(default="", description="Path to Ollama models directory")
    ocr_model: str = Field(default="glm-ocr:latest", description="OCR model for image/PDF text extraction")

    model_config = SettingsConfigDict(env_prefix="OLLAMA_")


class GeminiSettings(BaseSettings):
    """Google Gemini configuration."""
    keys: str = Field(default="", description="Comma-separated Gemini API keys")

    @property
    def key_list(self) -> list[str]:
        return [k.strip() for k in self.keys.split(",") if k.strip()]

    model_config = SettingsConfigDict(env_prefix="GEMINI_")


class BraveSettings(BaseSettings):
    """Brave Search configuration."""
    api_key: str = Field(default="", description="Brave Search API key")
    monthly_limit: int = Field(default=1500, description="Monthly API request limit")

    model_config = SettingsConfigDict(env_prefix="BRAVE_")


class HuggingFaceSettings(BaseSettings):
    """Hugging Face configuration."""
    token: str = Field(default="", description="Hugging Face API token")

    model_config = SettingsConfigDict(env_prefix="HF_")


class RAGSettings(BaseSettings):
    """RAG vector search configuration."""
    model: str = Field(
        default="sentence-transformers/paraphrase-multilingual-mpnet-base-v2",
        description="Sentence transformer model for embeddings"
    )
    device: str = Field(default="cpu", description="Device for embeddings (cpu/cuda)")

    model_config = SettingsConfigDict(env_prefix="RAG_")


class TurboQuantSettings(BaseSettings):
    """TurboQuant LLM optimization configuration."""
    enabled: bool = Field(default=True, description="Enable TurboQuant optimization")
    default_mode: str = Field(default="consultor", description="Default chat mode")
    auto_detect: bool = Field(default=True, description="Auto-detect hardware capabilities")

    model_config = SettingsConfigDict(env_prefix="TURBOQUANT_")


class BackgroundSettings(BaseSettings):
    """Background ritual configuration."""
    enable_heartbeat: bool = Field(default=True, description="Enable heartbeat logging")
    heartbeat_interval: int = Field(default=60, description="Heartbeat interval in seconds")
    suture_interval: int = Field(default=600, description="Wiki suture interval in seconds")
    graph_interval: int = Field(default=1800, description="Graph rebuild interval in seconds")

    model_config = SettingsConfigDict(env_prefix="")


class AppSettings(BaseSettings):
    """Main application settings."""
    telegram_token: str = Field(default="", description="Telegram bot token")
    default_model: str = Field(default="auto", description="Default model selection (ollama/gemini/auto)")
    obsidian_path: str = Field(default="", description="Path to Obsidian vault")

    ollama: OllamaSettings = Field(default_factory=OllamaSettings)
    gemini: GeminiSettings = Field(default_factory=GeminiSettings)
    brave: BraveSettings = Field(default_factory=BraveSettings)
    huggingface: HuggingFaceSettings = Field(default_factory=HuggingFaceSettings)
    rag: RAGSettings = Field(default_factory=RAGSettings)
    turboquant: TurboQuantSettings = Field(default_factory=TurboQuantSettings)
    background: BackgroundSettings = Field(default_factory=BackgroundSettings)

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @field_validator("telegram_token")
    @classmethod
    def validate_telegram_token(cls, v: str) -> str:
        if v and not v.startswith(("bot", "test_")):
            raise ValueError("Telegram token must start with 'bot'")
        return v

    @property
    def base_dir(self) -> Path:
        return Path(__file__).parent.parent

    @property
    def data_dir(self) -> Path:
        return self.base_dir / "data"

    @property
    def index_dir(self) -> Path:
        return self.base_dir / "index"

    @property
    def storage_dir(self) -> Path:
        return self.base_dir / "storage"

    @property
    def wiki_dir(self) -> Path:
        obsidian = Path(self.obsidian_path) if self.obsidian_path else self.base_dir.parent / "Obsidian"
        return obsidian / "wiki"

    @property
    def raw_dir(self) -> Path:
        obsidian = Path(self.obsidian_path) if self.obsidian_path else self.base_dir.parent / "Obsidian"
        return obsidian / "raw"

    def ensure_directories(self) -> None:
        """Create necessary directories."""
        for d in [self.data_dir, self.index_dir, self.storage_dir]:
            d.mkdir(parents=True, exist_ok=True)


_settings: Optional[AppSettings] = None


def get_settings() -> AppSettings:
    """Get application settings singleton."""
    global _settings
    if _settings is None:
        _settings = AppSettings()
    return _settings


def reset_settings() -> None:
    """Reset settings (useful for testing)."""
    global _settings
    _settings = None
