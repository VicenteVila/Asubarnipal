"""Scheduled research command handlers."""

from telegram import Update
from telegram.ext import CallbackContext

from core.bot_logger import logger
from core.research_scheduler import get_scheduler


async def schedule_research_cmd(update: Update, context: CallbackContext) -> None:
    """Schedule a recurring research task."""
    args = context.args

    if not args:
        await update.message.reply_text(
            "*Investigacion programada*\n\n"
            "Usa: /schedule <tema> [minutos]\n\n"
            "Ejemplos:\n"
            "`/schedule noticias IA 60` - Cada hora\n"
            "`/schedule avances LLM 1440` - Diario"
        )
        return

    minutes = 60
    topic_parts = []

    for arg in args:
        if arg.isdigit():
            minutes = int(arg)
        else:
            topic_parts.append(arg)

    topic = " ".join(topic_parts)

    if not topic:
        await update.message.reply_text("Error: Indica un tema para investigar")
        return

    if minutes < 15:
        await update.message.reply_text("Error: Intervalo minimo 15 minutos")
        return

    scheduler = get_scheduler()
    schedule = scheduler.add_schedule(
        topic=topic,
        interval_minutes=minutes,
        user_id=update.effective_user.id,
    )

    await update.message.reply_text(
        f"Investigacion programada\n\n"
        f"Tema: {topic}\n"
        f"Intervalo: cada {minutes} minutos\n"
        f"ID: {schedule['id']}\n\n"
        f"Usa /schedules para ver todas"
    )


async def list_schedules_cmd(update: Update, context: CallbackContext) -> None:
    """List all scheduled research tasks."""
    scheduler = get_scheduler()
    schedules = scheduler.list_schedules()

    if not schedules:
        await update.message.reply_text("No hay investigaciones programadas")
        return

    text = "Investigaciones programadas\n\n"
    for s in schedules:
        status = "Activa" if s.get("active", True) else "Pausada"
        last = s.get("last_run", "Nunca")
        text += f"ID {s['id']}: {s['topic']}\n"
        text += f"   Cada {s['interval_minutes']}min | Ejecuciones: {s.get('run_count', 0)}\n"
        text += f"   Ultima: {last[:19] if last != 'Nunca' else last} | {status}\n\n"

    text += "Usa /cancel_schedule <ID> para cancelar"

    await update.message.reply_text(text)


async def cancel_schedule_cmd(update: Update, context: CallbackContext) -> None:
    """Cancel a scheduled research task."""
    args = context.args

    if not args or not args[0].isdigit():
        await update.message.reply_text("Usa: /cancel_schedule <ID>")
        return

    schedule_id = int(args[0])
    scheduler = get_scheduler()

    if scheduler.remove_schedule(schedule_id):
        await update.message.reply_text(f"Programa {schedule_id} cancelado")
    else:
        await update.message.reply_text(f"Programa {schedule_id} no encontrado")


async def toggle_schedule_cmd(update: Update, context: CallbackContext) -> None:
    """Toggle a scheduled research task on/off."""
    args = context.args

    if not args or not args[0].isdigit():
        await update.message.reply_text("Usa: /toggle_schedule <ID>")
        return

    schedule_id = int(args[0])
    scheduler = get_scheduler()
    schedule = scheduler.toggle_schedule(schedule_id)

    if schedule:
        status = "activada" if schedule.get("active", True) else "pausada"
        await update.message.reply_text(f"Programa {schedule_id} {status}: {schedule['topic']}")
    else:
        await update.message.reply_text(f"Programa {schedule_id} no encontrado")
