"""Telegram Bot - Asubarnipal V2 Imperial Edition."""

import asyncio
import json
import logging
import os
import sys
import threading
from pathlib import Path

import telegram
from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Update,
    InputFile,
)
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
from app.service import AsubarnipalService
from core.background_manager import BackgroundManager, BraveCounter, MemorySkill
from core.dashboard_logic import DashboardManager
from core.wiki import Wiki

logging.basicConfig(
    format="%(asctime)s - [%(levelname)s] - %(message)s",
    level=logging.INFO,
    handlers=[
        logging.FileHandler(config.LOG_FILE, encoding="utf-8"),
    ],
)
logger = logging.getLogger(__name__)

service = AsubarnipalService()
dashboard_manager = DashboardManager()
wiki = Wiki()
bg_manager = BackgroundManager()
memory_skill = MemorySkill()
brave_counter = BraveCounter()

user_sessions = {}
current_model = config.DEFAULT_MODEL


def get_user_session(user_id: int) -> dict:
    if user_id not in user_sessions:
        user_sessions[user_id] = {
            "chat_history": [],
            "charla_mode": None,
            "last_result": None,
        }
    return user_sessions[user_id]


def create_main_keyboard() -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton("📊 Dashboard", callback_data="show_dashboard")],
        [InlineKeyboardButton("📚 Wiki", callback_data="show_wiki")],
        [InlineKeyboardButton("🔎 Query", callback_data="do_query")],
    ]
    return InlineKeyboardMarkup(buttons)


async def start_cmd(update: Update, context: CallbackContext):
    """Start command - welcome message."""
    text = """🏛️ *Asubarnipal V2 — El Legado de Nínive*

*Bienvenido, viajero del conocimiento.*

Soy un agente de conocimiento con wiki estructurado. Puedo ayudarte a:

📥 *Ingesta* — PDFs, YouTube, webs, Obsidian
🔎 *Consulta* — Búsqueda semántica y RAG
🕸️ *Estructura* — Grafos y clusters
🎭 *Charla* — 5 modos especializados
🤖 *Agente* — Razonamiento autónomo

*Comandos:*
/manual — Este documento
/status — Telemetría
/reporte — Auto-reflexión
/investigar <tema> — Investigación profunda
/charlar <tema> — Modos especializados

*Envía /start para comenzar.*"""

    await update.message.reply_text(text, parse_mode="Markdown", reply_markup=create_main_keyboard())


async def manual_cmd(update: Update, context: CallbackContext):
    """Send the manual to user."""
    try:
        if config.MANUAL_FILE.exists():
            await update.message.reply_document(
                InputFile(str(config.MANUAL_FILE)),
                caption="📖 *Manual de Asubarnipal V2*",
                parse_mode="Markdown"
            )
        else:
            await update.message.reply_text(
                f"📖 Manual: {config.MANUAL_FILE}\n\nEl archivo no existe."
            )
    except Exception as e:
        await update.message.reply_text(f"Error: {e}")


async def status_cmd(update: Update, context: CallbackContext):
    """Show system status."""
    try:
        heartbeat = {}
        if config.HEARTBEAT_FILE.exists():
            heartbeat = json.loads(config.HEARTBEAT_FILE.read_text())
        
        wiki_stats = wiki.get_all(limit=1000)
        
        bg_status = bg_manager.get_status()
        from core.background_manager import AgentState
        agent_state = AgentState()
        state = agent_state.get_status()
        
        text = f"""📊 *Estado del Sistema*

💓 *Heartbeat:*
• CPU: {heartbeat.get('cpu_percent', 'N/A')}%
• RAM: {heartbeat.get('memory_percent', 'N/A')}%
• Timestamp: {heartbeat.get('timestamp', 'N/A')}

🤖 *Agente:*
• Alive: {'✅ SI' if state.get('alive') else '❌ NO'}
• Último alive: {state.get('last_alive', 'N/A')}
• Último fallo: {state.get('last_failure', 'N/A')}
• Fallos: {state.get('failure_count', 0)}
• Éxitos: {state.get('success_count', 0)}

📚 *Wiki:*
• Entidades: {len(wiki_stats)}

🔍 *Brave:*
• Restantes: {brave_counter.get_left()}/mes

🕸️ *Rituales:*
• Running: {bg_status['running']}
• Last suture: {bg_status.get('last_suture', {}).get('timestamp', 'N/A')}
• Last graph: {bg_status.get('last_graph', {}).get('timestamp', 'N/A')}

🤖 *Modelo:* {current_model}"""

        await update.message.reply_text(text, parse_mode="Markdown")
    except Exception as e:
        await update.message.reply_text(f"Error: {e}")


async def reporte_cmd(update: Update, context: CallbackContext):
    """Generate agent self-reflection report."""
    recent_memories = memory_skill.get_recent(limit=10)
    
    text = f"""📝 *Informe de Auto-Reflexión*

*Últimas memorias:*
"""
    for m in recent_memories[-5:]:
        text += f"• {m.get('content', '')[:100]}\n"
    
    text += f"""
*Estadísticas:*
• Memorias: {len(recent_memories)}
• Wiki: {len(wiki.get_all())}

*El agente medita sobre su propósito...*
"""
    
    await update.message.reply_text(text, parse_mode="Markdown")


