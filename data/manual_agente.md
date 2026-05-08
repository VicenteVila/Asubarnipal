# 📖 Manual de Asubarnipal V2 — Imperial Edition
*🏛️ Asubarnipal V2 — El Legado de Nínive*

## 🤖 El Asistente

Asubarnipal es un agente de conocimiento con wiki estructurado. Funciona a través de Telegram y responde a comandos para gestionar información, investigar temas y mantener la base de conocimientos.

---

## 📋 Comandos de Telegram

### 🏛️ Comandos Principales

| Comando | Descripción |
|---------|-------------|
| `/start` | Mensaje de bienvenida con historia y comandos |
| `/manual` | Envía este manual al usuario |
| `/status` | Muestra telemetría (CPU, RAM), estadísticas del wiki, latido, últimos logs |
| `/reporte` | Genera informe de auto-reflexión del agente |

---

### 📥 Ingesta y Datos

| Comando | Descripción |
|---------|-------------|
| `/ingest <url>` | Extrae contenido de una web y lo guarda en la biblioteca |
| `/sync_obsidian` | Escanea el vault local de Obsidian e indexa todas las notas `.md` |
| `/investigar <tema>` | Búsqueda profunda en internet con síntesis y fuentes, luego ingiere al wiki |
| Enviar **PDF** | Adjunta un PDF → Extrae texto y lo ingiere al wiki |
| Enviar **YouTube link** | Detecta enlace YouTube → Extrae transcripción y crea nota |

---

### 🔎 Consulta y RAG

| Comando | Descripción |
|---------|-------------|
| `/query <pregunta>` | Consulta la biblioteca local. (Consultas breves activan bypass de charla amigable) |
| `/hubs` | Identifica los conceptos centrales de tu conocimiento |
| `/clusters` | Visualiza comunidades temáticas en tus notas |
| `/lint` | Diagnóstico de salud del wiki (enlaces rotos, notas huérfanas) |

---

### 🕸️ Estructura y Grafo

| Comando | Descripción |
|---------|-------------|
| `/indexar_wiki` | Reconstruye el índice del grafo de conocimiento |
| `/query_vectorial <búsqueda>` | Búsqueda semántica en el índice vectorial |

---

### 🎭 Charla (5 Modos)

Usa `/charlar <tema>` para iniciar una conversación especializada:

| Modo | Emoji | Descripción |
|------|-------|-------------|
| **Charla Libre** | 💬 | Conversación natural, creativa e intelectualmente estimulante |
| **Consultor Estratégico** | 🧠 | Análisis en 3 fases: Definición → Ejecución → Evaluación |
| **Devil's Advocate** | 🔥 | Crítica implacable, encuentra fallos lógicos y riesgos ocultos |
| **Modo Socrático** | ❓ | Guía mediante preguntas profundas, nunca da respuestas directas |
| **Expansión Lateral** | 🌐 | Perspectivas radicales: chef, ecosistema, músico de jazz, tribu, algoritmo |

*Puedes guardar el resumen de cualquier charla en el wiki al finalizar.*

---

### ⚙️ Configuración

| Comando | Descripción |
|---------|-------------|
| `/model` | Muestra el backend actual (Ollama/Gemini) |
| `/model ollama` | Forzar modelo local Ollama |
| `/model gemini` | Forzar Gemini API |
| `/model auto` | Detección automática |

---

### 🤖 Modo Agente Autónomo

| Comando | Descripción |
|---------|-------------|
| `/agente [tarea]` | Activa el núcleo de razonamiento autónoma |

El agente puede:
- **Planificar**: Divide tareas complejas en pasos
- **Ejecutar**: Escribe código, manipula archivos, instala plugins
- **Aprobar**: Acciones críticas requieren tu confirmación vía botones en Telegram

---

## 🛠️ Skills del Agente

Los skills son herramientas especializadas que el agente puede usar:

| Skill | Función |
|-------|---------|
| `planning_skill` | Descompone tareas complejas en pasos accionables: `planning_skill.decompose_task(task)` |
| `wiki_healer_skill` | Repara notas huérfanas y reconecta conocimiento: `WikiHealerSkill().heal_orphans()` |
| `graphify_skill` | Analiza arquitectura de código: `graphify_skill.analyze(directory)` |
| `turboquant_skill` | Optimización y cuantización de modelos LLM |
| `memory_skill` | Gestión de memoria persistida |
| `git_installer` | Instalación y gestión de repositorios (clone, pip install) |
| `telegram_sender_skill` | Envío de archivos y reportes al usuario |
| `refactor_skill` | Refactorización de código |
| `academic_researcher_skill` | Búsqueda académica |
| `karpathy_guidelines` | Directrices de Andrej Karpathy para agentes |

