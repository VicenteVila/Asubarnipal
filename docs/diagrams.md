# Diagramas de Flujo de Datos

Este documento contiene diagramas de arquitectura del sistema Asubarnipal.

## Diagrama 1: Flujo de un mensaje de Telegram

```mermaid
sequenceDiagram
    participant User as Usuario Telegram
    participant Bot as telegram_bot.py
    participant Handlers as handlers/
    participant Service as app/service.py
    participant LLM as LLMRouter
    participant Wiki as core/wiki.py

    User->>Bot: /query "python"
    Bot->>Handlers: routing por comando
    Handlers->>Wiki: wiki.search("python")
    Wiki-->>Handlers: [{"name": "Python", "tipo": "concept"}]
    Handlers-->>Bot: resultados formateados
    Bot-->>User: "🔎 Resultados para: python"
```

## Diagrama 2: Flujo del Agente Autónimo

```mermaid
flowchart TD
    A[Telegram: /agente <tarea>] --> B[agent_chat]
    B --> C[RAG search]
    C --> D[SkillRegistry.get_tools]
    D --> E{LLM Router}
    E -->|Ollama| F[Ollama API]
    E -->|Gemini| G[Gemini API]
    F -->|response| H[tool_calls?]
    G -->|response| H
    H -->|Sí| I[Ejecutar tools]
    I --> J[Loop: call_agent]
    H -->|No| K[Respuesta final]
    J --> E
    K --> L[Enviar a Telegram]
```

## Diagrama 3: Arquitectura de Background Rituals

```mermaid
flowchart LR
    subgraph BackgroundManager
        A[Heartbeat 60s] --> B[CPU/RAM]
        C[Suture 10min] --> D[Wiki Repair]
        E[Graph 30min] --> F[Vector Index]
    end

    subgraph Dashboard
        B --> G[heartbeat.json]
        D --> H[wiki.db]
        F --> I[knowledge_graph.json]
    end

    G --> J[Streamlit Dashboard]
    H --> J
    I --> J
```

## Diagrama 4: Flujo de Ingesta de URL

```mermaid
flowchart TD
    A[/ingest <url>] --> B[requests.get]
    B --> C{Status 200?}
    C -->|No| D[Error: HTTP]
    C -->|Sí| E[BeautifulSoup]
    E --> F[Limpiar HTML]
    F --> G[Detectar idioma]
    G --> H{Traducir?}
    H -->|Sí| I[Google Translator]
    H -->|No| J[Continuar]
    I --> J
    J --> K[LLM: generar resumen]
    K --> L[Extraer conceptos]
    L --> M[Crear entidades]
    M --> N[Relacionar notas]
    N --> O[Commit SQLite]
    O --> P[Respuesta a Telegram]
```

## Diagrama 5: Sistema de Chat Modes

```mermaid
flowchart TD
    A[/charlar <modo> <tema>] --> B{Modo válido?}
    B -->|No| C[Mostrar modos]
    B -->|Sí| D{Seleccionar modo}
    D -->|libre| E[Conversación natural]
    D -->|consultor| F[3 fases]
    D -->|devil| G[Crítica implacable]
    D -->|socrático| H[Preguntas]
    D -->|lateral| I[5 perspectivas]

    E --> J[AgentService]
    F --> J
    G --> J
    H --> J
    I --> J

    J --> K[LLM con system prompt]
    K --> L[Respuesta Telegram]
```

## Diagrama 6: Estructura de datos del Wiki

```mermaid
erDiagram
    ENTITIES {
        int id PK
        string name
        string content
        string tipo
        string fuente
        string tags
        string relacionados
    }

    RELATIONS {
        int id PK
        int from_entity FK
        int to_entity FK
        string relation_type
    }

    RAW_SOURCES {
        int id PK
        string source_hash
        string original_name
        string content
        string ingested_at
    }

    ENTITIES ||--o{ RELATIONS : "has"
    ENTITIES ||--o{ RAW_SOURCES : "sources"
```

## Diagrama 7: Pipeline de RAG

```mermaid
flowchart LR
    subgraph Indexación
        A[Docs] --> B[sentence-transformers]
        B --> C[Embeddings 384d]
        C --> D[FAISS Index]
    end

    subgraph Búsqueda
        E[Query] --> F[sentence-transformers]
        F --> G[Query Embedding]
        G --> H[FAISS search]
        H --> I[Top-K docs]
    end

    subgraph Recuperación
        I --> J[Contexto]
        J --> K[LLM prompt]
    end

    K --> L[Respuesta]
```

## Leyenda

- `→` Flujo principal
- `-->` Retorno de datos
- `{}` Decisión/condición
- `[]` Proceso
- `||--o{` Relación SQL