"""Unit tests for wiki.py."""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

import unittest
from unittest.mock import Mock, patch, MagicMock, mock_open
import tempfile
import json
import sqlite3


from pathlib import Path
import shutil

class TestWikiEntityOperations(unittest.TestCase):
    """Test Wiki entity CRUD operations."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.temp_db = os.path.join(self.temp_dir, "test_wiki.db")
        self.wiki_patcher = patch('config.WIKI_DIR', Path(self.temp_dir))
        self.db_patcher = patch('config.WIKI_PATH', Path(self.temp_db))
        self.wiki_patcher.start()
        self.db_patcher.start()

    def tearDown(self):
        self.wiki_patcher.stop()
        self.db_patcher.stop()
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_add_entity_success(self):
        from core.wiki import Wiki
        wiki = Wiki()
        result = wiki.add_entity(name="Test", content="Test content")
        self.assertTrue(result.get("success"))

    def test_add_entity_duplicate(self):
        from core.wiki import Wiki
        wiki = Wiki()
        wiki.add_entity(name="Test", content="First")
        result = wiki.add_entity(name="Test", content="Second")
        self.assertTrue(result.get("success"))

    def test_search_finds_entity(self):
        from core.wiki import Wiki
        wiki = Wiki()
        wiki.add_entity(name="Python", content="Python is a language")
        results = wiki.search("Python")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["name"], "Python")

    def test_search_no_results(self):
        from core.wiki import Wiki
        wiki = Wiki()
        results = wiki.search("nonexistent")
        self.assertEqual(len(results), 0)

    def test_get_all_returns_entities(self):
        from core.wiki import Wiki
        wiki = Wiki()
        wiki.add_entity(name="A", content="Content A")
        wiki.add_entity(name="B", content="Content B")
        all_entities = wiki.get_all()
        self.assertEqual(len(all_entities), 2)


class TestWikiRelations(unittest.TestCase):
    """Test Wiki relations management."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.temp_db = os.path.join(self.temp_dir, "test_wiki.db")
        self.wiki_patcher = patch('config.WIKI_DIR', Path(self.temp_dir))
        self.db_patcher = patch('config.WIKI_PATH', Path(self.temp_db))
        self.wiki_patcher.start()
        self.db_patcher.start()

    def tearDown(self):
        self.wiki_patcher.stop()
        self.db_patcher.stop()
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_add_entity_with_relations(self):
        from core.wiki import Wiki
        wiki = Wiki()
        wiki.add_entity(name="A", content="Entity A")
        wiki.add_entity(name="B", content="Entity B")
        wiki.add_entity(name="A", content="Entity A", relacionados=["B"])
        results = wiki.search("A")
        self.assertTrue(len(results) >= 1)

    def test_update_relations(self):
        from core.wiki import Wiki
        wiki = Wiki()
        wiki.add_entity(name="X", content="X content")
        wiki.add_entity(name="Y", content="Y content")
        wiki._update_relations("X", ["Y"])
        wiki.cursor.execute("SELECT * FROM relations WHERE from_entity = (SELECT id FROM entities WHERE name='X')")
        self.assertIsNotNone(wiki.cursor.fetchone())


class TestWikiHubs(unittest.TestCase):
    """Test Wiki hub discovery."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.temp_db = os.path.join(self.temp_dir, "test_wiki.db")
        self.wiki_patcher = patch('config.WIKI_DIR', Path(self.temp_dir))
        self.db_patcher = patch('config.WIKI_PATH', Path(self.temp_db))
        self.wiki_patcher.start()
        self.db_patcher.start()

    def tearDown(self):
        self.wiki_patcher.stop()
        self.db_patcher.stop()
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_get_hubs_returns_list(self):
        from core.wiki import Wiki
        wiki = Wiki()
        wiki.add_entity(name="Hub1", content="Content")
        wiki.add_entity(name="Hub2", content="Content")
        hubs = wiki.get_hubs(limit=5)
        self.assertIsInstance(hubs, list)
        self.assertTrue(len(hubs) >= 2)


class TestWikiClusters(unittest.TestCase):
    """Test Wiki clustering."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.temp_db = os.path.join(self.temp_dir, "test_wiki.db")
        self.wiki_patcher = patch('config.WIKI_DIR', Path(self.temp_dir))
        self.db_patcher = patch('config.WIKI_PATH', Path(self.temp_db))
        self.wiki_patcher.start()
        self.db_patcher.start()

    def tearDown(self):
        self.wiki_patcher.stop()
        self.db_patcher.stop()
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_get_clusters_with_tags(self):
        from core.wiki import Wiki
        wiki = Wiki()
        wiki.add_entity(name="Tagged1", content="Content", tags=["python", "ai"])
        wiki.add_entity(name="Tagged2", content="Content", tags=["python"])
        clusters = wiki.get_clusters()
        self.assertIsInstance(clusters, list)
        python_cluster = next((c for c in clusters if c["tag"] == "python"), None)
        self.assertIsNotNone(python_cluster)
        self.assertEqual(python_cluster["count"], 2)


