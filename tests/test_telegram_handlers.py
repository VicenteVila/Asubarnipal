"""Unit tests for telegram handlers."""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

import unittest
from unittest.mock import Mock, patch, AsyncMock, MagicMock
import asyncio


class MockUpdate:
    """Mock Telegram Update object."""
    def __init__(self, user_id=12345, first_name="Test", args=None):
        self.effective_user = Mock()
        self.effective_user.id = user_id
        self.effective_user.first_name = first_name
        self.message = MockMessage()
        self.effective_message = self.message
        self.callback_query = Mock()
        self.callback_query.data = None
        self._args = args or []


class MockMessage:
    """Mock Telegram Message with async reply_text."""
    def __init__(self):
        self.text = "test"
        self._reply = None
        self.document = None
        self.photo = None

    async def reply_text(self, text, parse_mode=None):
        self._reply = text
        return Mock()


class MockContext:
    """Mock Telegram CallbackContext."""
    def __init__(self, args=None):
        self.args = args or []


def run_async(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


class TestComandosHandlers(unittest.TestCase):
    """Test comandos.py handlers."""

    @patch('interface.handlers.comandos.logger')
    def test_start_cmd_response(self, mock_logger):
        from interface.handlers.comandos import start_cmd

        update = MockUpdate(first_name="TestUser")
        context = MockContext()

        run_async(start_cmd(update, context))

        self.assertIn("Bienvenido", update.message._reply)
        self.assertIn("TestUser", update.message._reply)

    @patch('interface.handlers.comandos.logger')
    def test_manual_cmd_response(self, mock_logger):
        from interface.handlers.comandos import manual_cmd

        update = MockUpdate()
        context = MockContext()

        run_async(manual_cmd(update, context))

        self.assertIn("Manual", update.message._reply)
        self.assertIn("/query", update.message._reply)


class TestWikiHandlers(unittest.TestCase):
    """Test wiki.py handlers."""

    @patch('interface.handlers.wiki.logger')
    @patch('core.wiki.Wiki')
    def test_query_cmd_with_results(self, mock_wiki_class, mock_logger):
        mock_wiki = Mock()
        mock_wiki.search.return_value = [
            {"name": "Python", "tipo": "concept"},
            {"name": "Python3", "tipo": "entity"}
        ]
        mock_wiki_class.return_value = mock_wiki

        from interface.handlers.wiki import query_cmd

        update = MockUpdate(args=["python"])
        context = MockContext(args=["python"])

        run_async(query_cmd(update, context))

        self.assertIn("Resultados para", update.message._reply)
        self.assertIn("Python", update.message._reply)

    def test_query_cmd_empty(self):
        with patch('core.wiki.Wiki') as mock_wiki_class:
            mock_wiki = Mock()
            mock_wiki.search.return_value = []
            mock_wiki_class.return_value = mock_wiki

            from interface.handlers.wiki import query_cmd

            update = MockUpdate(args=["nonexistent"])
            context = MockContext(args=["nonexistent"])

            run_async(query_cmd(update, context))

            self.assertIn("No encontré", update.message._reply)

    def test_query_cmd_no_args(self):
        from interface.handlers.wiki import query_cmd

        update = MockUpdate(args=[])
        context = MockContext(args=[])

        run_async(query_cmd(update, context))

        self.assertIn("Usa: /query", update.message._reply)

    def test_hubs_cmd(self):
        with patch('core.wiki.Wiki') as mock_wiki_class:
            mock_wiki = Mock()
            mock_wiki.get_hubs.return_value = [
                {"name": "AI", "connections": 10},
                {"name": "ML", "connections": 8}
            ]
            mock_wiki_class.return_value = mock_wiki

            from interface.handlers.wiki import hubs_cmd

            update = MockUpdate()
            context = MockContext()

            run_async(hubs_cmd(update, context))

            self.assertIn("Hubs", update.message._reply)
            self.assertIn("AI", update.message._reply)

    def test_clusters_cmd(self):
        with patch('core.wiki.Wiki') as mock_wiki_class:
            mock_wiki = Mock()
            mock_wiki.get_clusters.return_value = [
                {"tag": "python", "count": 5},
                {"tag": "ai", "count": 3}
            ]
            mock_wiki_class.return_value = mock_wiki

            from interface.handlers.wiki import clusters_cmd

            update = MockUpdate()
            context = MockContext()

            run_async(clusters_cmd(update, context))

            self.assertIn("Clusters", update.message._reply)
            self.assertIn("python", update.message._reply)

    def test_lint_cmd(self):
        with patch('core.wiki.Wiki') as mock_wiki_class:
            mock_wiki = Mock()
            mock_wiki.lint.return_value = {
                "total_entities": 100,
                "health_score": 85,
                "issues": [{"type": "orphan", "name": "Test"}]
            }
            mock_wiki_class.return_value = mock_wiki

            from interface.handlers.wiki import lint_cmd

            update = MockUpdate()
            context = MockContext()

            run_async(lint_cmd(update, context))

            self.assertIn("Diagnóstico", update.message._reply)
            self.assertIn("85", update.message._reply)


class TestBusquedaHandlers(unittest.TestCase):
    """Test busqueda.py handlers."""

    def test_ingest_cmd_no_url(self):
        from interface.handlers.busqueda import ingest_cmd

        update = MockUpdate(args=[])
        context = MockContext(args=[])

        run_async(ingest_cmd(update, context))

        self.assertIn("Usa", update.message._reply)
        self.assertIn("/ingest", update.message._reply)

    def test_investigar_cmd_no_args(self):
        with patch('core.background_manager.BraveCounter'):
            from interface.handlers.busqueda import investigar_cmd

            update = MockUpdate(args=[])
            context = MockContext(args=[])

            run_async(investigar_cmd(update, context))

            self.assertIn("Usa: /investigar", update.message._reply)


class TestChatHandlers(unittest.TestCase):
    """Test chat.py handlers."""

    @patch('interface.handlers.chat.logger')
    def test_charlar_cmd_no_args(self, mock_logger):
        from interface.handlers.chat import charlar_cmd

        update = MockUpdate(args=[])
        context = MockContext(args=[])

        run_async(charlar_cmd(update, context))

        self.assertIn("Modos de Charla", update.message._reply)
        self.assertIn("libre", update.message._reply)
        self.assertIn("consultor", update.message._reply)

    @patch('interface.handlers.chat.logger')
    def test_charlar_cmd_invalid_mode(self, mock_logger):
        from interface.handlers.chat import charlar_cmd

        update = MockUpdate(args=["invalid", "topic"])
        context = MockContext(args=["invalid", "topic"])

        run_async(charlar_cmd(update, context))

        self.assertIn("no reconocido", update.message._reply)

    @patch('interface.handlers.chat.logger')
    def test_charlar_cmd_no_topic(self, mock_logger):
        from interface.handlers.chat import charlar_cmd

        update = MockUpdate(args=["libre"])
        context = MockContext(args=["libre"])

        run_async(charlar_cmd(update, context))

        self.assertIn("Usa: /charlar <modo> <tema>", update.message._reply)


class TestAgenteHandlers(unittest.TestCase):
    """Test agente.py handlers."""

    @patch('interface.handlers.agente.logger')
    def test_agente_cmd_no_args(self, mock_logger):
        from interface.handlers.agente import agente_cmd

        update = MockUpdate(args=[])
        context = MockContext(args=[])

        run_async(agente_cmd(update, context))

        self.assertIn("Usa: /agente", update.message._reply)

    @patch('interface.handlers.agente.logger')
    def test_model_cmd_no_args(self, mock_logger):
        from interface.handlers.agente import model_cmd

        update = MockUpdate(args=[])
        context = MockContext(args=[])

        run_async(model_cmd(update, context))

        self.assertIn("Modelo Actual", update.message._reply)

    @patch('interface.handlers.agente.config.OLLAMA_BASE_URL', 'http://localhost:11434')
    @patch('interface.handlers.agente.requests.get')
    @patch('interface.handlers.agente.logger')
    def test_model_cmd_invalid(self, mock_logger, mock_get):
        mock_get.side_effect = Exception("Connection error")

        from interface.handlers.agente import model_cmd

        update = MockUpdate(args=["invalid_model"])
        context = MockContext(args=["invalid_model"])

        run_async(model_cmd(update, context))

        self.assertIn("no encontrado", update.message._reply)

    @patch('interface.handlers.agente.logger')
    def test_query_vectorial_cmd_no_args(self, mock_logger):
        from interface.handlers.agente import query_vectorial_cmd

        update = MockUpdate(args=[])
        context = MockContext(args=[])

        run_async(query_vectorial_cmd(update, context))

        self.assertIn("Usa: /query_vectorial", update.message._reply)

    @patch('interface.handlers.agente.logger')
    @patch('index.rag.RAGEngine')
    def test_query_vectorial_cmd_no_results(self, mock_engine_class, mock_logger):
        mock_engine = Mock()
        mock_engine.search.return_value = []
        mock_engine_class.return_value = mock_engine

        from interface.handlers.agente import query_vectorial_cmd

        update = MockUpdate(args=["nonexistent"])
        context = MockContext(args=["nonexistent"])

        run_async(query_vectorial_cmd(update, context))

        self.assertIn("No encontré", update.message._reply)


if __name__ == '__main__':
    unittest.main(verbosity=2)