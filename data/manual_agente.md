# 🧠 Manual de Referencia: Asubarnipal V2 (Imperial Edition)

Este documento es el registro maestro de capacidades, comandos y herramientas de Asubarnipal V2. Está diseñado para guiar tanto al usuario humano como al motor de razonamiento del bot.

---

## 1. Interfaz de Telegram: Comandos y Control

### 🛠️ Comandos de Ingesta y Datos
*   /ingest <url>: Extrae contenido de una web y lo guarda en la base de conocimientos.
*   /sync_obsidian: Escanea el vault local e indexa todas las notas .md.
*   /pdf (Adjunto): Extrae texto de documentos. Si incluyes un comentario (caption), el bot responderá dudas usando el documento como contexto.
*   *Enlaces de YouTube*: Envía un link de YouTube y el bot extraerá la transcripción automáticamente para sumarla a tu conocimiento.

### 🔎 Comandos de Consulta y RAG
*   /query <pregunta>: Consulta a la biblioteca local. (Nota: Consultas breves como "hola" activan el bypass de charla amigable para mayor velocidad).
*   /investigar <tema>: Búsqueda profunda en internet con síntesis y fuentes.
*   /status: *[NUEVO]* Informe de telemetría (CPU, RAM), estadísticas de la biblioteca y estado de los últimos rituales.
*   /manual: *[NUEVO]* Envía este documento directamente a tu chat de Telegram.

### 🕸️ Comandos de Estructura y Grafo
*   /hubs: Identifica los conceptos centrales de tu conocimiento.
*   /clusters: Visualiza comunidades temáticas en tus notas.
*   /lint: Diagnóstico de salud de la Wiki (enlaces rotos, notas huérfanas).

---

## 2. Motor de Conversación: /charlar

El comando /charlar <tema> permite diálogos profundos con 5 personalidades especializadas:
1.  *💬 Charla Libre*: Conversación natural.
2.  *🧠 Consultor Estratégico*: Análisis en 3 fases.
3.  *🔥 Devil's Advocate*: Crítica constructiva e implacable.
4.  *❓ Modo Socrático*: Guía mediante preguntas.
5.  *🌐 Expansión Lateral*: Perspectivas alternativas.

Puedes guardar el resumen de cualquier charla en tu Wiki al finalizar.

---

## 3. Modo Agente Autónomo: /agente

El comando /agente [tarea] activa el núcleo de razonamiento. El bot puede:
*   *Planificar*: Divide tareas complejas en pasos.
*   *Ejecutar*: Escribe código, manipula archivos e instala plugins.
*   *Aprobar*: Acciones críticas (como pip install) requieren tu confirmación vía botón en Telegram.

---

## 4. El Latido (BackgroundManager)

Asubarnipal nunca duerme. El motor de rituales se ejecuta en segundo plano:
*   💓 *Latido (Heartbeat)*: Actualiza data/heartbeat.json cada minuto.
*   💉 *Ritual de Sutura*: Cada 10 minutos sana notas huérfanas y conecta ideas.
*   🕸️ *Ritual de Grafo*: Cada 30 minutos actualiza el mapa de relaciones.
*   🌙 *Ritual de Medianoche (03:00 AM)*: Mantenimiento profundo, actualización de arquitectura (graphify) y escritura del "Resumen de Conciencia" en el Diario Maestro.

---

## 5. Catálogo de Skills (Herramientas del Agente)

### 📦 git_installer
*   clone_repo, execute_pip_install, install_skill_plugin.

### 📊 graphify_skill
*   Analiza arquitectura de código y genera reportes detallados.

### 💉 wiki_healer_skill
*   Detecta y reconecta automáticamente "islas" de conocimiento en la Wiki.

### 📤 telegram_sender_skill
*   Permite al agente enviarte archivos locales, reportes y manuales directamente.

### ⚖️ planning_skill
*   decompose_task: Toma una tarea compleja y la descompone en un plan de ejecución imperial con pasos lógicos, herramientas sugeridas y criterios de éxito.

### ⚡ turboquant_skill
*   Optimización de modelos LLM (1-bit, PolarQuant) y estrategias de cuantización.

---

## 6. Configuración de Sistema

*   /model [ollama|gemini|auto]: Cambia el backend global.
*   *Bypass RAG*: El sistema detecta automáticamente "charla inocua" para evitar procesamientos pesados en saludos o bromas.
*   *Dashboard Imperial*: Acceso local vía streamlit run dashboard_fixed.py para visualización avanzada de telemetría y grafos interactivos.