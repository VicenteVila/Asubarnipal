# 📖 Manual de Asubarnipal — Guía Completa

*El Legado de Nínive adaptado al siglo XXI*

---

## Índice

1. [Introducción](#1-introducción)
2. [Comandos de Sistema](#2-comandos-de-sistema)
3. [Comandos Wiki](#3-comandos-wiki)
4. [Ingesta de Contenido](#4-ingesta-de-contenido)
5. [Chat (/charlar)](#5-chat-charlar)
6. [Agente Autónomo](#6-agente-autónomo)
7. [H-Mem: Memoria Híbrida](#7-h-mem-memoria-híbrida)
8. [Vaults (Multi-Vault)](#8-vaults-multi-vault)
9. [Sesión y Chat](#9-sesión-y-chat)
10. [Configuración y Background Jobs](#10-configuración-y-background-jobs)
11. [Dashboard](#11-dashboard)
12. [Ejecución del Sistema](#12-ejecución-del-sistema)
13. [Skills del Agente](#13-skills-del-agente)

---

## 1. Introducción

Asubarnipal es un agente de conocimiento con arquitectura de dos modelos de IA:

```
PEQUEÑO (qwen2.5:1.5b) → Experto Bibliotecario → Busca y resume
GRANDE (qwen3.5:4b) → Analista → Responde con propuesta de investigación
```

**Sistema de memoria híbrido (H-Mem):** Combina un árbol temporal-semántico (como la memoria humana) con un grafo de entidades para dar al agente contexto de conversaciones anteriores.

Este manual puede consultarse con `/manual` en cualquier momento.

---

## 2. Comandos de Sistema

### 2.1 Comandos básicos

| Comando | Descripción | Ejemplo |
|---------|-------------|---------|
| `/start` | Mensaje de bienvenida con historia del bot | `/start` |
| `/manual` | Envía este manual al chat | `/manual` |
| `/status` | Telemetría: CPU, RAM, uptime, queries, tasa éxito, Brave restantes | `/status` |
| `/reporte` | Autodiagnóstico: uptime, queries, fallos, recursos, Brave, modelo, memoria | `/reporte` |
| `/model` | Muestra modelo actual. Con argumento, cambia de modelo | `/model` → muestra actual<br>`/model llama3:8b` → cambia |
| `/session` | Estado de sesión: mensajes, tokens, modo, modelo, límites | `/session` |
| `/clear_session` | Limpia historial de chat del usuario | `/clear_session` |

### 2.2 Salida esperada

**`/status`** devuelve:
```
🖥️ CPU: 12% | 💾 RAM: 4.2 GB
📊 Queries: 142 | ✅ Tasa éxito: 89%
🔍 Brave: 1,247 restantes
🤖 Agente: ONLINE (PID 1234, uptime 3h 22m)
📦 Vault activo: principal
```

---

## 3. Comandos Wiki

### 3.1 Consulta de conocimiento (/query)

**El comando más potente del bot.** Usa arquitectura de dos modelos:

```
/query <pregunta>
       ↓
📚 PEQUEÑO (qwen2.5:1.5b) → Busca en FTS5 → Resume con referencias
       ↓
🧠 GRANDE (qwen3.5:4b) → Genera respuesta + propuesta de investigación
       ↓
📋 Botones inline → Guardar / Crear nota / Standby
```

**Sintaxis:**
```
/query Qué es LoRA y cómo funciona?
/query En que consiste el entrenamiento con adapters?
/query Diferencias entre fine-tuning completo y LoRA
```

**Botones que aparecen después de cada respuesta:**

| Botón | Acción |
|-------|--------|
| 📊 Estructurada | Establece modo estructurado como preferido |
| 🧭 Exploratoria | Establece modo exploratorio como preferido |
| 💾 Guardar | Guarda la propuesta en memoria de investigaciones |
| 📝 Crear nota wiki | Crea una nota en el wiki con la propuesta |
| ⏸️ Standby | Guarda la propuesta para revisión posterior |

**两种 modos de propuesta:**

*Modo Estructurado:*
```
- Hallazgo: [qué se descubrió]
- Gap: [qué falta investigar]
- Impacto: [cómo mejora el bot]
- Prioridad: Alta/Media/Baja
- Acciones: 1. 2. 3.
- Métricas: [cómo medir éxito]
```

*Modo Exploratorio:*
```
- Temas relacionados encontrados
- Nuevas preguntas sugeridas
- Conexiones conceptuales
```

---

### 3.2 Exploración del wiki

| Comando | Descripción | Ejemplo |
|---------|-------------|---------|
| `/hubs` | Muestra los 10 conceptos más conectados del wiki | `/hubs` |
| `/clusters` | Muestra comunidades temáticas | `/clusters` |
| `/lint` | Diagnóstico de salud: score, entidades huérfanas, enlaces rotos | `/lint` |
| `/quality` | Calidad de ingestas recientes. Por defecto últimas 20 | `/quality 30` |

**`/hubs` salida:**
```
🕸️ Hubs — Conceptos Centrales

• Transformer (42 conexiones)
• LLM (38 conexiones)
• Attention (31 conexiones)
• RAG (27 conexiones)
• Agent (24 conexiones)
```

**`/quality` salida:**
```
📊 Calidad de Ingestas (últimas 20)

• Total ingesado: 20
• Score promedio: 78/100
• ⚠️ Baja calidad: 2

Por tipo:
📄 pdf: 8 ing., avg 82/100
🎬 youtube: 10 ing., avg 75/100
🌐 url: 2 ing., avg 70/100
```

---

### 3.3 Búsquedas especializadas

| Comando | Descripción | Ejemplo |
|---------|-------------|---------|
| `/queryhybrid <pregunta>` | Búsqueda híbrida SQLite + Obsidian vault. Alias: `/hybrid` | `/queryhybrid transformers attention` |
| `/query_vectorial <búsqueda>` | Búsqueda semántica en índice FAISS (embeddings) | `/query_vectorial redes neuronales recurrentes` |
| `/sync_obsidian` | Importa notas desde vault Obsidian externo | `/sync_obsidian` |
| `/indexar_wiki` | Reconstruye índice vectorial FAISS de todo el wiki | `/indexar_wiki` |

**¿Cuándo usar cada uno?**

| Comando | Cuándo usarlo |
|---------|---------------|
| `/query` | Preguntas sobre conceptos, necesita propuesta de investigación |
| `/queryhybrid` | Búsqueda rápida híbrida (SQLite + Obsidian) sin propuesta |
| `/query_vectorial` | Buscar por significado, no por palabras exactas |

---

## 4. Ingesta de Contenido

### 4.1 /ingest — Variantes

El bot ingiere contenido de múltiples fuentes y lo guarda automáticamente en wiki + SQLite + grafo:

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
| OCR con caption | Caption "ocr" + adjuntar imagen | Caption "ocr" + imagen |

**Pipeline de ingesta:**
```
1. Descarga y limpia HTML / extrae PDF / transcript de video
2. Detecta idioma
3. Traduce al español (si es necesario)
4. Genera resumen via LLM
5. Extrae conceptos clave y entidades
6. Busca notas relacionadas en wiki
7. Guarda en:
   ├─→ SQLite (data/wiki.db)      → /query encuentra inmediatamente
   ├─→ Obsidian wiki/*.md          → Dashboard Wiki muestra inmediatamente
   └─→ Propuesta de investigación → Sugiere próxima investigación
```

### 4.2 /investigar — Investigación profunda

Usa Brave Search para investigar un tema y ingiere automáticamente los mejores resultados:

| Sintaxis | Ejemplo |
|----------|---------|
| `/investigar <tema>` | `/investigar transformers attention mechanism 2024` |

**Salida:**
```
🔍 Investigando: transformers attention mechanism 2024

Encontrados 8 artículos relevantes:
1. [Paper] "Attention Is All You Need" → guardado
2. [Web] Tutorial sobre transformers → guardado
3. [Paper] "FlashAttention" → guardado
...
✅ Investigación completada. 8 fuentes ingestadas.
```

---

## 5. Chat (/charlar)

Usa `/charlar <modo> <tema>` para chatear en diferentes estilos especializados.

### 5.1 Los 5 modos

| Modo | Emoji | Descripción | Ejemplo |
|------|-------|-------------|---------|
| **libre** | 💬 | Conversación natural y creativa | `/charlar libre qué opinas de la IA generativa?` |
| **consultor** | 🧠 | Análisis en 3 fases: Definición → Ejecución → Evaluación | `/charlar consultor cómo optimizar este código?` |
| **devil** | 🔥 | Crítica implacable: encuentra fallos, riesgos, contradicciones | `/charlar devil es buena idea este producto?` |
| **socrático** | ❓ | Guía mediante preguntas, no da respuestas directas | `/charlar socrático qué es la consciencia?` |
| **lateral** | 🌐 | 5 perspectivas: Chef, Músico, Tribu, Algoritmo, Niño de 5 años | `/charlar lateral cómo lo vería un ninja?` |

### 5.2 Cómo elegir el modo

| Situación | Modo recomendado |
|---------|-------------------|
| Conversación casual, brainstorm | `libre` |
| Resolver un problema técnico, revisar código | `consultor` |
| Evaluar riesgos de una decisión, producto, plan | `devil` |
| Aprender un concepto nuevo, explorar ideas | `socrático` |
| Salir del pensamiento lineal, ver problema desde otro ángulo | `lateral` |

### 5.3 Ejemplos de cada modo

```
/charlar libre ¿Qué tendencias de IA son más relevantes para 2025?
  → Respuesta creativa, abierta, opinionada

/charlar consultor Optimiza esta función Python para reducir memoria
  → Fase 1: Definir el problema
  → Fase 2: Proponer soluciones
  → Fase 3: Evaluar pros/contras

/charlar devil Analiza los riesgos de usar LLMs para decisiones médicas
  → Crítica implacable: riesgos legales, técnicos, éticos

/charlar socrático Qué es el aprendizaje por refuerzo?
  → Te guía con preguntas: "¿Qué significa aprender?", "¿Cómo definirías refuerzo?"

/charlar lateral Cómo percibe un músico este problema de arquitectura?
  → Perspectivas: Chef 💭, Músico 🎵, Tribu 🏛️, Algoritmo ⚙️, Niño 👦
```

---

## 6. Agente Autónomo

### 6.1 Comandos de agente

| Comando | Descripción | Ejemplo |
|---------|-------------|---------|
| `/agente <tarea>` | Agente autónomo con ejecución de skills/herramientas | `/agente revisa el código y propon mejoras` |
| `/rate <1-5>` | Califica la última respuesta (1=Muy malo, 5=Excelente) | `/rate 4` |
| `/calidad` | Estadísticas: accuracy, promedio, conteos sí/no/ms, alertas | `/calidad` |

### 6.2 Cómo funciona /agente

El agente puede razonar de forma autónoma y ejecutar skills (funciones del sistema):

```
/agente revisa los últimos cambios en el proyecto y haz un resumen
       ↓
1. Lee archivos del proyecto
2. Analiza patrones
3. Ejecuta skills: run_command, read_file, write_file
4. Genera resumen con findings y propuestas
```

**¿Qué puede hacer el agente?**
- Leer y escribir archivos
- Ejecutar comandos del sistema
- Buscar en archivos
- Gestionar el wiki
- Clonar repositorios GitHub
- Traducir textos
- Ejecutar código Python

### 6.3 Calificar respuestas

Después de cada respuesta, el bot pregunta: *¿La respuesta fue precisa? (sí/no/ms)*

También puedes calificar manualmente:
```
/rate 5   → Excelente
/rate 3   → Aceptable
/rate 1   → Muy malo
```

---

## 7. H-Mem: Memoria Híbrida

### 7.1 ¿Qué es?

H-Mem es un **sistema de memoria conversacional** que da al agente contexto de lo que hablaste antes. Funciona en segundo plano — automáticamente.

Combina dos estructuras:

**Árbol Temporal-Semántico** (como la memoria humana):
```
L0 → events (1 día)
L1 → daily (7 días)
L2 → weekly (30 días)
L3 → monthly (90 días)
```
Las memorias nuevas entran en L0 y suben automáticamente si se consolidan.

**Grafo de Entidades** (red de conceptos):
```
Entidades: persona, organización, concepto, evento, tema, proyecto
Relaciones: related_to, works_on, part_of, depends_on...
```

### 7.2 Comandos H-Mem

| Comando | Descripción | Ejemplo |
|---------|-------------|---------|
| `/memoria` | Estado del sistema H-Mem | `/memoria` |
| `/recordar <texto>` | Guarda un recuerdo. Extrae entidades automáticamente | `/recordar El usuario trabaja en el proyecto Alpha` |
| `/pensar <pregunta>` | Consulta H-Mem con respuesta del LLM | `/pensar Sobre qué hablamos ayer?` |
| `/contexto <query>` | Obtiene contexto para usar en prompts | `/contexto proyectos de IA` |
| `/entidades` | Muestra hubs del grafo de entidades (top 8) | `/entidades` |
| `/recientes [n]` | Lista memorias recientes (default 10, max 30) | `/recientes 20` |

### 7.3 ¿Qué ganas con H-Mem?

| Capacidad | Sin H-Mem | Con H-Mem |
|-----------|-----------|-----------|
| Contexto de chats anteriores | ❌ Ninguno | ✅ Relevante |
| Seguimiento de entidades | ❌ Ninguno | ✅ Nombres, relaciones |
| Relevancia temporal | ❌ Ninguna | ✅ Reciente vs antiguo |
| Robustez de memoria | ❌ Ninguna | ✅ Memorias importantes pesan más |
| Razonamiento multi-hop | ❌ Ninguno | ✅ Conecta conceptos distantes |

**Ejemplo concret:**

```
Sin H-Mem:
  Usuario: "¿Qué discutimos sobre Python?"
  Bot: "No tengo información sobre esa conversación." ❌

Con H-Mem:
  Usuario: "¿Qué discutimos sobre Python?"
  Bot: "Según nuestra conversación del [fecha], hablamos sobre
        Python como lenguaje para IA. Mencionaste que trabajas
        en un proyecto con vectores de 512 dimensiones..." ✅
```

### 7.4 Integración automática

H-Mem funciona **automáticamente** en cada mensaje:

```
1. Antes de responder → busca contexto relevante en memoria
2. Después de responder → guarda la conversación
3. Siempre → extrae entidades y las conecta en el grafo
```

**No necesitas invocarlo manualmente** — cada vez que chateas, el bot aprende.

### 7.5 Ejemplos

```
/memoria
  → Muestra: nodos por nivel, entidades por tipo, pesos de ranking

/recordar El usuario prefiere respuestas técnicas con ejemplos de código
  → Guarda el recuerdo + extrae entidad "usuario" tipo "preference"

/pensar Qué sabes sobre proyectos de machine learning?
  → Busca en árbol + grafo → genera respuesta con contexto histórico

/contexto vector embeddings
  → Devuelve contexto relevante para usar en prompts (preview 1000 chars)

/entidades
  → Muestra: Python (12 menciones), ProyectoAlpha (8), IA (15)...
```

### 7.6 Diferencia con otros sistemas

| Sistema | Qué almacena | Cuándo lo usas |
|---------|-------------|----------------|
| **H-Mem** | Conversaciones y entidades | `/recordar`, `/pensar`, chats automáticos |
| **Wiki (/query)** | Notas estructuradas, papers, conceptos | `/query` para buscar conocimiento |
| **RAG (/query_vectorial)** | Documentos indexados por embeddings | Búsqueda semántica |
| **ProposalMemory** | Propuestas de investigación | `/query` + botón "Guardar" |

H-Mem no reemplaza a ninguno — complementa el sistema con **memoria conversacional**.

---

## 8. Vaults (Multi-Vault)

### 8.1 Comandos de gestión

| Comando | Descripción | Ejemplo |
|---------|-------------|---------|
| `/vaults` | Lista todos los vaults con stats | `/vaults` |
| `/vault_create <nombre>` | Crea nuevo vault (con confirmación) | `/vault_create investigacion_ia` |
| `/vault_use <nombre>` | Cambia vault activo. Todos los comandos wiki usan este | `/vault_use investigacion_ia` |
| `/vault_info` | Detalles del vault activo: nombre, path, DB, estadísticas | `/vault_info` |
| `/vault_delete <nombre>` | Elimina vault (con backup automático) | `/vault_delete antiguo` |
| `/vault_export [nombre]` | Exporta vault a JSON (sin args = activo) | `/vault_export ia` |
| `/vault_import <nombre> <ruta>` | Importa desde JSON | `/vault_import ia backup.json` |
| `/vault_connect <ruta> [nombre]` | Conecta vault Obsidian externo | `/vault_connect /mnt/Obsidian/proyecto` |
| `/vault_disconnect [nombre]` | Desconecta vault | `/vault_disconnect proyecto` |

### 8.2 Ejemplo de flujo

```
/vaults                              → Ver todos los vaults
/vault_create proyectos              → Crear nuevo vault
/vault_use proyectos                 → Cambiar al vault proyectos
/ingest https://arxiv.org/...        → Ingestar al vault activo
/query En que consiste RAG?          → Buscar en el vault activo
/vault_export proyectos              → Exportar a JSON
/vault_import proyectos backup.json → Importar desde JSON
```

### 8.3 Características

- **Vaults únicos**: Cada vault tiene su propia DB (`data/wiki_{nombre}.db`)
- **RAG separado**: Cada vault tiene su propio índice FAISS
- **Switch dinámico**: Cambia entre vaults sin reiniciar
- **Backup automático**: Al eliminar se crea backup en `data/backups/`
- **Vault principal**: Se crea automáticamente. No se puede eliminar

---

## 9. Sesión y Chat

### 9.1 Estado de sesión

| Comando | Descripción |
|---------|-------------|
| `/session` | Muestra: mensajes, tokens, modo, modelo, límites |
| `/clear_session` | Limpia el historial de chat del usuario |

### 9.2 Auto-detección

El bot detecta automáticamente estos patrones:

| Input | Acción |
|-------|---------|
| `http://...` (URL) | Auto-ingest de la URL |
| `sí/si/yes/y` | Registra evaluación positiva |
| `no/n` | Registra evaluación negativa |
| `ms/más o menos` | Registra evaluación neutral |
| `hola/buenas/hi` | Respuesta breve sin RAG (bypass) |
| Sesión pendiente + `sí` | Restaura historial de chat |
| Sesión pendiente + `no` | Limpia sesión guardada |

---

## 10. Configuración y Background Jobs

### 10.1 Endpoints LLM

- **Ollama:** `qwen3.5:4b` (local, configurable con `/model`)
- **Gemini:** Rotación automática entre claves configuradas

### 10.2 Background Rituals

| Ritual | Frecuencia | Función |
|--------|-------------|---------|
| 💓 **Heartbeat** | 60s | Registra CPU%, RAM% → `data/heartbeat.json` |
| 💉 **Sutura** | 10min | Limpia huérfanas, repara enlaces del wiki |
| 🕸️ **Grafo** | 30min | Reconstruye relaciones vectoriales |

### 10.3 TurboQuant

Optimiza automáticamente los parámetros de inferencia según el modo de chat:

| Modo | Primary | Fallback 1 | Fallback 2 |
|------|---------|------------|-------------|
| **libre** | qwen3.5:4b | qwen3:8b | gemma4:e4b |
| **consultor** | qwen3:8b | qwen3.5:9b | gemma4:e4b |
| **devil** | gemma4:e4b | qwen3:8b | qwen3.5:9b |
| **socrático** | qwen3.5:4b | qwen3:8b | qwen3.5:9b |
| **lateral** | qwen3.5:9b | qwen3:8b | qwen3.5:4b |

Si el modelo primario falla, prueba los fallbacks secuencialmente.

---

## 11. Dashboard

El dashboard de Streamlit proporciona interfaz visual para monitorizar y gestionar el sistema. Accede desde navegador en `http://localhost:8501`.

### 11.1 Pestañas disponibles

| # | Pestaña | Descripción |
|---|---------|-------------|
| 1 | **Dashboard** | Telemetría, KPI cards, gráficos CPU/RAM |
| 2 | **Wiki** | Inventario, timeline, propuestas de investigación, fuentes RAW |
| 3 | **Grafo** | Visualización del grafo, comunidades, hubs |
| 4 | **Logs** | Logs en tiempo real, filtrables |
| 5 | **Salud** | Diagnóstico: notas sin tags, stale, huérfanas |
| 6 | **Schema** | Viewer del CLAUDE.md |
| 7 | **Latido** | Configuración de background rituals |
| 8 | **Feeds** | Suscripciones RSS, alertas |
| 9 | **Analytics** | Historial de comandos, top comandos |
| 10 | **H-Mem** | Estado de memoria híbrida, árboles, grafos de entidades |

### 11.2 Propuestas de Investigación (Wiki tab)

Desde la pestaña Wiki del dashboard:

- **Stats**: propuestas activas, standby, archivadas
- **Modo preferido**: elige 📊 Estructurada o 🧭 Exploratoria
- **Lista de propuestas**: tabs para filtrar por estado
- **Acciones**: archivar, guardar en wiki, restaurar, eliminar

---

## 12. Ejecución del Sistema

```bash
# Agente Telegram (requiere TELEGRAM_TOKEN)
python -m interface.telegram_bot

# Dashboard Streamlit (abre en navegador)
streamlit run dashboard.py

# API REST (opcional, puerto 8000)
python -m api.main
```

---

## 13. Skills del Agente

El agente puede ejecutar funciones automáticamente cuando usas `/agente`. Disponibles:

### Archivo
| Función | Descripción |
|---------|-------------|
| `run_command` | Ejecuta comandos del sistema |
| `read_file` | Lee archivos |
| `write_file` | Escribe archivos |
| `list_files` | Lista archivos en directorio |
| `search_in_files` | Busca texto en archivos |

### LLM
| Función | Descripción |
|---------|-------------|
| `list_ollama_models` | Lista modelos Ollama disponibles |
| `pull_ollama_model` | Descarga un modelo Ollama |

### Sistema
| Función | Descripción |
|---------|-------------|
| `get_system_info` | Información del sistema |
| `get_env` | Obtiene variable de entorno |
| `set_env` | Establece variable de entorno |
| `check_service` | Verifica si un servicio está corriendo |

### Wiki
| Función | Descripción |
|---------|-------------|
| `get_wiki_stats` | Estadísticas del wiki |
| `search_wiki` | Busca en el wiki |
| `create_wiki_note` | Crea nota en el wiki |

### H-Mem
| Función | Descripción |
|---------|-------------|
| `hmem_remember` | Guarda en memoria híbrida |
| `hmem_recall` | Recupera de memoria |
| `hmem_think` | Query + respuesta del LLM |
| `hmem_get_context` | Contexto para prompts |
| `hmem_get_stats` | Estadísticas del sistema |
| `hmem_get_recent` | Memorias recientes |

### Research
| Función | Descripción |
|---------|-------------|
| `search_arxiv` | Busca en arXiv |
| `get_audio_summary` | Resume audio/video |

### GitHub
| Función | Descripción |
|---------|-------------|
| `clone_repo` | Clona repositorio Git |

### Traducción
| Función | Descripción |
|---------|-------------|
| `translate` | Traduce texto |
| `detect_language` | Detecta idioma |

### Python
| Función | Descripción |
|---------|-------------|
| `execute_python` | Ejecuta código Python |
| `install_package` | Instala paquete pip |

### Vault
| Función | Descripción |
|---------|-------------|
| `list_vaults` | Lista todos los vaults |
| `create_vault` | Crea nuevo vault |
| `switch_vault` | Cambia vault activo |
| `delete_vault` | Elimina vault (con backup) |
| `export_vault` | Exporta a JSON |
| `import_vault` | Importa desde JSON |

### TurboQuant
| Función | Descripción |
|---------|-------------|
| `optimize_llm` | Aplica settings según modo |
| `show_turbo_status` | Muestra estado actual |
| `benchmark_llm` | Benchmark de latencia |
| `get_recommended_context` | Calcula óptimo por modelo |

---

## 📜 Historia

**Ashurbanipal** (rey asirio, 668-627 a.C.) fue el último gran rey del Imperio Asirio. Su legado: la **Biblioteca de Nínive**, la primera colección sistemática del mundo. Su orden: *"Traedme cada tablilla que encontréis"*.

Este bot es el heredero moderno: no guarda arcilla, guarda conocimiento digital.