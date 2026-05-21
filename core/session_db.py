"""Session persistence using SQLite for chat history."""

import json
import logging
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any

import config

logger = logging.getLogger(__name__)


class SessionDB:
    """SQLite-based session persistence for user chat history."""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self) -> None:
        if self._initialized:
            return
        
        self._initialized = True
        self.db_path = config.DATA_DIR / "sessions.db"
        self._init_tables()
        logger.info(f"SessionDB initialized at {self.db_path}")
    
    def _init_tables(self):
        """Initialize database tables."""
        self.conn = sqlite3.connect(str(self.db_path))
        self.conn.row_factory = sqlite3.Row
        
        self.cursor = self.conn.cursor()
        
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER UNIQUE NOT NULL,
                charla_mode TEXT,
                last_model TEXT,
                fallback_tried INTEGER DEFAULT 0,
                system_prompt TEXT,
                created_at TEXT,
                updated_at TEXT
            )
        """)
        
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS session_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                tokens INTEGER DEFAULT 0,
                created_at TEXT,
                FOREIGN KEY(session_id) REFERENCES user_sessions(id)
            )
        """)
        
        self.cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_messages_session 
            ON session_messages(session_id)
        """)
        
        self.conn.commit()
    
    def _get_or_create_session(self, user_id: int) -> int:
        """Get existing session or create new one. Returns session_id."""
        now = datetime.now().isoformat()
        
        self.cursor.execute(
            "SELECT id FROM user_sessions WHERE user_id = ?",
            (user_id,)
        )
        row = self.cursor.fetchone()
        
        if row:
            self.cursor.execute(
                "UPDATE user_sessions SET updated_at = ? WHERE user_id = ?",
                (now, user_id)
            )
            self.conn.commit()
            return row[0]
        
        self.cursor.execute(
            """INSERT INTO user_sessions 
               (user_id, created_at, updated_at) 
               VALUES (?, ?, ?)""",
            (user_id, now, now)
        )
        self.conn.commit()
        return self.cursor.lastrowid
    
    def save_message(self, user_id: int, role: str, content: str, tokens: int = 0) -> bool:
        """Save a message to the session history."""
        try:
            session_id = self._get_or_create_session(user_id)
            now = datetime.now().isoformat()
            
            self.cursor.execute(
                """INSERT INTO session_messages 
                   (session_id, role, content, tokens, created_at)
                   VALUES (?, ?, ?, ?, ?)""",
                (session_id, role, content, tokens, now)
            )
            self.conn.commit()
            
            logger.debug(f"Saved message: role={role}, tokens={tokens}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save message: {e}")
            return False
    
    def load_history(self, user_id: int) -> List[Dict[str, str]]:
        """Load all messages for a user as a list of dicts."""
        try:
            self.cursor.execute(
                "SELECT id FROM user_sessions WHERE user_id = ?",
                (user_id,)
            )
            row = self.cursor.fetchone()
            
            if not row:
                return []
            
            session_id = row[0]
            
            self.cursor.execute(
                """SELECT role, content FROM session_messages 
                   WHERE session_id = ?
                   ORDER BY created_at ASC""",
                (session_id,)
            )
            
            messages = [
                {"role": r["role"], "content": r["content"]}
                for r in self.cursor.fetchall()
            ]
            
            return messages
            
        except Exception as e:
            logger.error(f"Failed to load history: {e}")
            return []
    
    def save_system_prompt(self, user_id: int, system_prompt: str) -> bool:
        """Save the system prompt for the session."""
        try:
            self._get_or_create_session(user_id)
            
            self.cursor.execute(
                "UPDATE user_sessions SET system_prompt = ? WHERE user_id = ?",
                (system_prompt, user_id)
            )
            self.conn.commit()
            return True
            
        except Exception as e:
            logger.error(f"Failed to save system prompt: {e}")
            return False
    
    def get_system_prompt(self, user_id: int) -> Optional[str]:
        """Get the stored system prompt for a user."""
        try:
            self.cursor.execute(
                "SELECT system_prompt FROM user_sessions WHERE user_id = ?",
                (user_id,)
            )
            row = self.cursor.fetchone()
            return row["system_prompt"] if row else None
            
        except Exception as e:
            logger.error(f"Failed to get system prompt: {e}")
            return None
    
    def update_session_meta(self, user_id: int, mode: str = None, model: str = None,
                           fallback_tried: int = None) -> bool:
        """Update session metadata (charla_mode, last_model, etc.)."""
        try:
            self._get_or_create_session(user_id)
            
            updates = []
            params = []
            
            if mode is not None:
                updates.append("charla_mode = ?")
                params.append(mode)
            
            if model is not None:
                updates.append("last_model = ?")
                params.append(model)
            
            if fallback_tried is not None:
                updates.append("fallback_tried = ?")
                params.append(fallback_tried)
            
            if updates:
                params.append(user_id)
                self.cursor.execute(
                    f"UPDATE user_sessions SET {', '.join(updates)} WHERE user_id = ?",
                    params
                )
                self.conn.commit()
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to update session meta: {e}")
            return False
    
    def get_session_info(self, user_id: int) -> Dict[str, Any]:
        """Get session summary info for a user."""
        try:
            self.cursor.execute(
                "SELECT id FROM user_sessions WHERE user_id = ?",
                (user_id,)
            )
            row = self.cursor.fetchone()
            
            if not row:
                return {
                    "exists": False,
                    "message_count": 0,
                    "total_tokens": 0,
                    "mode": None,
                    "last_model": None
                }
            
            session_id = row[0]
            
            self.cursor.execute(
                "SELECT COUNT(*), COALESCE(SUM(tokens), 0) FROM session_messages WHERE session_id = ?",
                (session_id,)
            )
            count_row = self.cursor.fetchone()
            
            self.cursor.execute(
                "SELECT charla_mode, last_model FROM user_sessions WHERE user_id = ?",
                (user_id,)
            )
            meta_row = self.cursor.fetchone()
            
            return {
                "exists": True,
                "message_count": count_row[0] if count_row else 0,
                "total_tokens": count_row[1] if count_row else 0,
                "mode": meta_row["charla_mode"] if meta_row else None,
                "last_model": meta_row["last_model"] if meta_row else None
            }
            
        except Exception as e:
            logger.error(f"Failed to get session info: {e}")
            return {"exists": False, "message_count": 0, "total_tokens": 0}
    
    def has_active_session(self, user_id: int) -> bool:
        """Check if user has messages in session."""
        try:
            self.cursor.execute(
                """SELECT COUNT(*) FROM session_messages s
                   JOIN user_sessions u ON s.session_id = u.id
                   WHERE u.user_id = ?""",
                (user_id,)
            )
            count = self.cursor.fetchone()[0]
            return count > 0
            
        except Exception as e:
            logger.error(f"Failed to check active session: {e}")
            return False
    
    def clear_session(self, user_id: int) -> bool:
        """Clear all messages for a user (keep session, delete messages)."""
        try:
            self.cursor.execute(
                "SELECT id FROM user_sessions WHERE user_id = ?",
                (user_id,)
            )
            row = self.cursor.fetchone()
            
            if row:
                session_id = row[0]
                self.cursor.execute(
                    "DELETE FROM session_messages WHERE session_id = ?",
                    (session_id,)
                )
                self.cursor.execute(
                    "UPDATE user_sessions SET system_prompt = NULL WHERE user_id = ?",
                    (user_id,)
                )
                self.conn.commit()
            
            logger.info(f"Session cleared for user {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to clear session: {e}")
            return False
    
    def delete_session(self, user_id: int) -> bool:
        """Delete entire session including metadata."""
        try:
            self.cursor.execute(
                "SELECT id FROM user_sessions WHERE user_id = ?",
                (user_id,)
            )
            row = self.cursor.fetchone()
            
            if row:
                session_id = row[0]
                self.cursor.execute("DELETE FROM session_messages WHERE session_id = ?", (session_id,))
                self.cursor.execute("DELETE FROM user_sessions WHERE user_id = ?", (user_id,))
                self.conn.commit()
            
            logger.info(f"Session deleted for user {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete session: {e}")
            return False
    
    def get_old_sessions(self, days: int = 30) -> List[int]:
        """Get user_ids of sessions older than specified days."""
        try:
            from datetime import timedelta
            cutoff = (datetime.now() - timedelta(days=days)).isoformat()
            
            self.cursor.execute(
                "SELECT user_id FROM user_sessions WHERE updated_at < ?",
                (cutoff,)
            )
            return [row[0] for row in self.cursor.fetchall()]
            
        except Exception as e:
            logger.error(f"Failed to get old sessions: {e}")
            return []
    
    def prune_old_sessions(self, days: int = 30) -> int:
        """Delete sessions older than specified days. Returns count deleted."""
        old_users = self.get_old_sessions(days)
        deleted = 0
        for user_id in old_users:
            if self.delete_session(user_id):
                deleted += 1
        return deleted
    
    def close(self) -> None:
        """Close database connection."""
        if self.conn:
            self.conn.close()
            logger.info("SessionDB connection closed")


def get_session_db() -> SessionDB:
    """Get singleton SessionDB instance."""
    return SessionDB()