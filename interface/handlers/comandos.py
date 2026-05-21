"""Basic commands handlers (/start, /manual, /status, /reporte)."""

import json
import psutil
import platform
import config
from telegram import Update
from telegram.ext import CallbackContext

from core.bot_logger import logger
from core.background_manager import BraveCounter


def get_status_text() -> str:
    """Get system status text."""
    cpu = psutil.cpu_percent(interval=0.5)
    mem = psutil.virtual_memory()
    mem_used = mem.used / (1024**3)
    mem_total = mem.total / (1024**3)

    stats = {}
    if config.DATA_DIR.exists():
        agent_file = config.DATA_DIR / "agent_state.json"
        if agent_file.exists():
            try:
                stats = json.loads(agent_file.read_text())
            except Exception:
                pass

    brave_left = 1500
    if config.DATA_DIR.exists():
        counter_file = config.DATA_DIR / "brave_counter.json"
        if counter_file.exists():
            try:
                data = json.loads(counter_file.read_text())
                brave_left = max(0, 1500 - data.get("count", 0))
            except Exception:
                pass

    return f"""🟢 *Estado del Sistema*

*Hardware:*
• CPU: {cpu:.1f}%
• RAM: {mem_used:.1f}/{mem_total:.1f} GB ({mem.percent}%)

*Procesos:*
• Uptime: {stats.get('uptime', 'N/A')}
• Queries: {stats.get('total_queries', 0)}
• Éxito: {stats.get('success_rate', 0):.1f}%

*Brave Search:*
• Restantes: {brave_left}/1500"""


async def start_cmd(update: Update, context: CallbackContext):
    """Handle /start command."""
    user = update.effective_user
    logger.incoming(f"/start from {user.first_name}")

    text = f"""👋 *¡Bienvenido, {user.first_name}!*

Soy *Asubarnipal*, tu agente de IA autónomo.

*Comandos disponibles:*

📚 *Wiki:*
• `/query <pregunta>` - Buscar en wiki
• `/hubs` - Conceptos centrales
• `/clusters` - Comunidades temáticas
• `/lint` - Diagnóstico de salud
• `/sync_obsidian` - Sincronizar Obsidian

🔍 *Búsqueda:*
• `/investigar <tema>` - Investigación profunda
• `/ingest <url>` - Añadir URL al wiki

💬 *Chat:*
• `/charlar <modo> <tema>` - 5 modos de conversación
• `/agente <tarea>` - Agente autónomo

⚙️ *Sistema:*
• `/status` - Estado del sistema
• `/model [nombre]` - Ver/cambiar modelo LLM
• `/reporte` - Autodiagnóstico del agente

*Usa /manual para ver todos los comandos.*"""

    await update.message.reply_text(text, parse_mode="Markdown")


async def manual_cmd(update: Update, context: CallbackContext):
    """Handle /manual command."""
    logger.incoming("/manual")

    text = """📖 *Manual de Usuario*

*Comandos disponibles:*

**Wiki:**
`/query <pregunta>` - Buscar en la wiki
`/hubs` - Ver conceptos más conectados
`/clusters` - Ver comunidades temáticas
`/lint` - Diagnóstico de salud del wiki
`/sync_obsidian` - Importar notas de Obsidian

**Búsqueda:**
`/ingest <url>` - Añadir URL al wiki
`/investigar <tema>` - Investigación profunda
`/query_vectorial <búsqueda>` - Búsqueda semántica

**Chat:**
`/charlar <modo> <tema>` - 5 modos:
  • libre - Conversación natural
  • consultor - Análisis en 3 fases
  • devil - Crítica implacable
  • socrático - Preguntas socráticas
  • lateral - Perspectivas alternativas

**Agente:**
`/agente <tarea>` - Ejecutar tarea autónoma

**Sistema:**
`/status` - Estado del sistema
`/model [nombre]` - Ver/cambiar modelo
`/reporte` - Autodiagnóstico"""

    await update.message.reply_text(text, parse_mode="Markdown")


async def status_cmd(update: Update, context: CallbackContext):
    """Handle /status command."""
    logger.incoming("/status")
    await update.message.reply_text(get_status_text(), parse_mode="Markdown")


async def reporte_cmd(update: Update, context: CallbackContext):
    """Handle /reporte command."""
    logger.incoming("/reporte")

    agent_file = config.DATA_DIR / "agent_state.json"
    heartbeat_file = config.DATA_DIR / "heartbeat.json"
    counter_file = config.DATA_DIR / "brave_counter.json"

    agent_state = {}
    if agent_file.exists():
        try:
            agent_state = json.loads(agent_file.read_text())
        except Exception:
            pass

    heartbeat = {}
    if heartbeat_file.exists():
        try:
            heartbeat = json.loads(heartbeat_file.read_text())
        except Exception:
            pass

    brave_left = 1500
    if counter_file.exists():
        try:
            data = json.loads(counter_file.read_text())
            brave_left = max(0, 1500 - data.get("count", 0))
        except Exception:
            pass

    text = f"""📊 *Autodiagnóstico del Agente*

*Sistema:*
• Uptime: {agent_state.get('uptime', 'N/A')}
• Queries totales: {agent_state.get('total_queries', 0)}
• Tasa éxito: {agent_state.get('success_rate', 0):.1f}%
• Fallos: {agent_state.get('total_failures', 0)}

*Recursos:*
• CPU actual: {heartbeat.get('cpu_percent', 'N/A')}%
• RAM actual: {heartbeat.get('memory_percent', 'N/A')}%

*Brave Search:*
• Restantes: {brave_left}/1500

*Modelo actual:* `{config.OLLAMA_MODEL}`

*Memoria:* {agent_state.get('memory_count', 0)} items"""

    await update.message.reply_text(text, parse_mode="Markdown")