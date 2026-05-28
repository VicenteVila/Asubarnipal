"""Integration tests for vault isolation."""

import os
import sys
import unittest
import tempfile
import json
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestVaultIntegration(unittest.TestCase):
    """Test vault creation, switching, and isolation."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.temp_path = Path(self.temp_dir.name)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_create_and_list_vaults(self):
        """Test creating vaults and listing them."""
        from core.vault_manager import VaultManager

        vm = VaultManager()
        vm.vaults_file = self.temp_path / "vaults.json"

        result_a = vm.create("vault_a", str(self.temp_path / "vault_a"))
        self.assertTrue(result_a["success"])

        result_b = vm.create("vault_b", str(self.temp_path / "vault_b"))
        self.assertTrue(result_b["success"])

        vaults = vm.list_vaults()
        self.assertGreaterEqual(len(vaults), 2)

    def test_switch_vault(self):
        """Test switching between vaults."""
        from core.vault_manager import VaultManager

        vm = VaultManager()
        vm.vaults_file = self.temp_path / "vaults.json"

        vm.create("vault_a", str(self.temp_path / "vault_a"))
        vm.create("vault_b", str(self.temp_path / "vault_b"))

        switch_a = vm.switch("vault_a")
        self.assertTrue(switch_a["success"])

        active = vm.get_active()
        self.assertEqual(active["name"], "vault_a")

        switch_b = vm.switch("vault_b")
        self.assertTrue(switch_b["success"])

        active = vm.get_active()
        self.assertEqual(active["name"], "vault_b")

    def test_vault_isolation(self):
        """Test that vaults are isolated from each other."""
        from core.vault_manager import VaultManager

        vm = VaultManager()
        vm.vaults_file = self.temp_path / "vaults.json"

        vm.create("isolated_a", str(self.temp_path / "isolated_a"))
        vm.create("isolated_b", str(self.temp_path / "isolated_b"))

        vm.switch("isolated_a")
        path_a = vm.get_active()["path"]

        vm.switch("isolated_b")
        path_b = vm.get_active()["path"]

        self.assertNotEqual(path_a, path_b)

    def test_delete_vault(self):
        """Test deleting a vault."""
        from core.vault_manager import VaultManager

        vm = VaultManager()
        vm.vaults_file = self.temp_path / "vaults.json"

        vm.create("to_delete", str(self.temp_path / "to_delete"))

        vaults_before = vm.list_vaults()

        result = vm.delete("to_delete")
        self.assertTrue(result["success"])

        vaults_after = vm.list_vaults()
        self.assertLess(len(vaults_after), len(vaults_before))

    def test_vault_persistence(self):
        """Test vault configuration persists across instances."""
        from core.vault_manager import VaultManager

        vm1 = VaultManager()
        vm1.vaults_file = self.temp_path / "vaults_persist.json"

        vm1.create("persistent", str(self.temp_path / "persistent"))

        vm2 = VaultManager()
        vm2.vaults_file = self.temp_path / "vaults_persist.json"

        vaults = vm2.list_vaults()
        vault_names = [v["name"] for v in vaults]
        self.assertIn("persistent", vault_names)


class TestVaultMemoryTreeIsolation(unittest.TestCase):
    """Test that memory trees are isolated per vault."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.temp_path = Path(self.temp_dir.name)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_different_vaults_different_dbs(self):
        """Test different vaults use different database files."""
        with patch("config.DATA_DIR", self.temp_path):
            from core.memory_tree import MemoryTree

            tree_a = MemoryTree(vault_name="vault_alpha")
            tree_b = MemoryTree(vault_name="vault_beta")

            self.assertNotEqual(tree_a.db_path, tree_b.db_path)
            self.assertIn("vault_alpha", str(tree_a.db_path))
            self.assertIn("vault_beta", str(tree_b.db_path))

            tree_a.close()
            tree_b.close()


if __name__ == "__main__":
    unittest.main(verbosity=2)
