"""Integration tests for core Telegram commands (set minimo vital).

Covers: /status, /queryhybrid, /memoria, /recordar, /vaults, /vault_use,
        /backup, /graphify, /graph_query, /graph_stats
"""

import os
import sys
import unittest
from unittest.mock import Mock, patch, MagicMock
import asyncio

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class MockUpdate:
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
    def __init__(self):
        self.text = "test"
        self._reply = None
        self._reply_markup = None
        self._replies = []
        self.document = None
        self.photo = None

    async def reply_text(self, text, parse_mode=None, reply_markup=None, **kwargs):
        self._reply = text
        self._reply_markup = reply_markup
        self._replies.append(text)
        return Mock()


class MockContext:
    def __init__(self, args=None):
        self.args = args or []
        self.user_data = {}


def run_async(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


class TestStatusCommand(unittest.TestCase):

    @patch("interface.handlers.comandos.config")
    @patch("interface.handlers.comandos.psutil")
    @patch("interface.handlers.comandos.logger")
    def test_status_cmd_returns_system_info(self, mock_logger, mock_psutil, mock_config):
        from interface.handlers.comandos import status_cmd

        mock_psutil.cpu_percent.return_value = 25.0
        mock_mem = Mock()
        mock_mem.used = 4 * 1024**3
        mock_mem.total = 16 * 1024**3
        mock_mem.percent = 25.0
        mock_psutil.virtual_memory.return_value = mock_mem

        mock_data_dir = Mock()
        mock_data_dir.exists.return_value = False
        mock_config.DATA_DIR = mock_data_dir

        update = MockUpdate()
        context = MockContext()
        run_async(status_cmd(update, context))

        self.assertIn("Estado del Sistema", update.message._reply)
        self.assertIn("CPU", update.message._reply)
        self.assertIn("RAM", update.message._reply)
        self.assertIn("Brave", update.message._reply)

    @patch("interface.handlers.comandos.config")
    @patch("interface.handlers.comandos.psutil")
    @patch("interface.handlers.comandos.logger")
    def test_status_cmd_with_agent_state(self, mock_logger, mock_psutil, mock_config):
        import json
        import tempfile
        from pathlib import Path
        from interface.handlers.comandos import status_cmd

        mock_psutil.cpu_percent.return_value = 10.0
        mock_mem = Mock()
        mock_mem.used = 2 * 1024**3
        mock_mem.total = 8 * 1024**3
        mock_mem.percent = 25.0
        mock_psutil.virtual_memory.return_value = mock_mem

        with tempfile.TemporaryDirectory() as tmpdir:
            data_dir = Path(tmpdir)
            agent_file = data_dir / "agent_state.json"
            agent_file.write_text(json.dumps({
                "uptime": "2h 30m",
                "total_queries": 42,
                "success_rate": 95.5,
            }))
            mock_config.DATA_DIR = data_dir

            update = MockUpdate()
            context = MockContext()
            run_async(status_cmd(update, context))

            self.assertIn("42", update.message._reply)
            self.assertIn("95.5", update.message._reply)


class TestQueryHybridCommand(unittest.TestCase):

    def test_queryhybrid_no_args(self):
        from interface.handlers.wiki import queryhybrid_cmd

        update = MockUpdate(args=[])
        context = MockContext(args=[])
        run_async(queryhybrid_cmd(update, context))

        self.assertIn("/queryhybrid", update.message._reply)

    @patch("interface.handlers.wiki.logger")
    def test_queryhybrid_with_args_no_results(self, mock_logger):
        from interface.handlers.wiki import queryhybrid_cmd

        with patch("core.hybrid_search.get_hybrid_search") as mock_hs_get:
            mock_hs = Mock()
            mock_hs.search.return_value = {
                "sqlite_results": [],
                "obsidian_results": [],
                "vault_active": None,
            }
            mock_hs_get.return_value = mock_hs

            update = MockUpdate(args=["test", "query"])
            context = MockContext(args=["test", "query"])
            run_async(queryhybrid_cmd(update, context))

            replies_text = " ".join(update.message._replies)
            self.assertIn("No encontr", replies_text)


class TestHMemCommands(unittest.TestCase):

    @patch("interface.handlers.hmem_commands.get_hmem_manager")
    @patch("interface.handlers.hmem_commands.logger")
    def test_memoria_cmd_success(self, mock_logger, mock_get):
        from interface.handlers.hmem_commands import memoria_cmd

        mock_hmem = Mock()
        mock_hmem.stats.return_value = {
            "tree": {
                "total_nodes": 50,
                "by_level": {"L0": 1, "L1": 5, "L2": 20, "L3": 24},
            },
            "graph": {
                "total_entities": 30,
                "total_relations": 45,
                "by_type": {"person": 10, "concept": 20},
            },
            "weights": {
                "theta1_semantic": 0.4,
                "theta2_temporal": 0.3,
                "theta3_robustness": 0.3,
            },
        }
        mock_get.return_value = mock_hmem

        update = MockUpdate()
        context = MockContext()
        run_async(memoria_cmd(update, context))

        self.assertIn("H-Mem", update.message._reply)
        self.assertIn("50", update.message._reply)
        self.assertIn("30", update.message._reply)

    @patch("interface.handlers.hmem_commands.get_hmem_manager")
    @patch("interface.handlers.hmem_commands.logger")
    def test_memoria_cmd_unavailable(self, mock_logger, mock_get):
        from interface.handlers.hmem_commands import memoria_cmd

        mock_get.side_effect = Exception("H-Mem not initialized")

        update = MockUpdate()
        context = MockContext()
        run_async(memoria_cmd(update, context))

        self.assertIn("no disponible", update.message._reply)

    @patch("interface.handlers.hmem_commands.logger")
    def test_recordar_cmd_no_args(self, mock_logger):
        from interface.handlers.hmem_commands import recordar_cmd

        update = MockUpdate(args=[])
        context = MockContext(args=[])
        run_async(recordar_cmd(update, context))

        self.assertIn("/recordar", update.message._reply)

    @patch("interface.handlers.hmem_commands.get_hmem_manager")
    @patch("interface.handlers.hmem_commands.logger")
    def test_recordar_cmd_success(self, mock_logger, mock_get):
        from interface.handlers.hmem_commands import recordar_cmd

        mock_hmem = Mock()
        mock_hmem.remember.return_value = {
            "tree_node_id": "abc123def456",
            "tree_level": 2,
            "graph_ingest": {"entities_extracted": 3},
        }
        mock_get.return_value = mock_hmem

        update = MockUpdate(args=["Python", "es", "genial"])
        context = MockContext(args=["Python", "es", "genial"])
        run_async(recordar_cmd(update, context))

        self.assertIn("Memoria guardada", update.message._reply)
        self.assertIn("L2", update.message._reply)
        self.assertIn("3", update.message._reply)

    @patch("interface.handlers.hmem_commands.logger")
    def test_pensar_cmd_no_args(self, mock_logger):
        from interface.handlers.hmem_commands import pensar_cmd

        update = MockUpdate(args=[])
        context = MockContext(args=[])
        run_async(pensar_cmd(update, context))

        self.assertIn("/pensar", update.message._reply)

    @patch("interface.handlers.hmem_commands.get_hmem_manager")
    @patch("interface.handlers.hmem_commands.logger")
    def test_pensar_cmd_success(self, mock_logger, mock_get):
        from interface.handlers.hmem_commands import pensar_cmd

        mock_hmem = Mock()
        mock_hmem.think.return_value = "Python es un lenguaje interpretado de alto nivel."
        mock_get.return_value = mock_hmem

        update = MockUpdate(args=["que", "es", "python"])
        context = MockContext(args=["que", "es", "python"])
        run_async(pensar_cmd(update, context))

        self.assertIn("H-Mem responde", update.message._reply)
        self.assertIn("Python", update.message._reply)

    @patch("interface.handlers.hmem_commands.get_hmem_manager")
    @patch("interface.handlers.hmem_commands.logger")
    def test_recientes_cmd_empty(self, mock_logger, mock_get):
        from interface.handlers.hmem_commands import recientes_cmd

        mock_hmem = Mock()
        mock_hmem.get_recent_memories.return_value = []
        mock_get.return_value = mock_hmem

        update = MockUpdate()
        context = MockContext()
        run_async(recientes_cmd(update, context))

        self.assertIn("no hay memorias", update.message._reply)

    @patch("interface.handlers.hmem_commands.get_hmem_manager")
    @patch("interface.handlers.hmem_commands.logger")
    def test_recientes_cmd_with_memories(self, mock_logger, mock_get):
        from interface.handlers.hmem_commands import recientes_cmd

        mock_hmem = Mock()
        mock_hmem.get_recent_memories.return_value = [
            {"content": "Primera memoria", "level": 1, "timestamp": "2026-05-28T10:00:00"},
            {"content": "Segunda memoria", "level": 2, "timestamp": "2026-05-28T11:00:00"},
        ]
        mock_get.return_value = mock_hmem

        update = MockUpdate()
        context = MockContext()
        run_async(recientes_cmd(update, context))

        self.assertIn("Memorias Recientes", update.message._reply)
        self.assertIn("Primera", update.message._reply)


class TestVaultCommands(unittest.TestCase):

    @patch("interface.handlers.vault.get_vault_manager")
    @patch("interface.handlers.vault.logger")
    def test_vaults_cmd_success(self, mock_logger, mock_get):
        from interface.handlers.vault import vaults_cmd

        mock_vm = Mock()
        mock_vm.list_vaults.return_value = {
            "success": True,
            "active_vault": "default",
            "vaults": [
                {"name": "default", "path": "/data/default", "active": True, "notes_count": 42, "description": ""},
                {"name": "research", "path": "/data/research", "active": False, "notes_count": 15, "description": "Research vault"},
            ],
            "total": 2,
        }
        mock_get.return_value = mock_vm

        update = MockUpdate()
        context = MockContext()
        run_async(vaults_cmd(update, context))

        self.assertIn("Vaults", update.message._reply)
        self.assertIn("default", update.message._reply)
        self.assertIn("research", update.message._reply)
        self.assertIn("42", update.message._reply)

    @patch("interface.handlers.vault.get_vault_manager")
    @patch("interface.handlers.vault.logger")
    def test_vaults_cmd_error(self, mock_logger, mock_get):
        from interface.handlers.vault import vaults_cmd

        mock_vm = Mock()
        mock_vm.list_vaults.return_value = {"success": False, "error": "DB corrupted"}
        mock_get.return_value = mock_vm

        update = MockUpdate()
        context = MockContext()
        run_async(vaults_cmd(update, context))

        self.assertIn("Error", update.message._reply)

    @patch("interface.handlers.vault.logger")
    def test_vault_use_cmd_no_args(self, mock_logger):
        from interface.handlers.vault import vault_use_cmd

        update = MockUpdate(args=[])
        context = MockContext(args=[])
        run_async(vault_use_cmd(update, context))

        self.assertIn("/vault_use", update.message._reply)

    @patch("interface.handlers.vault.get_vault_manager")
    @patch("interface.handlers.vault.logger")
    def test_vault_use_cmd_success(self, mock_logger, mock_get):
        from interface.handlers.vault import vault_use_cmd

        mock_vm = Mock()
        mock_vm.switch.return_value = {
            "success": True,
            "name": "research",
            "path": "/data/research",
        }
        mock_get.return_value = mock_vm

        update = MockUpdate(args=["research"])
        context = MockContext(args=["research"])
        run_async(vault_use_cmd(update, context))

        self.assertIn("Vault cambiado", update.message._reply)
        self.assertIn("research", update.message._reply)

    @patch("interface.handlers.vault.get_vault_manager")
    @patch("interface.handlers.vault.logger")
    def test_vault_use_cmd_not_found(self, mock_logger, mock_get):
        from interface.handlers.vault import vault_use_cmd

        mock_vm = Mock()
        mock_vm.switch.return_value = {"success": False, "error": "Vault 'nonexistent' not found"}
        mock_get.return_value = mock_vm

        update = MockUpdate(args=["nonexistent"])
        context = MockContext(args=["nonexistent"])
        run_async(vault_use_cmd(update, context))

        self.assertIn("Error", update.message._reply)

    def test_vault_create_cmd_no_args(self):
        from interface.handlers.vault import vault_create_cmd

        update = MockUpdate(args=[])
        context = MockContext(args=[])
        run_async(vault_create_cmd(update, context))

        self.assertIn("Crear nuevo vault", update.message._reply)

    def test_vault_import_cmd_no_args(self):
        from interface.handlers.vault import vault_import_cmd

        update = MockUpdate(args=[])
        context = MockContext(args=[])
        run_async(vault_import_cmd(update, context))

        self.assertIn("Importar vault", update.message._reply)

    def test_vault_connect_cmd_no_args(self):
        from interface.handlers.vault import vault_connect_cmd

        update = MockUpdate(args=[])
        context = MockContext(args=[])
        run_async(vault_connect_cmd(update, context))

        self.assertIn("Conectar vault", update.message._reply)


class TestBackupCommands(unittest.TestCase):

    @patch("interface.handlers.backup.get_backup_manager")
    @patch("interface.handlers.backup.logger")
    def test_backup_cmd_success(self, mock_logger, mock_get):
        from interface.handlers.backup import backup_cmd

        mock_bm = Mock()
        mock_bm.backup_vault.return_value = {
            "success": True,
            "backup": {
                "name": "backup_20260528",
                "vault": "default",
                "size_bytes": 102400,
                "timestamp": "2026-05-28T12:00:00",
            },
        }
        mock_get.return_value = mock_bm

        update = MockUpdate()
        context = MockContext()
        run_async(backup_cmd(update, context))

        replies = update.message._replies
        self.assertTrue(any("Backup creado" in r for r in replies))

    @patch("interface.handlers.backup.get_backup_manager")
    @patch("interface.handlers.backup.logger")
    def test_backup_cmd_error(self, mock_logger, mock_get):
        from interface.handlers.backup import backup_cmd

        mock_bm = Mock()
        mock_bm.backup_vault.return_value = {"success": False, "error": "Disk full"}
        mock_get.return_value = mock_bm

        update = MockUpdate()
        context = MockContext()
        run_async(backup_cmd(update, context))

        replies = update.message._replies
        self.assertTrue(any("Error" in r for r in replies))

    @patch("interface.handlers.backup.get_backup_manager")
    def test_backups_cmd_empty(self, mock_get):
        from interface.handlers.backup import backups_cmd

        mock_bm = Mock()
        mock_bm.list_backups.return_value = []
        mock_get.return_value = mock_bm

        update = MockUpdate()
        context = MockContext()
        run_async(backups_cmd(update, context))

        self.assertIn("No hay backups", update.message._reply)

    @patch("interface.handlers.backup.get_backup_manager")
    def test_backups_cmd_with_backups(self, mock_get):
        from interface.handlers.backup import backups_cmd

        mock_bm = Mock()
        mock_bm.list_backups.return_value = [
            {"name": "backup_1", "vault": "default", "size_bytes": 51200, "timestamp": "2026-05-28T10:00:00"},
        ]
        mock_bm.stats.return_value = {"total_backups": 1}
        mock_get.return_value = mock_bm

        update = MockUpdate()
        context = MockContext()
        run_async(backups_cmd(update, context))

        self.assertIn("backup_1", update.message._reply)

    def test_restore_cmd_no_args(self):
        from interface.handlers.backup import restore_cmd

        update = MockUpdate(args=[])
        context = MockContext(args=[])
        run_async(restore_cmd(update, context))

        self.assertIn("/restore", update.message._reply)

    @patch("interface.handlers.backup.get_backup_manager")
    def test_backup_stats_cmd(self, mock_get):
        from interface.handlers.backup import backup_stats_cmd

        mock_bm = Mock()
        mock_bm.stats.return_value = {
            "total_backups": 5,
            "total_size_bytes": 512000,
            "max_backups": 10,
            "auto_backup_interval": 3600,
            "last_backup": "2026-05-28T12:00:00",
        }
        mock_get.return_value = mock_bm

        update = MockUpdate()
        context = MockContext()
        run_async(backup_stats_cmd(update, context))

        self.assertIn("Total backups: 5", update.message._reply)


class TestGraphifyCommands(unittest.TestCase):

    @patch("interface.handlers.graphify_handler.build_graph")
    @patch("interface.handlers.graphify_handler.logger")
    def test_graphify_cmd_success(self, mock_logger, mock_build):
        from interface.handlers.graphify_handler import graphify_cmd

        mock_build.return_value = {
            "success": True,
            "stats": {
                "nodes": 150,
                "edges": 300,
                "communities": 8,
                "hubs": [
                    {"name": "Python", "connections": 25},
                    {"name": "AI", "connections": 20},
                ],
            },
        }

        update = MockUpdate()
        context = MockContext()
        run_async(graphify_cmd(update, context))

        replies = update.message._replies
        self.assertTrue(any("Grafo construido" in r for r in replies))
        self.assertTrue(any("150" in r for r in replies))

    @patch("interface.handlers.graphify_handler.build_graph")
    @patch("interface.handlers.graphify_handler.logger")
    def test_graphify_cmd_error(self, mock_logger, mock_build):
        from interface.handlers.graphify_handler import graphify_cmd

        mock_build.return_value = {"success": False, "error": "graphify not installed"}

        update = MockUpdate()
        context = MockContext()
        run_async(graphify_cmd(update, context))

        replies = update.message._replies
        self.assertTrue(any("Error" in r for r in replies))

    def test_graph_query_cmd_no_args(self):
        from interface.handlers.graphify_handler import graph_query_cmd

        update = MockUpdate(args=[])
        context = MockContext(args=[])
        run_async(graph_query_cmd(update, context))

        self.assertIn("/graph_query", update.message._reply)

    @patch("interface.handlers.graphify_handler.query_graph")
    @patch("interface.handlers.graphify_handler.logger")
    def test_graph_query_cmd_success(self, mock_logger, mock_query):
        from interface.handlers.graphify_handler import graph_query_cmd

        mock_query.return_value = {
            "success": True,
            "answer": "Transformers usa attention para procesar secuencias en paralelo.",
        }

        update = MockUpdate(args=["que", "son", "transformers"])
        context = MockContext(args=["que", "son", "transformers"])
        run_async(graph_query_cmd(update, context))

        replies = update.message._replies
        self.assertTrue(any("Respuesta del grafo" in r for r in replies))

    @patch("interface.handlers.graphify_handler.get_graph_stats")
    @patch("interface.handlers.graphify_handler.logger")
    def test_graph_stats_cmd_no_graph(self, mock_logger, mock_stats):
        from interface.handlers.graphify_handler import graph_stats_cmd

        mock_stats.return_value = {"exists": False}

        update = MockUpdate()
        context = MockContext()
        run_async(graph_stats_cmd(update, context))

        self.assertIn("No hay grafo", update.message._reply)

    @patch("interface.handlers.graphify_handler.get_graph_stats")
    @patch("interface.handlers.graphify_handler.logger")
    def test_graph_stats_cmd_with_graph(self, mock_logger, mock_stats):
        from interface.handlers.graphify_handler import graph_stats_cmd

        mock_stats.return_value = {
            "exists": True,
            "nodes": 200,
            "edges": 450,
            "communities": 12,
            "file_size_kb": 256.5,
            "last_built": "2026-05-28",
            "hubs": [{"name": "AI", "connections": 30}],
            "html_exists": True,
            "report_exists": True,
        }

        update = MockUpdate()
        context = MockContext()
        run_async(graph_stats_cmd(update, context))

        self.assertIn("200", update.message._reply)
        self.assertIn("450", update.message._reply)

    def test_graph_export_cmd_no_args(self):
        from interface.handlers.graphify_handler import graph_export_cmd

        update = MockUpdate(args=[])
        context = MockContext(args=[])
        run_async(graph_export_cmd(update, context))

        self.assertIn("Formatos", update.message._reply)

    def test_graph_add_cmd_no_args(self):
        from interface.handlers.graphify_handler import graph_add_cmd

        update = MockUpdate(args=[])
        context = MockContext(args=[])
        run_async(graph_add_cmd(update, context))

        self.assertIn("/graph_add", update.message._reply)


if __name__ == "__main__":
    unittest.main(verbosity=2)
