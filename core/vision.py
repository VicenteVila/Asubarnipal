"""Vision module - Image analysis via Ollama vision models."""

import base64
import os
import tempfile
from pathlib import Path
from typing import Optional, Tuple

import requests

import config
from core.bot_logger import logger

_OLLAMA_VISION_MODEL = os.getenv("OLLAMA_VISION_MODEL", "llava:7b")


def _encode_image(image_path: str) -> str:
    """Encode image to base64."""
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def analyze_image(
    image_path: str,
    prompt: str = "Describe this image in detail.",
    model: Optional[str] = None,
) -> Tuple[bool, str]:
    """Analyze an image using Ollama vision model.
    
    Returns:
        Tuple of (success, description_or_error)
    """
    model = model or _OLLAMA_VISION_MODEL
    
    if not os.path.exists(image_path):
        return False, "Image file not found"
    
    try:
        base64_image = _encode_image(image_path)
        
        payload = {
            "model": model,
            "prompt": prompt,
            "images": [base64_image],
            "stream": False,
        }
        
        resp = requests.post(
            f"{config.OLLAMA_BASE_URL}/api/generate",
            json=payload,
            timeout=120,
        )
        
        if resp.status_code == 200:
            result = resp.json()
            response_text = result.get("response", "").strip()
            if response_text:
                logger.info(f"Image analysis successful: {len(response_text)} chars")
                return True, response_text
            else:
                return False, "No response from vision model"
        else:
            return False, f"Ollama error: {resp.status_code} - {resp.text[:200]}"
            
    except requests.ConnectionError:
        return False, f"Cannot connect to Ollama at {config.OLLAMA_BASE_URL}. Is it running?"
    except Exception as e:
        logger.error(f"Image analysis failed: {e}")
        return False, f"Analysis error: {str(e)}"


def analyze_photo_telegram(photo_path: str) -> Tuple[bool, str]:
    """Analyze a Telegram photo with default prompt."""
    return analyze_image(
        photo_path,
        prompt="Describe what you see in this image. Include any text, objects, people, and context.",
    )


def extract_text_from_image(image_path: str) -> Tuple[bool, str]:
    """Extract text from image (OCR via vision model)."""
    return analyze_image(
        image_path,
        prompt="Extract all text from this image. Return only the text, nothing else.",
    )


def is_vision_available() -> bool:
    """Check if vision model is available."""
    try:
        resp = requests.get(f"{config.OLLAMA_BASE_URL}/api/tags", timeout=5)
        if resp.status_code == 200:
            models = [m.get("name", "") for m in resp.json().get("models", [])]
            return any("llava" in m or "vision" in m for m in models)
    except Exception:
        pass
    return False
