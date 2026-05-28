"""Tests for LIFE-HARNESS and HASP Telegram command handlers."""

import os
import sys
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestHarnessCommands(unittest.TestCase):
    """Test harness command handlers."""

    def setUp(self):
        self.update = MagicMock()
        self.update.message = MagicMock()
        self.update.message.reply_text = AsyncMock()
        self.context = MagicMock()
        self.context.args = []

    def test_harness_cmd_import(self):
        """Test harness_cmd can be imported."""
        from interface.handlers.harness_commands import harness_cmd
        self.assertTrue(callable(harness_cmd))

    def test_pfs_cmd_import(self):
        """Test pfs_cmd can be imported."""
        from interface.handlers.harness_commands import pfs_cmd
        self.assertTrue(callable(pfs_cmd))

    def test_pf_run_cmd_import(self):
        """Test pf_run_cmd can be imported."""
        from interface.handlers.harness_commands import pf_run_cmd
        self.assertTrue(callable(pf_run_cmd))

    def test_harness_reset_cmd_import(self):
        """Test harness_reset_cmd can be imported."""
        from interface.handlers.harness_commands import harness_reset_cmd
        self.assertTrue(callable(harness_reset_cmd))

    def test_get_harness_handlers(self):
        """Test get_harness_handlers returns all handlers."""
        from interface.handlers.harness_commands import get_harness_handlers
        handlers = get_harness_handlers()
        self.assertIn("harness", handlers)
        self.assertIn("pfs", handlers)
        self.assertIn("pf_run", handlers)
        self.assertIn("harness_reset", handlers)
        self.assertEqual(len(handlers), 4)


