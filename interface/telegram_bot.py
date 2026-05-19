"""Telegram Bot - Asubarnipal V2 Imperial Edition (Refactored)."""

import logging
import time
import random
import json

import telegram
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    Application,
    CallbackContext,
    CallbackQueryHandler,
    CommandHandler,
    MessageHandler,
    filters,
)

import config
from core.banner import inicio_completo
from core.bot_logger import logger
from core.wiki import Wiki
from app.service import AsubarnipalService
from core.background_manager import BackgroundManager, BraveCounter, AgentState

from interface.handlers import (
    start_cmd,
    manual_cmd,
    status_cmd,
    reporte_cmd,
    query_cmd,
    hubs_cmd,
    clusters_cmd,
    lint_cmd,
    sync_obsidian_cmd,
    ingest_cmd,
    investigar_cmd,
    charlar_cmd,
    agente_cmd,
    model_cmd,
    query_vectorial_cmd,
    rate_cmd,
    vaults_cmd,
    vault_create_cmd,
    vault_use_cmd,
    vault_info_cmd,
    vault_delete_cmd,
    vault_export_cmd,
    vault_import_cmd,
    vault_callback,
)

STATUS = {
    "start": "🟢",
    "ingest": "📥",
    "query": "🔎",
    "search": "🔍",
    "index": "🏗️",
    "save": "💾",
    "done": "✅",
    "error": "🔴",
    "thinking": "🧠",
    "alive": "💚",
}

service = None
wiki = None
bg_manager = None
brave_counter = None
user_sessions = {}

def get_user_session(user_id: int) -> dict:
    if user_id not in user_sessions:
        user_sessions[user_id] = {
            "chat_history": [],
            "charla_mode": None,
            "last_result": None,
        }
    return user_sessions[user_id]


async def handle_message(update: Update, context: CallbackContext):
    """Handle regular messages."""
    text = update.message.text

    if text.startswith("/"):
        return

    session = get_user_session(update.effective_user.id)

    bypass_rag = text.lower() in ["hola", "buenas", "qué tal", "hi", "hello", "?"]

    if bypass_rag:
        responses = [
            "¡Hola! ¿En qué puedo ayudarte?",
            "Buenos días. ¿Investigamos algo?",
            "¡Adelante! ¿Qué necesitas?"
        ]
        logger.incoming(f"[SALUDO] {text}")
        await update.message.reply_text(random.choice(responses))
        return

    logger.incoming(f"[TEXTO] {text[:80]}")

    if session.get("charla_mode"):
        topic = session.get("charla_topic", "")
        prompt = f"[Modo {session['charla_mode']}] {topic}\n\n{text}"
        logger.llm(f"Modo charlar: {session['charla_mode']}")
        result = service.agent_chat(prompt)
        await update.message.reply_text(result.get("response", ""))
        return

    with logger.group("Agent Chat"):
        result = service.agent_chat(text)
        response = result.get("response", "Sin respuesta")

    await update.message.reply_text(response[:4000])


async def agent_callback(update: Update, context: CallbackContext):
    """Handle agent callbacks."""
    query = update.callback_query
    await query.answer()

    if query.data == "show_dashboard":
        stats = {}
        if config.DATA_DIR.exists():
            agent_file = config.DATA_DIR / "agent_state.json"
            if agent_file.exists():
                try:
                    stats = json.loads(agent_file.read_text())
                except:
                    pass

        heartbeat = {}
        if config.HEARTBEAT_FILE.exists():
            heartbeat = json.loads(config.HEARTBEAT_FILE.read_text())

        text = f"""📊 *Dashboard*

*Consultas:*
• Total: {stats.get('total_queries', 0)}
• Éxito: {stats.get('success_rate', 0):.1f}%

*Sistema:*
• CPU: {heartbeat.get('cpu_percent', 'N/A')}%
• RAM: {heartbeat.get('memory_percent', 'N/A')}%

*Brave:*
• Restantes: {brave_counter.get_left()}"""

        await query.edit_message_text(text, parse_mode="Markdown")

    elif query.data == "show_wiki":
        entries = wiki.get_all(limit=20)
        if not entries:
            await query.edit_message_text("📚 Wiki vacío")
            return

        text = "📚 *Wiki — Últimas entradas*\n\n"
        for e in entries[:10]:
            text += f"• {e['name']} ({e.get('tipo', 'entity')})\n"

        await query.edit_message_text(text, parse_mode="Markdown")

    elif query.data == "agent_continue":
        await update.message.reply_text("Continuando...")
        result = service.agent_chat("Continúa con el siguiente paso")
        await update.message.reply_text(result.get("response", "")[:4000])


