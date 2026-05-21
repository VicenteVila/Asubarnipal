"""Search commands handlers (/ingest, /investigar)."""

import re
from pathlib import Path

from telegram import Update
from telegram.ext import CallbackContext

from core.bot_logger import logger


def is_url(text: str) -> bool:
    """Check if text is a URL."""
    return bool(re.match(r'^https?://', text.strip()))

def is_local_path(text: str) -> bool:
    """Check if text looks like a local file path."""
    text = text.strip()
    if is_url(text):
        return False
    return (
        Path(text).exists() or
        re.match(r'^[A-Za-z]:[\\\/]', text) or
        text.startswith('/') or
        text.startswith('~')
    )

def extract_url_from_text(text: str) -> str:
    """Extract URL from text (in case it's wrapped in quotes or other chars)."""
    text = text.strip().strip('"\'')
    url_match = re.search(r'https?://[^\s<>"\']+', text)
    if url_match:
        return url_match.group(0)
    return text if is_url(text) else ""


async def ingest_cmd(update: Update, context: CallbackContext):
    """Ingest URL, local file, or Telegram document to wiki."""
    from core.wiki import Wiki

    text_input = " ".join(context.args) if context.args else ""

    if update.message.document:
        await _ingest_telegram_document(update, context)
        return

    if update.message.photo:
        await _ingest_telegram_photo(update, context)
        return

    if not text_input:
        await update.message.reply_text(
            "📥 *Ingesta de contenido*\n\n"
            "Usa:\n"
            "• `/ingest <URL>` - Página web o YouTube\n"
            "• `/ingest <ruta>` - Archivo local (PDF, TXT, imagen)\n"
            "• Adjunta un archivo y usa /ingest",
            parse_mode="Markdown"
        )
        return

    text_input = text_input.strip()

    if is_url(text_input):
        await _ingest_url(update, text_input)
    elif is_local_path(text_input):
        await _ingest_local_file(update, text_input)
    else:
        url = extract_url_from_text(text_input)
        if url and is_url(url):
            await _ingest_url(update, url)
        else:
            await update.message.reply_text(
                "❌ No se pudo identificar el tipo de entrada.\n"
                "Usa una URL (http://...) o una ruta de archivo válida."
            )


async def _ingest_url(update: Update, url: str):
    """Ingest a URL."""
    from core.wiki import Wiki

    url = url.strip()
    logger.incoming(f"/ingest URL: {url[:80]}")

    is_youtube = "youtube.com" in url or "youtu.be" in url
    await update.message.reply_text(
        f"📥 Procesando URL...\n"
        f"{'🎬 Video de YouTube detectado' if is_youtube else '🌐 Página web'}\n"
        f"⏳ Esto puede tardar unos segundos..."
    )

    try:
        wiki = Wiki()
        result = wiki.ingest_url_smart(url)

        if result.get("success"):
            name = result.get("name", "Sin título")
            lang = result.get("language_detected", "?")
            translated = " (traducido)" if result.get("was_translated") else ""
            concepts = result.get("concepts_count", 0)
            summary = result.get("summary", "")

            parts = [f"✅ *Ingesta completada*\n\n📄 *{name}*"]

            if is_youtube:
                has_transcript = result.get("has_transcript", False)
                metadata = result.get("metadata", {})
                views = metadata.get("views", 0)
                duration = metadata.get("duration", 0)
                uploader = metadata.get("uploader", "")
                
                dur_min = duration // 60 if duration else 0
                dur_sec = duration % 60 if duration else 0
                dur_str = f"{dur_min}:{str(dur_sec).zfill(2)}"

                parts.append(f"🎬 *YouTube Video*")
                parts.append(f"• Transcript: {'✅' if has_transcript else '❌'}")
                parts.append(f"• Duración: {dur_str}")
                parts.append(f"• Vistas: {views:,}")
                parts.append(f"• Autor: {uploader}")
            else:
                parts.append(f"🌐 Idioma: `{lang}`{translated}")

            parts.append(f"\n📊 *Estadísticas:*")
            parts.append(f"• Conceptos: {concepts}")

            if is_youtube and result.get("has_transcript"):
                parts.append(f"• Transcript: ✅ extraído")

            if summary:
                parts.append(f"\n📝 *Resumen:*\n{summary[:400]}...")

            if result.get("concepts"):
                parts.append(f"\n🔗 *Conceptos:*\n{', '.join(result.get('concepts', [])[:8])}")

            logger.success(f"Ingest URL completo: {name}")
            await update.message.reply_text("\n".join(parts), parse_mode="Markdown")

        else:
            error = result.get("error", "Error desconocido")
            logger.error(f"Ingest URL falló: {error}")
            await update.message.reply_text(f"❌ Error: {error}")

    except Exception as e:
        logger.error(f"Ingest URL exception: {e}")
        await update.message.reply_text(f"❌ Error inesperado: {str(e)}")


