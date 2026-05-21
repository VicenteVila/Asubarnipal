"""Vault Manager - Gestión de múltiples vaults de conocimiento."""

import json
import os
import shutil
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime

import config

logger = logging.getLogger(__name__)


class VaultManager:
    """Manager for multiple Obsidian vaults."""

    CONFIG_FILE = config.DATA_DIR / "vaults_config.json"
    DEFAULT_VAULT_NAME = "principal"

    _instance: Optional['VaultManager'] = None

    def __new__(cls) -> Self:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self) -> None:
        if self._initialized:
            return

        self._initialized = True
        self._config: Dict[str, Any] = {}
        self._load_config()
        self._ensure_default_vault()

    def _load_config(self) -> None:
        """Load vault configuration from file."""
        if self.CONFIG_FILE.exists():
            try:
                with open(self.CONFIG_FILE, "r", encoding="utf-8") as f:
                    self._config = json.load(f)
            except Exception as e:
                logger.error(f"Error loading vault config: {e}")
                self._config = {"active_vault": None, "vaults": {}}
        else:
            self._config = {"active_vault": None, "vaults": {}}

    def _save_config(self) -> None:
        """Save vault configuration to file."""
        try:
            self.CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
            with open(self.CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(self._config, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Error saving vault config: {e}")

    def _ensure_default_vault(self) -> None:
        """Ensure default vault exists."""
        if not self._config.get("active_vault"):
            default_path = str(config.BASE_DIR / "obsidian_vault")
            self.create(self.DEFAULT_VAULT_NAME, default_path, "Vault principal de conocimiento")

    def _get_db_path(self, name: str) -> Path:
        """Get database path for a vault."""
        safe_name = name.replace(" ", "_").lower()
        return config.DATA_DIR / f"wiki_{safe_name}.db"

    def _get_index_path(self, name: str) -> Path:
        """Get RAG index path for a vault."""
        safe_name = name.replace(" ", "_").lower()
        return config.DATA_DIR / f"index_{safe_name}.faiss"

    def list_vaults(self) -> Dict[str, Any]:
        """List all vaults."""
        vaults = self._config.get("vaults", {})
        active = self._config.get("active_vault")

        result = []
        for name, info in vaults.items():
            db_path = Path(info.get("db_path", ""))
            count = 0
            if db_path.exists():
                try:
                    import sqlite3
                    conn = sqlite3.connect(str(db_path))
                    cursor = conn.execute("SELECT COUNT(*) FROM entities")
                    count = cursor.fetchone()[0]
                    conn.close()
                except Exception:
                    pass

            result.append({
                "name": name,
                "path": info.get("path"),
                "active": name == active,
                "notes_count": count,
                "description": info.get("description", ""),
                "created": info.get("created"),
            })

        return {
            "success": True,
            "active_vault": active,
            "vaults": result,
            "total": len(result),
        }

    def get_active(self) -> Optional[Dict[str, Any]]:
        """Get active vault info."""
        active_name = self._config.get("active_vault")
        if not active_name:
            return None

        vaults = self._config.get("vaults", {})
        if active_name not in vaults:
            return None

        info = vaults[active_name]
        return {
            "name": active_name,
            "path": info.get("path"),
            "db_path": info.get("db_path"),
            "index_path": info.get("index_path"),
            "description": info.get("description", ""),
            "created": info.get("created"),
        }

    def create(self, name: str, path: str, description: str = "") -> Dict[str, Any]:
        """
        Create a new vault.

        Args:
            name: Vault name (must be unique)
            path: Path to Obsidian vault folder
            description: Optional description

        Returns:
            Dict with success status and vault info
        """
        name = name.strip().lower().replace(" ", "_")

        if not name:
            return {"success": False, "error": "Nombre de vault inválido"}

        if name in self._config.get("vaults", {}):
            return {"success": False, "error": f"El vault '{name}' ya existe"}

        vaults = self._config.get("vaults", {})

        vault_path = Path(path)
        try:
            vault_path.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            return {"success": False, "error": f"No se pudo crear la carpeta: {e}"}

        db_path = self._get_db_path(name)
        index_path = self._get_index_path(name)

        vaults[name] = {
            "path": str(vault_path),
            "db_path": str(db_path),
            "index_path": str(index_path),
            "description": description,
            "created": datetime.now().strftime("%Y-%m-%d"),
        }

        self._config["vaults"] = vaults
        self._save_config()

        self._init_vault_db(db_path)

        logger.info(f"Vault created: {name} at {path}")
        return {
            "success": True,
            "name": name,
            "path": str(vault_path),
            "db_path": str(db_path),
            "index_path": str(index_path),
        }

    def _init_vault_db(self, db_path: Path) -> None:
        """Initialize vault database with schema."""
        try:
            import sqlite3
            conn = sqlite3.connect(str(db_path))
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS entities (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE NOT NULL,
                    content TEXT,
                    entity_type TEXT,
                    source TEXT,
                    created_at TEXT,
                    updated_at TEXT
                );
                CREATE TABLE IF NOT EXISTS relations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    from_entity TEXT,
                    to_entity TEXT,
                    relation_type TEXT,
                    created_at TEXT
                );
                CREATE TABLE IF NOT EXISTS tags (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    entity_name TEXT,
                    tag TEXT
                );
                CREATE INDEX IF NOT EXISTS idx_entity_name ON entities(name);
                CREATE INDEX IF NOT EXISTS idx_entity_type ON entities(entity_type);
            """)
            conn.close()
            logger.info(f"Vault DB initialized: {db_path}")
        except Exception as e:
            logger.error(f"Error initializing vault DB: {e}")

    def switch(self, name: str) -> Dict[str, Any]:
        """
        Switch to a different vault.

        Args:
            name: Vault name to switch to

        Returns:
            Dict with success status and new vault info
        """
        vaults = self._config.get("vaults", {})

        if name not in vaults:
            return {"success": False, "error": f"El vault '{name}' no existe"}

        info = vaults[name]
        vault_path = Path(info.get("path", ""))

        if not vault_path.exists():
            return {"success": False, "error": f"El vault '{name}' no existe en: {vault_path}"}

        self._config["active_vault"] = name
        self._save_config()

        logger.info(f"Switched to vault: {name}")
        return {
            "success": True,
            "name": name,
            "path": info.get("path"),
            "db_path": info.get("db_path"),
            "index_path": info.get("index_path"),
        }

    def delete(self, name: str, backup: bool = True) -> Dict[str, Any]:
        """
        Delete a vault.

        Args:
            name: Vault name to delete
            backup: Create backup before deleting

        Returns:
            Dict with success status
        """
        if name == self.DEFAULT_VAULT_NAME:
            return {"success": False, "error": "No se puede eliminar el vault principal"}

        vaults = self._config.get("vaults", {})

        if name not in vaults:
            return {"success": False, "error": f"El vault '{name}' no existe"}

        if self._config.get("active_vault") == name:
            return {"success": False, "error": "No se puede eliminar el vault activo. Usa /vault_use primero"}

        info = vaults[name]

        if backup:
            backup_dir = config.DATA_DIR / "backups"
            backup_dir.mkdir(exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = backup_dir / f"vault_{name}_{timestamp}.zip"

            try:
                import zipfile
                with zipfile.ZipFile(backup_path, "w") as zipf:
                    db_path = Path(info.get("db_path", ""))
                    if db_path.exists():
                        zipf.write(db_path, db_path.name)
                logger.info(f"Backup created: {backup_path}")
            except Exception as e:
                logger.warning(f"Backup failed: {e}")

        db_path = Path(info.get("db_path", ""))
        if db_path.exists():
            db_path.unlink()

        index_path = Path(info.get("index_path", ""))
        if index_path.exists():
            index_path.unlink()

        del vaults[name]
        self._config["vaults"] = vaults
        self._save_config()

        logger.info(f"Vault deleted: {name}")
        return {"success": True, "name": name}

    def export_vault(self, name: str, output_path: Optional[str] = None) -> Dict[str, Any]:
        """
        Export vault data to JSON.

        Args:
            name: Vault name to export
            output_path: Optional output file path

        Returns:
            Dict with success status and export path
        """
        vaults = self._config.get("vaults", {})

        if name not in vaults:
            return {"success": False, "error": f"El vault '{name}' no existe"}

        info = vaults[name]
        db_path = Path(info.get("db_path", ""))

        if not db_path.exists():
            return {"success": False, "error": f"DB del vault '{name}' no existe"}

        try:
            import sqlite3
            conn = sqlite3.connect(str(db_path))
            cursor = conn.execute("SELECT name, content, entity_type, source, created_at FROM entities")
            entities = []
            for row in cursor.fetchall():
                entities.append({
                    "name": row[0],
                    "content": row[1],
                    "type": row[2],
                    "source": row[3],
                    "created": row[4],
                })
            conn.close()

            export_data = {
                "vault_name": name,
                "exported_at": datetime.now().isoformat(),
                "entities_count": len(entities),
                "entities": entities,
            }

            if output_path is None:
                output_path = str(config.DATA_DIR / f"export_{name}.json")

            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False)

            logger.info(f"Vault exported: {name} to {output_path}")
            return {
                "success": True,
                "name": name,
                "export_path": output_path,
                "entities_count": len(entities),
            }

        except Exception as e:
            logger.error(f"Export failed: {e}")
            return {"success": False, "error": str(e)}

    def import_vault(self, name: str, file_path: str, create_new: bool = True) -> Dict[str, Any]:
        """
        Import vault data from JSON.

        Args:
            name: Target vault name
            file_path: Path to import file
            create_new: Create new vault or use existing

        Returns:
            Dict with success status
        """
        import_path = Path(file_path)

        if not import_path.exists():
            return {"success": False, "error": f"El archivo '{file_path}' no existe"}

        try:
            with open(import_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            entities = data.get("entities", [])
            if not entities:
                return {"success": False, "error": "Archivo no contiene entidades"}

            if name not in self._config.get("vaults", {}):
                default_path = str(config.DATA_DIR / f"vault_{name}")
                self.create(name, default_path, f"Vault importado desde {file_path}")

            vaults = self._config.get("vaults", {})
            info = vaults.get(name)
            if not info:
                return {"success": False, "error": "Error creando vault"}

            db_path = Path(info.get("db_path", ""))
            self._init_vault_db(db_path)

            import sqlite3
            conn = sqlite3.connect(str(db_path))

            for entity in entities:
                conn.execute("""
                    INSERT OR REPLACE INTO entities (name, content, entity_type, source, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    entity.get("name"),
                    entity.get("content"),
                    entity.get("type"),
                    entity.get("source"),
                    entity.get("created", datetime.now().strftime("%Y-%m-%d")),
                    datetime.now().strftime("%Y-%m-%d"),
                ))

            conn.commit()
            conn.close()

            logger.info(f"Vault imported: {name} from {file_path}, {len(entities)} entities")
            return {
                "success": True,
                "name": name,
                "entities_imported": len(entities),
            }

        except Exception as e:
            logger.error(f"Import failed: {e}")
            return {"success": False, "error": str(e)}

    def connect(self, path: str, name: str = None, description: str = "") -> Dict[str, Any]:
        """
        Connect to an existing Obsidian vault folder.

        Args:
            path: Path to existing Obsidian vault folder
            name: Optional name (defaults to folder name)
            description: Optional description

        Returns:
            Dict with success status and vault info
        """
        vault_path = Path(path)

        if not vault_path.exists():
            return {"success": False, "error": f"La carpeta '{path}' no existe"}

        if not vault_path.is_dir():
            return {"success": False, "error": f"'{path}' no es una carpeta"}

        # Use folder name as default
        if not name:
            name = vault_path.name.lower().replace(" ", "_")

        # Check if already connected
        vaults = self._config.get("vaults", {})
        if name in vaults:
            return {"success": False, "error": f"El vault '{name}' ya está conectado"}

        # Create vault config
        db_path = self._get_db_path(name)
        index_path = self._get_index_path(name)

        vaults[name] = {
            "path": str(vault_path),
            "db_path": str(db_path),
            "index_path": str(index_path),
            "description": description or f"Vault conectada desde {path}",
            "created": datetime.now().isoformat(),
            "connected": True,  # Mark as connected (external)
        }

        self._config["vaults"] = vaults
        self._save_config()

        logger.info(f"Connected to vault: {name} at {path}")
        return {
            "success": True,
            "name": name,
            "path": str(vault_path),
            "db_path": str(db_path),
            "description": vaults[name]["description"],
        }

    def disconnect(self, name: str = None) -> Dict[str, Any]:
        """
        Disconnect a vault (remove from config, optionally keep data).

        Args:
            name: Vault name to disconnect. If None, disconnects active vault.

        Returns:
            Dict with success status
        """
        vaults = self._config.get("vaults", {})

        # Use active vault if not specified
        if not name:
            name = self._config.get("active_vault")
            if not name:
                return {"success": False, "error": "No hay vault activo para desconectar"}

        if name not in vaults:
            return {"success": False, "error": f"El vault '{name}' no existe"}

        # Cannot disconnect default vault
        if name == self.DEFAULT_VAULT_NAME:
            return {"success": False, "error": "No se puede desconectar el vault principal"}

        info = vaults[name]
        was_active = self._config.get("active_vault") == name

        # Remove from config
        del vaults[name]
        self._config["vaults"] = vaults

        # If was active, clear active_vault
        if was_active:
            self._config["active_vault"] = None

        self._save_config()

        logger.info(f"Disconnected vault: {name}")
        return {
            "success": True,
            "name": name,
            "path": info.get("path"),
            "was_active": was_active,
        }

    def get_vault_notes_count(self, name: str = None) -> int:
        """Get count of .md files in vault."""
        if not name:
            name = self._config.get("active_vault")
            if not name:
                return 0

        vaults = self._config.get("vaults", {})
        if name not in vaults:
            return 0

        vault_path = Path(vaults[name].get("path", ""))
        if not vault_path.exists():
            return 0

        md_files = list(vault_path.rglob("*.md"))
        return len(md_files)


def get_vault_manager() -> VaultManager:
    """Get singleton VaultManager instance."""
    return VaultManager()


def get_active_vault() -> Optional[Dict[str, Any]]:
    """Convenience function to get active vault."""
    return get_vault_manager().get_active()


def list_all_vaults() -> Dict[str, Any]:
    """Convenience function to list all vaults."""
    return get_vault_manager().list_vaults()