async def model_cmd(update: Update, context: CallbackContext):
    """Show or change model."""
    global current_model
    
    args = context.args
    
    if not args:
        await update.message.reply_text(f"🤖 Modelo actual: *{current_model}*", parse_mode="Markdown")
        return
    
    new_model = args[0].lower()
    if new_model in ["ollama", "gemini", "auto"]:
        current_model = new_model
        await update.message.reply_text(f"✅ Modelo cambiado a: *{new_model}*", parse_mode="Markdown")
    else:
        await update.message.reply_text("Modelos: ollama, gemini, auto")


async def ingest_cmd(update: Update, context: CallbackContext):
    """Ingest URL to wiki."""
    url = " ".join(context.args)
    
    if not url:
        await update.message.reply_text("Usa: /ingest <URL>")
        return
    
    await update.message.reply_text(f"📥 Ingiriendo: {url}...")
    
    result = wiki.ingest_url(url)
    
    if result.get("success"):
        await update.message.reply_text(f"✅ Guardado: {result.get('name')}")
    else:
        await update.message.reply_text(f"❌ Error: {result.get('error')}")


async def sync_obsidian_cmd(update: Update, context: CallbackContext):
    """Sync from Obsidian vault."""
    await update.message.reply_text("🔄 Sincronizando Obsidian...")
    
    result = wiki.sync_obsidian()
    
    await update.message.reply_text(f"✅ Importadas: {result.get('imported', 0)} notas")


async def investigar_cmd(update: Update, context: CallbackContext):
    """Deep research on a topic."""
    topic = " ".join(context.args)
    
    if not topic:
        await update.message.reply_text("Usa: /investigar <tema>")
        return
    
    await update.message.reply_text(f"🔬 Investigando: *{topic}*...")
    
    if not brave_counter.can_search():
        await update.message.reply_text("❌ Límite Brave Search alcanzado")
        return
    
    from core.llm_router import BraveRouter
    brave = BraveRouter()
    
    results = brave.search(topic, num_results=5)
    brave_counter.increment()
    
    for r in results:
        wiki.ingest_url(r.get("url", ""))
    
    await update.message.reply_text(
        f"✅ Investigación completada\n"
        f"• Fuentes: {len(results)}\n"
        f"• Ingiridas al wiki: {len(results)}"
    )


async def query_cmd(update: Update, context: CallbackContext):
    """Query the wiki."""
    query = " ".join(context.args)
    
    if not query:
        await update.message.reply_text("Usa: /query <pregunta>")
        return
    
    results = wiki.search(query)
    
    if not results:
        await update.message.reply_text(f"No encontré resultados para: {query}")
        return
    
    text = f"🔎 *Resultados para: {query}*\n\n"
    for r in results[:5]:
        text += f"• {r['name']}\n"
    
    await update.message.reply_text(text, parse_mode="Markdown")


async def hubs_cmd(update: Update, context: CallbackContext):
    """Show hub concepts."""
    hubs = wiki.get_hubs(limit=10)
    
    text = "🕸️ *Hubs — Conceptos Centrales*\n\n"
    for h in hubs:
        text += f"• {h['name']} ({h['connections']} conexiones)\n"
    
    await update.message.reply_text(text, parse_mode="Markdown")


async def clusters_cmd(update: Update, context: CallbackContext):
    """Show thematic clusters."""
    clusters = wiki.get_clusters()
    
    text = "🔮 *Clusters — Comunidades Temáticas*\n\n"
    for c in clusters:
        text += f"• {c['tag']}: {c['count']}\n"
    
    await update.message.reply_text(text, parse_mode="Markdown")


async def lint_cmd(update: Update, context: CallbackContext):
    """Health check for wiki."""
    result = wiki.lint()
    
    text = f"""🔍 *Diagnóstico del Wiki*

• Entidades: {result['total_entities']}
• Health Score: {result['health_score']}%

*Issues:*
"""
    for issue in result['issues'][:10]:
        text += f"• {issue['type']}: {issue.get('name', 'N/A')}\n"
    
    await update.message.reply_text(text, parse_mode="Markdown")


async def indexar_wiki_cmd(update: Update, context: CallbackContext):
    """Rebuild knowledge graph index."""
    await update.message.reply_text("🔄 Reindexando wiki...")
    
    from index.rag import RAGEngine
    engine = RAGEngine()
    result = engine.index_directory(config.WIKI_DIR)
    
    await update.message.reply_text(f"✅ Indexadas: {result.get('indexed', 0)} notas")