---

## ⚙️ Configuración del Sistema

### Endpoints LLM

- **Ollama:** `qwen3:8b` (local, si está disponible)
- **Gemini:** API con rotación de claves

### Rutas (config.py)

- Wiki: `C:\Obsidian\wiki` (Windows) o configurable vía `.env`
- Raw: `C:\Obsidian\raw`
- Base de datos: `data/wiki.db`
- Índice vectorial: `data/vector.index`
- Logs: `data/agente.log`

### Variables de Entorno (.env)

```
GEMINI_KEYS=key1,key2,...
TELEGRAM_TOKEN=...
BRAVE_API_KEY=...
```

---

## 🔄 Background Rituals (El Latido)

El sistema ejecuta tareas automáticamente en segundo plano:

| Ritual | Frecuencia | Función |
|--------|------------|---------|
| 💓 **Heartbeat** | Cada 1 min | Actualiza `data/heartbeat.json` |
| 💉 **Sutura** | Cada 10 min | Sana notas huérfanas y reconecta ideas |
| 🕸️ **Grafo** | Cada 30 min | Actualiza el mapa de relaciones |
| 🌙 **Medianoche** | 03:00 AM | Mantenimiento profundo, graphify y escritura del "Resumen de Conciencia" |

---

## 🏗️ Arquitectura del Proyecto

```
Asubarnipal/
├── interface/
│ ├── telegram_bot.py # Bot Telegram + handlers
│ └── gracia.py # 5 modos de conversación
├── core/
│ ├── llm_router.py # Routing LLM (Gemini/Ollama)
│ ├── brave_counter.py # Contador Brave Search (1500/mes)
│ ├── background_manager.py
│ ├── dashboard_logic.py
│ ├── metrics.py
│ └── skill_registry.py
├── skills/ # 10 módulos de habilidades
├── storage/ # DB + writer markdown
├── index/ # Vector + graph
├── ingestion/ # Web, multimedia, search
├── app/
│ └── service.py # Servicio principal
├── data/ # Wiki, índices, logs, heartbeat
└── venv/ # Dependencias
```

---

## 📝 Schema del Wiki

Cada nota en el wiki sigue este schema (frontmatter obligatorio):

```yaml
---
tipo: source|entity|concept|synthesis|moc
fuente: "nombre de fuente o N/A"
fecha_ingesta: YYYY-MM-DD
fecha_actualizacion: YYYY-MM-DD
estado: draft|review|final
tags: [tag1, tag2]
relacionados: [[Nota1]], [[Nota2]]
---
```

### Convenciones de archivo

- **Fuentes crudas:** `/raw/` — INMUTABLES
- **Wiki generado:** `/wiki/` — El agente tiene control total
- **Notas de fuente:** `source_<hash>.md`
- **Páginas de entidad:** `entity_<nombre>.md`
- **Páginas de concepto:** `concept_<nombre>.md`
- **Síntesis:** `synthesis_<tema>.md`

---

## 🚀 Ejecución

```bash
# Iniciar el bot
python interface.telegram_bot

# O alternativamente (si existe)
python agente.py

# Dashboard Streamlit (opcional)
streamlit run dashboard_fixed.py

# Test de ingesta
python main.py
```

---

## ⚠️ Notas Importantes

1. **Brave Search:** 1500 llamadas/mes gratis. Al agotar, usa DuckDuckGo automáticamente.
2. **Contador Brave:** Se guarda en `data/brave_counter.json` y se resetea automáticamente cada mes.
3. **Ollama:** Si está corriendo, se usa por defecto para reducir costos.
4. **Wiki Schema:** Requiere frontmatter con `tipo`, `fuente`, `fecha_ingesta`, `estado`, `tags`, `relacionados`.
5. **Bypass RAG:** El sistema detecta automáticamente "charla inocua" (saludos, bromas) para evitar procesamientos pesados.
6. **PDF + YouTube:** Puedes enviar PDFs o enlaces de YouTube directamente al chat para ingestion automática.

---

## 📜 Historia

**Ashurbanipal** (rey asirio, 668-627 a.C.) fue el último gran rey del Imperio Asirio. Su legado más importante fue la **Biblioteca de Nínive**, la primera colección sistemática del mundo. Envió escribas por todo el mundo conocido con la orden: *"Traedme cada tablilla que encontréis"*.

Este bot es el heredero moderno de esa ambición: no guarda arcilla, guarda tu conocimiento digital.