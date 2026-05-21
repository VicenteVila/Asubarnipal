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
    """Query using two-model architecture: small librarian + large analyst."""
    query = " ".join(context.args)

    if not query:
        await update.message.reply_text("Usa: /query <pregunta>")
        return

    query = query.strip().strip('<>').strip()

    valid, error = validate_query(query)
    if not valid:
        logger.warn(f"Query wiki inválido: {error}")
        await update.message.reply_text(f"❌ Consulta inválida: {error}")
        return

    logger.incoming(f"/query {query}")

    try:
        from app.service import AgentService
        from core.librarian import get_librarian
        from core.memory import get_proposal_memory

        librarian = get_librarian()
        pm = get_proposal_memory()

        await update.message.reply_text("📚 Consultando biblioteca...")

        summary_data = librarian.search_and_summarize(query, limit=8)

        if summary_data.get("total_found", 0) == 0:
            await update.message.reply_text(f"No encontré información sobre: {query}")
            return

        await update.message.reply_text("🧠 Analizando información...")

        service = AgentService()

        preferred_modo = pm.get_preference()

        prompt = f"""Eres el Analista Experto de Asubarnipal.

RESUMEN DEL BIBLIOTECARIO:
{summary_data.get('resumen', '')}

FUENTES:
{chr(10).join(summary_data.get('sources', [])[:8])}

PREGUNTA ORIGINAL: {query}

Responde con el siguiente formato EXACTO:

## RESPUESTA
[Explicación clara en bullets y numbered steps. Responde directamente a la pregunta.]

## PROPUESTA DE INVESTIGACIÓN

### MODO ESTRUCTURADO:
- **Hallazgo:** [Qué se descubrió]
- **Gap:** [Qué no está resuelto o necesita más investigación]
- **Impacto:** [Cómo mejora esto al bot]
- **Prioridad:** Alta/Media/Baja
- **Acciones:** [Lista numerada de pasos concretos a seguir]
  1. [Paso 1]
  2. [Paso 2]
  3. [Paso 3]
- **Métricas:** [Cómo medimos si funcionó]

### MODO EXPLORATORIO:
- **Temas relacionados:** [Conceptos encontrados que podrían explorarse]
- **Nuevas preguntas:** [3-5 preguntas que surgieron de la investigación]
- **Conexiones:** [Cómo conecta esto con otros temas del conocimiento]

---

Genera AMBOS modos de propuesta. Sé preciso y accionable."""

        try:
            answer = service.llm.generate(prompt)

            if answer and len(answer) > 50 and not any(
                fail in answer for fail in ["⚠️ Fallo crítico", "No puedo responder", "no tengo información"]
            ):
                await update.message.reply_text(answer[:4000])
                logger.success(f"Query completado con respuesta")

                refs = summary_data.get("refs", [])

                estructurada_section = ""
                exploratoria_section = ""
                in_estructurada = False
                in_exploratoria = False

                for line in answer.split("\n"):
                    if "### MODO ESTRUCTURADO:" in line:
                        in_estructurada = True
                        in_exploratoria = False
                    elif "### MODO EXPLORATORIO:" in line:
                        in_exploratoria = True
                        in_estructurada = False
                    elif line.startswith("## "):
                        in_estructurada = False
                        in_exploratoria = False

                    if in_estructurada:
                        estructurada_section += line + "\n"
                    elif in_exploratoria:
                        exploratoria_section += line + "\n"

                keyboard = [
                    [
                        InlineKeyboardButton(
                            "📊 Estructurada" if preferred_modo == "estructurada" else "Estructurada",
                            callback_data=f"modo_estructurada:{answer[:50]}"
                        ),
                        InlineKeyboardButton(
                            "🧭 Exploratoria" if preferred_modo == "exploratoria" else "Exploratoria",
                            callback_data=f"modo_exploratoria:{answer[:50]}"
                        ),
                    ],
                    [
                        InlineKeyboardButton("💾 Guardar", callback_data=f"save_proposal:{answer[:50]}"),
                        InlineKeyboardButton("📝 Crear nota wiki", callback_data=f"wiki_proposal:{answer[:50]}"),
                    ],
                    [
                        InlineKeyboardButton("⏸️ Standby", callback_data=f"standby_proposal:{answer[:50]}"),
                    ],
                ]

                await update.message.reply_text(
                    "📋 *Modo de propuesta preferido:*",
                    reply_markup=InlineKeyboardMarkup(keyboard),
                    parse_mode="Markdown"
                )

                context.user_data["last_proposal"] = {
                    "pregunta": query,
                    "respuesta": answer,
                    "estructurada": estructurada_section,
                    "exploratoria": exploratoria_section,
                    "refs": refs,
                    "modo": preferred_modo,
                }

            else:
                raise ValueError("LLM returned empty or failure")

        except Exception as e:
            logger.error(f"Query error: {e}", exc=e)
            text = f"🔎 *Resultados para: {query}*\n\n"
            for ref in summary_data.get("refs", [])[:8]:
                text += f"• {ref['name'][:60]} [{ref['tipo']}]\n"
                if ref.get("content_preview"):
                    text += f"  _{ref['content_preview'][:150]}_...\n\n"
            await update.message.reply_text(text[:4000], parse_mode="Markdown")

    except Exception as e:
        logger.error(f"Query wiki exception", exc=e)
        await update.message.reply_text(f"❌ Error: {str(e)[:200]}")


