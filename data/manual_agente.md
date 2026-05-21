# Manual de Asubarnipal — Guia Completa

*El Legado de Ninive adaptado al siglo XXI*

---

## Indice

1. [Introduccion](#1-introduccion)
2. [Comandos de Sistema](#2-comandos-de-sistema)
3. [Comandos Wiki](#3-comandos-wiki)
4. [Ingesta de Contenido](#4-ingesta-de-contenido)
5. [Chat (/charlar)](#5-chat-charlar)
6. [Agente Autonomo](#6-agente-autonomo)
7. [Vision y OCR](#7-vision-y-ocr)
8. [Voz y STT](#8-voz-y-stt)
9. [Investigacion Programada](#9-investigacion-programada)
10. [H-Mem: Memoria Hibrida](#10-h-mem-memoria-hibrida)
11. [Grafo de Conocimiento (Graphify)](#11-grafo-de-conocimiento-graphify)
12. [Vaults (Multi-Vault)](#12-vaults-multi-vault)
13. [Backup y Recuperacion](#13-backup-y-recuperacion)
14. [Sesion y Chat](#14-sesion-y-chat)
15. [Configuracion y Background Jobs](#15-configuracion-y-background-jobs)
16. [Dashboard](#16-dashboard)
17. [REST API](#17-rest-api)
18. [Ejecucion del Sistema](#18-ejecucion-del-sistema)
19. [Skills del Agente](#19-skills-del-agente)

---

## 1. Introduccion

Asubarnipal es un agente de conocimiento con arquitectura de dos modelos de IA:

```
PEQUENO (qwen2.5:1.5b) → Experto Bibliotecario → Busca y resume
GRANDE (qwen3.5:4b) → Analista → Responde con propuesta de investigacion
```

**Sistema de memoria hibrido (H-Mem):** Combina un arbol temporal-semantico (como la memoria humana) con un grafo de entidades para dar al agente contexto de conversaciones anteriores.

**RAG Engine:** Busqueda hibrida (FAISS + BM25) con re-ranking por cross-encoder y chunking inteligente.

Este manual puede consultarse con `/manual` en cualquier momento.

---

## 2. Comandos de Sistema

### 2.1 Comandos basicos

| Comando | Descripcion | Ejemplo |
|---------|-------------|---------|
| `/start` | Mensaje de bienvenida con historia del bot | `/start` |
| `/manual` | Envia este manual al chat | `/manual` |
| `/status` | Telemetria: CPU, RAM, uptime, queries, tasa exito, Brave restantes | `/status` |
| `/reporte` | Autodiagnostico: uptime, queries, fallos, recursos, Brave, modelo, memoria | `/reporte` |
| `/model` | Muestra modelo actual. Selecciona con teclado inline | `/model` |
| `/session` | Estado de sesion: mensajes, tokens, modo, modelo, limites | `/session` |
| `/clear_session` | Limpia historial de chat del usuario | `/clear_session` |

---

## 3. Comandos Wiki

### 3.1 Consulta de conocimiento (/query)

**El comando mas potente del bot.** Usa arquitectura de dos modelos:

```
/query <pregunta>
       ↓
📚 PEQUENO → Busca en FTS5 → Resume con referencias
       ↓
🧠 GRANDE → Genera respuesta + propuesta de investigacion
       ↓
📋 Botones inline → Guardar / Crear nota / Standby
```

**Modos de busqueda (selecciona con teclado inline):**

| Modo | Descripcion |
|------|-------------|
| **Wiki** | Busqueda clasica con dos modelos |
| **Vectorial** | Busqueda semantica en indice FAISS |
| **Hibrido** | FAISS + BM25 + re-ranking cross-encoder |
| **H-Mem** | Consulta al sistema de memoria hibrida |

**Sintaxis:**
```
/query Que es LoRA y como funciona?
/query En que consiste el entrenamiento con adapters?
/query Diferencias entre fine-tuning completo y LoRA
```

### 3.2 Exploracion del wiki

| Comando | Descripcion | Ejemplo |
|---------|-------------|---------|
| `/hubs` | Muestra los 10 conceptos mas conectados del wiki | `/hubs` |
| `/clusters` | Muestra comunidades tematicas | `/clusters` |
| `/lint` | Diagnostico de salud: score, entidades huerfanas, enlaces rotos | `/lint` |
| `/quality` | Calidad de ingestas recientes. Por defecto ultimas 20 | `/quality 30` |

### 3.3 Busquedas especializadas

| Comando | Descripcion | Ejemplo |
|---------|-------------|---------|
| `/queryhybrid <pregunta>` | Busqueda hibrida SQLite + Obsidian vault. Alias: `/hybrid` | `/queryhybrid transformers attention` |
| `/query_vectorial <busqueda>` | Busqueda semantica en indice FAISS (embeddings) | `/query_vectorial redes neuronales recurrentes` |
| `/sync_obsidian` | Importa notas desde vault Obsidian externo | `/sync_obsidian` |
| `/indexar_wiki` | Reconstruye indice vectorial FAISS de todo el wiki | `/indexar_wiki` |

---

## 4. Ingesta de Contenido

### 4.1 /ingest — Variantes

El bot ingiere contenido de multiples fuentes y lo guarda automaticamente en wiki + SQLite + grafo:

```
/ingest <fuente> → descarga → limpia → resume → extrae conceptos → guarda
```

| Tipo | Sintaxis | Ejemplo |
|------|----------|---------|
| URL web | `/ingest <url>` | `/ingest https://arxiv.org/abs/2303.18223` |
| YouTube | `/ingest <url>` | `/ingest https://youtube.com/watch?v=abc123` |
| Archivo local | `/ingest <ruta>` | `/ingest C:\docs\paper.pdf` |
| PDF de Telegram | Adjunta archivo + `/ingest` | Adjuntar PDF → `/ingest` |
| Imagen OCR | Adjunta imagen + `/ingest` | Adjuntar imagen escaneada → `/ingest` |

**Pipeline de ingesta:**
```
1. Descarga y limpia HTML / extrae PDF / transcript de video
2. Detecta idioma
3. Traduce al espanol (si es necesario)
4. Genera resumen via LLM
5. Extrae conceptos clave y entidades
6. Busca notas relacionadas en wiki
7. Guarda en:
   ├─→ SQLite (data/wiki.db)      → /query encuentra inmediatamente
   ├─→ Obsidian wiki/*.md          → Dashboard Wiki muestra inmediatamente
   └─→ Propuesta de investigacion → Sugiere proxima investigacion
```

### 4.2 /investigar — Investigacion profunda

Usa Brave Search para investigar un tema y ingiere automaticamente los mejores resultados:

| Sintaxis | Ejemplo |
|----------|---------|
| `/investigar <tema>` | `/investigar transformers attention mechanism 2024` |

---

## 5. Chat (/charlar)

Usa `/charlar <modo> <tema>` para chatear en diferentes estilos especializados. Selecciona modo con teclado inline.

### 5.1 Los 5 modos

| Modo | Descripcion | Ejemplo |
|------|-------------|---------|
| **libre** | Conversacion natural y creativa | `/charlar libre que opinas de la IA generativa?` |
| **consultor** | Analisis en 3 fases: Definicion → Ejecucion → Evaluacion | `/charlar consultor como optimizar este codigo?` |
| **devil** | Critica implacable: encuentra fallos, riesgos, contradicciones | `/charlar devil es buena idea este producto?` |
| **socratico** | Guia mediante preguntas, no da respuestas directas | `/charlar socratico que es la consciencia?` |
| **lateral** | 5 perspectivas: Chef, Musico, Tribu, Algoritmo, Nino de 5 anos | `/charlar lateral como lo veria un ninja?` |

---

## 6. Agente Autonomo

### 6.1 Comandos de agente

| Comando | Descripcion | Ejemplo |
|---------|-------------|---------|
| `/agente <tarea>` | Agente autonomo con ejecucion de skills/herramientas | `/agente revisa el codigo y propon mejoras` |
| `/rate <1-5>` | Califica la ultima respuesta (1=Muy malo, 5=Excelente) | `/rate 4` |
| `/calidad` | Estadisticas: accuracy, promedio, conteos si/no/ms, alertas | `/calidad` |

### 6.2 Calificar respuestas

Despues de cada respuesta, el bot pregunta: *La respuesta fue precisa? (si/no/ms)*

Tambien puedes calificar manualmente:
```
/rate 5   → Excelente
/rate 3   → Aceptable
/rate 1   → Muy malo
```

---

## 7. Vision y OCR

Analiza imagenes con modelos de vision de Ollama (llava).

| Comando | Descripcion | Ejemplo |
|---------|-------------|---------|
| `/vision [prompt]` | Analiza la ultima foto con prompt personalizado | `/vision Que texto hay en esta imagen?` |
| `/ocr` | Extrae texto de la ultima foto | `/ocr` |

**Uso:**
1. Envia una foto al bot
2. Usa `/vision` o `/ocr` para analizarla

**Requisito:** Modelo llava instalado en Ollama:
```
ollama pull llava:7b
```

---

## 8. Voz y STT

Transcripcion automatica de mensajes de voz.

**Uso:**
1. Envia un mensaje de voz al bot
2. El bot transcribe automaticamente con Whisper
3. La transcripcion se procesa como un mensaje de texto normal

**Requisito (opcional):**
```
pip install openai-whisper
```

Sin Whisper instalado, el bot indica que STT no esta disponible.

---

## 9. Investigacion Programada

Programa investigaciones recurrentes que se ejecutan automaticamente.

| Comando | Descripcion | Ejemplo |
|---------|-------------|---------|
| `/schedule <tema> [min]` | Programa investigacion recurrente | `/schedule noticias IA 60` |
| `/schedules` | Lista todas las investigaciones programadas | `/schedules` |
| `/cancel_schedule <id>` | Cancela una investigacion programada | `/cancel_schedule 1` |
| `/toggle_schedule <id>` | Activa/desactiva una investigacion | `/toggle_schedule 1` |

**Ejemplos:**
```
/schedule noticias IA 60        → Cada hora
/schedule avances LLM 1440      → Diario
/schedule papers arxiv 4320     → Cada 3 dias
```

---

## 10. H-Mem: Memoria Hibrida

### 10.1 Que es?

H-Mem es un **sistema de memoria conversacional** que da al agente contexto de lo que hablaste antes. Funciona en segundo plano — automaticamente.

Combina dos estructuras:

**Arbol Temporal-Semantico** (como la memoria humana):
```
L0 → events (1 dia)
L1 → daily (7 dias)
L2 → weekly (30 dias)
L3 → monthly (90 dias)
```
Las memorias nuevas entran en L0 y suben automaticamente si se consolidan.

**Grafo de Entidades** (red de conceptos):
```
Entidades: persona, organizacion, concepto, evento, tema, proyecto
Relaciones: related_to, works_on, part_of, depends_on...
```

### 10.2 Comandos H-Mem

| Comando | Descripcion | Ejemplo |
|---------|-------------|---------|
| `/memoria` | Estado del sistema H-Mem | `/memoria` |
| `/recordar <texto>` | Guarda un recuerdo. Extrae entidades automaticamente | `/recordar El usuario trabaja en el proyecto Alpha` |
| `/pensar <pregunta>` | Consulta H-Mem con respuesta del LLM | `/pensar Sobre que hablamos ayer?` |
| `/contexto <query>` | Obtiene contexto para usar en prompts | `/contexto proyectos de IA` |
| `/entidades` | Muestra hubs del grafo de entidades (top 8) | `/entidades` |
| `/recientes [n]` | Lista memorias recientes (default 10, max 30) | `/recientes 20` |

---

## 11. Grafo de Conocimiento (Graphify)

### 11.1 Comandos de Telegram

| Comando | Descripcion | Ejemplo |
|---------|-------------|---------|
| `/graphify` | Construye el grafo de conocimiento completo | `/graphify` |
| `/graphify deep` | Modo profundo (extraccion agresiva de relaciones) | `/graphify deep` |
| `/graph_update` | Actualiza solo archivos cambiados (rapido) | `/graph_update` |
| `/graph_query <pregunta>` | Consulta el grafo con lenguaje natural | `/graph_query que conecta transformers con attention` |
| `/graph_stats` | Muestra estadisticas del grafo | `/graph_stats` |
| `/graph_report` | Muestra el reporte del grafo | `/graph_report` |
| `/graph_add <url>` | Anade una URL al grafo | `/graph_add https://arxiv.org/abs/1706.03762` |
| `/graph_export <formato>` | Exporta el grafo (html, svg, graphml, wiki, callflow) | `/graph_export svg` |

---

## 12. Vaults (Multi-Vault)

### 12.1 Comandos de gestion

| Comando | Descripcion | Ejemplo |
|---------|-------------|---------|
| `/vaults` | Lista todos los vaults con stats | `/vaults` |
| `/vault_create <nombre>` | Crea nuevo vault (con confirmacion) | `/vault_create investigacion_ia` |
| `/vault_use <nombre>` | Cambia vault activo | `/vault_use investigacion_ia` |
| `/vault_info` | Detalles del vault activo | `/vault_info` |
| `/vault_delete <nombre>` | Elimina vault (con backup automatico) | `/vault_delete antiguo` |
| `/vault_export [nombre]` | Exporta vault a JSON | `/vault_export ia` |
| `/vault_import <nombre> <ruta>` | Importa desde JSON | `/vault_import ia backup.json` |
| `/vault_connect <ruta> [nombre]` | Conecta vault Obsidian externo | `/vault_connect /mnt/Obsidian/proyecto` |
| `/vault_disconnect [nombre]` | Desconecta vault | `/vault_disconnect proyecto` |

### 12.2 Caracteristicas

- **Vaults unicos**: Cada vault tiene su propia DB (`data/wiki_{nombre}.db`)
- **RAG separado**: Cada vault tiene su propio indice FAISS
- **Switch dinamico**: Cambia entre vaults sin reiniciar
- **Backup automatico**: Al eliminar se crea backup en `data/backups/`
- **Vault principal**: Se crea automaticamente. No se puede eliminar

---

## 13. Backup y Recuperacion

Sistema de backup automatico con rotacion y restauracion.

| Comando | Descripcion | Ejemplo |
|---------|-------------|---------|
| `/backup [vault]` | Crea backup del vault activo o todos los datos | `/backup` |
| `/backups` | Lista todos los backups disponibles | `/backups` |
| `/restore <nombre>` | Restaura desde un backup | `/restore backup_full_20260521_172302` |
| `/backup_stats` | Muestra estadisticas de backup | `/backup_stats` |
| `/backup_clear` | Elimina todos los backups | `/backup_clear` |

**Caracteristicas:**
- Rotacion automatica (max 10 backups por defecto)
- Backup automatico cada 24h
- Restore de vaults y base de datos

---

## 14. Sesion y Chat

### 14.1 Auto-deteccion

El bot detecta automaticamente estos patrones:

| Input | Accion |
|-------|---------|
| `http://...` (URL) | Auto-ingest de la URL |
| `si/si/yes/y` | Registra evaluacion positiva |
| `no/n` | Registra evaluacion negativa |
| `ms/mas o menos` | Registra evaluacion neutral |
| `hola/buenas/hi` | Respuesta breve sin RAG (bypass) |
| Sesion pendiente + `si` | Restaura historial de chat |
| Sesion pendiente + `no` | Limpia sesion guardada |

---

## 15. Configuracion y Background Jobs

### 15.1 Background Rituals

| Ritual | Frecuencia | Funcion |
|--------|-------------|---------|
| Heartbeat | 60s | Registra CPU%, RAM% → `data/heartbeat.json` |
| Sutura | 10min | Limpia huerfanas, repara enlaces del wiki |
| Grafo | 30min | Reconstruye relaciones vectoriales |
| H-Mem | 30min | Consolida arbol temporal-semantico + grafo de entidades |
| Graphify | 30min | Reconstruye grafo de conocimiento interactivo |

### 15.2 TurboQuant

Optimiza automaticamente los parametros de inferencia segun el modo de chat:

| Modo | Primary | Fallback 1 | Fallback 2 |
|------|---------|------------|-------------|
| **libre** | qwen3.5:4b | qwen3:8b | gemma4:e4b |
| **consultor** | qwen3:8b | qwen3.5:9b | gemma4:e4b |
| **devil** | gemma4:e4b | qwen3:8b | qwen3.5:9b |
| **socratico** | qwen3.5:4b | qwen3:8b | qwen3.5:9b |
| **lateral** | qwen3.5:9b | qwen3:8b | qwen3.5:4b |

Si el modelo primario falla, prueba los fallbacks secuencialmente.

---

## 16. Dashboard

El dashboard de Streamlit proporciona interfaz visual para monitorizar y gestionar el sistema. Accede desde navegador en `http://localhost:8501`.

### 16.1 Pestanas disponibles

| # | Pestana | Descripcion |
|---|---------|-------------|
| 1 | **Dashboard** | Telemetria, KPI cards, graficos CPU/RAM |
| 2 | **Skills** | 50+ funciones disponibles |
| 3 | **Wiki** | Inventario, timeline, propuestas de investigacion |
| 4 | **Raw** | Tabla de fuentes raw |
| 5 | **Grafo** | Visualizacion del grafo, comunidades, hubs |
| 6 | **Logs** | Logs en tiempo real, filtrables |
| 7 | **Salud** | Diagnostico: notas sin tags, stale, huerfanas |
| 8 | **Schema** | Viewer del CLAUDE.md |
| 9 | **Latido** | Configuracion de background rituals |
| 10 | **Feeds** | Suscripciones RSS, alertas |
| 11 | **Analytics** | Historial de comandos, top comandos |
| 12 | **H-Mem** | Estado de memoria hibrida, arboles, grafos de entidades |

---

## 17. REST API

Accede en `http://localhost:8000/docs` para Swagger UI.

### 17.1 Endpoints

| Endpoint | Metodo | Descripcion |
|----------|--------|-------------|
| `/` | GET | Info de la API |
| `/health` | GET | Health check con uptime |
| `/metrics` | GET | Metricas de peticiones (error rate, tiempos) |
| `/command` | POST | Ejecutar comando via SkillRegistry |
| `/query` | POST | Consulta de conocimiento (wiki, vectorial, hybrid, hmem) |
| `/status` | GET | Estado del agente |
| `/stats` | GET | Estadisticas del wiki |
| `/feeds` | GET | Listar suscripciones RSS |
| `/feeds/subscribe` | POST | Suscribirse a feed RSS |
| `/feeds/unsubscribe` | POST | Cancelar suscripcion |
| `/feeds/check` | GET | Verificar actualizaciones de feeds |
| `/history` | GET | Historial de comandos |
| `/history/add` | POST | Anadir al historial |
| `/logs` | GET | Obtener logs del agente (con filtro por nivel) |
| `/schedules` | GET | Listar investigaciones programadas |
| `/vaults` | GET | Listar todos los vaults |

### 17.2 Caracteristicas

- Rate limiting: 60 req/min por IP
- CORS habilitado
- Autenticacion por API key (variable `API_KEYS`)
- Handlers de error con respuestas estructuradas
- Metricas: p95 response time, error rate

### 17.3 Ejemplo de uso

```bash
# Health check
curl http://localhost:8000/health

# Query de conocimiento
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{"query": "que es LoRA?", "mode": "hybrid", "top_k": 5}'

# Con API key
curl http://localhost:8000/status \
  -H "X-API-Key: tu_api_key"
```

---

## 18. Ejecucion del Sistema

### 18.1 Modo local

```bash
# Agente Telegram (requiere TELEGRAM_TOKEN)
python -m interface.telegram_bot

# Dashboard Streamlit (abre en navegador)
streamlit run dashboard.py

# API REST (opcional, puerto 8000)
python -m api.main
```

### 18.2 Docker

```bash
# Construir y iniciar todos los servicios
docker compose up -d

# Ver logs
docker compose logs -f bot

# Detener servicios
docker compose down

# Reconstruir tras cambios de codigo
docker compose up -d --build
```

Servicios disponibles:
- **Dashboard**: http://localhost:8501
- **API**: http://localhost:8001/docs
- **Bot**: Conecta a Ollama en `host.docker.internal:11434`

---

## 19. Skills del Agente

El agente puede ejecutar funciones automaticamente cuando usas `/agente`. Disponibles:

### Archivo
| Funcion | Descripcion |
|---------|-------------|
| `run_command` | Ejecuta comandos del sistema |
| `read_file` | Lee archivos |
| `write_file` | Escribe archivos |
| `list_files` | Lista archivos en directorio |
| `search_in_files` | Busca texto en archivos |

### LLM
| Funcion | Descripcion |
|---------|-------------|
| `list_ollama_models` | Lista modelos Ollama disponibles |
| `pull_ollama_model` | Descarga un modelo Ollama |

### Sistema
| Funcion | Descripcion |
|---------|-------------|
| `get_system_info` | Informacion del sistema |
| `get_env` | Obtiene variable de entorno |
| `set_env` | Establece variable de entorno |
| `check_service` | Verifica si un servicio esta corriendo |

### Wiki
| Funcion | Descripcion |
|---------|-------------|
| `get_wiki_stats` | Estadisticas del wiki |
| `search_wiki` | Busca en el wiki |
| `create_wiki_note` | Crea nota en el wiki |

### H-Mem
| Funcion | Descripcion |
|---------|-------------|
| `hmem_remember` | Guarda en memoria hibrida |
| `hmem_recall` | Recupera de memoria |
| `hmem_think` | Query + respuesta del LLM |
| `hmem_get_context` | Contexto para prompts |
| `hmem_get_stats` | Estadisticas del sistema |
| `hmem_get_recent` | Memorias recientes |

### Research
| Funcion | Descripcion |
|---------|-------------|
| `search_arxiv` | Busca en arXiv |
| `get_audio_summary` | Resume audio/video |

### GitHub
| Funcion | Descripcion |
|---------|-------------|
| `clone_repo` | Clona repositorio Git |

### Traduccion
| Funcion | Descripcion |
|---------|-------------|
| `translate` | Traduce texto |
| `detect_language` | Detecta idioma |

### Python
| Funcion | Descripcion |
|---------|-------------|
| `execute_python` | Ejecuta codigo Python |
| `install_package` | Instala paquete pip |

### Vault
| Funcion | Descripcion |
|---------|-------------|
| `list_vaults` | Lista todos los vaults |
| `create_vault` | Crea nuevo vault |
| `switch_vault` | Cambia vault activo |
| `delete_vault` | Elimina vault (con backup) |
| `export_vault` | Exporta a JSON |
| `import_vault` | Importa desde JSON |

### TurboQuant
| Funcion | Descripcion |
|---------|-------------|
| `optimize_llm` | Aplica settings segun modo |
| `show_turbo_status` | Muestra estado actual |
| `benchmark_llm` | Benchmark de latencia |
| `get_recommended_context` | Calcula optimo por modelo |

---

## Historia

**Ashurbanipal** (rey asirio, 668-627 a.C.) fue el ultimo gran rey del Imperio Asirio. Su legado: la **Biblioteca de Ninive**, la primera coleccion sistematica del mundo. Su orden: *"Traedme cada tablilla que encontreis"*.

Este bot es el heredero moderno: no guarda arcilla, guarda conocimiento digital.
