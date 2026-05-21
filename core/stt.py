"""Speech-to-Text module for voice message transcription."""

import os
import tempfile
from pathlib import Path
from typing import Optional, Tuple

from core.bot_logger import logger

_WHISPER_AVAILABLE = False
_WHISPER_MODEL = None

def _load_whisper() -> bool:
    """Load whisper model if available."""
    global _WHISPER_AVAILABLE, _WHISPER_MODEL
    if _WHISPER_AVAILABLE:
        return True
    try:
        import whisper
        model_name = os.getenv("WHISPER_MODEL", "base")
        _WHISPER_MODEL = whisper.load_model(model_name)
        _WHISPER_AVAILABLE = True
        logger.info(f"Whisper loaded with model: {model_name}")
        return True
    except ImportError:
        logger.warning("Whisper not available. Install with: pip install openai-whisper")
        return False
    except Exception as e:
        logger.error(f"Failed to load whisper: {e}")
        return False


def transcribe_audio(audio_path: str) -> Tuple[bool, str]:
    """Transcribe audio file to text.
    
    Returns:
        Tuple of (success, text_or_error)
    """
    if not _load_whisper():
        return False, "STT not available. Install openai-whisper: pip install openai-whisper"
    
    try:
        result = _WHISPER_MODEL.transcribe(audio_path)
        text = result.get("text", "").strip()
        if text:
            logger.info(f"Transcription successful: {len(text)} chars")
            return True, text
        else:
            return False, "No speech detected in audio"
    except Exception as e:
        logger.error(f"Transcription failed: {e}")
        return False, f"Transcription error: {str(e)}"


def transcribe_ogg(ogg_path: str) -> Tuple[bool, str]:
    """Transcribe OGG voice message from Telegram."""
    if not os.path.exists(ogg_path):
        return False, "Audio file not found"
    
    return transcribe_audio(ogg_path)
