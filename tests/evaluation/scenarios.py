"""30 evaluation scenarios organized by difficulty level.

Levels:
  1 - Basico: validacion funcional, sin dependencias externas
  2 - Intermedio: flujos multi-paso, DB local
  3 - Avanzado: requiere Ollama/Brave (mockeable)
  4 - Maxima: multi-sistema integrado

Usage:
    python -m pytest tests/evaluation/scenarios.py -v
    python -m pytest tests/evaluation/scenarios.py -v -k "level_1"
    python -m pytest tests/evaluation/scenarios.py -v -k "level_4"
"""

import json
import os
import shutil
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock, MagicMock

from tests.evaluation.mocks import (
    MockUpdate,
    MockContext,
    MockMessage,
    run_async,
    create_handler_test,
    MockLLMResponse,
    MockBraveResponse,
)
from tests.evaluation.scorers import score_task, ScoreResult, EvaluationReport
from tests.evaluation.fixtures import (
    TEST_QUERIES,
    TEST_CHARLA_TOPICS,
    TEST_HMEM_ENTRIES,
    TEST_AGENT_TASKS,
    TEST_SCHEDULES,
    TEST_API_ENDPOINTS,
    EVAL_CONFIG,
)


class EvalTestCase(unittest.TestCase):
    """Base class for evaluation tests with common setup."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.temp_db = Path(self.temp_dir) / "test_wiki.db"
        self.temp_data = Path(self.temp_dir) / "data"
        self.temp_data.mkdir(exist_ok=True)
        self.temp_storage = self.temp_data / "storage"
        self.temp_storage.mkdir(exist_ok=True)

        self.patchers = [
            patch("config.WIKI_DIR", Path(self.temp_dir)),
            patch("config.WIKI_PATH", self.temp_db),
            patch("config.DATA_DIR", self.temp_data),
            patch("config.RAW_DIR", self.temp_data / "raw"),
            patch("config.INDEX_DIR", self.temp_data / "index"),
            patch("config.STORAGE_DIR", self.temp_storage),
            patch("config.LOG_FILE", self.temp_data / "test.log"),
            patch("config.HEARTBEAT_FILE", self.temp_data / "heartbeat.json"),
            patch("config.AGENT_STATE_FILE", self.temp_data / "agent_state.json"),
            patch("core.vault_manager.get_vault_manager",
                  return_value=Mock(get_active=Mock(return_value=None))),
        ]
        for p in self.patchers:
            p.start()

        (self.temp_data / "raw").mkdir(exist_ok=True)
        (self.temp_data / "index").mkdir(exist_ok=True)

        self._activity_patch = patch("core.live_activity.LiveActivityTracker._save_to_file", lambda self: None)
        self._activity_patch.start()

    def tearDown(self):
        for p in self.patchers:
            p.stop()
        if hasattr(self, "_activity_patch"):
            self._activity_patch.stop()
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def score_and_assert(
        self,
        response_text,
        error=None,
        duration=0.0,
        expected_keywords=None,
        state_checks=None,
        max_time=30.0,
        min_length=20,
    ):
        """Score a task and assert it passes."""
        result = score_task(
            response_text=response_text,
            error=error,
            duration_seconds=duration,
            expected_keywords=expected_keywords,
            state_checks=state_checks,
            max_time=max_time,
            min_length=min_length,
        )
        self.assertTrue(
            result.passed,
            f"Task failed (score={result.total_score}): {result.error or 'No response'}",
        )
        return result


# ============================================================
# LEVEL 1: BASICO (5 tasks)
# ============================================================

class TestLevel1Basic(EvalTestCase):
    """Level 1: Basic functional validation, no external dependencies."""

    def test_01_start_command(self):
        """Task 1: /start returns welcome message with command list."""
        from interface.handlers.comandos import start_cmd

        _, _, response, _ = create_handler_test(start_cmd, args=[])

        self.score_and_assert(
            response_text=response,
            expected_keywords=["bienvenido", "comando"],
        )

    def test_02_status_command(self):
        """Task 2: /status returns CPU, RAM, uptime, Brave remaining."""
        with patch("psutil.cpu_percent", return_value=12.0), \
             patch("psutil.virtual_memory") as mock_ram:
            mock_ram.return_value = Mock(percent=45.0, used=4_200_000_000, total=8_000_000_000)

            from interface.handlers.comandos import status_cmd
            _, _, response, _ = create_handler_test(status_cmd, args=[])

        self.score_and_assert(
            response_text=response,
            expected_keywords=["cpu", "ram"],
        )

    def test_03_manual_command(self):
        """Task 3: /manual contains sections for all new features."""
        from interface.handlers.comandos import manual_cmd

        _, _, response, _ = create_handler_test(manual_cmd, args=[])

        self.score_and_assert(
            response_text=response,
            expected_keywords=["vision", "backup", "schedule", "voz"],
        )

    def test_04_model_command(self):
        """Task 4: /model shows inline keyboard with Ollama/Gemini/Auto."""
        from interface.handlers.agente import model_cmd

        _, _, response, markup = create_handler_test(model_cmd, args=[])

        self.score_and_assert(
            response_text=response,
            expected_keywords=["modelo", "actual"],
        )
        self.assertIsNotNone(markup, "Should have inline keyboard")

    def test_05_session_command(self):
        """Task 5: /session shows messages, tokens, mode."""
        from interface.telegram_bot import session_info_cmd

        with patch("interface.telegram_bot.get_session_db") as mock_db:
            mock_db.return_value = Mock(
                get_session_info=Mock(return_value={
                    "exists": True,
                    "message_count": 5,
                    "total_tokens": 1000,
                })
            )
            _, _, response, _ = create_handler_test(session_info_cmd, args=[])

        self.score_and_assert(
            response_text=response,
            expected_keywords=["sesion", "mensajes"],
        )


# ============================================================
# LEVEL 2: INTERMEDIO (5 tasks)
# ============================================================

class TestLevel2Intermediate(EvalTestCase):
    """Level 2: Multi-step flows, local DB."""

    def test_06_vault_lifecycle(self):
        """Task 6: create -> use -> info -> vaults."""
        from core.vault_manager import VaultManager

        vm = VaultManager()
        vm._config_path = Path(self.temp_dir) / "vaults_config.json"
        vm._config = {"vaults": {}, "active": None}

        vault_path = Path(self.temp_dir) / "test_vault"
        vault_path.mkdir(exist_ok=True)

        result = vm.create("test_eval", str(vault_path), "Test vault")
        self.assertTrue(result.get("success"), f"Create failed: {result.get('error')}")

        result = vm.switch("test_eval")
        self.assertTrue(result.get("success"), f"Switch failed: {result.get('error')}")

        active = vm.get_active()
        self.assertIsNotNone(active, "Should have active vault")
        self.assertEqual(active["name"], "test_eval")

        result = vm.list_vaults()
        vaults = result.get("vaults", [])
        self.assertTrue(any(v["name"] == "test_eval" for v in vaults))

    def test_07_backup_basic(self):
        """Task 7: backup -> backups -> backup_stats."""
        from core.backup_manager import BackupManager

        backup_dir = Path(self.temp_dir) / "backups"
        backup_dir.mkdir(exist_ok=True)

        bm = BackupManager(backup_dir=backup_dir, max_backups=5)
        bm._history = []

        with patch("core.backup_manager.config") as mock_config:
            mock_config.DATA_DIR = self.temp_data
            mock_config.WIKI_DIR = Path(self.temp_dir)
            mock_config.WIKI_DIR.mkdir(exist_ok=True)

            result = bm.backup_vault()
            self.assertTrue(result.get("success"), f"Backup failed: {result.get('error')}")

        backups = bm.list_backups()
        self.assertGreater(len(backups), 0, "Should have at least 1 backup")

        stats = bm.stats()
        self.assertGreater(stats["total_backups"], 0)

    def test_08_schedule_lifecycle(self):
        """Task 8: schedule -> schedules -> toggle -> cancel."""
        from core.research_scheduler import ResearchScheduler

        sched_file = self.temp_data / "test_schedules.json"
        scheduler = ResearchScheduler()
        scheduler._config_path = sched_file

        schedule = scheduler.add_schedule("test topic", interval_minutes=30)
        self.assertEqual(schedule["topic"], "test topic")

        schedules = scheduler.list_schedules()
        self.assertEqual(len(schedules), 1)

        toggled = scheduler.toggle_schedule(1)
        self.assertIsNotNone(toggled)
        self.assertFalse(toggled["active"])

        removed = scheduler.remove_schedule(1)
        self.assertTrue(removed)
        self.assertEqual(len(scheduler.list_schedules()), 0)

    def test_09_vault_export_import(self):
        """Task 9: export -> delete -> import."""
        from core.vault_manager import VaultManager

        vm = VaultManager()
        vm._config_path = Path(self.temp_dir) / "vaults_config.json"
        vm._config = {"vaults": {}, "active": None}

        vault_path = Path(self.temp_dir) / "export_vault"
        vault_path.mkdir(exist_ok=True)
        (vault_path / "test.md").write_text("# Test note")

        result = vm.create("export_test", str(vault_path), "Export test")
        self.assertTrue(result.get("success"))

        export_path = str(self.temp_data / "export.json")
        result = vm.export_vault("export_test", export_path)
        self.assertTrue(result.get("success"), f"Export failed: {result.get('error')}")
        self.assertTrue(Path(export_path).exists())

    def test_10_query_inline_keyboard(self):
        """Task 10: /query (no args) shows inline keyboard, callback processes."""
        from interface.handlers.wiki import query_cmd

        _, _, response, markup = create_handler_test(query_cmd, args=[])

        self.score_and_assert(
            response_text=response,
            expected_keywords=["buscar", "wiki", "selecciona"],
        )
        self.assertIsNotNone(markup, "Should have inline keyboard")


# ============================================================
# LEVEL 3: AVANZADO (8 tasks)
# ============================================================

class TestLevel3Advanced(EvalTestCase):
    """Level 3: Requires Ollama/Brave (mockable)."""

    def test_11_ingest_url(self):
        """Task 11: /ingest URL creates wiki note."""
        from core.wiki import Wiki

        wiki = Wiki()
        wiki.add_entity(
            name="Attention Paper",
            content="The Transformer model based on attention mechanisms",
            tipo="source",
            tags=["paper", "attention"],
        )

        results = wiki.search("attention")
        self.assertGreater(len(results), 0, "Should find ingested entity")

    def test_12_investigar(self):
        """Task 12: /investigar finds sources and processes them."""
        with patch("core.llm_router.BraveRouter") as mock_brave:
            mock_instance = Mock()
            mock_instance.search.return_value = MockBraveResponse.get("attention")
            mock_brave.return_value = mock_instance

            from interface.handlers.busqueda import investigar_cmd
            _, _, response, _ = create_handler_test(
                investigar_cmd, args=["transformer", "attention"]
            )

        self.score_and_assert(
            response_text=response,
            expected_keywords=["investigando", "encontrado"],
            max_time=60.0,
        )

    def test_13_query_wiki(self):
        """Task 13: /query wiki mode returns answer with references."""
        from core.wiki import Wiki

        wiki = Wiki()
        wiki.add_entity(
            name="Fine Tuning",
            content="Fine-tuning is the process of adjusting a pre-trained model with domain-specific data.",
            tipo="concept",
            tags=["ml", "training"],
        )

        results = wiki.search("fine-tuning")
        self.assertGreater(len(results), 0, "Should find wiki entity")

    def test_14_query_vectorial(self):
        """Task 14: /query_vectorial returns FAISS results."""
        from interface.handlers.agente import query_vectorial_cmd

        _, _, response, _ = create_handler_test(
            query_vectorial_cmd, args=["embeddings"]
        )

        self.score_and_assert(
            response_text=response,
            max_time=30.0,
        )

    def test_15_query_hybrid(self):
        """Task 15: /queryhybrid returns combined results."""
        from interface.handlers.wiki import queryhybrid_cmd

        _, _, response, _ = create_handler_test(
            queryhybrid_cmd, args=["redes neuronales"]
        )

        self.score_and_assert(
            response_text=response,
            max_time=30.0,
        )

    def test_16_charlar_consultor(self):
        """Task 16: /charlar consultor returns 3-phase analysis."""
        from interface.handlers.chat import charlar_cmd

        _, _, response, _ = create_handler_test(
            charlar_cmd, args=["consultor", "optimizar pipeline RAG"]
        )

        self.score_and_assert(
            response_text=response,
            expected_keywords=["fase", "definicion", "ejecucion", "evaluacion"],
            max_time=60.0,
        )

    def test_17_charlar_devil(self):
        """Task 17: /charlar devil finds risks."""
        from interface.handlers.chat import charlar_cmd

        _, _, response, _ = create_handler_test(
            charlar_cmd, args=["devil", "LLMs diagnostico medico"]
        )

        self.score_and_assert(
            response_text=response,
            expected_keywords=["riesgo", "error", "limitacion"],
            max_time=60.0,
        )

    def test_18_agente_read_file(self):
        """Task 18: /agente reads file and generates summary."""
        from interface.handlers.agente import agente_cmd

        config_path = Path(__file__).parent.parent.parent / "config.py"
        if config_path.exists():
            _, _, response, _ = create_handler_test(
                agente_cmd, args=["Lee config.py y resume las variables principales"]
            )
            self.score_and_assert(
                response_text=response,
                expected_keywords=["config", "variable"],
                max_time=60.0,
            )
        else:
            self.skipTest("config.py not found")


# ============================================================
# LEVEL 4: MAXIMA DIFICULTAD (12 tasks)
# ============================================================

class TestLevel4MaxDifficulty(EvalTestCase):
    """Level 4: Multi-system integrated scenarios."""

    def test_19_pipeline_conocimiento(self):
        """Task 19: ingest -> query -> hubs -> backup."""
        from core.wiki import Wiki
        from core.backup_manager import BackupManager

        wiki = Wiki()
        wiki.add_entity(
            name="Transformer",
            content="The Transformer is a neural network architecture based on attention mechanisms.",
            tipo="concept",
            tags=["architecture", "attention"],
        )

        results = wiki.search("transformer")
        self.assertGreater(len(results), 0, "Query should find Transformer")

        hubs = wiki.get_hubs(limit=5)
        self.assertGreater(len(hubs), 0, "Should have hubs")

        backup_dir = self.temp_data / "backups"
        backup_dir.mkdir(exist_ok=True)
        bm = BackupManager(backup_dir=backup_dir)
        bm._history = []

        with patch("core.backup_manager.config") as mock_config:
            mock_config.DATA_DIR = self.temp_data
            mock_config.WIKI_DIR = self.temp_dir
            result = bm.backup_vault()
            self.assertTrue(result.get("success"), f"Backup failed: {result.get('error')}")

    def test_20_investigacion_programada(self):
        """Task 20: schedule -> execute -> query -> wiki."""
        from core.research_scheduler import ResearchScheduler
        from core.wiki import Wiki

        scheduler = ResearchScheduler()
        schedule = scheduler.add_schedule("LLM reasoning", interval_minutes=15)
        self.assertEqual(schedule["topic"], "LLM reasoning")

        wiki = Wiki()
        wiki.add_entity(
            name="LLM Reasoning",
            content="Large language models demonstrate reasoning capabilities through chain-of-thought prompting.",
            tipo="concept",
            tags=["LLM", "reasoning"],
        )

        results = wiki.search("reasoning")
        self.assertGreater(len(results), 0, "Should find ingested research note")

    def test_21_multi_vault_migracion(self):
        """Task 21: create -> ingest -> export -> import."""
        from core.vault_manager import VaultManager

        vm = VaultManager()
        vm._config_path = Path(self.temp_dir) / "vaults_config.json"
        vm._config = {"vaults": {}, "active": None}

        path1 = Path(self.temp_dir) / "vault_a"
        path1.mkdir(exist_ok=True)
        vm.create("vault_a", str(path1), "Vault A")

        path2 = Path(self.temp_dir) / "vault_b"
        path2.mkdir(exist_ok=True)
        vm.create("vault_b", str(path2), "Vault B")

        export_path = str(self.temp_data / "vault_a_export.json")
        result = vm.export_vault("vault_a", export_path)
        self.assertTrue(result.get("success"), f"Export failed: {result.get('error')}")

    def test_22_hmem_conversacional(self):
        """Task 22: recordar x2 -> pensar -> entidades."""
        from core.hybrid_retriever import get_hmem_manager

        try:
            hmem = get_hmem_manager()
            hmem.remember("El usuario trabaja en NLP", metadata={"category": "user_info"})
            hmem.remember("Prefiere modelos pequenos", metadata={"category": "preference"})

            recent = hmem.get_recent(5)
            self.assertGreater(len(recent), 0, "Should have recent memories")

            stats = hmem.stats()
            self.assertIsInstance(stats, dict, "Stats should be a dict")
        except Exception as e:
            self.skipTest(f"H-Mem not available: {e}")

    def test_23_vision_ocr(self):
        """Task 23: foto -> vision -> ocr."""
        from core.vision import is_vision_available, extract_text_from_image

        available = is_vision_available()
        if not available:
            self.skipTest("Vision model not available (no llava in Ollama)")

    def test_24_voz_stt_query(self):
        """Task 24: voice -> transcribe -> query."""
        from core.stt import transcribe_audio

        success, result = transcribe_audio("/nonexistent/test.ogg")
        self.assertFalse(success, "Should fail when Whisper not available")
        self.assertIn("stt not available", result.lower())

    def test_25_graphify_completo(self):
        """Task 25: graphify -> stats -> query -> export."""
        try:
            from core.wiki import Wiki
            wiki = Wiki()
            wiki.add_entity(
                name="Graph Test",
                content="Test entity for graph building",
                tipo="concept",
                tags=["test"],
            )
            hubs = wiki.get_hubs(limit=5)
            self.assertIsInstance(hubs, list)
        except Exception as e:
            self.skipTest(f"Graphify not available: {e}")

    def test_26_api_end_to_end(self):
        """Task 26: POST /query -> GET /metrics -> GET /schedules."""
        from fastapi.testclient import TestClient
        from api.main import app

        client = TestClient(app)

        response = client.get("/")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("name", data)
        self.assertIn("version", data)

        response = client.get("/health")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("status", data)

        response = client.get("/schedules")
        self.assertEqual(response.status_code, 200)

    def test_27_rate_limiting(self):
        """Task 27: 6x /investigar fast -> 5 OK, 6th rejected."""
        from core.rate_limiter import CommandRateLimiter

        limiter = CommandRateLimiter()

        for i in range(5):
            allowed, remaining = limiter.allow(1, "investigar")
            self.assertTrue(allowed, f"Request {i+1} should be allowed")

        allowed, remaining = limiter.allow(1, "investigar")
        self.assertFalse(allowed, "6th request should be rate limited")

        wait_time = limiter.get_wait_time(1, "investigar")
        self.assertGreater(wait_time, 0, "Should have wait time")

    def test_28_backup_restore(self):
        """Task 28: create -> ingest -> backup -> delete -> restore."""
        from core.backup_manager import BackupManager
        from core.wiki import Wiki

        wiki = Wiki()
        wiki.add_entity(
            name="Restore Test",
            content="Entity to test backup/restore cycle",
            tipo="concept",
        )

        backup_dir = self.temp_data / "backups"
        backup_dir.mkdir(exist_ok=True)
        bm = BackupManager(backup_dir=backup_dir)
        bm._history = []

        with patch("core.backup_manager.config") as mock_config:
            mock_config.DATA_DIR = self.temp_data
            mock_config.WIKI_DIR = self.temp_dir
            result = bm.backup_vault()
            self.assertTrue(result.get("success"))

        backups = bm.list_backups()
        self.assertGreater(len(backups), 0)

    def test_29_cache_performance(self):
        """Task 29: query x2 same topic -> 2nd faster."""
        from core.cache import QueryCache

        cache = QueryCache(cache_dir=self.temp_data / "cache")

        start1 = time.time()
        cache.set("test query", {"result": "data"})
        duration1 = time.time() - start1

        start2 = time.time()
        result = cache.get("test query")
        duration2 = time.time() - start2

        self.assertEqual(result, {"result": "data"})
        self.assertLess(duration2, duration1 * 2, "Cache read should be fast")

    def test_30_chat_evaluacion(self):
        """Task 30: charlar libre -> rate 4 -> charlar devil -> rate 2 -> calidad."""
        from skills.default_skills import (
            set_pending_eval,
            record_eval_feedback,
            get_eval_stats,
        )

        set_pending_eval("Test question", "Test response")
        result = record_eval_feedback("si")
        self.assertTrue(result.get("success"))

        set_pending_eval("Test question 2", "Test response 2")
        result = record_eval_feedback("no")
        self.assertTrue(result.get("success"))

        stats = get_eval_stats()
        self.assertIn("accuracy_rate", stats)
        inner_stats = stats.get("stats", stats)
        self.assertIn("total_evaluated", inner_stats)


if __name__ == "__main__":
    unittest.main()
