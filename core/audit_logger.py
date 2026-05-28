"""Audit logging for sensitive operations."""

import json
import logging
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

import config

logger = logging.getLogger(__name__)


class AuditLogger:
    """
    Audit logger for tracking sensitive operations.
    
    Logs:
    - Vault operations (create, delete, switch)
    - Backup/restore operations
    - Configuration changes
    - API key rotations
    - Admin commands
    """

    def __init__(self, log_file: Optional[Path] = None) -> None:
        self.log_file = log_file or config.DATA_DIR / "audit.log"
        self.log_file.parent.mkdir(parents=True, exist_ok=True)

    def log(
        self,
        action: str,
        user_id: Optional[str] = None,
        resource: Optional[str] = None,
        details: Optional[dict[str, Any]] = None,
        severity: str = "info",
    ) -> None:
        """
        Log an audit event.
        
        Args:
            action: Operation performed
            user_id: User who performed the action
            resource: Resource affected
            details: Additional context
            severity: Log severity (info, warning, error, critical)
        """
        entry = {
            "timestamp": datetime.now().isoformat(),
            "epoch": time.time(),
            "action": action,
            "user_id": user_id,
            "resource": resource,
            "details": details or {},
            "severity": severity,
        }

        try:
            with open(self.log_file, "a") as f:
                f.write(json.dumps(entry, default=str) + "\n")
        except Exception as e:
            logger.error(f"Failed to write audit log: {e}")

        log_func = getattr(logger, severity, logger.info)
        log_func(
            f"AUDIT: {action} by {user_id or 'system'} "
            f"on {resource or 'N/A'}"
        )

    def log_vault_operation(
        self,
        operation: str,
        vault_name: str,
        user_id: Optional[str] = None,
        success: bool = True,
    ) -> None:
        """Log vault operation."""
        self.log(
            action=f"vault_{operation}",
            user_id=user_id,
            resource=vault_name,
            details={"success": success},
            severity="info" if success else "warning",
        )

    def log_backup_operation(
        self,
        operation: str,
        backup_name: Optional[str] = None,
        vault_name: Optional[str] = None,
        user_id: Optional[str] = None,
        success: bool = True,
    ) -> None:
        """Log backup/restore operation."""
        self.log(
            action=f"backup_{operation}",
            user_id=user_id,
            resource=backup_name or vault_name,
            details={"vault": vault_name, "success": success},
            severity="info" if success else "error",
        )

    def log_config_change(
        self,
        setting: str,
        old_value: Any,
        new_value: Any,
        user_id: Optional[str] = None,
    ) -> None:
        """Log configuration change."""
        self.log(
            action="config_change",
            user_id=user_id,
            resource=setting,
            details={
                "old_value": str(old_value)[:100],
                "new_value": str(new_value)[:100],
            },
            severity="warning",
        )

    def log_admin_command(
        self,
        command: str,
        user_id: Optional[str] = None,
        result: Optional[str] = None,
    ) -> None:
        """Log admin command execution."""
        self.log(
            action=f"admin_{command}",
            user_id=user_id,
            resource=command,
            details={"result": result},
            severity="info",
        )

    def log_security_event(
        self,
        event_type: str,
        user_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        details: Optional[dict[str, Any]] = None,
    ) -> None:
        """Log security-related event."""
        self.log(
            action=f"security_{event_type}",
            user_id=user_id,
            details={**(details or {}), "ip_address": ip_address},
            severity="critical",
        )

    def get_recent_entries(self, limit: int = 50) -> list[dict[str, Any]]:
        """Get recent audit log entries."""
        if not self.log_file.exists():
            return []

        entries = []
        try:
            with open(self.log_file, "r") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        try:
                            entries.append(json.loads(line))
                        except json.JSONDecodeError:
                            continue
        except Exception as e:
            logger.error(f"Failed to read audit log: {e}")
            return []

        return entries[-limit:]

    def search_entries(
        self,
        action: Optional[str] = None,
        user_id: Optional[str] = None,
        severity: Optional[str] = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """Search audit log entries by criteria."""
        entries = self.get_recent_entries(limit=1000)

        if action:
            entries = [e for e in entries if e.get("action") == action]
        if user_id:
            entries = [e for e in entries if e.get("user_id") == user_id]
        if severity:
            entries = [e for e in entries if e.get("severity") == severity]

        return entries[-limit:]


_audit_logger: Optional[AuditLogger] = None


def get_audit_logger() -> AuditLogger:
    """Get or create audit logger singleton."""
    global _audit_logger
    if _audit_logger is None:
        _audit_logger = AuditLogger()
    return _audit_logger