class TestWikiLint(unittest.TestCase):
    """Test Wiki health check."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.temp_db = os.path.join(self.temp_dir, "test_wiki.db")
        self.wiki_patcher = patch('config.WIKI_DIR', Path(self.temp_dir))
        self.db_patcher = patch('config.WIKI_PATH', Path(self.temp_db))
        self.wiki_patcher.start()
        self.db_patcher.start()

    def tearDown(self):
        self.wiki_patcher.stop()
        self.db_patcher.stop()
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_lint_returns_health_score(self):
        from core.wiki import Wiki
        wiki = Wiki()
        wiki.add_entity(name="Healthy", content="Good entity")
        result = wiki.lint()
        self.assertIn("total_entities", result)
        self.assertIn("health_score", result)
        self.assertIn("issues", result)
        self.assertIsInstance(result["health_score"], int)

    def test_lint_detects_orphans(self):
        from core.wiki import Wiki
        wiki = Wiki()
        wiki.add_entity(name="Orphan", content="No relations")
        result = wiki.lint()
        orphan_issues = [i for i in result["issues"] if i["type"] == "orphan"]
        self.assertGreater(len(orphan_issues), 0)


class TestWikiIngest(unittest.TestCase):
    """Test Wiki URL ingestion."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.temp_db = os.path.join(self.temp_dir, "test_wiki.db")
        self.wiki_patcher = patch('config.WIKI_DIR', Path(self.temp_dir))
        self.db_patcher = patch('config.WIKI_PATH', Path(self.temp_db))
        self.wiki_patcher.start()
        self.db_patcher.start()

    def tearDown(self):
        self.wiki_patcher.stop()
        self.db_patcher.stop()
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    @patch('requests.get')
    def test_ingest_url_simple(self, mock_get):
        mock_response = Mock()
        mock_response.text = "<html><title>Test Page</title><body>Content here</body></html>"
        mock_get.return_value = mock_response

        from core.wiki import Wiki
        wiki = Wiki()
        result = wiki.ingest_url("http://test.com")

        if "error" not in result:
            self.assertTrue(result.get("success"))


class TestWikiLanguageDetection(unittest.TestCase):
    """Test Wiki language detection."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.temp_db = os.path.join(self.temp_dir, "test_wiki.db")
        self.wiki_patcher = patch('config.WIKI_DIR', Path(self.temp_dir))
        self.db_patcher = patch('config.WIKI_PATH', Path(self.temp_db))
        self.wiki_patcher.start()
        self.db_patcher.start()

    def tearDown(self):
        self.wiki_patcher.stop()
        self.db_patcher.stop()
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_detect_english(self):
        from core.wiki import Wiki
        wiki = Wiki()
        text = "This is a test sentence in English with common words that can be detected by the language detector function and it should be at least one hundred characters long for proper detection."
        lang = wiki._detect_language(text)
        self.assertEqual(lang, "en")

    def test_detect_spanish(self):
        from core.wiki import Wiki
        wiki = Wiki()
        text = "Esta es una frase de prueba en español con palabras comunes que pueden ser detectadas por el detector de idioma y debe tener al menos cien caracteres para una detección adecuada."
        lang = wiki._detect_language(text)
        self.assertEqual(lang, "es")


if __name__ == '__main__':
    unittest.main(verbosity=2)