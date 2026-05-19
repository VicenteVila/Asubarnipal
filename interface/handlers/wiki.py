"""Wiki commands handlers (/query, /hubs, /clusters, /lint, /sync_obsidian)."""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import config
from telegram import Update
from telegram.ext import CallbackContext

from core.bot_logger import logger
from .validators import validate_query


async def query_cmd(update: Update, context: CallbackContext):
    """Query the wiki."""
    query = " ".join(context.args)

    if not query:
        await update.message.reply_text("Usa: /query <pregunta>")
        return

    valid, error = validate_query(query)
    if not valid:
        logger.warn(f"Query wiki inválido: {error}")
        await update.message.reply_text(f"❌ Consulta inválida: {error}")
        return

    query = query.strip()
    logger.incoming(f"/query {query}")

    try:
        from core.wiki import Wiki
        wiki = Wiki()

        with logger.group("Wiki Query"):
            results = wiki.search(query)
            logger.debug(f"Encontrados: {len(results)} resultados")

        if not results:
            logger.warn(f"Sin resultados para: {query}")
            await update.message.reply_text(f"No encontré resultados para: {query}")
            return

        text = f"🔎 *Resultados para: {query}*\n\n"
        for r in results[:5]:
            text += f"• {r['name']}\n"

        logger.success(f"Query completado: {len(results)} resultados")
        await update.message.reply_text(text, parse_mode="Markdown")
    except Exception as e:
        logger.error(f"Query wiki exception", exc=e)
        await update.message.reply_text(f"❌ Error en consulta")


async def hubs_cmd(update: Update, context: CallbackContext):
    """Show hub concepts."""
    from core.wiki import Wiki
    wiki = Wiki()

    hubs = wiki.get_hubs(limit=10)

    text = "🕸️ *Hubs — Conceptos Centrales*\n\n"
    for h in hubs:
        text += f"• {h['name']} ({h['connections']} conexiones)\n"

    await update.message.reply_text(text, parse_mode="Markdown")


async def clusters_cmd(update: Update, context: CallbackContext):
    """Show thematic clusters."""
    from core.wiki import Wiki
    wiki = Wiki()

    clusters = wiki.get_clusters()

    text = "🔮 *Clusters — Comunidades Temáticas*\n\n"
    for c in clusters:
        text += f"• {c['tag']}: {c['count']}\n"

    await update.message.reply_text(text, parse_mode="Markdown")


async def lint_cmd(update: Update, context: CallbackContext):
    """Health check for wiki."""
    from core.wiki import Wiki
    wiki = Wiki()

    result = wiki.lint()

    text = f"""🔍 *Diagnóstico del Wiki*

• Entidades: {result['total_entities']}
• Health Score: {result['health_score']}%

*Issues:*
"""
    for issue in result['issues'][:10]:
        text += f"• {issue['type']}: {issue.get('name', 'N/A')}\n"

    await update.message.reply_text(text, parse_mode="Markdown")


async def sync_obsidian_cmd(update: Update, context: CallbackContext):
    """Sync from Obsidian vault."""
    logger.incoming("/sync_obsidian")
    await update.message.reply_text("🔄 Sincronizando Obsidian...")

    from core.wiki import Wiki
    wiki = Wiki()
    result = wiki.sync_obsidian()

    count = result.get('imported', 0)
    logger.success(f"Sincronizado: {count} notas")
    await update.message.reply_text(f"✅ Importadas: {count} notas")