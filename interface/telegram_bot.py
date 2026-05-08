import asyncio
import logging
import os
import sys
from pathlib import Path

import telegram
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, CallbackContext, CallbackQueryHandler, CommandHandler, MessageHandler, filters

import config
from app.service import AgentService
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

service = None
dashboard_manager = None
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
        ],
    ]
    return InlineKeyboardMarkup(buttons)


async def start_cmd(update: Update, context: CallbackContext):
    await update.message.reply_text(
        "🤖 *Agente de Investigación*\n\n"
        "Puedo ayudarte con tareas de investigación, código y análisis de datos.\n\n"
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
    
    chat.history.append({"role": "user", "content": prompt})
    
    await chat.edit_reply_text("🤖 Ejecutando...", reply_markup=None)
    
    try:
        result = service.agent_chat(
            prompt,
            hist_to_pass=session.get("hist_to_pass", []),
        )
        
        response_text = result.get("response", "Sin respuesta")
        tool_calls = result.get("tool_calls", [])
        
        session["last_result"] = response_text
        session["hist_to_pass"] = chat.history[-5:]
        
        if tool_calls:
            buttons = [
                [InlineKeyboardButton("Continuar", callback_data="continue_step")],
                [InlineKeyboardButton("📊 Dashboard", callback_data="show_dashboard")],
            ]
            reply_markup = InlineKeyboardMarkup(buttons)
            await chat.reply_text(response_text[:4000], reply_markup=reply_markup)
        else:
            await chat.reply_text(response_text[:4000], reply_markup=create_keyboard())
            
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        await chat.reply_text(f"❌ Error: {e}")


async def agent_callback(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    session = get_user_session(user_id)
    
    if query.data == "show_dashboard":
        await show_dashboard(update, context)
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
        text += f"- Consultas: {stats.get('total_queries', 0)}\n"
        text += f"- Promedio: {stats.get('avg_time', 0):.2f}s\n"
        text += f"- Éxitos: {stats.get('success_rate', 0):.1f}%\n"
        
        await query.edit_message_text(text, parse_mode="Markdown")
    except Exception as e:
        await query.edit_message_text(f"Error dashboard: {e}")


async def error_handler(update: Update, context: CallbackContext):
    logger.error(f"Error: {context.error}", exc_info=True)


def main():
    global service, dashboard_manager
    
    logger.info("Iniciando agente...")
    
    service = AgentService()
    dashboard_manager = DashboardManager()
    
    app = Application.builder().token(config.TELEGRAM_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start_cmd))
    app.add_handler(CommandHandler("agente", agente_cmd))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(CallbackQueryHandler(agent_callback))
    app.add_error_handler(error_handler)
    
    logger.info("Application started")
    app.run_polling(poll_interval=2)


if __name__ == "__main__":
    main()