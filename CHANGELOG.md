# Asubarnipal V18 - Changelog

## Fecha: 18 Mayo 2026

---

## Nuevas Funcionalidades

### 1. Mejora del comando `/ingest`

#### Antes:
- Solo soportaba URLs web
- YouTube ingestion era básica (solo título)

#### Después:
- **URLs web**: Extracción de contenido con limpieza HTML
- **YouTube**: Transcript + metadata + traducción al castellano
- **Paths locales**: PDF, TXT, MD, imágenes
- **Documentos Telegram**: Archivos adjuntos con descarga automática
- **Imágenes**: OCR con glm-ocr:latest

#### Funciones nuevas en `core/wiki.py`:
```python
extract_with_ocr(file_path)      # OCR con glm-ocr:latest
ingest_pdf(file_path)            # PyPDF2 + fallback OCR
ingest_image(file_path)          # OCR para imágenes
ingest_file(file_path)           # Router por extensión
_ingest_youtube(url)             # Video con transcript
_extract_youtube_transcript(url)  # Extrae subtítulos
_extract_youtube_metadata(url)   # Metadata completa
```

---

### 2. Nuevo directorio `temp/`

- Archivos temporales para documentos Telegram
- Ubicación: `C:\Asubarnipal\temp\`

---

## 3. Comando `/charlar` mejorado con modelos específicos

| Modo | Modelo Ollama | Tamaño | Uso |
|------|---------------|--------|-----|
| **libre** | qwen3.5:0.8b | 1 GB | Conversación casual, máxima velocidad |
| **consultor** | qwen3:8b | 5.2 GB | Análisis en 3 fases, contexto amplio |
| **devil** | gemma4:e4b | 9.6 GB | Crítica implacable, máxima calidad |
| **socratico** | qwen3.5:4b | 3.4 GB | Diálogo socrático, balance |
| **lateral** | qwen3.5:9b | 6.6 GB | Perspectivas creativas, alta creatividad |

#### Configuración TurboQuant por modo:

| Modo | Contexto | Cache K | Cache V | Prioridad |
|------|----------|---------|---------|-----------|
| libre | 32K | turbo2 | turbo3 | speed |
| consultor | 64K | q8_0 | turbo4 | balanced |
| devil | 16K | q8_0 | q8_0 | quality |
| socratico | 48K | turbo4 | turbo3 | balanced |
| lateral | 24K | turbo3 | turbo4 | speed |

---

## Archivos modificados

| Archivo | Cambios |
|---------|---------|
| `core/wiki.py` | 5.5KB añadido: OCR, YouTube, PDF mejorado |
| `interface/handlers/busqueda.py` | Rewrite completo: detecta URLs/paths/docs |
| `config.py` | +1 línea: TEMP_DIR |
| `core/turboquant_modes.py` | Campo `model` añadido a ChatModeConfig |
| `core/turboquant_engine.py` | apply_mode() usa modelo del modo |
| `core/llm_router.py` | call_with_turbo() soporta modelo específico |
| `interface/handlers/chat.py` | Usa modelo específico por modo |

---

## Dependencias necesarias

```bash
pip install yt-dlp pdf2image pypdf2
```

Para OCR de PDFs página por página necesitas poppler-utils (Linux) o poppler-windows.

---

## Uso

### Ingest URL:
```
/ingest https://youtube.com/watch?v=...
/ingest https://example.com/article
```

### Ingest archivo local:
```
/ingest C:\Docs\articulo.pdf
/ingest C:\Images\documento.png
```

### Ingest documento Telegram:
1. Adjunta archivo en Telegram
2. Envía `/ingest`

### Charlar con modo específico:
```
/charlar devil ¿Es buena idea este proyecto?
/charlar consultor ¿Cómo optimizar este código?
/charlar socratico ¿Qué es la conciencia?
```

---

## Bugs corregidos

1. **Error "Message text is empty"** en telegram_bot.py
2. **BotLogger no soportaba exc_info=True** en error_handler
3. **/ingest no soportaba PDFs ni paths locales**

---

## Notas técnicas

### OCR con glm-ocr:latest
```python
def extract_with_ocr(file_path: str) -> str:
    from ollama import Client
    client = Client(config.OLLAMA_BASE_URL)

    with open(file_path, "rb") as f:
        img_b64 = base64.b64encode(f.read()).decode()

    resp = client.chat(
        model="glm-ocr:latest",
        messages=[{"role": "user", "content": f"<|img_b64|>{img_b64}<|img_b64|>"}]
    )
    return resp.message.content.strip()
```

### YouTube Transcript
Usa yt-dlp para extraer subtítulos en español/inglés, luego traduce a castellano con deep-translator.

### Cuantización TurboQuant
- `q8_0`: 8-bit, máxima calidad
- `turbo4`: ~4-bit, alta calidad
- `turbo3`: ~3-bit, buena
- `turbo2`: ~2-bit, máxima velocidad

---

## Estado: LISTO PARA PROBAR

Reiniciar bot y probar:
1. `/ingest` con URL de YouTube
2. `/ingest` con PDF local
3. `/charlar devil <tema>`
4. `/charlar consultor <tema>`