"""H-Mem memory commands handlers."""

import json
from core.hybrid_retriever import get_hmem_manager, get_hybrid_retriever
from core.bot_logger import logger


async def memoria_cmd(update, context):
    """Handle /memoria command - Show H-Mem status."""
    logger.incoming("/memoria")

    try:
        hmem = get_hmem_manager()
        stats = hmem.stats()
    except Exception as e:
        logger.warning(f"H-Mem stats error: {e}")
        await update.message.reply_text(f"❌ H-Mem no disponible: {e}")
        return

    tree_stats = stats.get("tree", {})
    graph_stats = stats.get("graph", {})

    tree_by_level = tree_stats.get("by_level", {})
    tree_lines = "\n".join([
        f"  • {k}: {v} nodos" for k, v in tree_by_level.items()
    ]) or "  (vacío)"

    graph_types = graph_stats.get("by_type", {})
    graph_lines = "\n".join([
        f"  • {k}: {v}" for k, v in graph_types.items()
    ]) or "  (vacío)"

    text = f"""🧠 *H-Mem: Sistema de Memoria Híbrida*

*Árbol Temporal:*
  Total nodos: {tree_stats.get('total_nodes', 0)}
{tree_lines}

*Grafo de Entidades:*
  Total entidades: {graph_stats.get('total_entities', 0)}
  Total relaciones: {graph_stats.get('total_relations', 0)}
{graph_lines}

*Pesos de Ranking:*
  • Semántico: {stats.get('weights', {}).get('theta1_semantic', '?')}
  • Temporal: {stats.get('weights', {}).get('theta2_temporal', '?')}
  • Robustez: {stats.get('weights', {}).get('theta3_robustness', '?')}
"""

    await update.message.reply_text(text, parse_mode="Markdown")


async def recordar_cmd(update, context):
    """Handle /recordar <texto> - Add memory to H-Mem."""
    logger.incoming("/recordar")

    if not context.args:
        await update.message.reply_text("📝 Uso: /recordar <texto a recordar>")
        return

    text = " ".join(context.args)

    try:
        hmem = get_hmem_manager()
        result = hmem.remember(text, metadata={"source": "telegram"})
    except Exception as e:
        logger.error(f"Remember error: {e}")
        await update.message.reply_text(f"❌ Error: {e}")
        return

    tree_id = result.get("tree_node_id", "N/A")
    tree_level = result.get("tree_level", 0)

    text = f"""💾 *Memoria guardada*

• Nodo: `{tree_id[:20]}...`
• Nivel: L{tree_level} (árbol)
• Entidades extraídas: {result.get('graph_ingest', {}).get('entities_extracted', 0)}"""

    await update.message.reply_text(text, parse_mode="Markdown")


async def pensar_cmd(update, context):
    """Handle /pensar <pregunta> - Query H-Mem with answer."""
    logger.incoming("/pensar")

    if not context.args:
        await update.message.reply_text("🧠 Uso: /pensar <pregunta>")
        return

    query = " ".join(context.args)

    try:
        hmem = get_hmem_manager()
        answer = hmem.think(query)
    except Exception as e:
        logger.error(f"Think error: {e}")
        await update.message.reply_text(f"❌ Error: {e}")
        return

    await update.message.reply_text(f"🧠 *H-Mem responde:*\n\n{answer}", parse_mode="Markdown")


async def contexto_cmd(update, context):
    """Handle /contexto <query> - Get memory context for prompt."""
    logger.incoming("/contexto")

    if not context.args:
        await update.message.reply_text("📋 Uso: /contexto <query>")
        return

    query = " ".join(context.args)

    try:
        hmem = get_hmem_manager()
        context_text = hmem.get_context(query)
    except Exception as e:
        logger.error(f"Context error: {e}")
        await update.message.reply_text(f"❌ Error: {e}")
        return

    if not context_text:
        context_text = "(Sin contexto encontrado)"

    preview = context_text[:1000] + ("..." if len(context_text) > 1000 else "")

    await update.message.reply_text(f"*Contexto para '{query}':*\n\n{preview}", parse_mode="Markdown")


async def entidades_cmd(update, context):
    """Handle /entidades - Show entity graph hubs."""
    logger.incoming("/entidades")

    try:
        hmem = get_hmem_manager()
        graph_data = hmem.retriever.get_entity_graph()
    except Exception as e:
        logger.error(f"Entities error: {e}")
        await update.message.reply_text(f"❌ Error: {e}")
        return

    hubs = graph_data.get("hubs", [])
    stats = graph_data.get("stats", {})

    if not hubs:
        await update.message.reply_text("🔗 *Grafo de Entidades*\n\n(no hay entidades aún)")
        return

    hubs_text = "\n".join([
        f"  {i+1}. {h.get('name', 'N/A')} ({h.get('entity_type', '?')}) - {h.get('connections', 0)} conexiones"
        for i, h in enumerate(hubs[:8])
    ])

    text = f"""🔗 *Grafo de Entidades - Hubs*

*Estadísticas:*
• Entidades: {stats.get('total_entities', 0)}
• Relaciones: {stats.get('total_relations', 0)}

*Top Entidades:*
{hubs_text}"""

    await update.message.reply_text(text, parse_mode="Markdown")


async def recientes_cmd(update, context):
    """Handle /recientes - Show recent memories."""
    logger.incoming("/recientes")

    limit = 10
    if context.args and context.args[0].isdigit():
        limit = min(int(context.args[0]), 30)

    try:
        hmem = get_hmem_manager()
        memories = hmem.get_recent_memories(limit=limit)
    except Exception as e:
        logger.error(f"Recent error: {e}")
        await update.message.reply_text(f"❌ Error: {e}")
        return

    if not memories:
        await update.message.reply_text("🕐 *Memorias recientes*\n\n(aún no hay memorias)")
        return

    lines = []
    for m in memories:
        content = (m.get("content") or m.get("summary") or "")[:100]
        level = m.get("level", 0)
        ts = m.get("timestamp", "")[:10]
        lines.append(f"• [{ts}] L{level}: {content}...")

    text = f"""🕐 *Memorias Recientes ({len(memories)})*

"""
    text += "\n".join(lines[:15])

    await update.message.reply_text(text, parse_mode="Markdown")


def get_hmem_handlers():
    """Return dict of H-Mem command handlers."""
    return {
        "memoria": memoria_cmd,
        "recordar": recordar_cmd,
        "pensar": pensar_cmd,
        "contexto": contexto_cmd,
        "entidades": entidades_cmd,
        "recientes": recientes_cmd,
    }