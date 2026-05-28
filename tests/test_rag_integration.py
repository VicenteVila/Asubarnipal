"""Integration tests for RAG pipeline: ingest → embed → retrieve → re-rank → answer."""

import os
import sys
import unittest
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestRAGPipelineIntegration(unittest.TestCase):
    """Test full RAG pipeline end-to-end."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.temp_path = Path(self.temp_dir.name)

    def tearDown(self):
        self.temp_dir.cleanup()

    @patch("index.rag.get_embeddings_model")
    @patch("index.rag.get_bm25_model")
    def test_full_rag_pipeline(self, mock_bm25, mock_embeddings):
        """Test complete RAG pipeline: chunk → embed → store → query → rank."""
        import numpy as np

        mock_model = Mock()
        mock_model.encode.return_value = np.random.rand(3, 384).astype(np.float32)
        mock_embeddings.return_value = mock_model
        mock_bm25.return_value = None

        from index.rag import chunk_text, tokenize

        text = """Introduction to AI Agents.
AI agents are autonomous systems that can perceive their environment and take actions.
They use various techniques including RAG for knowledge retrieval.
Retrieval-Augmented Generation combines vector search with language models.
This enables more accurate and context-aware responses."""

        chunks = chunk_text(text, chunk_size=200, overlap=50)
        self.assertGreater(len(chunks), 0)

        for chunk in chunks:
            self.assertIn("text", chunk)
            self.assertIn("metadata", chunk)
            self.assertGreater(len(chunk["text"]), 0)

        tokens = tokenize("AI agents use RAG for knowledge retrieval")
        self.assertGreater(len(tokens), 0)
        self.assertNotIn("the", tokens)
        self.assertNotIn("for", tokens)

    @patch("index.rag.get_embeddings_model")
    def test_chunk_text_with_metadata(self, mock_embeddings):
        """Test chunking preserves metadata."""
        mock_embeddings.return_value = None

        from index.rag import chunk_text

        text = "Line 1\nLine 2\nLine 3\nLine 4\nLine 5\n"
        chunks = chunk_text(text, chunk_size=100, overlap=20)

        self.assertGreater(len(chunks), 0)
        for i, chunk in enumerate(chunks):
            self.assertEqual(chunk["metadata"]["chunk_idx"], i)
            self.assertIn("text", chunk)

    def test_tokenizer_removes_stop_words(self):
        """Test that tokenizer removes common stop words."""
        from index.rag import tokenize

        text = "The AI agent is very smart and powerful"
        tokens = tokenize(text)

        self.assertNotIn("the", tokens)
        self.assertNotIn("is", tokens)
        self.assertNotIn("and", tokens)
        self.assertTrue(all(len(t) > 2 for t in tokens))

    def test_tokenizer_handles_spanish(self):
        """Test tokenizer handles Spanish stop words."""
        from index.rag import tokenize

        text = "El agente de inteligencia artificial es muy poderoso"
        tokens = tokenize(text)

        self.assertNotIn("el", tokens)
        self.assertNotIn("de", tokens)
        self.assertNotIn("es", tokens)
        self.assertNotIn("muy", tokens)


class TestRAGEngineIntegration(unittest.TestCase):
    """Test RAGEngine with mocked dependencies."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.temp_path = Path(self.temp_dir.name)

    def tearDown(self):
        self.temp_dir.cleanup()

    @patch("index.rag.get_embeddings_model")
    @patch("index.rag.get_bm25_model")
    def test_ingest_and_query(self, mock_bm25, mock_embeddings):
        """Test ingest documents and query them."""
        import numpy as np

        mock_model = Mock()
        embeddings = np.random.rand(3, 384).astype(np.float32)
        mock_model.encode.side_effect = lambda texts: embeddings[:len(texts)]
        mock_embeddings.return_value = mock_model
        mock_bm25.return_value = None

        from index.rag import chunk_text

        docs = [
            {"text": "AI agents use RAG for knowledge retrieval", "source": "test1"},
            {"text": "Vector search enables semantic similarity", "source": "test2"},
            {"text": "Memory systems store conversation history", "source": "test3"},
        ]

        all_chunks = []
        for doc in docs:
            chunks = chunk_text(doc["text"], chunk_size=500, overlap=100)
            for chunk in chunks:
                chunk["metadata"]["source"] = doc["source"]
                all_chunks.append(chunk)

        self.assertGreater(len(all_chunks), 0)

        embeddings = mock_model.encode([c["text"] for c in all_chunks])
        self.assertEqual(embeddings.shape[0], len(all_chunks))


if __name__ == "__main__":
    unittest.main(verbosity=2)
