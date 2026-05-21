"""Graphify commands handlers (/graphify, /graph_query, /graph_stats)."""

import logging

from telegram import Update
from telegram.ext import CallbackContext

from core.bot_logger import logger
from core.graphify_integration import (
    build_graph,
    query_graph,
    get_graph_stats,
    get_graph_report,
    update_graph,
    add_url_to_graph,
    export_graph,
)

logger = logging.getLogger(__name__)


async def graphify_cmd(update: Update, context: CallbackContext):
    """Build or rebuild knowledge graph with Graphify."""
    logger.incoming("/graphify")

    args = context.args
    mode = "default"
    force = False

    if "deep" in args:
        mode = "deep"
    if "force" in args:
        force = True

    await update.message.reply_text(
        f"🕸️ Construyendo grafo de conocimiento con Graphify...\n"
        f"Modo: {mode}"
    )

    result = build_graph(mode=mode, force=force)

    if result.get("success"):
        stats = result.get("stats", {})
        text = (
            f"✅ *Grafo construido exitosamente*\n\n"
            f"📊 *Estadísticas:*\n"
            f"• Nodos: {stats.get('nodes', 0)}\n"
            f"• Conexiones: {stats.get('edges', 0)}\n"
            f"• Comunidades: {stats.get('communities', 0)}\n"
            f"• Hubs principales: {len(stats.get('hubs', []))}\n\n"
            f"📁 *Archivos:*\n"
            f"• graph.html - Visualización interactiva\n"
            f"• graph.json - Grafo queryable\n"
            f"• GRAPH_REPORT.md - Resumen\n\n"
            f"Usa `/graph_query <pregunta>` para consultar el grafo."
        )

        if stats.get("hubs"):
            text += "\n\n🏛️ *Top Hubs:*\n"
            for hub in stats["hubs"][:5]:
                text += f"• {hub['name']} ({hub['connections']} conexiones)\n"

        await update.message.reply_text(text, parse_mode="Markdown")
    else:
        error = result.get("error", "Error desconocido")
        await update.message.reply_text(
            f"❌ Error construyendo grafo:\n{error}\n\n"
            f"Asegúrate de tener graphify instalado:\n"
            f"`pip install graphifyy`",
            parse_mode="Markdown"
        )


async def graph_update_cmd(update: Update, context: CallbackContext):
    """Update graph with changed files only."""
    logger.incoming("/graph_update")

    await update.message.reply_text("🔄 Actualizando grafo (solo archivos cambiados)...")

    result = update_graph()

    if result.get("success"):
        stats = result.get("stats", {})
        text = (
            f"✅ *Grafo actualizado*\n\n"
            f"• Nodos: {stats.get('nodes', 0)}\n"
            f"• Conexiones: {stats.get('edges', 0)}\n"
            f"• Comunidades: {stats.get('communities', 0)}"
        )
        await update.message.reply_text(text, parse_mode="Markdown")
    else:
        await update.message.reply_text(
            f"❌ Error: {result.get('error', 'Desconocido')}"
        )


async def graph_query_cmd(update: Update, context: CallbackContext):
    """Query the knowledge graph with a question."""
    if not context.args:
        await update.message.reply_text(
            "🔍 *Uso:* `/graph_query <pregunta>`\n\n"
            "Ejemplo: `/graph_query qué conecta transformers con attention`",
            parse_mode="Markdown"
        )
        return

    logger.incoming(f"/graph_query {' '.join(context.args)}")

    question = " ".join(context.args)
    await update.message.reply_text(f"🔍 Consultando grafo: {question}")

    result = query_graph(question)

    if result.get("success") and result.get("answer"):
        answer = result["answer"][:4000]
        await update.message.reply_text(f"💡 *Respuesta del grafo:*\n\n{answer}", parse_mode="Markdown")
    else:
        error = result.get("error", result.get("stderr", "Sin respuesta"))
        await update.message.reply_text(
            f"❌ No se pudo obtener respuesta:\n{error[:500]}",
            parse_mode="Markdown"
        )


