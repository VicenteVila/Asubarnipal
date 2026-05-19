# 📖 Manual de Asubarnipal V20 — Imperial Edition
*🏛️ Asubarnipal V20 — El Legado de Nínive*

---

## 🤖 El Asistente

Asubarnipal es un agente de conocimiento con wiki estructurado (Karpathy Pattern). Funciona a través de Telegram y responde a comandos para gestionar información, investigar temas y mantener la base de conocimientos.

Este manual puede consultarse con `/manual` en cualquier momento.

---

## 📋 Comandos de Telegram (21 comandos)

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
| `/ingest <url>` | Extrae contenido de web, traduce, resume, guarda en wiki + Obsidian + grafo |
| `/sync_obsidian` | Escanea el vault local de Obsidian e indexa todas las notas `.md` |
| `/investigar <tema>` | Búsqueda profunda: extrae entidades, conceptos, contradicciones |
| Enviar **PDF** | Adjunta un PDF → Extrae texto y lo ingiere al wiki |

### 🔎 Consulta y RAG (4)

| Comando | Descripción |
|---------|-------------|
| `/query <pregunta>` | Consulta el wiki primero (SQLite), luego LLM si no hay info |
| `/hubs` | Identifica los conceptos centrales del wiki |
| `/clusters` | Visualiza comunidades temáticas |
| `/lint` | Diagnóstico: huérfanas, stale, sin tags |

### 🕸️ Estructura y Grafo (2)

| Comando | Descripción |
|---------|-------------|
| `/indexar_wiki` | Reconstruye índice vectorial FAISS + grafo + comunidades + hubs |
| `/query_vectorial <búsqueda>` | Búsqueda semántica por embeddings (requiere `/indexar_wiki` previo) |

### 🎭 Charla (1)

| Comando | Descripción |
|---------|-------------|
| `/charlar <modo> <tema>` | Conversación especializada con TurboQuant (5 modos) |

### ⚙️ Configuración (1)

| Comando | Descripción |
|---------|-------------|
| `/model [ollama\|gemini\|auto]` | Cambiar backend LLM entre Ollama local y Gemini |

### 🤖 Agente Autónomo (2)

| Comando | Descripción |
|---------|-------------|
| `/agente [tarea]` | Activar razonamiento autónomo con ejecución de skills |
| `/rate [1-5]` | Calificar la última respuesta del agente (1=malo, 5=excelente) |

### 📚 Vaults de Conocimiento (7)

| Comando | Descripción |
|---------|-------------|
| `/vaults` | Lista todos los vaults y muestra el activo |
| `/vault_create <nombre>` | Crea un nuevo vault (con confirmación inline) |
| `/vault_use <nombre>` | Cambia al vault activo |
| `/vault_info` | Muestra detalles del vault activo |
| `/vault_delete <nombre>` | Elimina vault con backup automático |
| `/vault_export [nombre]` | Exporta vault a JSON |
| `/vault_import <nombre> <archivo>` | Importa vault desde JSON |

---

## 🎭 Modos de Charla

Usa `/charlar <modo> <tema>`:

| Modo | Emoji | Descripción |
|------|-------|-------------|
| **libre** | 💬 | Conversación natural y creativa |
| **consultor** | 🧠 | Análisis en 3 fases: Definición → Ejecución → Evaluación |
| **devil** | 🔥 | Crítica implacable, encuentra fallos y riesgos |
| **socrático** | ❓ | Guía mediante preguntas, no da respuestas |
| **lateral** | 🌐 | Perspectivas de chef, músico, tribu, algoritmo |

*Ejemplos:*
- `/charlar libre ¿Qué opinas de la IA?`
- `/charlar consultor ¿Cómo mejorar este código?`
- `/charlar devil ¿Es buena idea este producto?`
- `/charlar socrático ¿Qué es la conciencia?`
- `/charlar lateral ¿Cómo lo vería un ninja?`

---

## 🔄 Pipeline de Ingesta

Cuando ejecutas `/ingest <url>`:

```
1. Descarga y limpia HTML
2. Detecta idioma
3. Traduce al español (si es necesario)
4. Genera resumen via LLM
5. Extrae conceptos clave
6. Busca notas relacionadas
7. Guarda en:
   ├─→ SQLite (data/wiki.db)       → /query encuentra inmediatamente
   ├─→ Obsidian wiki/*.md          → Dashboard Wiki muestra inmediatamente
   └─→ graph.json + metadata.json  → Dashboard Grafo muestra inmediatamente
```

**Nota:** El índice FAISS para `/query_vectorial` se construye con `/indexar_wiki` (puede ejecutarse después de varias ingestas, no es inmediato).

