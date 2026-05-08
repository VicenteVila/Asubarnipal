# 📖 Manual de Asubarnipal V18 — Imperial Edition
*🏛️ Asubarnipal V18 — El Legado de Nínive*

## 🤖 El Asistente

Asubarnipal es un agente de conocimiento con wiki estructurado (Karpathy Pattern). Funciona a través de Telegram y responde a comandos para gestionar información, investigar temas y mantener la base de conocimientos.

---

## 📋 Comandos de Telegram

### 🏛️ Comandos Principales

| Comando | Descripción |
|---------|-------------|
| `/start` | Mensaje de bienvenida con historia y comandos |
| `/manual` | Envía este manual al usuario |
| `/status` | Muestra telemetría (CPU, RAM), estadísticas del wiki, latido, procesos |
| `/reporte` | Genera informe de auto-reflexión del agente |

---

### 📥 Ingesta y Datos

| Comando | Descripción |
|---------|-------------|
| `/ingest <url>` | Extrae contenido de una web y lo guarda en la biblioteca |
| `/sync_obsidian` | Escanea el vault local de Obsidian e indexa todas las notas `.md` |
| `/investigar <tema>` | Búsqueda profunda con síntesis Karpathy: extrae entidades, conceptos, contradicciones |
| Enviar **PDF** | Adjunta un PDF → Extrae texto y lo ingiere al wiki |
| Enviar **YouTube link** | Detecta enlace YouTube → Extrae transcripción y crea nota |

---

### 🔎 Consulta y RAG

| Comando | Descripción |
|---------|-------------|
| `/query <pregunta>` | Consulta el wiki primero, luego LLM si no hay info |
| `/hubs` | Identifica los conceptos centrales (betweenness centrality) |
| `/clusters` | Visualiza comunidades temáticas (Louvain) |
| `/lint` | Diagnóstico: huérfanas, stale, sin tags, contradicciones |

---

### 🕸️ Estructura y Grafo

| Comando | Descripción |
|---------|-------------|
| `/indexar_wiki` | Reconstruye índice vectorial + grafo + comunidades + hubs |
| `/query_vectorial <búsqueda>` | Búsqueda semántica por embeddings |

---

### 🎭 Charla (5 Modos)

Usa `/charlar <tema>` para iniciar una conversación:

| Modo | Emoji | Descripción |
|------|-------|-------------|
| **Charla Libre** | 💬 | Conversación natural |
| **Consultor Estratégico** | 🧠 | Análisis en 3 fases: Definición → Ejecución → Evaluación |
| **Devil's Advocate** | 🔥 | Crítica implacable |
| **Modo Socrático** | ❓ | Guía mediante preguntas |
| **Expansión Lateral** | 🌐 | Perspectivas radicales |

---

### ⚙️ Configuración

| Comando | Descripción |
|---------|-------------|
| `/model` | Muestra el backend actual (Ollama/Gemini) |
| `/model ollama` | Forzar modelo local |
| `/model gemini` | Forzar Gemini API |
| `/model auto` | Detección automática |

---

### 🤖 Modo Agente Autónomo

| Comando | Descripción |
|---------|-------------|
| `/agente [tarea]` | Activa el núcleo de razonamiento autónoma |

El agente puede:
- **Planificar**: Divide tareas en pasos
- **Ejecutar**: Escribe código, manipula archivos
- **Aprobar**: Acciones críticas requieren confirmación

---

## 🛠️ Skills del Agente

| Skill | Función |
|-------|---------|
| `hybrid_llm` | LLM híbrido con rotación de claves |
| `wiki_engine` | Pipeline completo Karpathy: ingesta, query, lint |
| `wiki_vector_index` | Embeddings, grafo, comunidades, hubs |
| `wiki_healer` | Repara huérfanas, reconecta conocimiento |
| `graph_builder` | Análisis de código + betweenness centrality |
| `turboquant` | Cuantización de modelos LLM |
| `memory_skill` | Memoria persistida + búsqueda |
| `extract_web` | Extrae contenido de URLs |
| `extract_youtube` | Extrae transcripciones YouTube |
| `extract_pdf` | Extrae texto de PDFs |

---

## ⚙️ Configuración del Sistema

### Endpoints LLM
- **Ollama:** `qwen3:8b` (local)
- **Gemini:** Rotación automática de claves API

### Rutas (config.py)