async def graph_stats_cmd(update: Update, context: CallbackContext):
    """Show knowledge graph statistics."""
    logger.incoming("/graph_stats")

    stats = get_graph_stats()

    if not stats.get("exists"):
        await update.message.reply_text(
            "🕸️ *No hay grafo disponible*\n\n"
            "Construye uno con `/graphify`",
            parse_mode="Markdown"
        )
        return

    text = (
        f"📊 *Estado del Grafo de Conocimiento*\n\n"
        f"🕸️ Nodos: {stats.get('nodes', 0)}\n"
        f"🔗 Conexiones: {stats.get('edges', 0)}\n"
        f"📊 Comunidades: {stats.get('communities', 0)}\n"
        f"💾 Tamaño: {stats.get('file_size_kb', 0):.1f} KB\n"
        f"🕐 Última construcción: {stats.get('last_built', 'N/A')}\n"
    )

    if stats.get("hubs"):
        text += "\n🏛️ *Top Hubs:*\n"
        for hub in stats["hubs"][:5]:
            text += f"• {hub['name']} ({hub['connections']} conexiones)\n"

    if stats.get("html_exists"):
        text += "\n✅ Visualización HTML disponible"
    if stats.get("report_exists"):
        text += "\n✅ Reporte disponible"

    await update.message.reply_text(text, parse_mode="Markdown")


async def graph_report_cmd(update: Update, context: CallbackContext):
    """Show the graph report."""
    logger.incoming("/graph_report")

    report = get_graph_report()

    if not report:
        await update.message.reply_text(
            "📋 No hay reporte disponible. Construye el grafo con `/graphify`",
            parse_mode="Markdown"
        )
        return

    # Truncate if too long for Telegram
    if len(report) > 4000:
        report = report[:3900] + "\n\n... (reporte truncado)"

    await update.message.reply_text(
        f"📋 *Reporte del Grafo:*\n\n{report}",
        parse_mode="Markdown"
    )


async def graph_add_cmd(update: Update, context: CallbackContext):
    """Add a URL to the knowledge graph."""
    if not context.args:
        await update.message.reply_text(
            "📥 *Uso:* `/graph_add <url>`\n\n"
            "Ejemplo: `/graph_add https://arxiv.org/abs/1706.03762`",
            parse_mode="Markdown"
        )
        return

    url = context.args[0]
    logger.incoming(f"/graph_add {url}")

    await update.message.reply_text(f"📥 Añadiendo al grafo: {url[:80]}...")

    result = add_url_to_graph(url)

    if result.get("success"):
        await update.message.reply_text("✅ URL añadida al grafo exitosamente.")
    else:
        await update.message.reply_text(
            f"❌ Error: {result.get('error', result.get('stderr', 'Desconocido'))}"
        )


async def graph_export_cmd(update: Update, context: CallbackContext):
    """Export graph in different formats."""
    if not context.args:
        await update.message.reply_text(
            "📤 *Formatos disponibles:*\n"
            "`/graph_export html` - Visualización interactiva\n"
            "`/graph_export svg` - Imagen vectorial\n"
            "`/graph_export graphml` - Para Gephi/yEd\n"
            "`/graph_export wiki` - Wiki markdown\n"
            "`/graph_export callflow` - Diagrama de flujo",
            parse_mode="Markdown"
        )
        return

    fmt = context.args[0]
    if fmt == "callflow":
        fmt = "callflow-html"

    logger.incoming(f"/graph_export {fmt}")

    await update.message.reply_text(f"📤 Exportando grafo como {fmt}...")

    result = export_graph(format=fmt)

    if result.get("success"):
        await update.message.reply_text(f"✅ Grafo exportado como {fmt}.")
    else:
        await update.message.reply_text(
            f"❌ Error: {result.get('error', result.get('stderr', 'Desconocido'))}"
        )