async def query_callback_handler(update: Update, context: CallbackContext):
    """Handle inline button callbacks for query proposals."""
    from core.memory import get_proposal_memory
    from core.wiki import Wiki

    query = update.callback_query
    await query.answer()

    data = query.data
    last_proposal = context.user_data.get("last_proposal", {})

    if not last_proposal:
        await query.edit_message_text("❌ No hay propuesta reciente para procesar.")
        return

    pm = get_proposal_memory()
    wiki = Wiki()

    if data.startswith("modo_"):
        modo = "estructurada" if data.startswith("modo_estructurada") else "exploratoria"
        pm.set_preference(modo)
        selected = "📊 Estructurada" if modo == "estructurada" else "🧭 Exploratoria"
        await query.edit_message_text(f"{selected} guardada como modo preferido.")

    elif data.startswith("save_proposal"):
        pm.save(
            pregunta=last_proposal.get("pregunta", ""),
            respuesta=last_proposal.get("respuesta", ""),
            propuesta=last_proposal.get(last_proposal.get("modo", "estructurada"), ""),
            modo=last_proposal.get("modo", "estructurada"),
            refs=last_proposal.get("refs", []),
        )
        await query.edit_message_text("💾 Propuesta guardada en memoria.")

    elif data.startswith("wiki_proposal"):
        modo = last_proposal.get("modo", "estructurada")
        propuesta_text = last_proposal.get(modo, last_proposal.get("respuesta", ""))

        wiki.save_research_proposal(
            pregunta=last_proposal.get("pregunta", ""),
            propuesta=propuesta_text,
            modo=modo,
            refs=last_proposal.get("refs", []),
        )
        await query.edit_message_text("📝 Propuesta guardada como nota en wiki.")

    elif data.startswith("standby_proposal"):
        pm.save_to_standby(
            pregunta=last_proposal.get("pregunta", ""),
            respuesta=last_proposal.get("respuesta", ""),
            propuesta=last_proposal.get("respuesta", ""),
            modo=last_proposal.get("modo", "estructurada"),
            refs=last_proposal.get("refs", []),
        )
        await query.edit_message_text("⏸️ Propuesta guardada en standby.")


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