| Variable | Default | Descripción |
|----------|---------|-------------|
| `OBSIDIAN_PATH` | `C:\Obsidian` | Vault principal |
| `WIKI_PATH` | `{OBSIDIAN_PATH}/wiki` | Wiki generado |
| `RAW_PATH` | `{OBSIDIAN_PATH}/raw` | Fuentes crudas |
| `INDEX_PATH` | `{OBSIDIAN_PATH}/index.md` | Índice del wiki |
| `LOG_MD_PATH` | `{OBSIDIAN_PATH}/log.md` | Log estructurado |
| `CLAUDE_PATH` | `{OBSIDIAN_PATH}/CLAUDE.md` | Schema del agente |
| `GRAPH_STORE_PATH` | `{OBSIDIAN_PATH}/graph_store` | Grafo + embeddings |

### Variables de Entorno (.env)
```
GEMINI_KEYS=key1,key2,key3
TELEGRAM_TOKEN=...
BRAVE_API_KEY=...
OLLAMA_BASE_URL=http://127.0.0.1:11434
```

---

## 🔄 Background Rituals (El Latido)

| Ritual | Frecuencia | Función |
|--------|------------|---------|
| 💓 **Heartbeat** | 1 min | CPU, RAM, proceso agente vivo |
| 💉 **Sutura** | 10 min | Sana huérfanas, reconecta ideas |
| 🕸️ **Grafo** | 30 min | Actualiza comunidades y hubs |
| 🌙 **Medianoche** | 03:00 | Mantenimiento + MOC + índice vectorial |

---

## 🏗️ Arquitectura del Proyecto

```
Asubarnipal/
├── agente.py              # Entry point (script completo)
├── dashboard.py         # Command Center Streamlit
├── config.py            # Configuración centralizada
├── core/
│   ├── llm_router.py    # Ollama/Gemini + rotación
│   ├── wiki.py         # WikiEngine + WikiVectorIndex
│   ├── background_manager.py  # Rituales
│   └── brave_counter.py # Contador Brave (1500/mes)
├── interface/
│   └── telegram_bot.py # Handlers de Telegram
├── skills/
│   └── default_skills.py
├── index/               # Vector + FAISS
├── storage/            # Memoria persistida
└── data/               # Logs, heartbeat, estados
```

---

## 📝 Schema del Wiki (Karpathy Pattern)

### Convenciones de archivo

- **Fuentes crudas:** `/raw/` — INMUTABLES
- **Wiki generado:** `/wiki/` — Control total del agente
- **Notas de fuente:** `source_<hash>.md`
- **Páginas de entidad:** `entity_<nombre>.md`
- **Páginas de concepto:** `concept_<nombre>.md`
- **Síntesis:** `synthesis_<tema>.md`
- **Mapas de contenido:** `_MAPA_MAESTRO.md`

### Frontmatter obligatorio

```yaml
---
tipo: source|entity|concept|synthesis|moc
titulo: "Nombre"
fuente: "nombre de fuente o N/A"
fecha_ingesta: YYYY-MM-DD
fecha_actualizacion: YYYY-MM-DD
estado: draft|review|final
tags: [tag1, tag2]
relacionados: [[Nota1]], [[Nota2]]
---
```

### Reglas de integración

1. **BUSCAR** entidades/conceptos existentes antes de crear
2. **DOCUMENTAR** contradicciones con fecha
3. **ACTUALIZAR** index.md después de cada ingesta
4. **CROSS-REFERENCIAR**: toda nota ≥ 2 wikilinks
5. **NUNCA** dejar nota huérfana

---

## 🔬 WikiVectorIndex

El agente mantiene un índice vectorial híbrido:

1. **Wikilinks** → aristas explícitas
2. **Similitud semántica** → aristas implícitas (threshold: 0.82)
3. **Comunidades** → Louvain community detection
4. **Hubs** → betweenness + degree centrality

---

## 🚀 Ejecución

```bash
# Agente (Terminal 1)
python agente.py

# Dashboard (Terminal 2)
streamlit run dashboard.py
```

O alternativamente:
```bash
python -m interface.telegram_bot
streamlit run dashboard.py
```

---

## ⚠️ Notas Importantes

1. **Brave Search:** 1500/mes. Al agotar, usa DuckDuckGo automáticamente.
2. **Contador Brave:** Se guarda en `data/brave_counter.json`, resetea mensual.
3. **Ollama:** Preferido por defecto para reducir costos.
4. **Schema obligatorio:** `tipo`, `fuente`, `fecha_ingesta`, `estado`, `tags`, `relacionados`.
5. **Bypass RAG:** "Charla inocua" → respuesta directa sin wiki.
6. **PDF + YouTube:** Enviar directamente al chat para ingesta.

---

## 📜 Historia

**Ashurbanipal** (rey asirio, 668-627 a.C.) fue el último gran rey del Imperio Asirio. Su legado: la **Biblioteca de Nínive**, la primera colección sistemática del mundo. Su orden: *"Traedme cada tablilla que encontréis"*.

Este bot es el heredero moderno: no guarda arcilla, guarda conocimiento digital.