async def _ingest_local_file(update: Update, file_path: str):
    """Ingest a local file."""
    from core.wiki import Wiki

    file_path = file_path.strip()
    path = Path(file_path)

    if not path.exists():
        await update.message.reply_text(f"❌ Archivo no encontrado: {file_path}")
        return

    logger.incoming(f"/ingest file: {file_path}")

    ext = path.suffix.lower()
    ext_names = {
        ".pdf": "PDF",
        ".txt": "texto",
        ".md": "markdown",
        ".png": "imagen PNG",
        ".jpg": "imagen JPG",
        ".jpeg": "imagen JPEG",
    }
    type_name = ext_names.get(ext, ext)

    await update.message.reply_text(
        f"📄 Procesando archivo {type_name}...\n"
        f"📁 `{path.name}`\n"
        f"⏳ {'Extrayendo texto con OCR' if ext in ['.pdf', '.png', '.jpg', '.jpeg'] else 'Procesando'}..."
    )

    try:
        wiki = Wiki()

        if ext == ".pdf":
            result = wiki.ingest_pdf(str(path))
        elif ext in [".png", ".jpg", ".jpeg"]:
            result = wiki.ingest_image(str(path))
        else:
            result = wiki.ingest_file(str(path))

        if result.get("success"):
            name = result.get("name", path.stem)
            content_len = len(result.get("content", "")) if isinstance(result.get("content"), str) else 0

            parts = [
                f"✅ *Archivo ingestado*\n\n📄 *{name}*",
                f"• Tipo: {type_name}",
                f"• Caracteres extraídos: {content_len:,}",
            ]

            if ext == ".pdf":
                pages = result.get("pages_processed", "?")
                digital_pages = result.get("digital_pages", 0)
                ocr_pages = result.get("ocr_pages", [])
                parts.append(f"• Páginas: {pages} total, {digital_pages} digital, {len(ocr_pages)} OCR")
                if ocr_pages:
                    # Show page ranges for OCR
                    if len(ocr_pages) <= 10:
                        parts.append(f"• Páginas OCR: {ocr_pages}")
                    else:
                        # Show ranges
                        ranges = []
                        start = ocr_pages[0]
                        end = ocr_pages[0]
                        for p in ocr_pages[1:]:
                            if p == end + 1:
                                end = p
                            else:
                                ranges.append(f"{start}-{end}" if start != end else str(start))
                                start = end = p
                        ranges.append(f"{start}-{end}" if start != end else str(start))
                        parts.append(f"• Páginas OCR: {', '.join(ranges)}")

            logger.success(f"Ingest file completo: {name}")
            await update.message.reply_text("\n".join(parts), parse_mode="Markdown")

        else:
            error = result.get("error", "Error desconocido")
            logger.error(f"Ingest file falló: {error}")
            await update.message.reply_text(f"❌ Error: {error}")

    except Exception as e:
        logger.error(f"Ingest file exception: {e}")
        await update.message.reply_text(f"❌ Error inesperado: {str(e)}")