class TestHarnessCmdExecution(unittest.TestCase):
    """Test harness command execution."""

    def setUp(self):
        self.update = MagicMock()
        self.update.message = MagicMock()
        self.update.message.reply_text = AsyncMock()
        self.context = MagicMock()
        self.context.args = []

    @patch("interface.handlers.harness_commands.get_harness")
    def test_harness_cmd_success(self, mock_get_harness):
        """Test /harness command with valid stats."""
        import asyncio
        from interface.handlers.harness_commands import harness_cmd

        mock_harness = MagicMock()
        mock_harness.get_stats.return_value = {
            "total_interventions": 5,
            "contract_layer": {"cached_contracts": 10, "corrections_applied": 3},
            "skill_layer": {"total_skills": 2, "failure_history": 1, "skills": []},
            "action_layer": {"validated_actions": 50, "rejected_actions": 2},
            "trajectory_layer": {
                "active_trajectories": 1,
                "recoveries_triggered": 3,
                "config": {"max_stagnation": 3, "max_actions": 50},
            },
        }
        mock_get_harness.return_value = mock_harness

        asyncio.run(harness_cmd(self.update, self.context))
        self.update.message.reply_text.assert_called_once()
        call_args = self.update.message.reply_text.call_args
        self.assertIn("LIFE-HARNESS", call_args[0][0])

    @patch("interface.handlers.harness_commands.get_harness")
    def test_harness_cmd_error(self, mock_get_harness):
        """Test /harness command with error."""
        import asyncio
        from interface.handlers.harness_commands import harness_cmd

        mock_get_harness.side_effect = Exception("Harness not available")

        asyncio.run(harness_cmd(self.update, self.context))
        self.update.message.reply_text.assert_called_once()
        call_args = self.update.message.reply_text.call_args
        self.assertIn("Error", call_args[0][0])

    @patch("interface.handlers.harness_commands.get_pf_registry")
    def test_pfs_cmd_success(self, mock_get_registry):
        """Test /pfs command with registered PFs."""
        import asyncio
        from interface.handlers.harness_commands import pfs_cmd

        mock_registry = MagicMock()
        mock_registry.list_pfs.return_value = [
            {
                "name": "retry_on_failure",
                "description": "Retry on failure",
                "preconditions": [("last_action.status", "error")],
                "priority": 10,
                "invocations": 5,
                "success_count": 3,
            },
            {
                "name": "fallback_on_exhaustion",
                "description": "Fallback when exhausted",
                "preconditions": [("last_action.status", "timeout")],
                "priority": 5,
                "invocations": 2,
                "success_count": 1,
            },
        ]
        mock_get_registry.return_value = mock_registry

        asyncio.run(pfs_cmd(self.update, self.context))
        self.update.message.reply_text.assert_called_once()
        call_args = self.update.message.reply_text.call_args
        self.assertIn("Program Functions", call_args[0][0])
        self.assertIn("2", call_args[0][0])

    @patch("interface.handlers.harness_commands.get_pf_registry")
    def test_pfs_cmd_empty(self, mock_get_registry):
        """Test /pfs command with no PFs."""
        import asyncio
        from interface.handlers.harness_commands import pfs_cmd

        mock_registry = MagicMock()
        mock_registry.list_pfs.return_value = []
        mock_get_registry.return_value = mock_registry

        asyncio.run(pfs_cmd(self.update, self.context))
        self.update.message.reply_text.assert_called_once()
        call_args = self.update.message.reply_text.call_args
        self.assertIn("no hay PFs", call_args[0][0])

    def test_pf_run_cmd_no_args(self):
        """Test /pf_run command without arguments."""
        import asyncio
        from interface.handlers.harness_commands import pf_run_cmd

        self.context.args = []
        asyncio.run(pf_run_cmd(self.update, self.context))
        self.update.message.reply_text.assert_called_once()
        call_args = self.update.message.reply_text.call_args
        self.assertIn("Uso:", call_args[0][0])

    @patch("interface.handlers.harness_commands.get_pf_registry")
    def test_pf_run_cmd_success(self, mock_get_registry):
        """Test /pf_run command with valid PF."""
        import asyncio
        from interface.handlers.harness_commands import pf_run_cmd

        mock_registry = MagicMock()
        mock_registry.execute_pf.return_value = {"action": "retry", "message": "Retrying"}
        mock_get_registry.return_value = mock_registry

        self.context.args = ["retry_on_failure", '{"last_action": {"status": "error"}}']
        asyncio.run(pf_run_cmd(self.update, self.context))
        self.update.message.reply_text.assert_called_once()
        call_args = self.update.message.reply_text.call_args
        self.assertIn("PF Ejecutado", call_args[0][0])

    @patch("interface.handlers.harness_commands.get_pf_registry")
    def test_pf_run_cmd_not_found(self, mock_get_registry):
        """Test /pf_run command with non-existent PF."""
        import asyncio
        from interface.handlers.harness_commands import pf_run_cmd

        mock_registry = MagicMock()
        mock_registry.execute_pf.return_value = None
        mock_get_registry.return_value = mock_registry

        self.context.args = ["nonexistent_pf", "{}"]
        asyncio.run(pf_run_cmd(self.update, self.context))
        self.update.message.reply_text.assert_called_once()
        call_args = self.update.message.reply_text.call_args
        self.assertIn("no encontrado", call_args[0][0])

    def test_pf_run_cmd_invalid_json(self):
        """Test /pf_run command with invalid JSON."""
        import asyncio
        from interface.handlers.harness_commands import pf_run_cmd

        self.context.args = ["retry_on_failure", "not valid json"]
        asyncio.run(pf_run_cmd(self.update, self.context))
        self.update.message.reply_text.assert_called_once()
        call_args = self.update.message.reply_text.call_args
        self.assertIn("JSON inválido", call_args[0][0])

    @patch("interface.handlers.harness_commands.get_harness")
    def test_harness_reset_cmd_success(self, mock_get_harness):
        """Test /harness_reset command."""
        import asyncio
        from interface.handlers.harness_commands import harness_reset_cmd

        mock_harness = MagicMock()
        mock_get_harness.return_value = mock_harness

        asyncio.run(harness_reset_cmd(self.update, self.context))
        mock_harness.reset_stats.assert_called_once()
        self.update.message.reply_text.assert_called_once()
        call_args = self.update.message.reply_text.call_args
        self.assertIn("reseteadas", call_args[0][0])


if __name__ == "__main__":
    unittest.main(verbosity=2)
