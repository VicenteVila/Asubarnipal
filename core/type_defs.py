"""Shared type definitions for Asubarnipal V2."""

from __future__ import annotations

from typing import Any, TypedDict, Optional
from datetime import datetime


class MessageDict(TypedDict, total=False):
    """Standard message format for LLM interactions."""
    role: str
    content: str
    name: str
    tool_calls: list[dict[str, Any]]
    tool_call_id: str


class ToolCallDict(TypedDict, total=False):
    """Tool call structure from LLM responses."""
    id: str
    type: str
    function: dict[str, str]


class LLMResponse(TypedDict, total=False):
    """Standardized LLM response structure."""
    response: str
    model: str
    time: float
    tool_calls: list[ToolCallDict]
    error: str
    turbo: dict[str, Any]


class RetrievalResult(TypedDict, total=False):
    """Result from H-Mem retrieval operations."""
    node: dict[str, Any]
    content: str
    semantic_sim: float
    temporal_relevance: float
    robustness: float
    combined_score: float
    level: int
    timestamp: str
    metadata: dict[str, Any]


class MemoryEvidence(TypedDict, total=False):
    """Memory evidence from tree or graph retrieval."""
    source: str
    entity_type: str
    content: str
    metadata: dict[str, Any]
    score: float


class VaultConfig(TypedDict, total=False):
    """Vault configuration structure."""
    name: str
    path: str
    db_path: str
    index_path: str
    created_at: str
    last_used: str
    active: bool


class QueryPlan(TypedDict, total=False):
    """Query planning structure for H-Mem retrieval."""
    sub_queries: list[dict[str, Any]]
    temporal_hints: list[str]
    focus: str


class SubQuery(TypedDict, total=False):
    """Individual sub-query in a retrieval plan."""
    query: str
    scope: str
    time_range: Optional[tuple[str, str]]
    entities: list[str]


class TurboStateDict(TypedDict, total=False):
    """TurboQuant engine state."""
    mode: Optional[str]
    model: Optional[str]
    context: int
    cache_k: str
    cache_v: str
    is_applied: bool
    last_applied: Optional[str]


class EntityDict(TypedDict, total=False):
    """Entity structure for knowledge graph."""
    name: str
    entity_type: str
    profile: str
    created_at: str
    updated_at: str
    relations: int
    robustness: float


class RelationDict(TypedDict, total=False):
    """Relation structure between entities."""
    source: str
    target: str
    relation_type: str
    strength: float
    created_at: str


class WikiNoteDict(TypedDict, total=False):
    """Wiki note metadata structure."""
    title: str
    path: str
    tipo: str
    fuente: str
    fecha_ingesta: str
    fecha_actualizacion: str
    estado: str
    tags: list[str]
    relacionados: list[str]


class FeedSubscriptionDict(TypedDict, total=False):
    """RSS feed subscription structure."""
    url: str
    name: str
    interval: int
    last_check: str
    alerts: int
    enabled: bool


class BackupInfoDict(TypedDict, total=False):
    """Backup metadata structure."""
    name: str
    path: str
    size: int
    created_at: str
    vault: str
    type: str


class ScheduledJobDict(TypedDict, total=False):
    """Scheduled research job structure."""
    id: str
    topic: str
    interval_minutes: int
    enabled: bool
    last_run: Optional[str]
    next_run: Optional[str]
    created_at: str


class AgentStateDict(TypedDict, total=False):
    """Agent runtime state structure."""
    mode: str
    model: str
    messages_count: int
    tokens_used: int
    session_start: str
    last_activity: str
    current_task: Optional[str]


class HeartbeatDict(TypedDict, total=False):
    """System heartbeat metrics."""
    timestamp: str
    cpu_percent: float
    ram_percent: float
    ram_used_mb: float
    ram_total_mb: float
    uptime_seconds: float


class MetricsDict(TypedDict, total=False):
    """API metrics structure."""
    total_requests: int
    total_errors: int
    error_rate: float
    requests_by_endpoint: dict[str, int]
    avg_response_time: float
    timestamp: str
