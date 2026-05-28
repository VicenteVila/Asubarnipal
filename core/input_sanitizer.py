"""Input sanitization for Telegram and API inputs."""

import re
import html
from typing import Optional


MAX_INPUT_LENGTH = 4096
MAX_QUERY_LENGTH = 2000
MAX_COMMAND_LENGTH = 500


def sanitize_text(text: str, max_length: int = MAX_INPUT_LENGTH) -> str:
    """
    Sanitize user input text.
    
    - Truncates to max_length
    - Removes null bytes
    - Strips leading/trailing whitespace
    - Normalizes whitespace
    """
    if not text:
        return ""
    
    text = text[:max_length]
    text = text.replace("\x00", "")
    text = text.strip()
    text = re.sub(r"\s+", " ", text)
    
    return text


def sanitize_query(query: str) -> str:
    """Sanitize RAG/search query."""
    return sanitize_text(query, max_length=MAX_QUERY_LENGTH)


def sanitize_command(command: str) -> str:
    """Sanitize command input."""
    cleaned = sanitize_text(command, max_length=MAX_COMMAND_LENGTH)
    cleaned = re.sub(r"[^\w\s\/\-\.\?\!\,\:\;\(\)]", "", cleaned)
    return cleaned


def escape_html(text: str) -> str:
    """Escape HTML entities to prevent XSS."""
    return html.escape(text, quote=True)


def prevent_prompt_injection(text: str) -> str:
    """
    Detect and neutralize potential prompt injection attempts.
    
    Patterns detected:
    - System prompt overrides
    - Role-playing attempts
    - Instruction overrides
    """
    injection_patterns = [
        r"(?i)ignore\s+previous\s+instructions",
        r"(?i)you\s+are\s+now\s+",
        r"(?i)system\s*:\s*",
        r"(?i)role\s*:\s*system",
        r"(?i)disregard\s+all\s+prior",
        r"(?i)forget\s+everything",
        r"(?i)new\s+instructions?\s*:",
        r"(?i)act\s+as\s+",
        r"(?i)pretend\s+to\s+be\s+",
        r"<\|.*?\|>",
        r"\[INST\].*?\[/INST\]",
        r"###\s*(System|Instruction|User|Assistant)",
    ]
    
    cleaned = text
    for pattern in injection_patterns:
        if re.search(pattern, cleaned):
            cleaned = re.sub(pattern, "[REDACTED]", cleaned, flags=re.IGNORECASE)
    
    return cleaned


def validate_telegram_message(text: str) -> tuple[bool, str]:
    """
    Validate a Telegram message.
    
    Returns:
        (is_valid, sanitized_text) or (False, error_message)
    """
    if not text or not text.strip():
        return False, "Empty message"
    
    if len(text) > MAX_INPUT_LENGTH:
        return False, f"Message too long (max {MAX_INPUT_LENGTH} chars)"
    
    sanitized = sanitize_text(text)
    sanitized = prevent_prompt_injection(sanitized)
    
    return True, sanitized


def validate_api_input(data: dict, required_fields: list[str]) -> tuple[bool, str]:
    """
    Validate API input data.
    
    Returns:
        (is_valid, error_message)
    """
    for field in required_fields:
        if field not in data:
            return False, f"Missing required field: {field}"
        
        value = data[field]
        if isinstance(value, str):
            if not value.strip():
                return False, f"Field '{field}' cannot be empty"
            
            if len(value) > MAX_INPUT_LENGTH:
                return False, f"Field '{field}' too long (max {MAX_INPUT_LENGTH} chars)"
    
    return True, ""


def sanitize_url(url: str) -> tuple[bool, str]:
    """
    Validate and sanitize URL input.
    
    Returns:
        (is_valid, sanitized_url) or (False, error_message)
    """
    if not url:
        return False, "Empty URL"
    
    url = url.strip()
    
    if len(url) > 2048:
        return False, "URL too long (max 2048 chars)"
    
    url_pattern = re.compile(
        r"^https?://"
        r"(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|"
        r"localhost|"
        r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})"
        r"(?::\d+)?"
        r"(?:/?|[/?]\S+)$",
        re.IGNORECASE,
    )
    
    if not url_pattern.match(url):
        return False, "Invalid URL format"
    
    return True, url
