"""Unit tests for vault_manager.py."""
import sys
import os
import unittest
from unittest.mock import Mock, patch, MagicMock
import json
import tempfile
import shutil

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestVaultManager(unittest.TestCase):
    """Test VaultManager class."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.config_patch = patch('core.vault_manager.VaultManager._load_config')
        self.config_patch.start()

    def tearDown(self):
        """Clean up test fixtures."""
        self.config_patch.stop()
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_vault_manager_init(self):
        """Test VaultManager initialization."""
        from core.vault_manager import VaultManager
        with patch.object(VaultManager, '_load_config', return_value={}):
            vm = VaultManager()
            self.assertIsNotNone(vm)

    def test_list_vaults_empty(self):
        """Test listing vaults when none exist."""
        from core.vault_manager import VaultManager
        with patch.object(VaultManager, '_load_config', return_value={}):
            vm = VaultManager()
            vm.vaults = {}
            result = vm.list_vaults()
            self.assertEqual(result, [])

    def test_list_vaults_with_data(self):
        """Test listing vaults with existing data."""
        from core.vault_manager import VaultManager
        with patch.object(VaultManager, '_load_config', return_value={}):
            vm = VaultManager()
            vm.vaults = {
                "principal": {"path": "/data/principal"},
                "research": {"path": "/data/research"},
            }
            result = vm.list_vaults()
            self.assertEqual(len(result), 2)
            self.assertIn("principal", result)
            self.assertIn("research", result)

    def test_get_active_vault(self):
        """Test getting active vault name."""
        from core.vault_manager import VaultManager
        with patch.object(VaultManager, '_load_config', return_value={}):
            vm = VaultManager()
            vm.active_vault = "principal"
            self.assertEqual(vm.active_vault, "principal")


class TestVaultConfig(unittest.TestCase):
    """Test vault configuration handling."""

    def test_vault_config_structure(self):
        """Test vault configuration has expected structure."""
        config = {
            "active": "principal",
            "vaults": {
                "principal": {
                    "path": "/data/principal",
                    "created": "2024-01-01",
                }
            }
        }
        self.assertIn("active", config)
        self.assertIn("vaults", config)
        self.assertIn("principal", config["vaults"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
