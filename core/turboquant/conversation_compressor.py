"""Conversation history compressor.

Compresses long conversation histories by summarizing non-critical messages
while preserving critical messages (tool calls, decisions) and recent context.
"""

import re
import logging
from typing import List, Dict, Optional, Any
from dataclasses import dataclass

logger = logging.getLogger(__name__)

CRITICAL_KEYWORDS = [
    "decidí", "decisión", "conclusión", "resultado",
    "decided", "decision", "conclusion", "result",
    "acordamos", "acuerdo", "approve", "aprobado",
]


@dataclass
class CompressionResult:
    """Result of compressing a conversation."""
    original_length: int
    compressed_length: int
    reduction_pct: float
    preserved_critical: int
    has_summary: bool

    def to_dict(self) -> Dict[str, Any]:
        return {
            "original_length": self.original_length,
            "compressed_length": self.compressed_length,
            "reduction_pct": round(self.reduction_pct, 1),
            "preserved_critical": self.preserved_critical,
            "has_summary": self.has_summary,
        }


class ConversationCompressor:
    """Compresor de historial conversacional.

    Estrategia:
    1. Mantener últimos N mensajes completos.
    2. Resumir mensajes antiguos.
    3. Preservar mensajes críticos (con herramientas, decisiones).

    Args:
        max_messages: Número máximo de mensajes a mantener completos.
        summary_threshold: Umbral para comenzar a resumir.
    """

    def __init__(self, max_messages: int = 50, summary_threshold: int = 20):
        self.max_messages = max_messages
        self.summary_threshold = summary_threshold

    def compress(self, messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Comprimir historial de conversación.

        Args:
            messages: Lista de mensajes con formato {"role": ..., "content": ...}.

        Returns:
            Lista comprimida de mensajes.
        """
        if len(messages) <= self.max_messages:
            return self._tag_length(len(messages), messages)

        recent = messages[-self.summary_threshold:]
        old = messages[:-self.summary_threshold]

        critical = [m for m in old if self._is_critical(m)]
        non_critical = [m for m in old if not self._is_critical(m)]

        summary_text = self._summarize(non_critical)
        compressed: List[Dict[str, Any]] = []

        if summary_text:
            compressed.append({
                "role": "system",
                "content": f"[Resumen de conversación anterior: {summary_text}]",
            })

        compressed.extend(critical)
        compressed.extend(recent)

        return self._tag_length(len(messages), compressed)

    def compress_to_token_budget(
        self,
        messages: List[Dict[str, Any]],
        max_tokens: int = 4096,
        tokenizer=None,
    ) -> List[Dict[str, Any]]:
        """Comprimir para cumplir un presupuesto de tokens.

        Args:
            messages: Lista de mensajes.
            max_tokens: Máximo de tokens permitidos.
            tokenizer: Tokenizer para contar tokens (default: len del texto/4).

        Returns:
            Lista comprimida de mensajes.
        """
        current_tokens = self._count_tokens(messages, tokenizer)
        if current_tokens <= max_tokens:
            return self._tag_length(len(messages), messages)

        self.max_messages = max(10, self.max_messages // 2)
        compressed = self.compress(messages)

        current_tokens = self._count_tokens(compressed, tokenizer)
        iteration = 0
        while current_tokens > max_tokens and iteration < 5:
            compressed = compressed[:-5]
            current_tokens = self._count_tokens(compressed, tokenizer)
            iteration += 1

        return self._tag_length(len(messages), compressed)

    def _is_critical(self, message: Dict[str, Any]) -> bool:
        """Determina si un mensaje es crítico."""
        if "tool_calls" in message or "function_call" in message:
            return True

        role = message.get("role", "")
        if role in ("tool", "function"):
            return True

        content = message.get("content", "")
        if any(kw in content.lower() for kw in CRITICAL_KEYWORDS):
            return True

        return False

    def _summarize(self, messages: List[Dict[str, Any]]) -> str:
        """Resume mensajes no críticos.

        Usa resumen extractivo simple (primeras/últimas oraciones).
        """
        if not messages:
            return ""

        texts = [m.get("content", "") for m in messages if m.get("content")]
        text = "\n".join(texts)

        return self._extractive_summary(text, max_sentences=3)

    def _extractive_summary(self, text: str, max_sentences: int = 3) -> str:
        """Genera resumen extractivo simple."""
        sentences = re.split(r'(?<=[.!?])\s+', text)
        sentences = [s.strip() for s in sentences if len(s.strip()) > 20]

        if not sentences:
            return text[:200]

        if len(sentences) <= max_sentences:
            return ". ".join(sentences) + "."

        first_half = max_sentences // 2
        selected = sentences[:first_half] + sentences[-(max_sentences - first_half):]

        return ". ".join(selected) + "."

    def _count_tokens(self, messages: List[Dict[str, Any]], tokenizer=None) -> int:
        """Cuenta tokens aproximados."""
        text = " ".join(m.get("content", "") for m in messages)
        if tokenizer is not None:
            return len(tokenizer.encode(text))
        return len(text) // 4  # aprox 4 chars por token

    def _tag_length(
        self, original: int, messages: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Añade metadata de compresión a los mensajes."""
        return messages
