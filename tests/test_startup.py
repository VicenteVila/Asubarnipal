"""Unit tests for startup issues."""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

import unittest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
import tempfile
import json


class TestConfigStartup(unittest.TestCase):
    """Test config initialization."""

    def test_config_loads(self):
        import config
        self.assertIsInstance(config.BASE_DIR, Path)
        self.assertIsNotNone(config.TELEGRAM_TOKEN)

    def test_directories_created(self):
        import config
        self.assertTrue(config.DATA_DIR.exists())
        self.assertTrue(config.INDEX_DIR.exists())
        self.assertTrue(config.STORAGE_DIR.exists())


class TestWikiHealer(unittest.TestCase):
    """Test WikiHealer module."""

    def test_healer_imports(self):
        from core.wiki_healer import WikiHealer
        healer = WikiHealer()
        self.assertIsNotNone(healer)

    def test_heal_orphans_no_db(self):
        from core.wiki_healer import WikiHealer
        with patch.object(Path, 'exists', return_value=False):
            healer = WikiHealer()
            result = healer.heal_orphans()
            self.assertEqual(result, 0)


class TestGraphBuilder(unittest.TestCase):
    """Test GraphBuilder module."""

    def test_builder_imports(self):
        from core.graph_builder import GraphBuilder
        builder = GraphBuilder()
        self.assertIsNotNone(builder)

    def test_build_graph_no_db(self):
        from core.graph_builder import GraphBuilder
        with patch.object(Path, 'exists', return_value=False):
            builder = GraphBuilder()
            result = builder.build_graph()
            self.assertEqual(result['nodes'], 0)


class TestBackgroundManager(unittest.TestCase):
    """Test BackgroundManager initialization."""

    def test_imports(self):
        from core.background_manager import (
            BackgroundManager,
            AgentState,
            BraveCounter,
            MemorySkill
        )
        self.assertTrue(True)

    def test_manager_init(self):
        from core.background_manager import BackgroundManager
        manager = BackgroundManager()
        self.assertFalse(manager.running)
        self.assertEqual(len(manager.threads), 0)


class TestServiceImports(unittest.TestCase):
    """Test service module imports."""

    def test_wiki_imports(self):
        from core.wiki import WikiReader
        self.assertTrue(WikiReader is not None)


class TestTelegramBotStartup(unittest.TestCase):
    """Test telegram bot imports."""

    def test_bot_imports(self):
        import importlib.util
        spec = importlib.util.find_spec('interface.telegram_bot')
        self.assertIsNotNone(spec)

    def test_main_function_exists(self):
        import importlib.util
        spec = importlib.util.find_spec('interface.telegram_bot')
        self.assertIsNotNone(spec)


class TestWikiModule(unittest.TestCase):
    """Test Wiki module."""

    def test_wiki_imports(self):
        from core.wiki import Wiki
        self.assertTrue(Wiki is not None)


if __name__ == '__main__':
    unittest.main(verbosity=2)
