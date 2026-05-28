"""Shared fixtures for integration tests."""

import os
import sys
import tempfile
import json
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch
from typing import Generator

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest.fixture
def temp_dir() -> Generator[Path, None, None]:
    """Create a temporary directory for test data."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def temp_db_path(temp_dir: Path) -> Path:
    """Create a temporary SQLite database path."""
    return temp_dir / "test.db"


@pytest.fixture
def mock_ollama_response() -> dict:
    """Mock Ollama chat response."""
    mock_msg = Mock()
    mock_msg.content = "This is a test response from Ollama"
    mock_msg.tool_calls = []
    
    mock_resp = Mock()
    mock_resp.message = mock_msg
    return mock_resp


@pytest.fixture
def mock_llm_router(mock_ollama_response: Mock) -> Generator[Mock, None, None]:
    """Mock LLMRouter with predefined responses."""
    with patch("core.llm_router.LLMRouter") as mock_class:
        mock_instance = Mock()
        mock_instance.chat.return_value = {
            "response": "Test response",
            "model": "qwen3.5:4b",
            "time": 0.5,
            "tool_calls": [],
        }
        mock_instance.generate.return_value = "Test generated text"
        mock_instance.use_ollama = True
        mock_instance.model = "qwen3.5:4b"
        mock_class.return_value = mock_instance
        yield mock_instance


@pytest.fixture
def mock_embeddings_model() -> Generator[Mock, None, None]:
    """Mock sentence-transformers embeddings model."""
    import numpy as np
    
    with patch("index.rag.get_embeddings_model") as mock_get:
        mock_model = Mock()
        mock_model.encode.return_value = np.random.rand(2, 384).astype(np.float32)
        mock_get.return_value = mock_model
        yield mock_model


@pytest.fixture
def mock_faiss() -> Generator[Mock, None, None]:
    """Mock FAISS index operations."""
    import numpy as np
    
    with patch("index.rag.faiss") as mock_faiss_module:
        mock_index = Mock()
        mock_index.ntotal = 0
        mock_index.search.return_value = (
            np.array([[0.9, 0.8, 0.7]]),
            np.array([[0, 1, 2]])
        )
        mock_faiss_module.IndexFlatIP.return_value = mock_index
        mock_faiss_module.read_index.return_value = mock_index
        yield mock_faiss_module


@pytest.fixture
def sample_wiki_note() -> dict:
    """Sample wiki note with frontmatter."""
    return {
        "title": "Test Entity",
        "tipo": "entity",
        "fuente": "test",
        "fecha_ingesta": "2024-01-01",
        "fecha_actualizacion": "2024-01-01",
        "estado": "draft",
        "tags": ["test", "entity"],
        "relacionados": ["Related Note"],
        "content": "This is a test entity for integration testing.",
    }


@pytest.fixture
def sample_memory_content() -> str:
    """Sample memory content for H-Mem tests."""
    return "The AI agent system uses RAG for knowledge retrieval and H-Mem for persistent memory."


@pytest.fixture
def mock_fastapi_app() -> Generator[Mock, None, None]:
    """Mock FastAPI application for API tests."""
    with patch("api.main.app") as mock_app:
        mock_app.title = "Asubarnipal API"
        mock_app.version = "2.0.0"
        yield mock_app


@pytest.fixture
def mock_telegram_update() -> Mock:
    """Mock Telegram update object."""
    mock_message = Mock()
    mock_message.text = "/test"
    mock_message.message_id = 123
    mock_message.date = 1700000000
    
    mock_user = Mock()
    mock_user.id = 42
    mock_user.first_name = "TestUser"
    mock_user.username = "testuser"
    mock_message.from_user = mock_user
    
    mock_chat = Mock()
    mock_chat.id = 42
    mock_chat.type = "private"
    mock_message.chat = mock_chat
    
    mock_update = Mock()
    mock_update.message = mock_message
    return mock_update


@pytest.fixture
def mock_vault_manager() -> Generator[Mock, None, None]:
    """Mock VaultManager for vault isolation tests."""
    with patch("core.vault_manager.VaultManager") as mock_class:
        mock_instance = Mock()
        mock_instance.get_active.return_value = {"name": "default", "path": "/tmp/test_vault"}
        mock_instance.list_vaults.return_value = [
            {"name": "default", "path": "/tmp/test_vault", "active": True},
            {"name": "test_vault", "path": "/tmp/test_vault_2", "active": False},
        ]
        mock_class.return_value = mock_instance
        yield mock_instance


@pytest.fixture
def sample_rag_chunks() -> list[dict]:
    """Sample RAG chunks for ingestion tests."""
    return [
        {
            "text": "First chunk about AI agents and their capabilities.",
            "metadata": {"source": "test", "chunk_idx": 0},
        },
        {
            "text": "Second chunk about RAG systems and vector search.",
            "metadata": {"source": "test", "chunk_idx": 1},
        },
        {
            "text": "Third chunk about memory systems and knowledge graphs.",
            "metadata": {"source": "test", "chunk_idx": 2},
        },
    ]


@pytest.fixture
def mock_brave_response() -> dict:
    """Mock Brave Search API response."""
    return {
        "web": {
            "results": [
                {
                    "title": "Test Result 1",
                    "url": "https://example.com/1",
                    "description": "Description of test result 1",
                },
                {
                    "title": "Test Result 2",
                    "url": "https://example.com/2",
                    "description": "Description of test result 2",
                },
            ]
        }
    }


@pytest.fixture
def mock_gemini_response() -> dict:
    """Mock Gemini API response."""
    return {
        "candidates": [
            {
                "content": {
                    "parts": [{"text": "Gemini test response"}]
                }
            }
        ]
    }


@pytest.fixture
def async_client():
    """Create an async HTTP client for API tests."""
    try:
        import httpx
        return httpx.AsyncClient
    except ImportError:
        return None