async def charlar_cmd(update: Update, context: CallbackContext):
    """Start specialized chat mode."""
    topic = " ".join(context.args)
    
    if not topic:
        text = """🎭 *Modos de Charla:*

1️⃣ 💬 Charla Libre — Conversación natural
2️⃣ 🧠 Consultor — Análisis en 3 fases
3️⃣ 🔥 Devil's Advocate — Crítica implacable
4️⃣ ❓ Socrático — Preguntas profundas
5️⃣ 🌐 Lateral — Perspectivas alternativas

Usa: /charlar <modo> <tema>

Ejemplo: /charlar socrático ¿Qué es la inteligencia?"""
        await update.message.reply_text(text, parse_mode="Markdown")
        return
    
    modes = {
        "libre": "Conversación natural y creativa",
        "consultor": "Análisis en 3 fases: Definición → Ejecución → Evaluación",
        "devil": "Crítica implacable, encuentra fallos y riesgos",
        "socratico": "Guía mediante preguntas, no da respuestas",
        "lateral": "Perspectivas de chef, músico, tribu, algoritmo",
    }
    
    session = get_user_session(update.effective_user.id)
    session["charla_mode"] = "consultor"
    session["charla_topic"] = topic
    
    await update.message.reply_text(
        f"🎭 *Modo Consultor Activado*\n\nTema: {topic}\n\nComenzando análisis en 3 fases...",
        parse_mode="Markdown"
    )


async def query_vectorial_cmd(update: Update, context: CallbackContext):
    """Vector search in index."""
    query = " ".join(context.args)
    
    if not query:
        await update.message.reply_text("Usa: /query_vectorial <búsqueda>")
        return
    
    from index.rag import RAGEngine
    engine = RAGEngine(config.INDEX_DIR / "index.faiss")
    results = engine.search(query)
    
    if not results:
        await update.message.reply_text(f"No encontré resultados para: {query}")
        return
    
    text = f"🔎 *Resultados vectoriales:*\n\n"
    for r in results:
        text += f"• {r['document']} (dist: {r['distance']:.2f})\n"
    
    await update.message.reply_text(text, parse_mode="Markdown")


async def agente_cmd(update: Update, context: CallbackContext):
    """Activate autonomous agent."""
    task = " ".join(context.args)
    
    if not task:
        await update.message.reply_text("Usa: /agente <tarea>")
        return
    
    session = get_user_session(update.effective_user.id)
    
    await update.message.reply_text(f"🤖 *Agente Activado*\n\nTarea: {task}\n\nEjecutando...", parse_mode="Markdown")
    
    result = service.agent_chat(task)
    
    response = result.get("response", "Sin respuesta")
    
    await update.message.reply_text(
        f"🤖 *Resultado:*\n\n{response[:4000]}",
        parse_mode="Markdown"
    )
    
    if result.get("tool_calls"):
        buttons = [
            [InlineKeyboardButton("Continuar", callback_data="agent_continue")],
        ]
        await update.message.reply_text("¿Continuar?", reply_markup=InlineKeyboardMarkup(buttons))


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
        import random
        await update.message.reply_text(random.choice(responses))
        return
    
    if session.get("charla_mode"):
        topic = session.get("charla_topic", "")
        prompt = f"[Modo {session['charla_mode']}] {topic}\n\n{text}"
        result = service.agent_chat(prompt)
        await update.message.reply_text(result.get("response", ""))
        return
    
    result = service.agent_chat(text)
    await update.message.reply_text(result.get("response", "Sin respuesta")[:4000])


async def agent_callback(update: Update, context: CallbackContext):
    """Handle agent callbacks."""
    query = update.callback_query
    await query.answer()
    
    if query.data == "show_dashboard":
        await show_dashboard(update, context)
    elif query.data == "show_wiki":
        await show_wiki(update, context)
    elif query.data == "agent_continue":
        await update.message.reply_text("Continuando...")
        result = service.agent_chat("Continúa con el siguiente paso")
        await update.message.reply_text(result.get("response", "")[:4000])


async def show_dashboard(update: Update, context: CallbackContext):
    """Show dashboard stats."""
    query = update.callback_query
    
    try:
        stats = dashboard_manager.get_stats()
        
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
    except Exception as e:
        await query.edit_message_text(f"Error: {e}")


async def show_wiki(update: Update, context: CallbackContext):
    """Show wiki entries."""
    query = update.callback_query
    
    try:
        entries = wiki.get_all(limit=20)
        
        if not entries:
            await query.edit_message_text("📚 Wiki vacío")
            return
        
        text = "📚 *Wiki — Últimas entradas*\n\n"
        for e in entries[:10]:
            text += f"• {e['name']} ({e.get('tipo', 'entity')})\n"
        
        await query.edit_message_text(text, parse_mode="Markdown")
    except Exception as e:
        await query.edit_message_text(f"Error: {e}")


async def error_handler(update: Update, context: CallbackContext):
    logger.error(f"Error: {context.error}", exc_info=True)


def main():
    global service, bg_manager
    
    inicio_completo()
    
    logger.info("🏛️ Iniciando Asubarnipal V18...")
    
    try:
        service = AsubarnipalService()
    except Exception as e:
        logger.warning(f"Service init: {e}")
    
    bg_manager.start()
    
    from core.background_manager import AgentState
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
    
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(CallbackQueryHandler(agent_callback))
    app.add_error_handler(error_handler)
    
    logger.info("🤖 Application started")
    app.run_polling(poll_interval=2)


if __name__ == "__main__":
    main()