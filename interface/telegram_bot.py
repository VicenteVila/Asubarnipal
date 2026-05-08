"""Telegram bot interface - recovered from logs."""

import asyncio
import logging
import os
import sys
from pathlib import Path

import telegram
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, CallbackContext, CallbackQueryHandler, CommandHandler, MessageHandler, filters

import config
from app.service import AsubarnipalService
from core.dashboard_logic import DashboardManager

logging.basicConfig(
    format="%(asctime)s - [%(levelname)s] - %(message)s",
    level=logging.INFO,
    handlers=[
        logging.FileHandler(config.LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger(__name__)

service = AsubarnipalService()
dashboard_manager = DashboardManager()
user_sessions = {}


def get_user_session(user_id: int) -> dict:
    if user_id not in user_sessions:
        user_sessions[user_id] = {
            "chat_history": [],
            "plan": None,
            "current_step": 0,
            "last_result": None,
        }
    return user_sessions[user_id]


def create_keyboard(step: int = 0) -> InlineKeyboardMarkup:
    buttons = [
        [
            InlineKeyboardButton("Continuar", callback_data=f"continue_{step}"),
            InlineKeyboardButton("Explicar", callback_data=f"explain_{step}"),
        ],
        [
            InlineKeyboardButton("📊 Dashboard", callback_data="show_dashboard"),
            InlineButton("📚 Wiki", callback_data="show_wiki"),
        ],
    ]
    return InlineKeyboardMarkup(buttons)


async def start_cmd(update: Update, context: CallbackContext):
    await update.message.reply_text(
        "🤖 *Asubarnipal - Agente de Investigación*\n\n"
        "Puedo ayudarte con:\n"
        "• Investigación automática\n"
        "• Wiki y knowledge graph\n"
        "• Búsqueda en web\n"
        "• Análisis de código\n"
        "• TurboQuant\n\n"
        "Usa /agente <tu_pregunta> para empezar.",
        parse_mode="Markdown"
    )


async def agente_cmd(update: Update, context: CallbackContext):
    text = " ".join(context.args)
    if not text:
        await update.message.reply_text("Usa: /agente <tu pregunta>")
        return
    
    await _process_agent_turn(update, context, text)


async def handle_message(update: Update, context: CallbackContext):
    text = update.message.text
    if text.startswith("/"):
        return
    
    await _process_agent_turn(update, context, text)


async def _process_agent_turn(update: Update, context: CallbackContext, user_message: str):
    user_id = update.effective_user.id
    session = get_user_session(user_id)
    
    chat = update.message or update.callback_query.message
    
    if session.get("last_result"):
        prompt = f"{user_message}\n\nRESULTADO PREVIO:\n{session['last_result']}\n\n¿Cuál es el siguiente paso?"
    else:
        prompt = user_message
    
    session["chat_history"].append({"role": "user", "content": prompt})
    
    await chat.edit_reply_text("🤖 Ejecutando...", reply_markup=None)
    
    try:
        result = service.agent_chat(
            prompt,
            hist_to_pass=session.get("hist_to_pass", []),
        )
        
        response_text = result.get("response", "Sin respuesta")
        tool_calls = result.get("tool_calls", [])
        
        session["last_result"] = response_text
        session["hist_to_pass"] = session["chat_history"][-5:]
        
        if tool_calls:
            buttons = [
                [InlineKeyboardButton("Continuar", callback_data="continue_step")],
                [InlineKeyboardButton("📊 Dashboard", callback_data="show_dashboard")],
            ]
            reply_markup = InlineKeyboardMarkup(buttons)
            await chat.reply_text(response_text[:4000], reply_markup=reply_markup)
        else:
            await chat.reply_text(response_text[:4000], reply_markup=create_keyboard())
            
        dashboard_manager.record_query(True, result.get("time", 0))
            
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        await chat.reply_text(f"❌ Error: {e}")
        dashboard_manager.record_query(False, 0, str(e))


async def agent_callback(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    session = get_user_session(user_id)
    
    if query.data == "show_dashboard":
        await show_dashboard(update, context)
        return
    if query.data == "show_wiki":
        await show_wiki(update, context)
        return
    
    if query.data.startswith("continue"):
        await _process_agent_turn(
            update, context,
            "La herramienta terminó con éxito. ¿Cuál es el siguiente paso?"
        )
    elif query.data.startswith("explain"):
        await _process_agent_turn(
            update, context,
            "Explica lo que acabas de hacer."
        )


async def show_dashboard(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    
    try:
        stats = dashboard_manager.get_stats()
        text = f"📊 *Dashboard*\n\n"
        text += f"- Consultas totales: {stats.get('total_queries', 0)}\n"
        text += f"- Exitosas: {stats.get('successful', 0)}\n"
        text += f"- Fallidas: {stats.get('failed', 0)}\n"
        text += f"- Tiempo promedio: {stats.get('avg_time', 0):.2f}s\n"
        text += f"- Tasa de éxito: {stats.get('success_rate', 0):.1f}%\n"
        
        await query.edit_message_text(text, parse_mode="Markdown")
    except Exception as e:
        await query.edit_message_text(f"Error dashboard: {e}")


async def show_wiki(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    
    try:
        from app.service import WikiReader
        wiki = WikiReader(config)
        entries = wiki.get_all(limit=20)
        
        if not entries:
            await query.edit_message_text("📚 Wiki vacío")
            return
        
        text = "📚 *Wiki - Últimas entradas*\n\n"
        for name, etype, content in entries[:10]:
            text += f"• {name} ({etype})\n"
        
        await query.edit_message_text(text, parse_mode="Markdown")
    except Exception as e:
        await query.edit_message_text(f"Error wiki: {e}")


async def research_cmd(update: Update, context: CallbackContext):
    """Research a topic automatically."""
    topic = " ".join(context.args)
    if not topic:
        await update.message.reply_text("Usa: /research <tema>")
        return
    
    await update.message.reply_text(f"🔬 Investigando: {topic}...")
    
    result = service.research_topic(topic)
    
    text = f"✅ *Investigación: {topic}*\n\n"
    text += f"Fuentes encontradas: {len(result.get('sources', []))}\n"
    text += f"Entidades guardadas: {result.get('entities_saved', 0)}"
    
    await update.message.reply_text(text, parse_mode="Markdown")


async def wiki_search_cmd(update: Update, context: CallbackContext):
    """Search wiki."""
    query = " ".join(context.args)
    if not query:
        await update.message.reply_text("Usa: /wiki <búsqueda>")
        return
    
    result = service.query_wiki(query)
    results = result.get("results", [])
    
    if not results:
        await update.message.reply_text(f"No encontraron resultados para: {query}")
        return
    
    text = f"📚 *Resultados para: {query}*\n\n"
    for r in results[:5]:
        text += f"• {r['name']}\n"
    
    await update.message.reply_text(text, parse_mode="Markdown")


async def ingest_cmd(update: Update, context: CallbackContext):
    """Ingest URL to wiki."""
    url = " ".join(context.args)
    if not url:
        await update.message.reply_text("Usa: /ingest <URL>")
        return
    
    await update.message.reply_text(f"📥 Ingiriendo: {url}...")
    
    result = service.ingest_url(url)
    
    if result.get("success"):
        await update.message.reply_text(f"✅ Guardado: {result.get('name')}")
    else:
        await update.message.reply_text(f"❌ Error: {result.get('error')}")


async def status_cmd(update: Update, context: CallbackContext):
    """Show status - recovers from logs."""
    try:
        from app.service import WikiReader
        wiki = WikiReader(config)
        entries = wiki.get_all()
        
        stats = dashboard_manager.get_stats()
        
        text = "📊 *Estado del Sistema*\n\n"
        text += f"• Entradas Wiki: {len(entries)}\n"
        text += f"• Consultas: {stats.get('total_queries', 0)}\n"
        text += f"• Éxito: {stats.get('success_rate', 0):.1f}%\n"
        
        await update.message.reply_text(text, parse_mode="Markdown")
    except Exception as e:
        logger.error(f"Status error: {e}", exc_info=True)
        await update.message.reply_text(f"Error: {e}")


async def error_handler(update: Update, context: CallbackContext):
    logger.error(f"Error: {context.error}", exc_info=True)


def main():
    global service, dashboard_manager
    
    logger.info("Iniciando Asubarnipal...")
    
    try:
        service = AsubarnipalService()
        dashboard_manager = DashboardManager()
    except Exception as e:
        logger.warning(f"Service init warning: {e}")
        service = AsubarnipalService() if hasattr(AsubarnipalService, '__init__') else None
        dashboard_manager = DashboardManager()
    
    app = Application.builder().token(config.TELEGRAM_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start_cmd))
    app.add_handler(CommandHandler("agente", agente_cmd))
    app.add_handler(CommandHandler("research", research_cmd))
    app.add_handler(CommandHandler("wiki", wiki_search_cmd))
    app.add_handler(CommandHandler("ingest", ingest_cmd))
    app.add_handler(CommandHandler("status", status_cmd))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(CallbackQueryHandler(agent_callback))
    app.add_error_handler(error_handler)
    
    logger.info("Application started")
    app.run_polling(poll_interval=2)


if __name__ == "__main__":
    main()