---

## ⚙️ Configuración del Sistema

### Endpoints LLM

- **Ollama:** `qwen3.5:4b` (local, configurable)
- **Gemini:** Rotación automática entre varias claves

### Rutas (Karpathy Pattern)

| Variable | Ruta | Descripción |
|----------|-----|-------------|
| `OBSIDIAN_PATH` | `c:\Obsidian` | Vault principal de Obsidian |
| `WIKI_DIR` | `c:\Obsidian\wiki` | Wiki generado (archivos .md) |
| `RAW_DIR` | `c:\Obsidian\raw` | Fuentes RAW |
| `GRAPH_STORE` | `c:\Obsidian\graph_store` | Grafos + embeddings FAISS |
| `WIKI_PATH` | `c:\Asubarnipal\data\wiki.db` | Base de datos SQLite |
| `LOG_FILE` | `c:\Asubarnipal\data\agente.log` | Logs del agente |

---

## 🔄 Background Rituals

| Ritual | Frecuencia | Función |
|--------|------------|---------|
| 💓 **Heartbeat** | 1 min | Telemetry alive (CPU, RAM) |
| 💉 **Sutura** | 10 min | Sana huérfanas, limpia wiki |
| 🕸️ **Grafo** | 30 min | Actualiza grafo y comunidades |

---

## 📚 Gestión de Vaults

Asubarnipal soporta múltiples vaults de conocimiento, cada uno con su propia base de datos SQLite y índice RAG.

### Características:
- **Vaults únicos**: Cada vault tiene su propia DB (`data/wiki_{nombre}.db`)
- **RAG separado**: Cada vault tiene su propio índice FAISS (`data/index_{nombre}.faiss`)
- **Switch dinámico**: Cambia entre vaults sin reiniciar
- **Backup automático**: Al eliminar un vault se crea backup en `data/backups/`

### Ejemplo de uso:
```
/vaults                              # Ver todos los vaults
/vault_create investigacion_ia        # Crear nuevo vault
/vault_use investigacion_ia           # Cambiar al vault IA
/ingest https://arxiv.org/...         # Ingestar al vault activo
/vault_export investigacion_ia        # Exportar a JSON
```

### Vault principal:
El vault "principal" se crea automáticamente si no existe. No se puede eliminar.

---

## ⚡ TurboQuant - Optimización de LLM

TurboQuant optimiza automáticamente los parámetros de inferencia según el modo de chat activo.

### Modos de optimización:

| Modo /charlar | Contexto | Cache K | Cache V | Prioridad |
|----------------|----------|---------|---------|-----------|
| **libre** | 32K | turbo2 | turbo3 | Velocidad |
| **consultor** | 64K | q8_0 | turbo4 | Balance |
| **devil** | 16K | q8_0 | q8_0 | Calidad |
| **socratico** | 48K | turbo4 | turbo3 | Balance |
| **lateral** | 24K | turbo3 | turbo4 | Velocidad |

### Auto-detección:
TurboQuant se aplica automáticamente según el modo usado con `/charlar`. No requiere configuración manual.

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
# Agente Telegram
python -m interface.telegram_bot

# Dashboard Streamlit (abre en navegador)
streamlit run dashboard.py

# API REST (opcional, puerto 8000)
python -m api.main
```

---

## 🖥️ Dashboard (12 pestañas)

El dashboard de Streamlit proporciona una interfaz visual para monitorizar y gestionar el sistema.

### Pestañas disponibles:

| # | Pestaña | Descripción |
|---|---------|-------------|
| 1 | **Dashboard** | Telemetría, KPI cards, gráficos CPU/RAM, composición del wiki |
| 2 | **Skills** | 40+ funciones ejecutables (Archivo, LLM, Sistema, Wiki, Memoria, Research, GitHub) |
| 3 | **Wiki** | Inventario de notas, timeline, fuentes RAW, viewer de notas |
| 4 | **Raw** | Fuentes crudas inmutables |
| 5 | **Grafo** | Visualización interactiva del grafo de conocimiento, hubs, comunidades |
| 6 | **Logs** | Logs del agente en tiempo real, filtrables |
| 7 | **Salud** | Diagnóstico del wiki: hubs, notas sin tags, notas stale (>30 días) |
| 8 | **Schema** | Viewer del CLAUDE.md |
| 9 | **Latido** | Configuración de background rituals, editar intervalos, próximas ejecuciones |
| 10 | **Feeds** | Suscripciones RSS, alertas, historial de updates |
| 11 | **Analytics** | Historial de comandos, top comandos, memoria persistente |
| 12 | **Search** | Búsqueda global en notas, skills y comandos |

### Características del Dashboard:

- **Tema oscuro moderno** con glassmorphism
- **Avatar del agente** cargado dinámicamente
- **Estado del proceso Agente** en tiempo real (PID, uptime, CPU, RAM)
- **Gráficos interactivos** con Plotly (heatmap de actividad, timeline, grafo)
- **Búsqueda global** que busca en notas, skills y comandos
- **Notificaciones RSS** con toast alerts
- **Actualización automática** configurable

---

## 🌐 API REST (Opcional)

Endpoints disponibles en `http://localhost:8000`:

