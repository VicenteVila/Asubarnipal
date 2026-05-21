"""Vault management command handlers for Telegram."""

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackContext

import config
from core.bot_logger import logger
from core.vault_manager import get_vault_manager

PENDING_ACTIONS = {}


async def vaults_cmd(update: Update, context: CallbackContext):
    """List all vaults and show active one."""
    logger.incoming("/vaults")

    vm = get_vault_manager()
    result = vm.list_vaults()

    if not result.get("success"):
        await update.message.reply_text(f"❌ Error: {result.get('error')}")
        return

    active = result.get("active_vault")
    vaults = result.get("vaults", [])

    text = f"📚 *Vaults de Conocimiento*\n\n"
    text += f"🟢 Activo: *{active}*\n\n"
    text += "_" * 30 + "\n\n"

    for v in vaults:
        status = "✅" if v["active"] else "⬜"
        count = v.get("notes_count", 0)
        text += f"{status} *{v['name']}*\n"
        text += f"   📂 {v['path']}\n"
        text += f"   📊 Notas: {count}\n"
        if v.get("description"):
            text += f"   📝 {v['description']}\n"
        text += "\n"

    text += f"_Total: {result.get('total', 0)} vaults_"

    await update.message.reply_text(text, parse_mode="Markdown")


async def vault_create_cmd(update: Update, context: CallbackContext):
    """Create a new vault."""
    args = context.args

    if not args:
        await update.message.reply_text(
            "📦 *Crear nuevo vault*\n\n"
            "Usa: /vault_create <nombre>\n\n"
            "Ejemplo: `/vault_create investigacion_ia`"
        )
        return

    name = " ".join(args).strip()
    logger.incoming(f"/vault_create {name}")

    vm = get_vault_manager()

    if name.lower().replace(" ", "_") in vm._config.get("vaults", {}):
        await update.message.reply_text(f"❌ El vault '{name}' ya existe")
        return

    user_id = update.effective_user.id
    PENDING_ACTIONS[user_id] = {
        "action": "vault_create_confirm",
        "name": name,
    }

    keyboard = [
        [InlineKeyboardButton("✅ Confirmar", callback_data="vault_confirm"),
         InlineKeyboardButton("❌ Cancelar", callback_data="vault_cancel")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        f"📦 *Confirmar creación de vault*\n\n"
        f"📛 Nombre: *{name}*\n\n"
        f"Indica la ruta del vault:",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )


async def vault_use_cmd(update: Update, context: CallbackContext):
    """Switch to a different vault."""
    args = context.args

    if not args:
        await update.message.reply_text(
            "🔄 *Cambiar vault activo*\n\n"
            "Usa: /vault_use <nombre>\n\n"
            "Para ver los vaults disponibles: `/vaults`"
        )
        return

    name = " ".join(args).strip()
    logger.incoming(f"/vault_use {name}")

    vm = get_vault_manager()
    result = vm.switch(name)

    if result.get("success"):
        await update.message.reply_text(
            f"✅ *Vault cambiado*\n\n"
            f"📛 Nombre: *{result['name']}*\n"
            f"📂 Path: `{result['path']}`\n\n"
            f"Todos los comandos de wiki usarán este vault.",
            parse_mode="Markdown"
        )
    else:
        await update.message.reply_text(f"❌ Error: {result.get('error')}")


async def vault_info_cmd(update: Update, context: CallbackContext):
    """Show info about active vault."""
    logger.incoming("/vault_info")

    vm = get_vault_manager()
    vault = vm.get_active()

    if not vault:
        await update.message.reply_text("❌ No hay vault activo")
        return

    import sqlite3
    from pathlib import Path

    db_path = Path(vault.get("db_path", ""))
    notes = 0
    concepts = 0

    if db_path.exists():
        try:
            conn = sqlite3.connect(str(db_path))
            cursor = conn.execute("SELECT COUNT(*) FROM entities")
            notes = cursor.fetchone()[0]

            cursor = conn.execute("SELECT COUNT(*) FROM entities WHERE entity_type = 'entity'")
            concepts = cursor.fetchone()[0]
            conn.close()
        except Exception:
            pass

    await update.message.reply_text(
        f"📂 *Vault Activo*\n\n"
        f"📛 Nombre: *{vault['name']}*\n"
        f"📝 Descripción: {vault.get('description', 'N/A')}\n"
        f"📂 Path: `{vault['path']}`\n"
        f"🗄️ DB: `{vault['db_path']}`\n\n"
        f"📊 *Estadísticas:*\n"
        f"   • Notas: {notes}\n"
        f"   • Conceptos: {concepts}\n"
        f"   • Creado: {vault.get('created', 'N/A')}",
        parse_mode="Markdown"
    )


async def vault_delete_cmd(update: Update, context: CallbackContext):
    """Delete a vault with confirmation."""
    args = context.args

    if not args:
        await update.message.reply_text(
            "🗑️ *Eliminar vault*\n\n"
            "Usa: /vault_delete <nombre>\n\n"
            "⚠️ Se creará backup automático antes de eliminar.\n"
            "⚠️ No se puede eliminar el vault principal."
        )
        return

    name = " ".join(args).strip()
    logger.incoming(f"/vault_delete {name}")

    if name == "principal":
        await update.message.reply_text("❌ No se puede eliminar el vault 'principal'")
        return

    vm = get_vault_manager()

    if name not in vm._config.get("vaults", {}):
        await update.message.reply_text(f"❌ El vault '{name}' no existe")
        return

    user_id = update.effective_user.id
    PENDING_ACTIONS[user_id] = {
        "action": "vault_delete_confirm",
        "name": name,
    }

    keyboard = [
        [InlineKeyboardButton("🗑️ Eliminar", callback_data="vault_confirm"),
         InlineKeyboardButton("❌ Cancelar", callback_data="vault_cancel")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        f"⚠️ *Confirmar eliminación*\n\n"
        f"📛 Vault: *{name}*\n\n"
        f"Se creará backup en `data/backups/` antes de eliminar.\n"
        f"Esta acción no se puede deshacer.",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )


async def vault_export_cmd(update: Update, context: CallbackContext):
    """Export vault to JSON."""
    args = context.args

    if not args:
        vm = get_vault_manager()
        active = vm.get_active()
        name = active["name"] if active else None
    else:
        name = " ".join(args).strip()

    if not name:
        await update.message.reply_text("❌ No hay vault activo ni nombre especificado")
        return

    logger.incoming(f"/vault_export {name}")

    vm = get_vault_manager()
    result = vm.export_vault(name)

    if result.get("success"):
        await update.message.reply_text(
            f"📤 *Vault exportado*\n\n"
            f"📛 Vault: *{name}*\n"
            f"📁 Archivo: `{result['export_path']}`\n"
            f"📊 Entidades: {result['entities_count']}",
            parse_mode="Markdown"
        )
    else:
        await update.message.reply_text(f"❌ Error: {result.get('error')}")


async def vault_import_cmd(update: Update, context: CallbackContext):
    """Import vault from JSON."""
    args = context.args

    if len(args) < 2:
        await update.message.reply_text(
            "📥 *Importar vault*\n\n"
            "Usa: /vault_import <nombre> <ruta_archivo>\n\n"
            "Ejemplo: `/vault_import ia backup.json`"
        )
        return

    name = args[0]
    file_path = " ".join(args[1:])
    logger.incoming(f"/vault_import {name} {file_path}")

    vm = get_vault_manager()
    result = vm.import_vault(name, file_path)

    if result.get("success"):
        await update.message.reply_text(
            f"📥 *Vault importado*\n\n"
            f"📛 Vault: *{name}*\n"
            f"📊 Entidades importadas: {result['entities_imported']}"
        )
    else:
        await update.message.reply_text(f"❌ Error: {result.get('error')}")


async def vault_callback(update: Update, context: CallbackContext):
    """Handle vault inline button callbacks."""
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    action_data = PENDING_ACTIONS.get(user_id)

    if not action_data:
        await query.edit_message_text("❌ Acción expirada o inválida")
        return

    action = action_data.get("action")
    name = action_data.get("name")

    if query.data == "vault_cancel":
        del PENDING_ACTIONS[user_id]
        await query.edit_message_text("❌ Acción cancelada")
        return

    if query.data == "vault_confirm":
        vm = get_vault_manager()

        if action == "vault_create_confirm":
            default_path = str(config.DATA_DIR / f"vault_{name}")

            result = vm.create(name, default_path, f"Vault {name}")

            if result.get("success"):
                vm.switch(name)
                del PENDING_ACTIONS[user_id]
                await query.edit_message_text(
                    f"✅ *Vault creado*\n\n"
                    f"📛 Nombre: *{name}*\n"
                    f"📂 Path: `{result['path']}`\n\n"
                    f"🟢 Vault activado automáticamente."
                )
            else:
                await query.edit_message_text(f"❌ Error: {result.get('error')}")

        elif action == "vault_delete_confirm":
            result = vm.delete(name, backup=True)

            del PENDING_ACTIONS[user_id]

            if result.get("success"):
                await query.edit_message_text(f"✅ Vault '{name}' eliminado con backup")
            else:
                await query.edit_message_text(f"❌ Error: {result.get('error')}")

        else:
            await query.edit_message_text("❌ Acción desconocida")
    else:
        await query.edit_message_text("❌ Callback desconocido")


async def vault_connect_cmd(update: Update, context: CallbackContext):
    """Connect to an existing Obsidian vault folder."""
    args = context.args

    if not args:
        await update.message.reply_text(
            "🔗 *Conectar vault existente*\n\n"
            "Usa: /vault_connect <ruta> [nombre]\n\n"
            "Ejemplos:\n"
            "`/vault_connect C:\\Users\\Vicente\\Documentos\\Obsidian\\mi_vault`\n"
            "`/vault_connect /mnt/c/Obsidian/investigacion investigacion`"
        )
        return

    path = args[0]
    name = " ".join(args[1:]) if len(args) > 1 else None

    logger.incoming(f"/vault_connect {path} {name if name else ''}")

    vm = get_vault_manager()
    result = vm.connect(path, name, "Vault conectada externamente")

    if result.get("success"):
        # Auto-activate
        if result.get("name"):
            vm.switch(result["name"])

        await update.message.reply_text(
            f"✅ *Vault conectada*\n\n"
            f"📛 Nombre: *{result['name']}*\n"
            f"📂 Path: `{result['path']}`\n\n"
            f"🟢 Vault activado automáticamente."
        )
    else:
        await update.message.reply_text(f"❌ Error: {result.get('error')}")


async def vault_disconnect_cmd(update: Update, context: CallbackContext):
    """Disconnect a vault."""
    args = context.args

    name = args[0] if args else None

    logger.incoming(f"/vault_disconnect {name if name else 'active'}")

    vm = get_vault_manager()
    result = vm.disconnect(name)

    if result.get("success"):
        text = f"✅ *Vault desconectada*\n\n"
        text += f"📛 Nombre: *{result['name']}*\n"
        text += f"📂 Path: `{result['path']}`\n"
        if result.get("was_active"):
            text += "\n⚠️ Era el vault activo - ahora no hay ninguno activo."
        await update.message.reply_text(text, parse_mode="Markdown")
    else:
        await update.message.reply_text(f"❌ Error: {result.get('error')}")