async def quality_cmd(update: Update, context: CallbackContext):
    """Quality check for recent ingests."""
    from core.wiki import Wiki
    import logging as _logger

    logger.incoming("/quality")
    wiki = Wiki()

    limit = 20
    if context.args and context.args[0].isdigit():
        limit = min(int(context.args[0]), 50)

    result = wiki.get_ingest_quality(limit)

    if result["total"] == 0:
        await update.message.reply_text("📊 No hay ingestas registradas aún.")
        return

    text = f"""📊 *Calidad de Ingestas (últimas {limit})*

• Total ingesado: {result['total']}
• Score promedio: {result['avg_score']}/100
• ⚠️ Baja calidad: {result['low_quality_count']}

"""

    if result["by_type"]:
        text += "*Por tipo:*\n"
        for t, data in result["by_type"].items():
            emoji = {"pdf": "📄", "youtube": "🎬", "url": "🌐"}.get(t, "📦")
            text += f"{emoji} {t}: {data['count']} ing., avg {data['avg_score']:.0f}/100\n"

    if result["recent"]:
        text += "\n*Recientes:*\n"
        for e in result["recent"][-5:]:
            score = e["quality_score"]
            emoji = "⚠️" if score < 50 else "✅"
            name = e["name"][:30] + "..." if len(e["name"]) > 30 else e["name"]
            text += f"{emoji} {score}/100 - {name}\n"

    alerts = wiki.get_quality_alerts()
    if alerts:
        text += "\n*⚠️ Alertas de baja calidad:*\n"
        for a in alerts[:3]:
            text += f"• {a['name'][:40]} (score: {a['quality_score']})\n"

    await update.message.reply_text(text, parse_mode="Markdown")
    logger.success(f"Quality report: avg={result['avg_score']}, low_quality={result['low_quality_count']}")


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


async def queryhybrid_cmd(update: Update, context: CallbackContext):
    """Hybrid search - queries both SQLite and Obsidian vault."""
    query = " ".join(context.args)

    if not query:
        await update.message.reply_text(
            "🔍 *Búsqueda Híbrida*\n\n"
            "Usa: /queryhybrid <pregunta>\n\n"
            "Busca en SQLite y Obsidian vault activa.\n"
            "Combina resultados de ambas fuentes."
        )
        return

    query = query.strip().strip('<>').strip()
    logger.incoming(f"/queryhybrid {query}")

    await update.message.reply_text(f"🔍 Buscando en SQLite + Obsidian...")

    try:
        from core.hybrid_search import get_hybrid_search
        from app.service import AgentService

        hs = get_hybrid_search()

        # Get combined context
        context_text = hs.get_context_for_llm(query, max_chars=4000)

        if "No se encontró información" in context_text:
            await update.message.reply_text(f"No encontré información sobre: {query}")
            return

        # Use agent to generate answer from combined context
        service = AgentService()
        prompt = f"""Basándote en esta información de múltiples fuentes (SQLite + Obsidian), responde la pregunta:

Contexto:
{context_text}

Pregunta: {query}

Responde de forma clara y detallada. Indica de qué fuente obtuviste cada información."""

        answer = service.llm.generate(prompt)

        if answer and len(answer) > 20:
            # Also show search stats
            search_results = hs.search(query, limit=5)
            stats = f"\n\n📊 *Estadísticas de búsqueda:*\n"
            stats += f"• SQLite: {search_results.get('sqlite_count', 0)} resultados\n"
            stats += f"• Obsidian: {search_results.get('obsidian_count', 0)} resultados\n"
            if search_results.get('vault_active'):
                stats += f"• Vault activa: `{search_results.get('vault_active')}`"

            await update.message.reply_text(answer[:3500] + stats, parse_mode="Markdown")
            logger.success(f"Hybrid query completed")
        else:
            await update.message.reply_text(f"No pude generar respuesta para: {query}")

    except Exception as e:
        logger.error(f"Hybrid query error: {e}", exc=e)
        await update.message.reply_text(f"❌ Error en búsqueda híbrida: {str(e)[:200]}")