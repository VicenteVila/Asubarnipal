"""LIFE-HARNESS and HASP command handlers."""

import json
from typing import Any
from telegram import Update
from telegram.ext import CallbackContext
from core.runtime_harness import get_harness
from core.skill_programs import get_pf_registry
from core.bot_logger import logger


async def harness_cmd(update: Update, context: CallbackContext) -> None:
    """Handle /harness - Show LIFE-HARNESS runtime statistics."""
    logger.incoming("/harness")

    try:
        harness = get_harness()
        stats = harness.get_stats()
    except Exception as e:
        logger.error(f"Harness stats error: {e}")
        await update.message.reply_text(f"❌ Error obteniendo stats: {e}")
        return

    contract = stats.get("contract_layer", {})
    skill = stats.get("skill_layer", {})
    action = stats.get("action_layer", {})
    trajectory = stats.get("trajectory_layer", {})

    text = f"""🛡️ *LIFE-HARNESS Runtime Stats*

*Layer 1 - Contract:*
  • Contratos cacheados: {contract.get('cached_contracts', 0)}
  • Contratos calibrados: {contract.get('calibrated_contracts', 0)}

*Layer 2 - Skill:*
  • Skills registradas: {skill.get('total_skills', 0)}
  • Skills inyectadas: {skill.get('injected_skills', 0)}

*Layer 3 - Action:*
  • Acciones validadas: {action.get('validated_actions', 0)}
  • Acciones rechazadas: {action.get('rejected_actions', 0)}

*Layer 4 - Trajectory:*
  • Trayectorias activas: {trajectory.get('active_trajectories', 0)}
  • Intervenciones: {trajectory.get('total_interventions', 0)}
    - Loops detectados: {trajectory.get('loop_interventions', 0)}
    - Retries forzados: {trajectory.get('retry_interventions', 0)}
    - Budget agotado: {trajectory.get('budget_interventions', 0)}

*Total intervenciones:* {stats.get('total_interventions', 0)}
"""

    await update.message.reply_text(text, parse_mode="Markdown")


async def pfs_cmd(update: Update, context: CallbackContext) -> None:
    """Handle /pfs - List available Program Functions."""
    logger.incoming("/pfs")

    try:
        registry = get_pf_registry()
        pfs = registry.list_pfs()
    except Exception as e:
        logger.error(f"PFs list error: {e}")
        await update.message.reply_text(f"❌ Error listando PFs: {e}")
        return

    if not pfs:
        await update.message.reply_text("📋 *Program Functions*\n\n(no hay PFs registradas)")
        return

    lines = []
    for pf in pfs:
        name = pf.get("name", "N/A")
        desc = pf.get("description", "Sin descripción")
        preconditions = pf.get("preconditions", [])
        precond_str = ", ".join([f"{k}={v}" for k, v in preconditions[:2]])
        if len(preconditions) > 2:
            precond_str += f" (+{len(preconditions)-2} más)"
        
        lines.append(f"• *{name}*\n  {desc}\n  Precondiciones: `{precond_str}`")

    text = f"""📋 *Program Functions ({len(pfs)})*

""" + "\n\n".join(lines)

    await update.message.reply_text(text, parse_mode="Markdown")


async def pf_run_cmd(update: Update, context: CallbackContext) -> None:
    """Handle /pf_run <name> [state_json] - Execute a specific Program Function."""
    logger.incoming("/pf_run")

    if not context.args:
        await update.message.reply_text(
            "🎯 Uso: /pf_run <nombre_pf> [estado_json]\n\n"
            "Ejemplo: `/pf_run retry_on_failure {\"last_action\": {\"status\": \"error\"}}`",
            parse_mode="Markdown"
        )
        return

    pf_name = context.args[0]
    state_json = " ".join(context.args[1:]) if len(context.args) > 1 else "{}"

    try:
        state = json.loads(state_json)
    except json.JSONDecodeError as e:
        await update.message.reply_text(f"❌ JSON inválido: {e}")
        return

    try:
        registry = get_pf_registry()
        result = registry.execute_pf(pf_name, state)
    except Exception as e:
        logger.error(f"PF run error: {e}")
        await update.message.reply_text(f"❌ Error ejecutando PF: {e}")
        return

    if result is None:
        await update.message.reply_text(f"⚠️ PF `{pf_name}` no encontrado o precondiciones no cumplidas", parse_mode="Markdown")
        return

    result_str = json.dumps(result, indent=2, ensure_ascii=False)[:1000]
    text = f"""✅ *PF Ejecutado: {pf_name}*

*Resultado:*
```
{result_str}
```"""

    await update.message.reply_text(text, parse_mode="Markdown")


async def harness_reset_cmd(update: Update, context: CallbackContext) -> None:
    """Handle /harness_reset - Reset harness statistics."""
    logger.incoming("/harness_reset")

    try:
        harness = get_harness()
        harness.reset_stats()
        await update.message.reply_text("✅ Estadísticas del harness reseteadas")
    except Exception as e:
        logger.error(f"Harness reset error: {e}")
        await update.message.reply_text(f"❌ Error reseteando: {e}")


def get_harness_handlers() -> dict[str, Any]:
    """Return dict of harness command handlers."""
    return {
        "harness": harness_cmd,
        "pfs": pfs_cmd,
        "pf_run": pf_run_cmd,
        "harness_reset": harness_reset_cmd,
    }
