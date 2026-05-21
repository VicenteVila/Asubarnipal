"""Wiki ingest module - URL, YouTube, PDF, OCR, and file ingestion."""

import json
import logging
import re
import time
from datetime import datetime
from pathlib import Path

import config

logger = logging.getLogger(__name__)


class WikiIngestMixin:
    """Mixin class with all ingestion methods for the Wiki class."""

    def ingest_url(self, url: str) -> dict:
        """Ingest content from URL (legacy simple version)."""
        import requests
        from bs4 import BeautifulSoup

        try:
            resp = requests.get(url, timeout=30)
            soup = BeautifulSoup(resp.text, "html.parser")

            title = soup.title.string if soup.title else url
            text = soup.get_text()[:20000]

            return self.add_entity(
                name=title, content=text, tipo="source", fuente=url, estado="final"
            )
        except Exception as e:
            return {"error": str(e)}

    def _is_youtube_url(self, url: str) -> bool:
        """Check if URL is a YouTube video."""
        return "youtube.com" in url or "youtu.be" in url

    def _check_node_js(self) -> tuple:
        """Check if Node.js is available. Returns (available, path)."""
        import os
        import shutil
        import subprocess

        node_path = shutil.which('node')
        if node_path:
            try:
                result = subprocess.run(['node', '--version'],
                                       capture_output=True, text=True, timeout=5)
                if result.returncode == 0:
                    return True, node_path
            except Exception:
                pass

        if os.name == 'nt':
            program_files = os.environ.get('ProgramFiles', 'C:\\Program Files')
            node_paths = [
                os.path.join(program_files, 'nodejs', 'node.exe'),
                os.path.join(os.environ.get('LOCALAPPDATA', ''), 'Programs', 'nodejs', 'node.exe'),
                r"C:\Program Files\nodejs\node.exe",
            ]
            for path in node_paths:
                if os.path.exists(path):
                    os.environ['PATH'] = os.path.dirname(path) + ';' + os.environ.get('PATH', '')
                    return True, path

        return False, None

    def _extract_video_id(self, url: str) -> str:
        """Extract YouTube video ID from various URL formats."""
        import urllib.parse
        parsed = urllib.parse.urlparse(url)
        if "youtube.com" in parsed.hostname or "www.youtube.com" in parsed.hostname:
            qs = urllib.parse.parse_qs(parsed.query)
            return qs.get("v", [None])[0]
        elif "youtu.be" in parsed.hostname:
            return parsed.path.lstrip("/").split("?")[0]
        return None

    def _extract_youtube_transcript(self, video_url: str) -> tuple:
        """Extract transcript from YouTube video. Returns (transcript, metadata)."""
        transcript = ""
        metadata = {}

        video_id = self._extract_video_id(video_url)
        if video_id:
            try:
                from youtube_transcript_api import YouTubeTranscriptApi
                logger.info(f"Trying youtube-transcript-api for {video_id}...")

                ytt = YouTubeTranscriptApi()
                fetched = ytt.fetch(video_id, languages=["es", "en"])
                snippets = list(fetched)

                if snippets:
                    lines = []
                    for s in snippets:
                        start = s.get("start", 0) if isinstance(s, dict) else getattr(s, "start", 0)
                        text = s.get("text", "").strip() if isinstance(s, dict) else getattr(s, "text", "").strip()
                        if text:
                            minutes = int(start // 60)
                            seconds = int(start % 60)
                            lines.append(f"[{minutes:02d}:{seconds:02d}] {text}")
                    transcript = "\n".join(lines)
                    logger.info(f"youtube-transcript-api OK: {len(transcript)} chars")
            except Exception as e:
                logger.warning(f"youtube-transcript-api failed: {e}")

        if not transcript:
            try:
                import yt_dlp
                logger.info("Falling back to yt-dlp for transcript...")

                node_available, node_path = self._check_node_js()

                ydl_opts = {
                    'writesubtitles': True, 'writeautomaticsub': True,
                    'subtitleslangs': ['es', 'en', 'en-US', 'en-GB'],
                    'skip_download': True, 'quiet': True,
                }
                if node_available:
                    ydl_opts['js_runtimes'] = {'node': {}}

                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(video_url, download=False)

                metadata = {
                    'title': info.get('title', ''), 'description': info.get('description', '')[:2000],
                    'duration': info.get('duration', 0), 'view_count': info.get('view_count', 0),
                    'uploader': info.get('uploader', ''), 'upload_date': info.get('upload_date', ''),
                    'thumbnail': info.get('thumbnail', ''),
                }

                subtitle_langs = ['es', 'es-ES', 'es-419', 'en', 'en-US', 'en-GB']
                subs_dict = info.get('subtitles', {})
                auto_dict = info.get('automatic_captions', {})
                chosen_subs = None

                for lang in subtitle_langs:
                    if subs_dict.get(lang):
                        chosen_subs = subs_dict[lang]
                        break
                if not chosen_subs:
                    for lang in subtitle_langs:
                        if auto_dict.get(lang):
                            chosen_subs = auto_dict[lang]
                            break
                if not chosen_subs and auto_dict:
                    first_lang = next(iter(auto_dict.keys()))
                    chosen_subs = auto_dict[first_lang]

                if chosen_subs:
                    import requests as req
                    for fmt_entry in chosen_subs[:3]:
                        sub_url = fmt_entry.get('url', '')
                        if not sub_url:
                            continue
                        for attempt in range(3):
                            try:
                                if attempt > 0:
                                    time.sleep(3 ** attempt)
                                resp = req.get(sub_url, timeout=20, headers={'User-Agent': 'Mozilla/5.0'})
                                if resp.ok:
                                    if 'vtt' in resp.headers.get('Content-Type', '').lower() or sub_url.endswith('.vtt'):
                                        texts = self._parse_vtt_content(resp.text)
                                    else:
                                        texts = self._parse_srt_content(resp.text)
                                    if texts:
                                        transcript = "\n".join(texts)
                                        logger.info(f"yt-dlp transcript OK: {len(transcript)} chars")
                                        break
                                elif resp.status_code == 429:
                                    time.sleep(10)
                            except Exception as e:
                                logger.warning(f"Subtitle download error: {e}")
                        if transcript:
                            break
                else:
                    logger.warning("yt-dlp: no subtitles available")

            except ImportError:
                logger.warning("yt-dlp not installed")
            except Exception as e:
                logger.warning(f"yt-dlp transcript extraction failed: {e}")

        if not metadata:
            metadata = self._extract_youtube_metadata(video_url)

        return transcript, metadata

    def _extract_youtube_metadata(self, url: str) -> dict:
        """Extract enhanced metadata from YouTube URL."""
        try:
            import yt_dlp
            ydl_opts = {'quiet': True, 'skip_download': True}
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
            return {
                'title': info.get('title', ''), 'description': info.get('description', ''),
                'duration': info.get('duration', 0), 'view_count': info.get('view_count', 0),
                'uploader': info.get('uploader', ''), 'upload_date': info.get('upload_date', ''),
                'tags': info.get('tags', [])[:20], 'category': info.get('categories', [''])[0],
                'thumbnail': info.get('thumbnail', ''),
            }
        except Exception as e:
            logger.warning(f"YouTube metadata extraction failed: {e}")
            return {}

    def _parse_vtt_content(self, content: str) -> list:
        """Parse WebVTT subtitle format."""
        texts = []
        current_start = 0
        current_text = []

        for line in content.split('\n'):
            line = line.strip()
            if '-->' in line:
                try:
                    start_str = line.split('-->')[0].strip()
                    parts = start_str.split(':')
                    if len(parts) >= 2:
                        minutes = int(parts[-2])
                        seconds_parts = parts[-1].split('.')
                        seconds = int(seconds_parts[0])
                        current_start = minutes * 60 + seconds
                except Exception:
                    pass
                continue
            if line and not line.startswith('WEBVTT') and not line.startswith('NOTE'):
                if line.startswith('<'):
                    continue
                clean_text = re.sub(r'<[^>]+>', '', line)
                if clean_text.strip():
                    current_text.append(clean_text.strip())
            elif current_text:
                texts.append(f"[{int(current_start // 60):02d}:{int(current_start % 60):02d}] {' '.join(current_text)}")
                current_text = []

        if current_text:
            texts.append(f"[{int(current_start // 60):02d}:{int(current_start % 60):02d}] {' '.join(current_text)}")

        return texts

    def _parse_srt_content(self, content: str) -> list:
        """Parse SRT subtitle format."""
        from bs4 import BeautifulSoup
        texts = []
        soup = BeautifulSoup(content, 'html.parser')

        for seg in soup.find_all('text'):
            text = seg.get_text(strip=True)
            if text:
                try:
                    start = float(seg.get('start', 0))
                    texts.append(f"[{int(start // 60):02d}:{int(start % 60):02d}] {text}")
                except Exception:
                    texts.append(text)

        if not texts:
            for line in content.split('\n'):
                line = line.strip()
                if '-->' in line or line.isdigit():
                    continue
                elif line:
                    texts.append(line)

        return texts

    def _ingest_youtube(self, url: str, translate_to: str, activity) -> dict:
        """Special ingestion for YouTube videos."""
        try:
            activity.ingest_step("Extrayendo metadata", 10)
            metadata = self._extract_youtube_metadata(url)

            activity.ingest_step("Extrayendo transcript", 30)
            transcript, _ = self._extract_youtube_transcript(url)

            title = metadata.get('title', url)
            description = metadata.get('description', '')
            uploader = metadata.get('uploader', '')
            duration = metadata.get('duration', 0)
            views = metadata.get('view_count', 0)
            upload_date = metadata.get('upload_date', '')
            tags = metadata.get('tags', [])

            activity.ingest_step("Procesando contenido", 50)

            if transcript:
                content_to_process = f"TRANSCRIPCION DEL VIDEO:\n{transcript}"
            else:
                content_to_process = f"DESCRIPCION:\n{description}" if description else ""

            if not content_to_process:
                return {"error": "No se pudo extraer contenido del video"}

            activity.ingest_step("Detectando idioma", 60)
            lang = self._detect_language(content_to_process)
            logger.info(f"Detected language: {lang}, target: {translate_to}")

            translated_content = content_to_process
            was_translated = False
            if lang != translate_to and lang != "unknown":
                activity.ingest_step("Traduciendo", 70)
                translated_content, was_translated = self._translate_text(content_to_process, target=translate_to)

            activity.ingest_step("Generando resumen", 75)
            summary = self._generate_summary(translated_content[:8000])

            activity.ingest_step("Extrayendo conceptos", 80)
            concepts = self._extract_concepts(translated_content[:8000])
            if tags:
                concepts.extend([t for t in tags[:5] if t not in concepts])

            activity.ingest_step("Guardando en wiki", 90)

            dur_min = duration // 60 if duration else 0
            dur_sec = duration % 60 if duration else 0

            content_full = f"""# {title}

**Duracion:** {dur_min}:{str(dur_sec).zfill(2)} | **Visitas:** {views:,}
**Autor:** {uploader} | **Fecha:** {upload_date or 'N/A'}

## Transcripcion
{translated_content[:25000]}

## Metadatos
- **Tags:** {', '.join(tags[:15]) if tags else 'N/A'}
- **Descripcion:** {description[:1000] if description else 'N/A'}
"""

            entity_tags = concepts[:10] + ["youtube", "video"]

            self.add_entity(
                name=title, content=content_full, tipo="video", fuente=url,
                estado="final", tags=entity_tags, relacionados=[]
            )

            self.save_to_obsidian(
                name=title, content=content_full, tipo="video", fuente=url,
                tags=entity_tags, relacionados=[]
            )

            for concept in concepts[:6]:
                clean = concept.strip()[:100]
                if clean and len(clean) > 2:
                    self.add_entity(
                        name=clean, content=f"Concepto del video: {title}",
                        tipo="concept", fuente=url, estado="final",
                        tags=["auto-generated", "youtube"]
                    )

            result = {
                "success": True, "name": title, "language_detected": lang,
                "was_translated": was_translated, "has_transcript": bool(transcript),
                "summary": summary, "concepts_count": len(concepts[:6]),
                "concepts": concepts[:5],
                "metadata": {"duration": duration, "views": views, "uploader": uploader, "upload_date": upload_date},
                "obsidian_saved": True,
            }

            quality_info = self.track_ingest_quality("youtube", title, {
                "content_length": len(translated_content), "duration_seconds": duration,
                "transcript_chars": len(transcript) if transcript else 0,
                "concepts_found": len(concepts)
            })
            result["quality_score"] = quality_info["quality_score"]
            result["quality_alerts"] = quality_info.get("alerts", [])

            activity.ingest_complete(success=True, details=f"{len(concepts)} conceptos, transcript={bool(transcript)}, quality={quality_info['quality_score']}")
            return result

        except Exception as e:
            activity.ingest_complete(success=False, details=str(e))
            logger.error(f"YouTube ingest error: {e}")
            return {"error": str(e)}

    def ingest_url_smart(self, url: str, translate_to: str = "es") -> dict:
        """Smart URL ingestion with content extraction, language detection, translation, summary, concepts."""
        import requests
        from bs4 import BeautifulSoup
        from core.live_activity import get_tracker

        activity = get_tracker()
        activity.ingest_start(url)

        if self._is_youtube_url(url):
            return self._ingest_youtube(url, translate_to, activity)

        try:
            activity.ingest_step("Descargando", 10)
            resp = requests.get(url, timeout=30, headers={"User-Agent": "Mozilla/5.0 (compatible; Asubarnipal/1.0)"})

            if not resp.ok:
                activity.ingest_complete(success=False, details=f"HTTP {resp.status_code}")
                return {"error": f"HTTP {resp.status_code}"}

            activity.ingest_step("Limpiando HTML", 20)
            soup = BeautifulSoup(resp.text, "html.parser")
            title = soup.title.string.strip() if soup.title else url

            for tag in soup(["script", "style", "nav", "footer", "header", "aside", "noscript", "iframe", "form", "button"]):
                tag.decompose()

            activity.ingest_step("Extrayendo texto", 30)
            main_content = soup.get_text(separator=" ", strip=True)
            main_content = re.sub(r'\s+', ' ', main_content)[:30000]

            activity.ingest_step("Detectando idioma", 40)
            lang = self._detect_language(main_content)

            translated_content = main_content
            was_translated = False
            if lang != translate_to:
                activity.ingest_step("Traduciendo", 50)
                translated_content, was_translated = self._translate_text(main_content, target=translate_to)

            activity.ingest_step("Generando resumen", 60)
            summary = self._generate_summary(translated_content[:8000])

            activity.ingest_step("Extrayendo conceptos", 70)
            concepts = self._extract_concepts(translated_content[:5000])

            activity.ingest_step("Buscando relacionados", 80)
            related = self._find_related_notes(concepts[:5])

            activity.ingest_step("Creando entidades", 85)
            concept_entities = []
            for concept in concepts[:8]:
                clean_concept = concept.strip()[:100]
                if clean_concept and len(clean_concept) > 2:
                    self.add_entity(
                        name=clean_concept, content=f"Concepto extraido de: {title}",
                        tipo="concept", fuente=url, estado="final",
                        tags=["auto-generated", "from-ingest"]
                    )
                    concept_entities.append(clean_concept)
                    self.save_to_obsidian(
                        name=clean_concept, content=f"Concepto extraido de: {title}",
                        tipo="concept", fuente=url, tags=["auto-generated", "from-ingest"]
                    )

            activity.ingest_step("Guardando fuente", 90)
            relacionados = [{"name": rel["name"], "relation": "related"} for rel in related]

            self.add_entity(
                name=title, content=translated_content[:30000], tipo="source", fuente=url,
                estado="final", tags=concepts[:10], relacionados=relacionados
            )

            activity.ingest_step("Guardando en Obsidian", 92)
            obsidian_result = self.save_to_obsidian(
                name=title, content=translated_content[:30000], tipo="source", fuente=url,
                tags=concepts[:10], relacionados=[r["name"] for r in related[:10]]
            )

            result = {
                "success": True, "name": title, "language_detected": lang,
                "was_translated": was_translated, "summary": summary,
                "concepts_count": len(concept_entities), "related_count": len(related),
                "concepts": concept_entities[:5],
                "obsidian_saved": obsidian_result.get("success", False),
                "obsidian_path": obsidian_result.get("path", ""),
                "content_length": len(translated_content), "html_length": len(resp.text),
            }

            quality_info = self.track_ingest_quality("url", title, {
                "content_length": len(translated_content), "html_length": len(resp.text),
                "concepts_found": len(concept_entities)
            })
            result["quality_score"] = quality_info["quality_score"]
            result["quality_alerts"] = quality_info.get("alerts", [])

            activity.ingest_complete(success=True, details=f"{len(concept_entities)} conceptos, quality={quality_info['quality_score']}")
            return result

        except Exception as e:
            activity.ingest_complete(success=False, details=str(e))
            logger.error(f"Smart ingest error: {e}")
            return {"error": str(e)}

    def _detect_language(self, text: str) -> str:
        """Detect language using simple heuristics."""
        if not text or len(text) < 100:
            return "unknown"

        sample = text[:1000].lower()
        spanish_indicators = ["el", "la", "los", "las", "es", "son", "de", "que", "en", "un", "una", "por", "con", "para", "como", "esta", "pero", "porque", "este", "tiene", "hace", "solo", "mas", "bien", "ahora", "cuando", "asi"]
        english_indicators = ["the", "a", "an", "is", "are", "of", "in", "to", "for", "with", "on", "at", "by", "from", "this", "that", "have", "has", "will", "would", "could", "should", "just", "like", "get", "one"]

        es_count = sum(1 for w in spanish_indicators if f" {w} " in f" {sample} ")
        en_count = sum(1 for w in english_indicators if f" {w} " in f" {sample} ")

        if es_count >= 2 and es_count >= en_count:
            return "es"
        elif en_count >= 2 and en_count >= es_count:
            return "en"
        elif es_count > en_count:
            return "es"
        elif en_count > 0:
            return "en"
        return "unknown"

    def _translate_text(self, text: str, target: str = "es") -> tuple:
        """Translate text using deep-translator (with chunking for long texts)."""
        try:
            from deep_translator import GoogleTranslator

            max_chunk = 4500
            if len(text) <= max_chunk:
                translator = GoogleTranslator(source="auto", target=target)
                return translator.translate(text), True

            chunks = []
            lines = text.split('\n')
            current_chunk = ""

            for line in lines:
                if len(current_chunk) + len(line) + 1 > max_chunk:
                    if current_chunk:
                        chunks.append(current_chunk)
                    current_chunk = line
                else:
                    current_chunk += "\n" + line if current_chunk else line

            if current_chunk:
                chunks.append(current_chunk)

            logger.info(f"Translating {len(chunks)} chunks...")
            translated_chunks = []
            for i, chunk in enumerate(chunks):
                translator = GoogleTranslator(source="auto", target=target)
                translated_chunks.append(translator.translate(chunk))
                if i < len(chunks) - 1:
                    time.sleep(0.5)

            return "\n".join(translated_chunks), True

        except ImportError:
            logger.info("deep-translator not installed, skipping translation")
            return text, False
        except Exception as e:
            logger.warning(f"Translation failed: {e}, returning original")
            return text, False

    def _generate_summary(self, text: str) -> str:
        """Generate summary using LLM."""
        try:
            from core.llm_router import LLMRouter
            llm = LLMRouter()
            prompt = f"""Resume el siguiente texto en 3-5 lineas concisas, capturando los puntos principales:

{text[:5000]}

RESUMEN:"""
            result = llm.generate(prompt)
            return result[:500] if result else "Resumen no disponible"
        except Exception as e:
            logger.warning(f"Summary generation failed: {e}")
            return "Resumen no disponible"

    def _extract_concepts(self, text: str) -> list:
        """Extract key concepts using LLM."""
        try:
            from core.llm_router import LLMRouter
            llm = LLMRouter()
            prompt = f"""Extrae 10-15 conceptos clave del siguiente texto.
Los conceptos deben ser los mas importantes y relevantes del texto.
Devuelve SOLO los conceptos separados por comas (sin numeros, sin explicaciones):

{text[:6000]}

CONCEPTOS:"""
            result = llm.generate(prompt)
            if result:
                concepts = [c.strip() for c in result.split(",") if c.strip()]
                return concepts[:15]
            return []
        except Exception as e:
            logger.warning(f"Concept extraction failed: {e}")
            return []

    def _find_related_notes(self, concepts: list) -> list:
        """Find existing wiki notes related to concepts."""
        related = []
        for concept in concepts:
            results = self.search(concept, limit=3)
            for r in results:
                if r["name"] not in [rel["name"] for rel in related]:
                    related.append({"name": r["name"], "tipo": r.get("tipo", "unknown")})
                    if len(related) >= 10:
                        break
        return related

    def _check_ocr_model_available(self) -> bool:
        """Verify that the configured OCR model is loaded in Ollama."""
        import requests as _req
        try:
            resp = _req.get(f"{config.OLLAMA_BASE_URL}/api/tags", timeout=5)
            if not resp.ok:
                return False
            models = [m["name"] for m in resp.json().get("models", [])]
            ocr_model = config.OCR_MODEL
            return any(
                m == ocr_model or m.startswith(ocr_model.split(":")[0])
                for m in models
            )
        except Exception as e:
            logger.warning(f"Could not contact Ollama to check OCR model: {e}")
            return False

    def extract_with_ocr(self, file_path: str, max_retries: int = 2) -> str:
        """Extract text from image using Ollama vision model."""
        from ollama import Client

        ocr_model = config.OCR_MODEL
        if not self._check_ocr_model_available():
            logger.error(f"OCR model '{ocr_model}' is not available. Run: ollama pull {ocr_model}")
            return ""

        client = Client(config.OLLAMA_BASE_URL)

        try:
            with open(file_path, "rb") as f:
                img_bytes = f.read()
        except Exception as e:
            logger.error(f"Cannot read image file: {e}")
            return ""

        prompts = [
            "Eres un OCR especializado. Extrae TODO el texto de esta imagen. Mantén la estructura y párrafos. Devuelve solo el texto EXTRAÍDO, sin comentarios.",
            "Extract ALL text visible in this image. Preserve structure and formatting. Output only the extracted text.",
        ]

        for prompt_text in prompts:
            for attempt in range(max_retries):
                try:
                    logger.info(f"OCR attempt {attempt + 1} using '{ocr_model}'...")
                    resp = client.chat(
                        model=ocr_model,
                        messages=[{"role": "user", "content": prompt_text, "images": [img_bytes]}],
                        options={"num_ctx": 8192},
                    )
                    text = resp.message.content.strip()
                    if text and len(text) > 10:
                        logger.info(f"OCR success: {len(text)} chars from {Path(file_path).name}")
                        return text
                    else:
                        logger.warning(f"OCR returned empty or too short: {len(text)} chars")
                except Exception as ocr_error:
                    logger.warning(f"OCR attempt {attempt + 1} failed: {ocr_error}")
                    if attempt < max_retries - 1:
                        time.sleep(1)

        logger.error(f"OCR failed after {max_retries} attempts for {file_path}")
        return ""

    def _process_pdf_page_ocr(self, pdf_path: str, page_num: int, dpi: int = 200, timeout: int = 180) -> str:
        """OCR a single PDF page using PyMuPDF + Ollama vision model."""
        ocr_model = config.OCR_MODEL
        if not self._check_ocr_model_available():
            logger.error(f"OCR model '{ocr_model}' is not available. Run: ollama pull {ocr_model}")
            return ""

        try:
            import fitz
            from ollama import Client

            logger.info(f"Converting page {page_num + 1} to image with PyMuPDF...")

            doc = fitz.open(pdf_path)
            page = doc.load_page(page_num)
            zoom = dpi / 72
            mat = fitz.Matrix(zoom, zoom)
            pix = page.get_pixmap(matrix=mat)

            config.TEMP_DIR.mkdir(exist_ok=True, parents=True)
            temp_img = config.TEMP_DIR / f"ocr_page_{page_num}.png"
            pix.save(str(temp_img))
            doc.close()

            with open(temp_img, "rb") as f:
                img_bytes = f.read()

            client = Client(config.OLLAMA_BASE_URL)
            resp = client.chat(
                model=ocr_model,
                messages=[{"role": "user", "content": "Extract ALL text from this image. Preserve structure and formatting. Output only the extracted text.", "images": [img_bytes]}],
                options={"num_ctx": 8192},
            )

            text = resp.message.content.strip()

            try:
                temp_img.unlink()
            except Exception:
                pass

            if text:
                logger.info(f"Page {page_num + 1}: OCR extracted {len(text)} chars")
            return text

        except ImportError as e:
            logger.error(f"Missing dependency for OCR: {e}")
            return ""
        except Exception as e:
            logger.error(f"OCR failed on page {page_num + 1}: {e}")
            return ""

    def ingest_file(self, file_path: str) -> dict:
        """Ingest a local file based on its extension."""
        path = Path(file_path)

        if not path.exists():
            return {"error": f"File not found: {file_path}"}

        ext = path.suffix.lower()

        if ext == ".pdf":
            return self.ingest_pdf(str(path))
        elif ext in [".txt", ".md", ".csv"]:
            return self._ingest_text_file(str(path))
        elif ext in [".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp"]:
            return self.ingest_image(str(path))
        elif ext == ".docx":
            return self._ingest_docx(str(path))
        else:
            return {"error": f"Unsupported file type: {ext}"}

    def _ingest_text_file(self, file_path: str) -> dict:
        """Ingest plain text file."""
        try:
            content = Path(file_path).read_text(encoding="utf-8", errors="ignore")
            name = Path(file_path).stem
            return self.add_entity(
                name=name, content=content[:50000], tipo="source",
                fuente=file_path, estado="final", tags=["text-file"]
            )
        except Exception as e:
            return {"error": str(e)}

    def ingest_image(self, file_path: str) -> dict:
        """Ingest an image file using OCR."""
        try:
            text = self.extract_with_ocr(file_path)
            if not text:
                return {"error": "OCR no pudo extraer texto de la imagen"}

            name = Path(file_path).stem
            return self.add_entity(
                name=name, content=text, tipo="image-ocr",
                fuente=file_path, estado="final", tags=["ocr", "image"]
            )
        except Exception as e:
            return {"error": str(e)}

    def _analyze_pdf_pages(self, pdf_path: str) -> dict:
        """Analyze PDF pages to detect which need OCR."""
        try:
            from pypdf import PdfReader
        except ImportError:
            import PyPDF2 as _pypdf2
            PdfReader = _pypdf2.PdfReader

        with open(pdf_path, 'rb') as f:
            reader = PdfReader(f)
            num_pages = len(reader.pages)

            pages_need_ocr = []
            pages_with_text = []

            for i in range(num_pages):
                page_text = reader.pages[i].extract_text() or ""
                text_stripped = page_text.strip()
                text_len = len(text_stripped)

                needs_ocr = text_len < 200 or text_len == 0

                if needs_ocr:
                    pages_need_ocr.append(i)
                else:
                    pages_with_text.append(i)

            logger.info(f"PDF analysis: {len(pages_with_text)} pages with text, {len(pages_need_ocr)} need OCR")
            return {
                "total_pages": num_pages,
                "pages_need_ocr": pages_need_ocr,
                "pages_with_text": pages_with_text
            }

    def ingest_pdf(self, file_path: str, use_ocr_fallback: bool = True, force_ocr: bool = False) -> dict:
        """Ingest PDF with intelligent page-by-page OCR."""
        try:
            try:
                from pypdf import PdfReader
            except ImportError:
                import PyPDF2 as _pypdf2
                PdfReader = _pypdf2.PdfReader

            import fitz

            logger.info(f"Starting PDF ingestion: {Path(file_path).name}")

            page_analysis = self._analyze_pdf_pages(file_path)
            pages_need_ocr = page_analysis["pages_need_ocr"]
            pages_with_text = page_analysis["pages_with_text"]
            num_pages = page_analysis["total_pages"]

            with open(file_path, 'rb') as f:
                reader = PdfReader(f)
                page_texts = {}

                for page_idx in pages_with_text:
                    page_text = reader.pages[page_idx].extract_text() or ""
                    page_texts[page_idx] = page_text

                digital_chars = sum(len(t.strip()) for t in page_texts.values())
                logger.info(f"Extracted {digital_chars} chars from {len(pages_with_text)} digital pages")

            ocr_texts = {}
            ocr_pages = []

            should_use_ocr = force_ocr or (use_ocr_fallback and len(pages_need_ocr) > 0)

            if should_use_ocr and self._check_ocr_model_available():
                logger.info(f"Applying OCR to {len(pages_need_ocr)} pages...")
                for page_idx in pages_need_ocr:
                    ocr_text = self._process_pdf_page_ocr(file_path, page_idx)
                    if ocr_text and len(ocr_text.strip()) > 50:
                        ocr_texts[page_idx] = ocr_text
                        ocr_pages.append(page_idx + 1)
                    elif page_idx in page_texts and page_texts[page_idx].strip():
                        ocr_texts[page_idx] = page_texts[page_idx]
            else:
                logger.info("Skipping OCR (not needed or model unavailable)")

            combined_parts = []
            for i in range(num_pages):
                if i in ocr_texts:
                    combined_parts.append(ocr_texts[i])
                elif i in page_texts:
                    combined_parts.append(page_texts[i])

            full_text = "\n".join(combined_parts)

            if not full_text.strip():
                return {"error": "No se pudo extraer texto del PDF"}

            name = Path(file_path).stem
            try:
                doc = fitz.open(file_path)
                pdf_title = doc.metadata.get("title", "")
                if pdf_title and len(pdf_title.strip()) > 5:
                    name = pdf_title.strip()[:200]
                doc.close()
            except Exception as e:
                logger.warning(f"Could not extract PDF title: {e}")

            content_limit = 500000
            result = self.add_entity(
                name=name, content=full_text[:content_limit], tipo="source",
                fuente=file_path, estado="final",
                tags=["pdf", "document", f"pages:{num_pages}"] + (["ocr-assisted"] if ocr_pages else [])
            )

            if result.get("success"):
                result["pages_processed"] = num_pages
                result["digital_pages"] = len(pages_with_text)
                result["ocr_pages"] = ocr_pages
                result["has_ocr"] = bool(ocr_pages)
                result["content_length"] = len(full_text)
                result["truncated"] = len(full_text) > content_limit

                quality_info = self.track_ingest_quality("pdf", name, result)
                result["quality_score"] = quality_info["quality_score"]
                result["quality_alerts"] = quality_info.get("alerts", [])

            return result

        except ImportError as ie:
            logger.error(f"Missing PDF dependency: {ie}")
            return {"error": f"Missing PDF dependency: {ie}"}
        except Exception as e:
            logger.error(f"PDF ingest error: {e}")
            return {"error": str(e)}

    def save_research_proposal(self, pregunta: str, propuesta: str, modo: str, refs: list) -> dict:
        """Save research proposal as a wiki note with frontmatter."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        slug = _slugify(pregunta)[:50]
        name = f"research_proposal_{timestamp}"

        content_lines = [
            f"# Propuesta de Investigacion",
            f"**Pregunta Original:** {pregunta}",
            f"**Modo:** {modo}",
            f"**Fecha:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "", "---", "",
            "## Propuesta", propuesta, "",
            "## Referencias",
        ]
        for ref in refs:
            ref_name = ref.get("name", "Sin nombre")
            ref_tipo = ref.get("tipo", "entity")
            ref_preview = ref.get("content_preview", "")[:200]
            content_lines.extend([f"### {ref_name}", f"**Tipo:** {ref_tipo}", f"**Extracto:** {ref_preview}", ""])

        content = "\n".join(content_lines)

        result = self.add_entity(
            name=name, content=content, tipo="synthesis", fuente="research_agent",
            estado="draft", tags=["research", "proposal", modo, "investigacion"], relacionados=[]
        )

        logger.info(f"Research proposal saved: {name}")
        return result

    def get_last_source(self, content_type: str = "all") -> dict:
        """Get the last ingested source (PDF, YouTube, URL)."""
        if content_type == "pdf":
            self.cursor.execute("""
                SELECT name, tipo, content, fuente, fecha_ingesta FROM entities
                WHERE tipo = 'source' AND fuente LIKE '%temp%'
                ORDER BY fecha_ingesta DESC LIMIT 1
            """)
        elif content_type == "youtube":
            self.cursor.execute("""
                SELECT name, tipo, content, fuente, fecha_ingesta FROM entities
                WHERE tipo = 'video' ORDER BY fecha_ingesta DESC LIMIT 1
            """)
        elif content_type == "url":
            self.cursor.execute("""
                SELECT name, tipo, content, fuente, fecha_ingesta FROM entities
                WHERE tipo = 'source' AND fuente LIKE 'http%'
                AND fuente NOT LIKE '%youtube%' AND fuente NOT LIKE '%temp%'
                ORDER BY fecha_ingesta DESC LIMIT 1
            """)
        else:
            self.cursor.execute("""
                SELECT name, tipo, content, fuente, fecha_ingesta FROM entities
                WHERE tipo IN ('source', 'video') AND fuente IS NOT NULL AND fuente != ''
                AND fuente NOT LIKE '%obsidian%'
                ORDER BY fecha_ingesta DESC LIMIT 1
            """)

        row = self.cursor.fetchone()
        if row:
            return {"name": row[0], "tipo": row[1], "content": row[2], "fuente": row[3], "fecha": row[4]}
        return None

    def get_last_ingested(self, limit: int = 5) -> list:
        """Get the last N ingested sources ordered by fecha_ingesta."""
        self.cursor.execute("""
            SELECT name, tipo, content, fuente, fecha_ingesta FROM entities
            WHERE (
                (tipo = 'video')
                OR (tipo = 'source' AND fuente IS NOT NULL AND fuente != ''
                    AND fuente NOT LIKE '%obsidian%'
                    AND (fuente LIKE '%temp%' OR fuente LIKE '%.pdf%' OR fuente LIKE 'http%'))
            )
            ORDER BY fecha_ingesta DESC LIMIT ?
        """, (limit,))
        results = []
        for row in self.cursor.fetchall():
            results.append({
                "name": row[0], "tipo": row[1], "content": row[2],
                "fuente": row[3], "fecha": row[4]
            })
        return results
