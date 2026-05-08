# 📖 Manual de Asubarnipal V18 — Imperial Edition
*🏛️ Asubarnipal V18 — El Legado de Nínive*

---

## 🤖 El Asistente

Asubarnipal es un agente de conocimiento con wiki estructurado (Karpathy Pattern). Funciona a través de Telegram y responde a comandos para gestionar información, investigar temas y mantener la base de conocimientos.

Este manual puede consultarse con `/manual` en cualquier momento.

---

## 📋 Comandos de Telegram (16 comandos)

### 🏛️ Comandos Principales (4)

| Comando | Descripción |
|---------|-------------|
| `/start` | Mensaje de bienvenida con historia y comandos |
| `/manual` | Envía este manual al usuario |
| `/status` | Muestra telemetría (CPU, RAM), estadísticas del wiki, proceso agente |
| `/reporte` | Genera informe de auto-reflexión del agente |

### 📥 Ingesta y Datos (4)

| Comando | Descripción |
|---------|-------------|
| `/ingest <url>` | Extrae contenido de una web y lo guarda en la biblioteca |
| `/sync_obsidian` | Escanea el vault local de Obsidian e indexa todas las notas `.md` |
| `/investigar <tema>` | Búsqueda profunda: extrae entidades, conceptos, contradicciones |
| Enviar **PDF** | Adjunta un PDF → Extrae texto y lo ingiere al wiki |

### 🔎 Consulta y RAG (4)

| Comando | Descripción |
|---------|-------------|
| `/query <pregunta>` | Consulta el wiki primero, luego LLM si no hay info |
| `/hubs` | Identifica los conceptos centrales (betweenness centrality) |
| `/clusters` | Visualiza comunidades temáticas (Louvain) |
| `/lint` | Diagnóstico: huérfanas, stale, sin tags, contradicciones |

### 🕸️ Estructura y Grafo (2)

| Comando | Descripción |
|---------|-------------|
| `/indexar_wiki` | Reconstruye índice vectorial + grafo + comunidades + hubs |
| `/query_vectorial <búsqueda>` | Búsqueda semántica por embeddings |

### 🎭 Charla (1)

| Comando | Descripción |
|---------|-------------|
| `/charlar <tema>` | Iniciar conversación especializada (5 modos disponibles) |

### ⚙️ Configuración (1)

| Comando | Descripción |
|---------|-------------|
| `/model [ollama\|gemini\|auto]` | Cambiar backend LLM |

### 🤖 Agente Autónomo (1)

| Comando | Descripción |
|---------|-------------|
| `/agente [tarea]` | Activar razonamiento autónomo |

---

## 🎭 Modos de Charla

Usa `/charlar <tema>` para iniciar:

| Modo | Emoji | Descripción |
|------|-------|-------------|
| **Charla Libre** | 💬 | Conversación natural |
| **Consultor** | 🧠 | Análisis en 3 fases: Definición → Ejecución → Evaluación |
| **Devil's Advocate** | 🔥 | Crítica implacable |
| **Modo Socrático** | ❓ | Guía mediante preguntas |
| **Expansión Lateral** | 🌐 | Perspectivas radicales |

---

## ⚙️ Configuración del Sistema

### Endpoints LLM

- **Ollama:** `qwen3:8b` (local)
- **Gemini:** Rotación automática

### Rutas (Karpathy Pattern)

| Variable | Ruta | Descripción |
|----------|-----|-------------|
| `OBSIDIAN_PATH` | `c:\Obsidian` | Vault principal |
| `WIKI_DIR` | `c:\Obsidian\wiki` | Wiki generado |
| `RAW_DIR` | `c:\Obsidian\raw` | Fuentes RAW |
| `GRAPH_STORE` | `c:\Obsidian\graph_store` | Grafos + embeddings |
| `LOG_FILE` | `c:\Asubarnipal\data\agente.log` | Logs del agente |

---

## 🔄 Background Rituals

| Ritual | Frecuencia | Función |
|--------|------------|---------|
| 💓 **Heartbeat** | 1 min | Telemetry alive |
| 💉 **Sutura** | 10 min | Sana huérfanas |
| 🕸️ **Grafo** | 30 min | Comunidades y hubs |
| 🌙 **Medianoche** | 03:00 | Mantenimiento |

---

## 🏗️ Pipeline de Ingesta (Karpathy Pattern)

1. **Raw** → `c:\Obsidian\raw\` (inmutable)
2. **Analizar** → Entidades + Conceptos
3. **Entity Pages** → `c:\Obsidian\wiki\entity_*.md`
4. **Source Note** → `c:\Obsidian\wiki\source_*.md`
5. **Index** → `c:\Obsidian\index.md`

---

## 🚀 Ejecución

```bash
# Agente
python -m interface.telegram_bot

# Dashboard
streamlit run dashboard.py
```

---

## 📜 Historia

**Ashurbanipal** (rey asirio, 668-627 a.C.) fue el último gran rey del Imperio Asirio. Su legado: la **Biblioteca de Nínive**, la primera colección sistemática del mundo. Su orden: *"Traedme cada tablilla que encontréis"*.

Este bot es el heredero moderno: no guarda arcilla, guarda conocimiento digital.