async def _ingest_telegram_document(update: Update, context: CallbackContext):
    """Ingest a document sent via Telegram."""
    from core.wiki import Wiki
    import config

    doc = update.message.document
    file_name = doc.file_name or "documento"
    mime_type = doc.mime_type or ""

    logger.incoming(f"/ingest Telegram doc: {file_name} ({mime_type})")

    await update.message.reply_text(
        f"📎 Descargando documento...\n"
        f"📄 `{file_name}`\n"
        f"⏳ Procesando..."
    )

    try:
        logger.info(f"Ingest doc: Step 1 - Getting file from Telegram...")
        bot = context.bot
        file = await bot.get_file(doc.file_id)

        config.TEMP_DIR.mkdir(exist_ok=True, parents=True)
        temp_path = config.TEMP_DIR / file_name

        logger.info(f"Ingest doc: Step 2 - Downloading to {temp_path}...")
        await file.download_to_drive(str(temp_path))
        logger.info(f"Ingest doc: Step 2 complete - File downloaded: {temp_path.stat().st_size} bytes")

        logger.info(f"Ingest doc: Step 3 - Initializing Wiki...")
        wiki = Wiki()
        logger.info(f"Ingest doc: Step 3 complete - Wiki initialized")

        if mime_type == "application/pdf" or file_name.lower().endswith(".pdf"):
            force_ocr = "ocr" in (update.message.caption or "").lower()
            logger.info(f"Ingest doc: Step 4 - Starting PDF ingestion (force_ocr={force_ocr})...")
            result = wiki.ingest_pdf(str(temp_path), force_ocr=force_ocr)
            logger.info(f"Ingest doc: Step 4 complete - PDF ingestion done")
        else:
            logger.info(f"Ingest doc: Step 4 - Starting file ingestion...")
            result = wiki.ingest_file(str(temp_path))
            logger.info(f"Ingest doc: Step 4 complete - File ingestion done")

        try:
            temp_path.unlink()
        except:
            pass

        if result.get("success"):
            name = result.get("name", file_name)
            parts = [
                f"✅ *Documento ingestado*\n\n📄 *{name}*",
                f"• Tipo: {mime_type or 'desconocido'}",
                f"• Páginas: {result.get('pages_processed', '?')}",
            ]

            if result.get("has_ocr"):
                ocr_pages = result.get("ocr_pages", [])
                parts.append(f"• OCR: ✅ ({len(ocr_pages)} páginas)")
            
            content_len = result.get("content_length", 0)
            if content_len > 0:
                parts.append(f"• Contenido: {content_len:,} caracteres")
            
            if result.get("truncated"):
                parts.append(f"⚠️ Truncado a 150k caracteres")

            await update.message.reply_text("\n".join(parts), parse_mode="Markdown")
            logger.success(f"Ingest Telegram doc completo: {file_name}")
        else:
            await update.message.reply_text(f"❌ Error: {result.get('error')}")

    except Exception as e:
        logger.error(f"Ingest Telegram doc exception: {e}")
        await update.message.reply_text(f"❌ Error: {str(e)}")


async def _ingest_telegram_photo(update: Update, context: CallbackContext):
    """Ingest a photo sent via Telegram using OCR."""
    from core.wiki import Wiki
    import config

    photo = update.message.photo[-1]

    logger.incoming("/ingest Telegram photo")

    await update.message.reply_text("🖼️ Procesando imagen con OCR...\n⏳ Extrayendo texto...")

    try:
        bot = context.bot
        file = await bot.get_file(photo.file_id)

        config.TEMP_DIR.mkdir(exist_ok=True, parents=True)
        temp_path = config.TEMP_DIR / f"photo_{photo.file_id}.jpg"

        await file.download_to_drive(str(temp_path))

        wiki = Wiki()
        result = wiki.ingest_image(str(temp_path))

        try:
            temp_path.unlink()
        except:
            pass

        if result.get("success"):
            name = result.get("name", f"Imagen_{photo.file_id}")
            text_len = len(result.get("content", "")) if isinstance(result.get("content"), str) else 0
            await update.message.reply_text(
                f"✅ *Imagen procesada*\n\n📄 *{name}*\n• Caracteres extraídos: {text_len}",
                parse_mode="Markdown"
            )
            logger.success(f"Ingest photo completo")
        else:
            await update.message.reply_text(f"❌ OCR falló: {result.get('error')}")

    except Exception as e:
        logger.error(f"Ingest photo exception: {e}")
        await update.message.reply_text(f"❌ Error: {str(e)}")


async def investigar_cmd(update: Update, context: CallbackContext):
    """Research a topic deeply."""
    topic = " ".join(context.args)

    if not topic:
        await update.message.reply_text("Usa: /investigar <tema>")
        return

    valid, error_msg = _validate_topic(topic)
    if not valid:
        logger.warn(f"Investigar topic inválido: {error_msg}")
        await update.message.reply_text(f"❌ Tema inválido: {error_msg}")
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
        logger.error(f"Investigar exception: {e}")
        await update.message.reply_text(f"❌ Error inesperado durante investigación")


def _validate_topic(topic: str) -> tuple:
    """Validate research topic."""
    if not topic or len(topic.strip()) < 2:
        return False, "Tema demasiado corto"
    if len(topic) > 200:
        return False, "Tema demasiado largo (máx 200 caracteres)"
    return True, ""


def _validate_url(url: str) -> tuple:
    """Validate URL."""
    if not url:
        return False, "URL vacía"
    url = url.strip()
    if not url.startswith(("http://", "https://")):
        return False, "Debe empezar con http:// o https://"
    return True, ""