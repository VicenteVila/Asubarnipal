"""Search commands handlers (/ingest, /investigar)."""

import config
from telegram import Update
from telegram.ext import CallbackContext

from core.bot_logger import logger
from .validators import validate_url, validate_topic


async def ingest_cmd(update: Update, context: CallbackContext):
    """Ingest a URL to wiki."""
    url = " ".join(context.args)

    if not url:
        await update.message.reply_text("Usa: /ingest <URL>")
        return

    valid, error = validate_url(url)
    if not valid:
        logger.warn(f"Ingest URL inválida: {error}")
        await update.message.reply_text(f"❌ URL inválida: {error}")
        return

    url = url.strip()
    logger.incoming(f"/ingest {url}")
    await update.message.reply_text(f"📥 Ingiriendo: {url}\n\n⏳ Procesando contenido...")

    try:
        from core.wiki import Wiki
        wiki = Wiki()
        result = wiki.ingest_url_smart(url)

        if result.get("success"):
            lang = result.get("language_detected", "?")
            translated = " (traducido)" if result.get("was_translated") else ""
            concepts = result.get("concepts_count", 0)
            related = result.get("related_count", 0)
            summary = result.get("summary", "")

            logger.success(f"Ingest completo: {result.get('name')}")

            response = f"""✅ *Ingesta completada*

📄 *{result.get('name')}*
🌐 Idioma: `{lang}`{translated}

📊 *Estadísticas:*
• Conceptos extraídos: {concepts}
• Notas relacionadas: {related}

📝 *Resumen:*
{summary[:300]}{"..." if len(summary or "") > 300 else ""}

🔗 *Conceptos:*
{', '.join(result.get('concepts', [])[:5])}"""

            await update.message.reply_text(response, parse_mode="Markdown")
        else:
            logger.error(f"Ingest falló", exc=None)
            await update.message.reply_text(f"❌ Error: {result.get('error')}")
    except Exception as e:
        logger.error(f"Ingest exception", exc=e)
        await update.message.reply_text(f"❌ Error inesperado durante ingest")


async def investigar_cmd(update: Update, context: CallbackContext):
    """Research a topic deeply."""
    topic = " ".join(context.args)

    if not topic:
        await update.message.reply_text("Usa: /investigar <tema>")
        return

    valid, error = validate_topic(topic)
    if not valid:
        logger.warn(f"Investigar topic inválido: {error}")
        await update.message.reply_text(f"❌ Tema inválido: {error}")
        return

    topic = topic.strip()
    logger.incoming(f"/investigar {topic}")
    await update.message.reply_text(f"🔬 Investigando: *{topic}*...")

    try:
        from core.background_manager import BraveCounter
        brave_counter = BraveCounter()

        if not brave_counter.can_search():
            logger.warn("Límite Brave Search alcanzado")
            await update.message.reply_text("❌ Límite Brave Search alcanzado")
            return

        from core.llm_router import BraveRouter
        brave = BraveRouter()

        with logger.group("Brave Search"):
            results = brave.search(topic, num_results=5)
            logger.rag_search(topic, len(results))

        from core.wiki import Wiki
        wiki = Wiki()
        ingested = 0
        for r in results:
            try:
                wiki.ingest_url(r.get("url", ""))
                ingested += 1
            except Exception as e:
                logger.warn(f"URL ingest falló: {r.get('url', '')[:50]}")

        logger.success(f"Investigación completa: {len(results)} fuentes, {ingested} ingiridas")
        await update.message.reply_text(
            f"✅ Investigación completada\n"
            f"• Fuentes: {len(results)}\n"
            f"• Ingiridas al wiki: {ingested}"
        )
    except Exception as e:
        logger.error(f"Investigar exception", exc=e)
        await update.message.reply_text(f"❌ Error inesperado durante investigación")