async def indexar_wiki_cmd(update: Update, context: CallbackContext):
    """Build wiki index."""
    logger.info("🏗️ Indexando wiki...")
    await update.message.reply_text("🏗️ Reconstruyendo índice vectorial...")

    from index.rag import RAGEngine
    engine = RAGEngine(config.INDEX_DIR / "index.faiss")
    result = engine.build_index(str(config.WIKI_DIR))

    text = f"""✅ *Índice vectorial reconstruido*

• Documentos indexados: {result.get('indexed', 0)}
• Embeddings guardados"""

    await update.message.reply_text(text, parse_mode="Markdown")


async def error_handler(update: Update, context: CallbackContext):
    logger.error(f"Error: {context.error}", exc_info=True)


def main():
    global service, bg_manager, wiki, brave_counter

    inicio_completo()
    logger.info("🏛️ Iniciando Asubarnipal V18...")

    wiki = Wiki()
    logger.info("📚 Wiki inicializada")

    brave_counter = BraveCounter()
    logger.info("🔍 Brave counter inicializado")

    try:
        service = AsubarnipalService()
    except Exception as e:
        logger.warning(f"Service init: {e}")
        service = None

    bg_manager = BackgroundManager()
    bg_manager.start()

    agent_state = AgentState()
    agent_state.mark_alive()
    logger.info("🤖 Agent marked as alive")

    app = Application.builder().token(config.TELEGRAM_TOKEN).build()

    app.add_handler(CommandHandler("start", start_cmd))
    app.add_handler(CommandHandler("manual", manual_cmd))
    app.add_handler(CommandHandler("status", status_cmd))
    app.add_handler(CommandHandler("reporte", reporte_cmd))
    app.add_handler(CommandHandler("model", model_cmd))
    app.add_handler(CommandHandler("ingest", ingest_cmd))
    app.add_handler(CommandHandler("sync_obsidian", sync_obsidian_cmd))
    app.add_handler(CommandHandler("investigar", investigar_cmd))
    app.add_handler(CommandHandler("query", query_cmd))
    app.add_handler(CommandHandler("hubs", hubs_cmd))
    app.add_handler(CommandHandler("clusters", clusters_cmd))
    app.add_handler(CommandHandler("lint", lint_cmd))
    app.add_handler(CommandHandler("indexar_wiki", indexar_wiki_cmd))
    app.add_handler(CommandHandler("query_vectorial", query_vectorial_cmd))
    app.add_handler(CommandHandler("charlar", charlar_cmd))
    app.add_handler(CommandHandler("agente", agente_cmd))
    app.add_handler(CommandHandler("rate", rate_cmd))
    app.add_handler(CommandHandler("vaults", vaults_cmd))
    app.add_handler(CommandHandler("vault_create", vault_create_cmd))
    app.add_handler(CommandHandler("vault_use", vault_use_cmd))
    app.add_handler(CommandHandler("vault_info", vault_info_cmd))
    app.add_handler(CommandHandler("vault_delete", vault_delete_cmd))
    app.add_handler(CommandHandler("vault_export", vault_export_cmd))
    app.add_handler(CommandHandler("vault_import", vault_import_cmd))

    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(CallbackQueryHandler(agent_callback))
    app.add_handler(CallbackQueryHandler(vault_callback))
    app.add_error_handler(error_handler)

    logger.info("🤖 Application started")
    app.run_polling(poll_interval=2)


if __name__ == "__main__":
    main()