"""Validation commands for Telegram bot (/validar, /citas)."""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from telegram import Update
from telegram.ext import CallbackContext

from core.bot_logger import logger
from core.wiki.ingest_validator import IngestValidator, build_ingest_metadata
from core.wiki.citation_extractor import CitationExtractor
from core.wiki.citation_verifier import CitationVerifier


async def validar_cmd(update: Update, context: CallbackContext) -> None:
    """Validate the last ingested source against schemas, citations, and quality."""
    from core.wiki import Wiki

    logger.incoming("/validar")

    wiki = Wiki()
    last = wiki.get_last_source("all")
    if not last:
        await update.message.reply_text("❌ No hay fuentes ingeridas para validar.")
        return

    content = last.get("content", "")
    name = last.get("name", "unknown")
    fuente = last.get("fuente", "")

    await update.message.reply_text(
        f"🔍 *Validando:* {name[:60]}...\n⏳ Procesando...",
        parse_mode="Markdown",
    )

    content_type = _detect_content_type(last)
    metadata = build_ingest_metadata(content_type, {
        "name": name, "fuente": fuente,
        "url": fuente if content_type == "url" else "",
        "content_length": len(content),
    })

    validator = IngestValidator(use_crossref=False)
    result = validator.process(content_type, metadata, content=content)

    text = _format_validation_result(content_type, name, result)
    await update.message.reply_text(text, parse_mode="Markdown")
    logger.success(f"Validación completada para {name[:60]}: score={result.quality_score}")


async def citas_cmd(update: Update, context: CallbackContext) -> None:
    """Extract and verify citations from the last ingested source."""
    from core.wiki import Wiki

    logger.incoming("/citas")

    wiki = Wiki()
    last = wiki.get_last_source("all")
    if not last:
        await update.message.reply_text("❌ No hay fuentes ingeridas para extraer citas.")
        return

    content = last.get("content", "")
    name = last.get("name", "unknown")

    if not content or len(content) < 200:
        await update.message.reply_text("⚠️ El contenido de la última fuente es demasiado corto para extraer citas.")
        return

    await update.message.reply_text(
        f"🔍 *Extrayendo citas de:* {name[:60]}...\n⏳ Procesando...",
        parse_mode="Markdown",
    )

    extractor = CitationExtractor()
    citations = extractor.extract(content)

    if not citations:
        await update.message.reply_text(
            f"📋 *Citas en:* {name[:60]}\n\n"
            "No se encontraron citas en formato APA, MLA, Chicago, IEEE o inline.",
            parse_mode="Markdown",
        )
        return

    use_crossref = "--no-crossref" not in context.args
    verifier = CitationVerifier(use_crossref=use_crossref)
    results = verifier.verify_batch(citations[:15])

    lines = [f"📋 *Citas encontradas en:* {name[:60]}"]
    lines.append(f"\n*Total:* {len(citations)} | *Mostrando:* {min(len(results), 15)}")

    verified = sum(1 for r in results if r.verificado)
    lines.append(f"*Verificadas:* {verified}/{len(results)}\n")

    for i, vr in enumerate(results[:15], 1):
        c = vr.citation
        status = "✅" if vr.verificado else "❌"
        confidence = f" ({vr.score_confianza:.0%})" if vr.verificado else ""
        lines.append(f"{i}. {status} *[{c.formato}]* {c.texto_original[:120]}{confidence}")
        if vr.doi_encontrado:
            lines.append(f"   DOI: `{vr.doi_encontrado}`")

    if len(citations) > 15:
        lines.append(f"\n... y {len(citations) - 15} más.")

    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")
    logger.success(f"{len(citations)} citas extraídas de {name[:60]}, {verified} verificadas")


def _detect_content_type(last: dict) -> str:
    """Detect content type from last ingested source dict."""
    tipo = last.get("tipo", "")
    fuente = last.get("fuente", "")

    if tipo == "video":
        return "youtube"
    if tipo == "source" and ".pdf" in fuente.lower():
        return "pdf"
    if tipo == "source" and (fuente.startswith("http") or "youtube" not in fuente.lower()):
        return "url"
    return "url"


def _format_validation_result(content_type: str, name: str, result) -> str:
    """Format validation result as markdown text."""
    lines = [f"🔍 *Validación de ingesta:* {name[:60]}"]
    lines.append(f"📂 *Tipo:* {content_type}")
    lines.append(f"")

    schema_emoji = "✅" if result.schema_valid else "⚠️"
    lines.append(f"{schema_emoji} *Schema:* {'Válido' if result.schema_valid else 'Errores encontrados'}")
    if result.schema_errors:
        for err in result.schema_errors[:3]:
            lines.append(f"  • {err[:100]}")
        if len(result.schema_errors) > 3:
            lines.append(f"  ... y {len(result.schema_errors) - 3} más")

    lines.append(f"")
    lines.append(f"📊 *Score de calidad:* {result.quality_score:.0f}/100")
    if result.quality_factors:
        lines.append(f"*Factores:*")
        for factor, score in result.quality_factors.items():
            bar = _score_bar(score)
            lines.append(f"  {bar} {factor}: {score:.0f}")
    if result.quality_warnings:
        for w in result.quality_warnings[:3]:
            lines.append(f"  ⚠️ {w}")

    lines.append(f"")
    lines.append(f"📋 *Citas:* {result.citations_extracted} extraídas, {result.citations_verified} verificadas")
    if result.citations_extracted > 0:
        rate = result.citation_verification_rate * 100
        lines.append(f"  Tasa de verificación: {rate:.0f}%")

    return "\n".join(lines)


def _score_bar(score: float, width: int = 8) -> str:
    """Generate a text bar for a score value."""
    filled = max(0, min(width, int(score / 100 * width)))
    return "█" * filled + "░" * (width - filled)
