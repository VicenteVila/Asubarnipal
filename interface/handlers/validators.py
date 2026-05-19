"""Input validation helpers for handlers."""

import re
from typing import Optional, Tuple

URL_REGEX = re.compile(
    r'^https?://'
    r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'
    r'localhost|'
    r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'
    r'(?::\d+)?'
    r'(?:/?|[/?]\S+)$',
    re.IGNORECASE
)


def validate_url(url: str) -> Tuple[bool, Optional[str]]:
    """Validate URL format and length."""
    if not url:
        return False, "URL vacía"
    
    url = url.strip()
    
    if len(url) > 2000:
        return False, "URL demasiado larga (max 2000 chars)"
    
    if not URL_REGEX.match(url):
        return False, "URL inválida (debe empezar con http:// o https://)"
    
    return True, None


def validate_task(task: str, max_len: int = 500) -> Tuple[bool, Optional[str]]:
    """Validate agent task input."""
    if not task:
        return False, "Tarea vacía"
    
    task = task.strip()
    
    if len(task) < 3:
        return False, "Tarea demasiado corta (min 3 chars)"
    
    if len(task) > max_len:
        return False, f"Tarea demasiado larga (max {max_len} chars)"
    
    return True, None


def validate_query(query: str, max_len: int = 300) -> Tuple[bool, Optional[str]]:
    """Validate search query input."""
    if not query:
        return False, "Consulta vacía"
    
    query = query.strip()
    
    if len(query) < 2:
        return False, "Consulta demasiado corta (min 2 chars)"
    
    if len(query) > max_len:
        return False, f"Consulta demasiado larga (max {max_len} chars)"
    
    return True, None


def validate_topic(topic: str, max_len: int = 200) -> Tuple[bool, Optional[str]]:
    """Validate research topic input."""
    if not topic:
        return False, "Tema vacío"
    
    topic = topic.strip()
    
    if len(topic) < 3:
        return False, "Tema demasiado corto (min 3 chars)"
    
    if len(topic) > max_len:
        return False, f"Tema demasiado largo (max {max_len} chars)"
    
    return True, None


def sanitize_input(text: str, max_len: int = 1000) -> str:
    """Sanitize user input - strip whitespace and truncate."""
    if not text:
        return ""
    text = text.strip()
    return text[:max_len]