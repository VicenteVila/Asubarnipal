"""Agent commands handlers (/agente, /model, /query_vectorial)."""

import time
import requests
import config
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackContext

from core.bot_logger import logger
from .validators import validate_task, validate_query


async def agente_cmd(update: Update, context: CallbackContext) -> None:
    """Activate autonomous agent."""
    task = " ".join(context.args)

    if not task:
        await update.message.reply_text("Usa: /agente <tarea>")
        return

    valid, error = validate_task(task)
    if not valid:
        logger.warn(f"Agente task inválida: {error}")
        await update.message.reply_text(f"❌ Tarea inválida: {error}")
        return

    task = task.strip()
    logger.agent(task)

    from app.service import AgentService
    service = AgentService()

    start = time.time()
    result = service.agent_chat(task)
    duration = time.time() - start

    response = result.get("response", "Sin respuesta")

    if result.get("tool_calls") and update and update.message:
        logger.debug(f"Tool calls: {len(result.get('tool_calls', []))}")
        try:
            buttons = [[InlineKeyboardButton("Continuar", callback_data="agent_continue")]]
            await update.message.reply_text("¿Continuar?", reply_markup=InlineKeyboardMarkup(buttons))
        except Exception as e:
            logger.warning(f"No se pudo enviar botones: {e}")

    logger.agent_end(response[:80])
    
    # Verificar que update aún es válido antes de responder
    try:
        if update and update.message:
            await update.message.reply_text(
                f"🤖 *Resultado:*\n\n{response[:4000]}",
                parse_mode="Markdown"
            )
        else:
            logger.warning("Update no disponible para responder")
    except Exception as e:
        logger.error(f"Error al enviar respuesta: {e}")


async def model_cmd(update: Update, context: CallbackContext) -> None:
    """Show or switch LLM model."""
    args = context.args

    if not args:
        text = f"""*Modelo Actual:* `{config.OLLAMA_MODEL}`

*Ollama:* qwen3.5:4b, qwen3.5:8b, llama3:8b
*Gemini:* gemini-2.0-flash, gemini-1.5-flash, gemini-1.5-pro

*Selecciona un modelo o usa: /model <nombre>*"""

        from .keyboards import build_model_keyboard
        await update.message.reply_text(text, parse_mode="Markdown", reply_markup=build_model_keyboard())
        return

    new_model = args[0].lower()

    ollama_valid = False
    try:
        resp = requests.get(f"{config.OLLAMA_BASE_URL}/api/tags", timeout=5)
        if resp.status_code == 200:
            models = [m.get("name", "").lower() for m in resp.json().get("models", [])]
            if new_model in models or any(new_model in m for m in models):
                ollama_valid = True
    except Exception:
        pass

    gemini_models = ["gemini", "gemini-2.0-flash", "gemini-1.5-flash", "gemini-1.5-pro"]
    gemini_valid = new_model in gemini_models or new_model.startswith("gemini")

    if ollama_valid or gemini_valid:
        await update.message.reply_text(
            f"✅ Modelo cambiado a: *{new_model}*",
            parse_mode="Markdown"
        )
    else:
        await update.message.reply_text(
            f"❌ Modelo '{new_model}' no encontrado.\n\n"
            "Usa `/model` sin argumentos para ver los disponibles.",
            parse_mode="Markdown"
        )


async def query_vectorial_cmd(update: Update, context: CallbackContext) -> None:
    """Vector search in index."""
    query = " ".join(context.args)

    if not query:
        await update.message.reply_text("Usa: /query_vectorial <búsqueda>")
        return

    valid, error = validate_query(query)
    if not valid:
        logger.warn(f"Query vectorial inválido: {error}")
        await update.message.reply_text(f"❌ Consulta inválida: {error}")
        return

    query = query.strip()
    logger.incoming(f"/query_vectorial {query}")

    try:
        from index.rag import RAGEngine
        engine = RAGEngine(config.INDEX_DIR / "index.faiss")
        results = engine.search(query)

        if not results:
            await update.message.reply_text(f"No encontré resultados para: {query}")
            return

        text = "🔎 *Resultados vectoriales:*\n\n"
        for r in results:
            text += f"• {r['document']} (dist: {r['distance']:.2f})\n"

        logger.success(f"Vector search: {len(results)} resultados")
        await update.message.reply_text(text, parse_mode="Markdown")
    except Exception as e:
        logger.error(f"Query vectorial exception: {e}")
        await update.message.reply_text(f"❌ Error en búsqueda vectorial")


