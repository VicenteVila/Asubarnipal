"""Vault management skills for the agent."""

import logging
from typing import Dict, Any

from core.vault_manager import get_vault_manager

logger = logging.getLogger(__name__)


def list_vaults() -> Dict[str, Any]:
    """
    List all available vaults.

    Returns:
        Dict with vault list and active vault
    """
    try:
        vm = get_vault_manager()
        result = vm.list_vaults()
        return result
    except Exception as e:
        logger.error(f"list_vaults failed: {e}", exc=e)
        return {"success": False, "error": str(e)}


def create_vault(name: str, path: str, description: str = "") -> Dict[str, Any]:
    """
    Create a new vault.

    Args:
        name: Vault name (unique)
        path: Path to vault folder
        description: Optional description

    Returns:
        Dict with success status and vault info
    """
    try:
        vm = get_vault_manager()
        result = vm.create(name, path, description)
        return result
    except Exception as e:
        logger.error(f"create_vault failed: {e}", exc=e)
        return {"success": False, "error": str(e)}


def switch_vault(name: str) -> Dict[str, Any]:
    """
    Switch to a different vault.

    Args:
        name: Vault name to switch to

    Returns:
        Dict with success status and new vault info
    """
    try:
        vm = get_vault_manager()
        result = vm.switch(name)
        return result
    except Exception as e:
        logger.error(f"switch_vault failed: {e}", exc=e)
        return {"success": False, "error": str(e)}


def delete_vault(name: str, backup: bool = True) -> Dict[str, Any]:
    """
    Delete a vault with optional backup.

    Args:
        name: Vault name to delete
        backup: Create backup before deleting

    Returns:
        Dict with success status
    """
    try:
        vm = get_vault_manager()
        result = vm.delete(name, backup)
        return result
    except Exception as e:
        logger.error(f"delete_vault failed: {e}", exc=e)
        return {"success": False, "error": str(e)}


def export_vault(name: str, output_path: str = None) -> Dict[str, Any]:
    """
    Export vault data to JSON file.

    Args:
        name: Vault name to export
        output_path: Optional output file path

    Returns:
        Dict with success status and export path
    """
    try:
        vm = get_vault_manager()
        result = vm.export_vault(name, output_path)
        return result
    except Exception as e:
        logger.error(f"export_vault failed: {e}", exc=e)
        return {"success": False, "error": str(e)}


def import_vault(name: str, file_path: str) -> Dict[str, Any]:
    """
    Import vault data from JSON file.

    Args:
        name: Target vault name
        file_path: Path to import file

    Returns:
        Dict with success status
    """
    try:
        vm = get_vault_manager()
        result = vm.import_vault(name, file_path)
        return result
    except Exception as e:
        logger.error(f"import_vault failed: {e}", exc=e)
        return {"success": False, "error": str(e)}


def get_active_vault() -> Dict[str, Any]:
    """
    Get information about the active vault.

    Returns:
        Dict with active vault info
    """
    try:
        vm = get_vault_manager()
        vault = vm.get_active()

        if not vault:
            return {"success": False, "error": "No active vault"}

        return {
            "success": True,
            "vault": vault,
            "name": vault.get("name"),
            "path": vault.get("path"),
        }
    except Exception as e:
        logger.error(f"get_active_vault failed: {e}", exc=e)
        return {"success": False, "error": str(e)}


def get_vault_stats(name: str = None) -> Dict[str, Any]:
    """
    Get statistics for a vault.

    Args:
        name: Vault name (uses active if None)

    Returns:
        Dict with vault statistics
    """
    try:
        vm = get_vault_manager()

        if name:
            result = vm.list_vaults()
            vaults = result.get("vaults", [])
            vault_info = next((v for v in vaults if v["name"] == name), None)
        else:
            vault_info = vm.get_active()

        if not vault_info:
            return {"success": False, "error": "Vault not found"}

        import sqlite3
        from pathlib import Path

        db_path = vault_info.get("db_path") if isinstance(vault_info, dict) else None
        if not db_path:
            return {"success": False, "error": "No db_path"}

        path = Path(db_path)
        if not path.exists():
            return {"success": True, "name": name or "unknown", "notes": 0}

        conn = sqlite3.connect(str(path))
        cursor = conn.execute("SELECT COUNT(*) FROM entities")
        total = cursor.fetchone()[0]

        cursor = conn.execute("SELECT COUNT(*) FROM entities WHERE entity_type = 'entity'")
        entities = cursor.fetchone()[0]

        conn.close()

        return {
            "success": True,
            "name": name or vault_info.get("name"),
            "notes": total,
            "entities": entities,
            "relations": total - entities,
        }
    except Exception as e:
        logger.error(f"get_vault_stats failed: {e}", exc=e)
        return {"success": False, "error": str(e)}