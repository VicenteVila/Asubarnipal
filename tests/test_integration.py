"""Integration tests for Asubarnipal system."""
import sys
import os
import unittest
from unittest.mock import Mock, patch, MagicMock
import asyncio

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestServiceImports(unittest.TestCase):
    """Test all service modules import correctly."""

    def test_import_agent_service(self):
        """Test AgentService imports."""
        from app.service import AgentService
        self.assertIsNotNone(AgentService)

    def test_import_hmem_service(self):
        """Test HMemService imports."""
        from app.service import HMemService
        self.assertIsNotNone(HMemService)

    def test_import_asubarnipal_service(self):
        """Test AsubarnipalService imports."""
        from app.service import AsubarnipalService
        self.assertIsNotNone(AsubarnipalService)


class TestHandlerImports(unittest.TestCase):
    """Test all handler modules import correctly."""

    def test_import_comandos(self):
        """Test comandos handler imports."""
        from interface.handlers import comandos
        self.assertIsNotNone(comandos)

    def test_import_wiki_handler(self):
        """Test wiki handler imports."""
        from interface.handlers import wiki
        self.assertIsNotNone(wiki)

    def test_import_busqueda_handler(self):
        """Test busqueda handler imports."""
        from interface.handlers import busqueda
        self.assertIsNotNone(busqueda)

    def test_import_chat_handler(self):
        """Test chat handler imports."""
        from interface.handlers import chat
        self.assertIsNotNone(chat)

    def test_import_agente_handler(self):
        """Test agente handler imports."""
        from interface.handlers import agente
        self.assertIsNotNone(agente)


class TestCoreModuleImports(unittest.TestCase):
    """Test all core modules import correctly."""

    def test_import_llm_router(self):
        """Test llm_router imports."""
        from core import llm_router
        self.assertIsNotNone(llm_router)

    def test_import_memory(self):
        """Test memory imports."""
        from core import memory
        self.assertIsNotNone(memory)

    def test_import_wiki(self):
        """Test wiki imports."""
        from core import wiki
        self.assertIsNotNone(wiki)

    def test_import_wiki_healer(self):
        """Test wiki_healer imports."""
        from core import wiki_healer
        self.assertIsNotNone(wiki_healer)

    def test_import_graph_builder(self):
        """Test graph_builder imports."""
        from core import graph_builder
        self.assertIsNotNone(graph_builder)

    def test_import_background_manager(self):
        """Test background_manager imports."""
        from core import background_manager
        self.assertIsNotNone(background_manager)

    def test_import_vault_manager(self):
        """Test vault_manager imports."""
        from core import vault_manager
        self.assertIsNotNone(vault_manager)

    def test_import_dashboard_logic(self):
        """Test dashboard_logic imports."""
        from core import dashboard_logic
        self.assertIsNotNone(dashboard_logic)

    def test_import_feed_tracker(self):
        """Test feed_tracker imports."""
        from core import feed_tracker
        self.assertIsNotNone(feed_tracker)

    def test_import_skill_registry(self):
        """Test skill_registry imports."""
        from core import skill_registry
        self.assertIsNotNone(skill_registry)


class TestSkillImports(unittest.TestCase):
    """Test all skill modules import correctly."""

    def test_import_default_skills(self):
        """Test default_skills imports."""
        from skills import default_skills
        self.assertIsNotNone(default_skills)

    def test_import_vault_skills(self):
        """Test vault_skills imports."""
        from skills import vault_skills
        self.assertIsNotNone(vault_skills)

    def test_import_optimize_llm(self):
        """Test optimize_llm imports."""
        from skills import optimize_llm
        self.assertIsNotNone(optimize_llm)


class TestAPIImports(unittest.TestCase):
    """Test API module imports correctly."""

    def test_import_api_main(self):
        """Test API main module imports."""
        from api import main
        self.assertIsNotNone(main)


class TestIndexImports(unittest.TestCase):
    """Test index module imports correctly."""

    def test_import_rag(self):
        """Test RAG module imports."""
        from index import rag
        self.assertIsNotNone(rag)


if __name__ == "__main__":
    unittest.main(verbosity=2)
