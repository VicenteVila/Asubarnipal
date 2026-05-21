"""Vision command handlers."""

from telegram import Update
from telegram.ext import CallbackContext

from core.bot_logger import logger


async def vision_cmd(update: Update, context: CallbackContext) -> None:
    """Analyze an image with optional custom prompt."""
    args = context.args
    prompt = " ".join(args) if args else "Describe this image in detail."

    last_photo = context.user_data.get("last_photo")

    if not last_photo:
        await update.message.reply_text(
            "Analisis de imagenes\n\n"
            "Envia una foto primero, luego usa:\n"
            "`/vision [pregunta sobre la imagen]`\n\n"
            "Ejemplos:\n"
            "`/vision Que texto hay en esta imagen?`\n"
            "`/vision Cuantas personas hay?`\n"
            "`/vision` - Descripcion general"
        )
        return

    logger.incoming(f"/vision {prompt[:50]}")

    from core.vision import analyze_image

    await update.message.reply_text("Analizando imagen...")

    success, result = analyze_image(last_photo, prompt=prompt)

    if success:
        await update.message.reply_text(result[:4000])
    else:
        await update.message.reply_text(f"Error: {result}")


async def ocr_cmd(update: Update, context: CallbackContext) -> None:
    """Extract text from last received image."""
    last_photo = context.user_data.get("last_photo")

    if not last_photo:
        await update.message.reply_text(
            "Envia una foto primero, luego usa `/ocr` para extraer texto."
        )
        return

    logger.incoming("/ocr")

    from core.vision import extract_text_from_image

    await update.message.reply_text("Extrayendo texto...")

    success, result = extract_text_from_image(last_photo)

    if success:
        await update.message.reply_text(f"Texto extraido:\n\n{result}"[:4000])
    else:
        await update.message.reply_text(f"Error OCR: {result}")
