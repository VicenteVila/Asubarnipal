"""Backup command handlers."""

from telegram import Update
from telegram.ext import CallbackContext

from core.bot_logger import logger
from core.backup_manager import get_backup_manager


async def backup_cmd(update: Update, context: CallbackContext) -> None:
    """Create a backup of active vault or all data."""
    args = context.args
    vault_name = args[0] if args else None

    logger.incoming(f"/backup {vault_name or 'full'}")

    await update.message.reply_text("Creando backup...")

    bm = get_backup_manager()
    result = bm.backup_vault(vault_name)

    if result.get("success"):
        backup = result["backup"]
        size_kb = backup["size_bytes"] / 1024
        await update.message.reply_text(
            f"Backup creado\n\n"
            f"Nombre: {backup['name']}\n"
            f"Vault: {backup['vault']}\n"
            f"Tamano: {size_kb:.1f} KB\n"
            f"Fecha: {backup['timestamp'][:19]}"
        )
    else:
        await update.message.reply_text(f"Error backup: {result.get('error')}")


async def backups_cmd(update: Update, context: CallbackContext) -> None:
    """List all backups."""
    bm = get_backup_manager()
    backups = bm.list_backups()

    if not backups:
        await update.message.reply_text("No hay backups disponibles")
        return

    text = "Backups disponibles\n\n"
    for b in backups[:10]:
        size_kb = b["size_bytes"] / 1024
        text += f"- {b['name']}\n"
        text += f"  Vault: {b['vault']} | {size_kb:.1f} KB | {b['timestamp'][:19]}\n\n"

    stats = bm.stats()
    text += f"Total: {stats['total_backups']} backups"

    await update.message.reply_text(text)


async def restore_cmd(update: Update, context: CallbackContext) -> None:
    """Restore from a backup."""
    args = context.args

    if not args:
        await update.message.reply_text(
            "Restaurar backup\n\n"
            "Usa: /restore <nombre_backup>\n\n"
            "Ver backups disponibles con /backups"
        )
        return

    backup_name = args[0]
    logger.incoming(f"/restore {backup_name}")

    await update.message.reply_text(f"Restaurando desde {backup_name}...")

    bm = get_backup_manager()
    result = bm.restore_backup(backup_name)

    if result.get("success"):
        await update.message.reply_text(f"Backup restaurado: {backup_name}")
    else:
        await update.message.reply_text(f"Error restauracion: {result.get('error')}")


async def backup_stats_cmd(update: Update, context: CallbackContext) -> None:
    """Show backup statistics."""
    bm = get_backup_manager()
    stats = bm.stats()

    text = (
        f"Estadisticas de backup\n\n"
        f"Total backups: {stats['total_backups']}\n"
        f"Tamano total: {stats['total_size_bytes'] / 1024:.1f} KB\n"
        f"Maximo backups: {stats['max_backups']}\n"
        f"Intervalo auto: {stats['auto_backup_interval'] / 3600:.0f}h\n"
        f"Ultimo backup: {stats['last_backup'][:19] if stats['last_backup'] else 'Nunca'}"
    )

    await update.message.reply_text(text)


async def backup_clear_cmd(update: Update, context: CallbackContext) -> None:
    """Clear all backups."""
    bm = get_backup_manager()
    backups = bm.list_backups()

    if not backups:
        await update.message.reply_text("No hay backups que eliminar")
        return

    for b in backups:
        bm.delete_backup(b["name"])

    await update.message.reply_text(f"Eliminados {len(backups)} backups")
