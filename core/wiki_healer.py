"""WikiHealer - Repara entradas huerfanas en la wiki."""

import logging
import sqlite3
from pathlib import Path
from typing import Optional

import config

logger = logging.getLogger(__name__)


class WikiHealer:
    """Repara y limpia entradas huerfanas en la wiki."""
    
    def __init__(self, wiki_path: Optional[Path] = None) -> None:
        self.wiki_path = wiki_path or config.WIKI_DIR
        self.db_path = config.WIKI_PATH
        self._init_connection()
    
    def _init_connection(self) -> None:
        """Inicializa conexion a la base de datos."""
        if not self.db_path.exists():
            logger.warning(f"Wiki database not found: {self.db_path}")
            self.conn = None
            return
        
        self.conn = sqlite3.connect(str(self.db_path))
        self.conn.row_factory = sqlite3.Row
        self.cursor = self.conn.cursor()
    
    def heal_orphans(self) -> int:
        """Encuentra y repara entradas huerfanas."""
        if self.conn is None:
            return 0
        
        healed = 0
        
        try:
            self.cursor.execute("""
                SELECT id, name, relacionados, tags 
                FROM entities 
                WHERE estado = 'orphan'
            """)
            orphans = self.cursor.fetchall()
            
            for orphan in orphans:
                try:
                    relacionados = orphan[2] if len(orphan) > 2 else '[]'
                    tags = orphan[3] if len(orphan) > 3 else '[]'
                    
                    if isinstance(relacionados, str):
                        relacionados = json.loads(relacionados) if relacionados else []
                    if isinstance(tags, str):
                        tags = json.loads(tags) if tags else []
                    
                    if not relacionados and not tags:
                        self.cursor.execute("""
                            UPDATE entities 
                            SET estado = 'draft'
                            WHERE id = ?
                        """, (orphan[0],))
                        healed += 1
                        
                except Exception as e:
                    logger.warning(f"Error healing orphan {orphan[0]}: {e}")
            
            self.conn.commit()
            logger.info(f"Healed {healed} orphan entries")
            
        except Exception as e:
            logger.error(f"Error in heal_orphans: {e}")
        
        return healed
    
    def cleanup_duplicates(self) -> int:
        """Elimina entradas duplicadas."""
        if self.conn is None:
            return 0
        
        removed = 0
        
        try:
            self.cursor.execute("""
                SELECT name, COUNT(*) as cnt 
                FROM entities 
                GROUP BY name 
                HAVING cnt > 1
            """)
            duplicates = self.cursor.fetchall()
            
            for dup in duplicates:
                self.cursor.execute("""
                    DELETE FROM entities 
                    WHERE name = ? AND id NOT IN (
                        SELECT MIN(id) FROM entities WHERE name = ?
                    )
                """, (dup['name'], dup['name']))
                removed += self.cursor.rowcount
            
            self.conn.commit()
            logger.info(f"Removed {removed} duplicate entries")
            
        except Exception as e:
            logger.error(f"Error in cleanup_duplicates: {e}")
        
        return removed
    
    def vacuum_database(self) -> bool:
        """Ejecuta VACUUM en la base de datos."""
        if self.conn is None:
            return False
        
        try:
            self.cursor.execute("VACUUM")
            self.conn.commit()
            logger.info("Database vacuumed")
            return True
        except Exception as e:
            logger.error(f"Error in vacuum_database: {e}")
            return False
    
    def close(self) -> None:
        """Cierra la conexion."""
        if self.conn:
            self.conn.close()
