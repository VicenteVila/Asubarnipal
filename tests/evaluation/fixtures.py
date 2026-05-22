"""Test fixtures for evaluation scenarios."""

from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class TestURL:
    """URL fixture for ingest/research tests."""
    url: str
    expected_type: str
    expected_keywords: list[str] = field(default_factory=list)


TEST_URLS = {
    "arxiv_attention": TestURL(
        url="https://arxiv.org/abs/1706.03762",
        expected_type="paper",
        expected_keywords=["attention", "transformer", "neural"],
    ),
    "arxiv_bert": TestURL(
        url="https://arxiv.org/abs/1810.04805",
        expected_type="paper",
        expected_keywords=["BERT", "pre-training", "language"],
    ),
    "arxiv_lora": TestURL(
        url="https://arxiv.org/abs/2106.09685",
        expected_type="paper",
        expected_keywords=["LoRA", "adaptation", "fine-tuning"],
    ),
}


@dataclass
class TestQuery:
    """Query fixture for search tests."""
    question: str
    expected_keywords: list[str] = field(default_factory=list)
    mode: str = "wiki"


TEST_QUERIES = {
    "attention": TestQuery(
        question="Que es el mecanismo de attention?",
        expected_keywords=["attention", "pesos", "contexto"],
    ),
    "transformer": TestQuery(
        question="Como funciona un transformer?",
        expected_keywords=["encoder", "decoder", "self-attention"],
    ),
    "rag": TestQuery(
        question="Que es RAG y como funciona?",
        expected_keywords=["retrieval", "generacion", "contexto"],
    ),
    "fine_tuning": TestQuery(
        question="Que es fine-tuning?",
        expected_keywords=["ajuste", "entrenamiento", "modelo"],
    ),
}


@dataclass
class TestCharlaTopic:
    """Topic fixture for charlar tests."""
    topic: str
    mode: str
    expected_elements: list[str] = field(default_factory=list)


TEST_CHARLA_TOPICS = {
    "consultor_rag": TestCharlaTopic(
        topic="Como optimizar un pipeline RAG para produccion?",
        mode="consultor",
        expected_elements=["fase", "definicion", "ejecucion", "evaluacion"],
    ),
    "devil_llm_medico": TestCharlaTopic(
        topic="Es buena idea usar LLMs para diagnostico medico?",
        mode="devil",
        expected_elements=["riesgo", "error", "responsabilidad", "limitacion"],
    ),
    "libre_ia": TestCharlaTopic(
        topic="Que tendencias de IA son mas relevantes para 2025?",
        mode="libre",
        expected_elements=[],
    ),
    "socratico_conciencia": TestCharlaTopic(
        topic="Que es la consciencia?",
        mode="socratico",
        expected_elements=["pregunta", "que", "como"],
    ),
    "lateral_ninja": TestCharlaTopic(
        topic="Como percibiria un ninja un problema de arquitectura de software?",
        mode="lateral",
        expected_elements=["perspectiva", "angulo"],
    ),
}


@dataclass
class TestHMemEntry:
    """Memory entry fixture for H-Mem tests."""
    content: str
    metadata: dict[str, Any] = field(default_factory=dict)


TEST_HMEM_ENTRIES = [
    TestHMemEntry(
        content="El usuario trabaja en un proyecto de procesamiento de lenguaje natural",
        metadata={"category": "user_info", "type": "project"},
    ),
    TestHMemEntry(
        content="Prefiere modelos pequenos y eficientes para inferencia local",
        metadata={"category": "preference", "type": "model"},
    ),
    TestHMemEntry(
        content="El proyecto usa Ollama con qwen3.5:4b como modelo principal",
        metadata={"category": "technical", "type": "stack"},
    ),
]


@dataclass
class TestAgentTask:
    """Task fixture for agent tests."""
    task: str
    expected_skills: list[str] = field(default_factory=list)
    expected_output_keywords: list[str] = field(default_factory=list)


TEST_AGENT_TASKS = {
    "read_config": TestAgentTask(
        task="Lee el archivo config.py y resume las variables principales de configuracion",
        expected_skills=["read_file"],
        expected_output_keywords=["config", "variable", "path"],
    ),
    "list_files": TestAgentTask(
        task="Lista los archivos Python en el directorio core/",
        expected_skills=["list_files"],
        expected_output_keywords=[".py", "core"],
    ),
}


@dataclass
class TestSchedule:
    """Schedule fixture for research scheduler tests."""
    topic: str
    interval_minutes: int
    expected_keywords: list[str] = field(default_factory=list)


TEST_SCHEDULES = [
    TestSchedule(
        topic="noticias inteligencia artificial",
        interval_minutes=60,
        expected_keywords=["IA", "noticias"],
    ),
    TestSchedule(
        topic="avances en modelos de lenguaje",
        interval_minutes=120,
        expected_keywords=["LLM", "modelo"],
    ),
]


@dataclass
class TestAPIEndpoint:
    """API endpoint fixture."""
    method: str
    path: str
    body: Optional[dict] = None
    expected_status: int = 200
    expected_keys: list[str] = field(default_factory=list)


TEST_API_ENDPOINTS = [
    TestAPIEndpoint("GET", "/", expected_keys=["name", "version", "status"]),
    TestAPIEndpoint("GET", "/health", expected_keys=["status", "uptime_seconds"]),
    TestAPIEndpoint("GET", "/status", expected_keys=["alive", "timestamp"]),
    TestAPIEndpoint("GET", "/stats", expected_keys=["wiki_notes", "raw_sources"]),
    TestAPIEndpoint("GET", "/schedules", expected_keys=["schedules", "timestamp"]),
    TestAPIEndpoint("GET", "/vaults", expected_keys=["success", "vaults"]),
]


EVAL_CONFIG = {
    "max_brave_calls_per_run": 10,
    "brave_call_count": 0,
    "timeout_basic": 5,
    "timeout_intermediate": 15,
    "timeout_advanced": 60,
    "timeout_max": 120,
    "min_response_length": 20,
    "max_response_length": 4000,
}