async def rate_cmd(update: Update, context: CallbackContext) -> None:
    """Rate the last agent response (1-5)."""
    args = context.args

    if not args:
        await update.message.reply_text(
            "📊 *Calificar última respuesta*\n\n"
            "Usa: /rate <1-5>\n\n"
            "• 1 = Muy malo\n"
            "• 2 = Malo\n"
            "• 3 = Regular\n"
            "• 4 = Bueno\n"
            "• 5 = Excelente\n\n"
            "Ejemplo: `/rate 5`",
            parse_mode="Markdown"
        )
        return

    try:
        rating = int(args[0])
        if rating < 1 or rating > 5:
            raise ValueError("Rating must be 1-5")
    except ValueError:
        await update.message.reply_text("❌ Rating debe ser entre 1 y 5. Ejemplo: `/rate 4`")
        return

    # Get last response
    from skills.default_skills import get_last_response
    last_resp = get_last_response()

    if not last_resp.get("success") or not last_resp.get("response"):
        await update.message.reply_text("❌ No hay respuesta anterior para calificar.")
        return

    last = last_resp["response"]
    query = last.get("query", "")
    response = last.get("response", "")

    # Record feedback
    from skills.default_skills import record_feedback
    result = record_feedback(query, response, rating)

    if result.get("success"):
        stats = result.get("stats", {})
        rating_emoji = {
            1: "😞",
            2: "😕",
            3: "😐",
            4: "🙂",
            5: "🌟"
        }

        await update.message.reply_text(
            f"{rating_emoji.get(rating, '⭐')} *Calificación guardada: {rating}/5*\n\n"
            f"📊 Promedio: {stats.get('avg_rating', 0):.1f}/5\n"
            f"📈 Total calificado: {stats.get('total_ratings', 0)}\n"
            f"✅ Buenos: {stats.get('good_count', 0)} | ❌ Malos: {stats.get('bad_count', 0)}",
            parse_mode="Markdown"
        )
    else:
        await update.message.reply_text(f"❌ Error: {result.get('error')}")


async def calidad_cmd(update: Update, context: CallbackContext) -> None:
    """Show quality statistics of agent responses."""
    from skills.default_skills import get_eval_stats
    import logging as _logger

    logger.incoming("/calidad")

    result = get_eval_stats(20)

    if result.get("error"):
        await update.message.reply_text(f"❌ Error: {result['error']}")
        return

    total = result.get("total", 0)
    if total == 0:
        await update.message.reply_text(
            "📊 *Calidad de Respuestas*\n\n"
            "Aún no hay evaluaciones.\n"
            "Después de cada respuesta del agente, se te preguntará:\n"
            "¿La respuesta fue precisa? (sí/no/ms)",
            parse_mode="Markdown"
        )
        return

    stats = result.get("stats", {})
    accuracy = stats.get("accuracy_rate", 0) * 100
    avg_rating = stats.get("avg_rating", 0)
    yes_c = stats.get("yes_count", 0)
    no_c = stats.get("no_count", 0)
    ms_c = stats.get("ms_count", 0)

    text = f"""📊 *Calidad de Respuestas*

*Estadísticas:*
• Evaluadas: {total}
• Accuracy: {accuracy:.0f}%
• Promedio: {avg_rating}/5

*Respuestas:*
✅ Sí: {yes_c}
❌ No: {no_c}
😐 Más o menos: {ms_c}
"""

    # Show low quality alerts
    recent = result.get("recent", [])
    low_quality = [e for e in recent if e.get("user_feedback") == "no"]
    if low_quality:
        text += "\n*⚠️ Respuestas de baja calidad:*\n"
        for e in low_quality[:3]:
            query = e.get("query", "")[:40]
            text += f"• {query}...\n"

    # Check for accuracy alert
    if accuracy < 60 and total >= 5:
        text += f"\n⚠️ *Alerta*: Accuracy bajo ({accuracy:.0f}%). Revisa las respuestas del agente."

    await update.message.reply_text(text, parse_mode="Markdown")
    logger.success(f"Calidad: {accuracy:.0f}% accuracy, {total} evaluadas")


async def model_callback(update: Update, context: CallbackContext) -> None:
    """Handle inline keyboard callback for /model."""
    query = update.callback_query
    await query.answer()

    data = query.data
    if data.startswith("model:"):
        model = data.split(":")[1]
        config.OLLAMA_MODEL = model
        context.user_data["preferred_model"] = model
        await query.edit_message_text(f"✅ Modelo cambiado a: *{model}*", parse_mode="Markdown")