| Endpoint | Método | Descripción |
|----------|--------|-------------|
| `/` | GET | Info del agente |
| `/health` | GET | Health check |
| `/status` | GET | Estado del agente |
| `/stats` | GET | Estadísticas wiki |
| `/command` | POST | Ejecutar comando |
| `/feeds` | GET | Listar suscripciones |
| `/feeds/check` | GET | Verificar actualizaciones |
| `/history` | GET | Historial de comandos |
| `/logs` | GET | Logs del agente |

---

## 📡 Feed Tracker

Suscríbete a RSS/Atom feeds para recibir alertas:

- Desde Dashboard → pestaña "📡 Feeds"
- Añadir URL → Recibir alertas automáticas
- Notificaciones via Streamlit toast

---

## 📈 Analytics

Historial de comandos y estadísticas:

- Top 10 comandos más usados
- Comandos por fecha
- Primer y último comando
- Búsqueda en memorias persistentes

---

## 📜 Historia

**Ashurbanipal** (rey asirio, 668-627 a.C.) fue el último gran rey del Imperio Asirio. Su legado: la **Biblioteca de Nínive**, la primera colección sistemática del mundo. Su orden: *"Traedme cada tablilla que encontréis"*.

Este bot es el heredero moderno: no guarda arcilla, guarda conocimiento digital.

---

## ⚡ Skills del Agente (40+ funciones)

El agente puede ejecutar estas funciones automáticamente cuando usas `/agente`:

### 🗂️ Archivo
| Función | Descripción |
|---------|-------------|
| `run_command` | Ejecuta comandos del sistema |
| `read_file` | Lee archivos |
| `write_file` | Escribe archivos |
| `list_files` | Lista archivos en directorio |
| `search_in_files` | Busca texto en archivos |

### 🧠 LLM
| Función | Descripción |
|---------|-------------|
| `list_ollama_models` | Lista modelos Ollama disponibles |
| `pull_ollama_model` | Descarga un modelo Ollama |

### 💻 Sistema
| Función | Descripción |
|---------|-------------|
| `get_system_info` | Información del sistema |
| `get_env` | Obtiene variable de entorno |
| `set_env` | Establece variable de entorno |
| `check_service` | Verifica si un servicio está corriendo |

### 📚 Wiki
| Función | Descripción |
|---------|-------------|
| `get_wiki_stats` | Estadísticas del wiki |
| `search_wiki` | Busca en el wiki |
| `create_wiki_note` | Crea nota en el wiki |

### 🧠 Memoria
| Función | Descripción |
|---------|-------------|
| `remember` | Guarda en memoria persistente |
| `recall` | Recupera de memoria |
| `get_memories` | Lista todas las memorias |
| `memory_stats` | Estadísticas de memoria |

### 🔬 Research
| Función | Descripción |
|---------|-------------|
| `search_arxiv` | Busca en arXiv |
| `get_audio_summary` | Resume audio/video |

### 🌐 GitHub
| Función | Descripción |
|---------|-------------|
| `clone_repo` | Clona repositorio Git |

### 🌐 Traducción
| Función | Descripción |
|---------|-------------|
| `translate` | Traduce texto |
| `detect_language` | Detecta idioma |

### 🐍 Python
| Función | Descripción |
|---------|-------------|
| `execute_python` | Ejecuta código Python |
| `install_package` | Instala paquete pip |

### 📚 Vault
| Función | Descripción |
|---------|-------------|
| `list_vaults` | Lista todos los vaults |
| `create_vault` | Crea nuevo vault |
| `switch_vault` | Cambia vault activo |
| `delete_vault` | Elimina vault (con backup) |
| `export_vault` | Exporta a JSON |
| `import_vault` | Importa desde JSON |

### ⚡ TurboQuant
| Función | Descripción |
|---------|-------------|
| `optimize_llm` | Aplica settings según modo |
| `show_turbo_status` | Muestra estado actual |
| `benchmark_llm` | Benchmark de latencia |
| `get_recommended_context` | Calcula óptimo por modelo |

*Usa `/agente clona el repo github.com/username/repo y dime qué contiene`*