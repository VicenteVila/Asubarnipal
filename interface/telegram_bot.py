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
from core.session_db import get_session_db, SessionDB
from app.service import AsubarnipalService
from core.background_manager import BackgroundManager, BraveCounter, AgentState

PENDING_RESTORE = {}

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
    quality_cmd,
    queryhybrid_cmd,
    query_callback_handler,
    ingest_cmd,
    investigar_cmd,
    charlar_cmd,
    agente_cmd,
    model_cmd,
    query_vectorial_cmd,
    rate_cmd,
    calidad_cmd,
    vaults_cmd,
    vault_create_cmd,
    vault_use_cmd,
    vault_info_cmd,
    vault_delete_cmd,
    vault_export_cmd,
    vault_import_cmd,
    vault_connect_cmd,
    vault_disconnect_cmd,
    vault_callback,
)

from interface.handlers.hmem_commands import (
    memoria_cmd,
    recordar_cmd,
    pensar_cmd,
    contexto_cmd,
    entidades_cmd,
    recientes_cmd,
)

from interface.handlers.graphify_handler import (
    graphify_cmd,
    graph_update_cmd,
    graph_query_cmd,
    graph_stats_cmd,
    graph_report_cmd,
    graph_add_cmd,
    graph_export_cmd,
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

MAX_HISTORY_TOKENS = 16000
MAX_HISTORY_MESSAGES = 100

FALLBACK_CHAIN = {
    "libre": ["nemotron-3-nano:4b", "qwen3.5:4b", "qwen3:8b"],
    "consultor": ["qwen3:8b", "qwen3.5:9b", "gemma4:e4b"],
    "devil": ["gemma4:e4b", "qwen3:8b", "qwen3.5:9b"],
    "socratico": ["qwen3.5:4b", "qwen3:8b", "qwen3.5:9b"],
    "lateral": ["qwen3.5:9b", "qwen3:8b", "qwen3.5:4b"],
    "default": ["qwen3.5:4b", "qwen3:8b", "gemma4:e4b"],
}

def get_user_session(user_id: int) -> dict:
    if user_id not in user_sessions:
        user_sessions[user_id] = {
            "chat_history": [],
            "charla_mode": None,
            "last_result": None,
            "last_model": None,
            "fallback_tried": 0,
        }
    return user_sessions[user_id]

def _estimate_tokens(text: str) -> int:
    return len(text) // 4

def _trim_history(history: list, max_tokens: int = MAX_HISTORY_TOKENS, 
                  max_messages: int = MAX_HISTORY_MESSAGES) -> list:
    total_tokens = sum(_estimate_tokens(m.get("content", "")) for m in history)
    
    while (total_tokens > max_tokens or len(history) > max_messages) and len(history) > 2:
        removed = history.pop(0)
        total_tokens -= _estimate_tokens(removed.get("content", ""))
    
    return history

def _save_to_db(user_id: int, role: str, content: str):
    """Save a message to SQLite session database."""
    try:
        session_db = get_session_db()
        tokens = _estimate_tokens(content)
        session_db.save_message(user_id, role, content, tokens)
        
        total_tokens = session_db.get_session_info(user_id).get("total_tokens", 0)
        if total_tokens > MAX_HISTORY_TOKENS:
            _prune_db_history(user_id)
    except Exception as e:
        logger.warning(f"Failed to save to DB: {e}")

def _load_from_db(user_id: int) -> list:
    """Load chat history from SQLite."""
    try:
        session_db = get_session_db()
        return session_db.load_history(user_id)
    except Exception as e:
        logger.warning(f"Failed to load from DB: {e}")
        return []

def _prune_db_history(user_id: int):
    """Prune old messages from DB to stay within limits."""
    try:
        session_db = get_session_db()
        history = session_db.load_history(user_id)
        
        trimmed = _trim_history(history.copy(), MAX_HISTORY_TOKENS, MAX_HISTORY_MESSAGES)
        
        if len(trimmed) < len(history):
            session_db.clear_session(user_id)
            for msg in trimmed:
                session_db.save_message(user_id, msg["role"], msg["content"], 
                                        _estimate_tokens(msg.get("content", "")))
            logger.info(f"Pruned DB history for user {user_id}")
    except Exception as e:
        logger.warning(f"Failed to prune DB: {e}")

def _clear_db_session(user_id: int):
    """Clear session in database."""
    try:
        session_db = get_session_db()
        session_db.clear_session(user_id)
    except Exception as e:
        logger.warning(f"Failed to clear DB session: {e}")

def _get_fallback_model(mode: str, fallback_tried: int) -> str:
    chain = FALLBACK_CHAIN.get(mode, FALLBACK_CHAIN["default"])
    if fallback_tried < len(chain):
        return chain[fallback_tried]
    return chain[-1]

def _build_messages(system_prompt: str, user_text: str, history: list) -> list:
    messages = [{"role": "system", "content": system_prompt}]
    for msg in history:
        messages.append({"role": msg.get("role", "user"), "content": msg.get("content", "")})
    messages.append({"role": "user", "content": user_text})
    return messages


async def handle_message(update: Update, context: CallbackContext):
    """Handle regular messages."""
    text = update.message.text
    user_id = update.effective_user.id

    if text.startswith("/"):
        return

    # Handle sí/no/ms evaluation feedback
    fb = text.lower().strip()
    if fb in ["sí", "si", "si", "yes", "y", "no", "n", "ms", "más o menos", "mas o menos", "maybe"]:
        from skills.default_skills import record_eval_feedback
        result = record_eval_feedback(text)
        if result.get("success"):
            feedback = result["feedback"]
            stats = result.get("stats", {})
            emoji = {"sí": "✅", "no": "❌", "más o menos": "😐"}.get(feedback, "📊")
            await update.message.reply_text(
                f"{emoji} *Evaluación registrada: {feedback}*\n\n"
                f"Accuracy: {stats.get('accuracy_rate', 0)*100:.0f}%\n"
                f"Total: {stats.get('total_evaluated', 0)}",
                parse_mode="Markdown"
            )
            return
        # If fails (no pending eval), continue to normal chat
    
    # Auto-detectar URLs y hacer ingest automáticamente
    import re
    if re.match(r'^https?://', text.strip()):
        logger.incoming(f"[URL detectada] {text[:80]}")
        await update.message.reply_text("🔗 URL detectada. Procesando...")
        
        from interface.handlers.busqueda import _ingest_url
        try:
            await _ingest_url(update, text.strip())
            return
        except Exception as e:
            logger.error(f"Auto-ingest URL failed: {e}")
            # Si falla, continuar como chat normal

    session_db = get_session_db()
    session_info = session_db.get_session_info(user_id)
    
    if session_info.get("exists") and session_info.get("message_count", 0) > 0:
        if user_id not in PENDING_RESTORE:
            PENDING_RESTORE[user_id] = "waiting"
            
            msg_count = session_info.get("message_count", 0)
            total_tokens = session_info.get("total_tokens", 0)
            
            await update.message.reply_text(
                f"📋 *Sesión guardada encontrada*\n\n"
                f"Tienes {msg_count} mensajes guardados "
                f"({total_tokens:,} tokens).\n\n"
                f"¿Restaurar historial?\n"
                f"• Escribe *sí* para continuar\n"
                f"• Escribe *no* para limpiar",
                parse_mode="Markdown"
            )
            return

    if PENDING_RESTORE.get(user_id) == "waiting":
        if text.lower() in ["sí", "si", "yes", "s", "y"]:
            history = _load_from_db(user_id)
            session = get_user_session(user_id)
            session["chat_history"] = history
            
            system_prompt = session_db.get_system_prompt(user_id)
            if system_prompt:
                session["system_prompt"] = system_prompt
            
            PENDING_RESTORE.pop(user_id, None)
            
            charlar_mode = session_info.get("mode")
            if charlar_mode:
                session["charla_mode"] = charlar_mode
            
            await update.message.reply_text(
                f"✅ *Historial restaurado*\n\n"
                f"Se cargaron {len(history)} mensajes."
            )
            
        elif text.lower() in ["no", "n"]:
            _clear_db_session(user_id)
            PENDING_RESTORE.pop(user_id, None)
            
            await update.message.reply_text("🗑️ Sesión limpiada.")
        else:
            await update.message.reply_text("Escribe *sí* o *no* para continuar.")
        return

    session = get_user_session(user_id)

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
        charlar_mode = session.get("charla_mode")
        
        try:
            from core.turboquant_engine import apply_chat_mode
            from core.turboquant_modes import get_mode_config
            
            mode_cfg = get_mode_config(charlar_mode)
            primary_model = mode_cfg.model if mode_cfg else None
            
            from interface.handlers.chat import MODES
            mode_system = MODES.get(charlar_mode, {}).get(
                "system", "Responde de forma útil y creativa."
            )
            
            if not session.get("system_prompt"):
                session_db.save_system_prompt(user_id, mode_system)
            
            history = _trim_history(session.get("chat_history", []))
            messages = _build_messages(mode_system, text, history)
            
            result = None
            response = ""
            models_tried = []
            
            for attempt in range(3):
                current_model = _get_fallback_model(
                    charlar_mode, 
                    session.get("fallback_tried", 0) + attempt
                )
                models_tried.append(current_model)
                
                apply_chat_mode(charlar_mode, model=current_model)
                
                logger.info(f"Chat attempt {attempt+1}: mode={charlar_mode}, model={current_model}")
                
                try:
                    result = service.llm.call_with_turbo(
                        messages, 
                        mode=charlar_mode, 
                        model=current_model
                    )
                    response = result.get("response", "").strip()
                    
                    if response:
                        logger.info(f"Success: {current_model} gave response ({len(response)} chars)")
                        session["fallback_tried"] = 0
                        break
                    else:
                        logger.warning(f"No response from {current_model}, trying fallback...")
                        
                except Exception as call_error:
                    logger.warning(f"Call error with {current_model}: {call_error}")
                    response = ""
                
                time.sleep(2 * (attempt + 1))
            
            if not response:
                session["fallback_tried"] = session.get("fallback_tried", 0) + 1
                logger.error(f"All models failed for {charlar_mode}. Tries: {session['fallback_tried']}")
            
            session["chat_history"].append({"role": "user", "content": text})
            _save_to_db(user_id, "user", text)
            
            if response:
                session["chat_history"].append({"role": "assistant", "content": response})
                _save_to_db(user_id, "assistant", response)
            
            session["chat_history"] = _trim_history(session["chat_history"])
            
            session_db.update_session_meta(user_id, mode=charlar_mode, model=primary_model)
            
            logger.info(f"Charla mode {charlar_mode} completed. Models tried: {models_tried}")
            
        except Exception as e:
            logger.error(f"Charla mode error: {e}", exc=e)
            response = ""
        
        if not response:
            response = "Lo siento, no pude generar una respuesta. ¿Quieres reformular la pregunta?"
        
        await update.message.reply_text(response[:4000])
        return

    with logger.group("Agent Chat"):
        hmem_context = ""
        try:
            from core.hybrid_retriever import get_hmem_manager
            hmem = get_hmem_manager()
            hmem_context = hmem.get_context(text)
            if hmem_context:
                logger.info(f"H-Mem context added: {len(hmem_context)} chars")
        except Exception as e:
            logger.debug(f"H-Mem context unavailable: {e}")
        
        if hmem_context:
            try:
                result = service.llm.generate(
                    f"Contexto relevante de la memoria:\n{hmem_context}\n\n---\n\nPregunta: {text}"
                )
                response = result.strip()
            except Exception as e:
                logger.warning(f"LLM generate with context failed: {e}")
                result = service.agent_chat(text)
                response = result.get("response", "Sin respuesta").strip()
        else:
            result = service.agent_chat(text)
            response = result.get("response", "Sin respuesta").strip()

    if not response:
        response = "Lo siento, no pude generar una respuesta."
    
    session["chat_history"].append({"role": "user", "content": text})
    _save_to_db(user_id, "user", text)
    
    if response:
        session["chat_history"].append({"role": "assistant", "content": response})
        _save_to_db(user_id, "assistant", response)
        
        try:
            from core.hybrid_retriever import get_hmem_manager
            hmem = get_hmem_manager()
            hmem.remember(
                f"Conversación: Usuario preguntó sobre '{text[:100]}'. "
                f"Agente respondió: {response[:300]}",
                metadata={
                    "source": "telegram_chat",
                    "type": "conversation",
                    "user_id": user_id,
                }
            )
            logger.info("Conversation saved to H-Mem")
        except Exception as e:
            logger.debug(f"H-Mem save failed: {e}")
    
    session["chat_history"] = _trim_history(session["chat_history"])

    await update.message.reply_text(response[:4000])

    # Ask for evaluation
    await update.message.reply_text(
        "📊 ¿La respuesta fue precisa? (sí/no/ms)"
    )


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
                except Exception:
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

    try:
        from index.rag import RAGEngine
        engine = RAGEngine()
        
        result = engine.index_directory(config.WIKI_DIR, glob_pattern="*.md")
        
        indexed_count = result.get('indexed', len(result.get('texts', [])))
        
        text = f"""✅ *Índice vectorial reconstruido*

• Documentos indexados: {indexed_count}
• Embeddings guardados"""

        logger.info(f"Index completed: {indexed_count} documents")
        await update.message.reply_text(text, parse_mode="Markdown")
        
    except Exception as e:
        logger.error(f"Index error: {e}")
        await update.message.reply_text(f"❌ Error al indexar: {str(e)}")


async def error_handler(update: Update, context: CallbackContext):
    logger.error(f"Error: {context.error}")


async def clear_session_cmd(update: Update, context: CallbackContext):
    """Clear user session history from database."""
    user_id = update.effective_user.id
    
    try:
        session_db = get_session_db()
        session_info = session_db.get_session_info(user_id)
        
        if not session_info.get("exists"):
            await update.message.reply_text("ℹ️ No hay sesión activa.")
            return
        
        msg_count = session_info.get("message_count", 0)
        _clear_db_session(user_id)
        
        if user_id in PENDING_RESTORE:
            PENDING_RESTORE.pop(user_id, None)
        
        user_sessions.pop(user_id, None)
        
        await update.message.reply_text(
            f"🗑️ *Sesión limpiada*\n\n"
            f"Se eliminaron {msg_count} mensajes guardados.",
            parse_mode="Markdown"
        )
        
        logger.info(f"Session cleared for user {user_id}")
        
    except Exception as e:
        logger.error(f"Clear session error: {e}")
        await update.message.reply_text(f"❌ Error al limpiar sesión: {e}")


async def session_info_cmd(update: Update, context: CallbackContext):
    """Show session info."""
    user_id = update.effective_user.id
    
    try:
        session_db = get_session_db()
        info = session_db.get_session_info(user_id)
        
        if not info.get("exists") or info.get("message_count", 0) == 0:
            await update.message.reply_text("ℹ️ No hay mensajes guardados.")
            return
        
        text = f"""📋 *Estado de la Sesión*

• Mensajes: {info.get('message_count', 0)}
• Tokens: {info.get('total_tokens', 0):,}
• Modo: {info.get('mode', 'N/A')}
• Modelo: {info.get('last_model', 'N/A')}

Límites:
• Máx mensajes: {MAX_HISTORY_MESSAGES}
• Máx tokens: {MAX_HISTORY_TOKENS:,}"""
        
        await update.message.reply_text(text, parse_mode="Markdown")
        
    except Exception as e:
        logger.error(f"Session info error: {e}")
        await update.message.reply_text(f"❌ Error: {e}")


def main() -> None:
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
    app.add_handler(MessageHandler(filters.Document.ALL, ingest_cmd))
    app.add_handler(MessageHandler(filters.PHOTO, ingest_cmd))
    app.add_handler(CommandHandler("sync_obsidian", sync_obsidian_cmd))
    app.add_handler(CommandHandler("investigar", investigar_cmd))
    app.add_handler(CommandHandler("query", query_cmd))
    app.add_handler(CommandHandler("hubs", hubs_cmd))
    app.add_handler(CommandHandler("clusters", clusters_cmd))
    app.add_handler(CommandHandler("lint", lint_cmd))
    app.add_handler(CommandHandler("quality", quality_cmd))
    app.add_handler(CommandHandler("queryhybrid", queryhybrid_cmd))
    app.add_handler(CommandHandler("hybrid", queryhybrid_cmd))
    app.add_handler(CommandHandler("indexar_wiki", indexar_wiki_cmd))
    app.add_handler(CommandHandler("query_vectorial", query_vectorial_cmd))
    app.add_handler(CommandHandler("charlar", charlar_cmd))
    app.add_handler(CommandHandler("agente", agente_cmd))
    app.add_handler(CommandHandler("rate", rate_cmd))
    app.add_handler(CommandHandler("calidad", calidad_cmd))
    app.add_handler(CommandHandler("vaults", vaults_cmd))
    app.add_handler(CommandHandler("vault_create", vault_create_cmd))
    app.add_handler(CommandHandler("vault_use", vault_use_cmd))
    app.add_handler(CommandHandler("vault_info", vault_info_cmd))
    app.add_handler(CommandHandler("vault_delete", vault_delete_cmd))
    app.add_handler(CommandHandler("vault_export", vault_export_cmd))
    app.add_handler(CommandHandler("vault_import", vault_import_cmd))
    app.add_handler(CommandHandler("vault_connect", vault_connect_cmd))
    app.add_handler(CommandHandler("vault_disconnect", vault_disconnect_cmd))
    app.add_handler(CommandHandler("clear_session", clear_session_cmd))
    app.add_handler(CommandHandler("session", session_info_cmd))

    app.add_handler(CommandHandler("memoria", memoria_cmd))
    app.add_handler(CommandHandler("recordar", recordar_cmd))
    app.add_handler(CommandHandler("pensar", pensar_cmd))
    app.add_handler(CommandHandler("contexto", contexto_cmd))
    app.add_handler(CommandHandler("entidades", entidades_cmd))
    app.add_handler(CommandHandler("recientes", recientes_cmd))

    app.add_handler(CommandHandler("graphify", graphify_cmd))
    app.add_handler(CommandHandler("graph_update", graph_update_cmd))
    app.add_handler(CommandHandler("graph_query", graph_query_cmd))
    app.add_handler(CommandHandler("graph_stats", graph_stats_cmd))
    app.add_handler(CommandHandler("graph_report", graph_report_cmd))
    app.add_handler(CommandHandler("graph_add", graph_add_cmd))
    app.add_handler(CommandHandler("graph_export", graph_export_cmd))

    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(CallbackQueryHandler(agent_callback))
    app.add_handler(CallbackQueryHandler(vault_callback))
    app.add_handler(CallbackQueryHandler(query_callback_handler))
    app.add_error_handler(error_handler)

    logger.info("🤖 Application started")
    app.run_polling(poll_interval=2)


if __name__ == "__main__":
    main()