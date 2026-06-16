# Issues Sugeridos - Roadmap de Optimización Arquitectónica

Este documento contiene los issues sugeridos para implementar el roadmap de optimización. Puedes crearlos manualmente en GitHub copiando los títulos y descripciones.

**Referencia**: [ROADMAP-ARQUITECTURA.md](./ROADMAP-ARQUITECTURA.md)

---

## Fase 1: Validación Estricta de Ingesta (ALTA PRIORIDAD)

### Issue 1.1: Definir esquemas YAML para validación de fuentes

**Título**: `feat: definir esquemas YAML para validación de ingesta`

**Etiquetas**: `enhancement`, `phase-1`, `high-priority`

**Descripción**:
```
## Objetivo
Crear esquemas YAML para validar metadatos de cada tipo de fuente durante la ingesta.

## Especificación
Crear los siguientes archivos:
- `core/wiki/schemas/url.yaml`
- `core/wiki/schemas/pdf.yaml`
- `core/wiki/schemas/youtube.yaml`

Cada esquema debe definir:
- Campos obligatorios y opcionales
- Tipos de datos
- Validaciones (longitud, formato, rangos)
- Valores por defecto

## Referencia
Ver [FASE-1-VALIDACION-INGESTA.md](./docs/FASE-1-VALIDACION-INGESTA.md) sección 1.1

## Criterios de aceptación
- [ ] Esquemas YAML creados para los 3 tipos de fuente
- [ ] Validaciones definidas para cada campo
- [ ] Documentación de esquemas en comentarios YAML

## Estimación
4 horas
```

---

### Issue 1.2: Implementar validador de esquemas

**Título**: `feat: implementar validador de esquemas para ingesta`

**Etiquetas**: `enhancement`, `phase-1`, `high-priority`

**Descripción**:
```
## Objetivo
Implementar módulo que valide datos contra esquemas YAML antes y después de la ingesta.

## Especificación
Crear `core/wiki/validators.py` con:
- `validar_esquema(datos, tipo)`: Valida contra esquema YAML
- `validar_antes_de_ingesta(datos, tipo)`: Validación pre-ingesta
- `validar_despues_de_ingesta(entidad_id)`: Validación post-ingesta

## Dependencias
- Issue #1.1 (esquemas YAML)
- PyYAML

## Referencia
Ver [FASE-1-VALIDACION-INGESTA.md](./docs/FASE-1-VALIDACION-INGESTA.md) sección 4

## Criterios de aceptación
- [ ] Funciones de validación implementadas
- [ ] Tests unitarios (cobertura > 90%)
- [ ] Integración con flujos de ingesta

## Estimación
6 horas
```

---

### Issue 1.3: Implementar extractor de citas

**Título**: `feat: implementar extractor de citas de documentos`

**Etiquetas**: `enhancement`, `phase-1`, `high-priority`

**Descripción**:
```
## Objetivo
Extraer citas de documentos durante la ingesta y estructurarlas.

## Especificación
Crear `core/wiki/citation_extractor.py` con:
- `extraer_citas(texto)`: Extrae todas las citas del texto
- `parsear_cita(cita_texto)`: Parsea componentes de una cita
- Soporte para formatos: APA, MLA, Chicago, IEEE

## Referencia
Ver [FASE-1-VALIDACION-INGESTA.md](./docs/FASE-1-VALIDACION-INGESTA.md) sección 2.1

## Criterios de aceptación
- [ ] Extractor funcional para los 4 formatos principales
- [ ] Tests con documentos de ejemplo
- [ ] Integración con flujos de ingesta

## Estimación
8 horas
```

---

### Issue 1.4: Implementar verificador de citas

**Título**: `feat: implementar verificador de citas con APIs externas`

**Etiquetas**: `enhancement`, `phase-1`, `high-priority`

**Descripción**:
```
## Objetivo
Verificar que las citas extraídas existen y son accesibles.

## Especificación
Crear `core/wiki/citation_verifier.py` con:
- `verificar_cita(cita)`: Verifica una cita individual
- `verificar_citas_batch(citas)`: Verifica múltiples citas
- Integraciones:
  - CrossRef API (para DOIs)
  - Google Scholar API (opcional)
  - Base de datos local (wiki.db)

## Dependencias
- Issue #1.3 (extractor de citas)

## Referencia
Ver [FASE-1-VALIDACION-INGESTA.md](./docs/FASE-1-VALIDACION-INGESTA.md) sección 2.2

## Criterios de aceptación
- [ ] Verificador funcional con CrossRef API
- [ ] Fallback a búsqueda local
- [ ] Caché de verificaciones (evitar re-verificar)
- [ ] Tests con citas reales

## Estimación
10 horas
```

---

### Issue 1.5: Implementar calculadores de score de calidad

**Título**: `feat: implementar calculadores de score de calidad por tipo`

**Etiquetas**: `enhancement`, `phase-1`, `high-priority`

**Descripción**:
```
## Objetivo
Calcular score de calidad (0-100) para cada entidad ingestada.

## Especificación
Crear `core/wiki/quality_scorer.py` con:
- `calcular_score_url(entidad)`: Score para URLs
- `calcular_score_pdf(entidad)`: Score para PDFs
- `calcular_score_youtube(entidad)`: Score para YouTube
- `calcular_metricas_citas(entidad)`: Métricas de citas

## Factores de scoring
Ver [FASE-1-VALIDACION-INGESTA.md](./docs/FASE-1-VALIDACION-INGESTA.md) sección 3.1

## Dependencias
- Issue #1.4 (verificador de citas)

## Criterios de aceptación
- [ ] Calculadores implementados para los 3 tipos
- [ ] Score almacenado en base de datos
- [ ] Tests con entidades de ejemplo

## Estimación
6 horas
```

---

### Issue 1.6: Integrar validación en flujos de ingesta

**Título**: `feat: integrar validación de calidad en flujos de ingesta`

**Etiquetas**: `enhancement`, `phase-1`, `high-priority`

**Descripción**:
```
## Objetivo
Integrar validación de esquemas, citas y calidad en los flujos de ingesta existentes.

## Especificación
Modificar `core/wiki/ingest.py`:
- `ingest_url()`: Añadir validación pre y post-ingesta
- `ingest_pdf()`: Añadir validación pre y post-ingesta
- `_ingest_youtube()`: Añadir validación pre y post-ingesta

## Flujo
1. Validar esquema antes de ingestar
2. Ejecutar ingesta
3. Extraer y verificar citas
4. Calcular score de calidad
5. Actualizar métricas en base de datos

## Dependencias
- Issues #1.2, #1.3, #1.4, #1.5

## Referencia
Ver [FASE-1-VALIDACION-INGESTA.md](./docs/FASE-1-VALIDACION-INGESTA.md) sección 4

## Criterios de aceptación
- [ ] Validación integrada en los 3 flujos
- [ ] Score de calidad calculado automáticamente
- [ ] Citas verificadas durante ingesta
- [ ] Tests de integración

## Estimación
8 horas
```

---

### Issue 1.7: Añadir comandos de validación

**Título**: `feat: añadir comandos de validación y calidad`

**Etiquetas**: `enhancement`, `phase-1`, `high-priority`

**Descripción**:
```
## Objetivo
Añadir comandos Telegram para validar y consultar calidad de entidades.

## Especificación
Añadir a `interface/handlers/wiki.py`:
- `/validar <id>`: Valida una entidad específica
- `/calidad <id>`: Muestra score de calidad
- `/citas <id>`: Muestra métricas de citas
- `/calidad_stats`: Muestra estadísticas globales de calidad

## Dependencias
- Issue #1.6 (integración en flujos)

## Criterios de aceptación
- [ ] 4 comandos implementados
- [ ] Respuestas formateadas correctamente
- [ ] Tests de comandos

## Estimación
6 horas
```

---

### Issue 1.8: Crear dashboard de calidad

**Título**: `feat: crear dashboard de calidad de ingesta`

**Etiquetas**: `enhancement`, `phase-1`, `high-priority`

**Descripción**:
```
## Objetivo
Crear tab de dashboard para visualizar métricas de calidad.

## Especificación
Crear `dashboard/tabs/tab_calidad.py`:
- Score de calidad promedio
- Distribución de scores por tipo
- Porcentaje de citas verificadas
- Citas huérfanas
- Evolución temporal de calidad

## Dependencias
- Issue #1.6 (integración en flujos)

## Criterios de aceptación
- [ ] Dashboard funcional en Streamlit
- [ ] Gráficos de métricas principales
- [ ] Filtros por tipo y fecha
- [ ] Integración con tabs existentes

## Estimación
8 horas
```

---

## Fase 2: Aceleración de TurboQuant (PRIORIDAD MEDIA)

### Issue 2.1: Instalar PyTorch y dependencias

**Título**: `feat: instalar PyTorch y librerías de cuantización`

**Etiquetas**: `enhancement`, `phase-2`, `medium-priority`

**Descripción**:
```
## Objetivo
Instalar PyTorch y librerías necesarias para cuantización.

## Especificación
Añadir a `requirements.txt`:
- torch>=2.0.0
- torchvision
- torchaudio
- bitsandbytes>=0.41.0
- accelerate>=0.24.0
- transformers>=4.35.0

## Instalación
```bash
# Con CUDA 11.8
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
pip install bitsandbytes accelerate transformers
```

## Verificación
Crear script de verificación que compruebe:
- PyTorch instalado correctamente
- CUDA disponible (si aplica)
- Librerías de cuantización funcionales

## Criterios de aceptación
- [ ] Dependencias instaladas
- [ ] Script de verificación funcional
- [ ] Documentación de instalación

## Estimación
2 horas
```

---

### Issue 2.2: Crear adaptador GGUF → PyTorch

**Título**: `feat: crear adaptador para convertir modelos GGUF a PyTorch`

**Etiquetas**: `enhancement`, `phase-2`, `medium-priority`

**Descripción**:
```
## Objetivo
Crear adaptador que permita cargar modelos GGUF en PyTorch.

## Especificación
Crear `core/turboquant/pytorch_adapter.py`:
- Clase `PyTorchModelAdapter`
- Métodos:
  - `load()`: Carga y convierte modelo
  - `_extract_weights()`: Extrae pesos de GGUF
  - `_create_pytorch_model()`: Crea modelo PyTorch

## Dependencias
- Issue #2.1 (PyTorch instalado)

## Referencia
Ver [FASE-2-TURBOQUANT.md](./docs/FASE-2-TURBOQUANT.md) sección 1.2

## Criterios de aceptación
- [ ] Adaptador funcional para al menos 1 arquitectura
- [ ] Tests con modelo de prueba
- [ ] Documentación de uso

## Estimación
12 horas
```

---

### Issue 2.3: Implementar cuantización asimétrica de 4 bits

**Título**: `feat: implementar cuantización asimétrica de 4 bits`

**Etiquetas**: `enhancement`, `phase-2`, `medium-priority`

**Descripción**:
```
## Objetivo
Implementar cuantización de 4 bits con rangos asimétricos.

## Especificación
Crear `core/turboquant/quantizer.py`:
- Clase `AsymmetricQuantizer`
- Métodos:
  - `quantize(tensor)`: Cuantiza a 4 bits
  - `dequantize(tensor, min, max)`: Dequantiza a float32

## Fórmula
```
v_q = round((v - min) / (max - min) * 15)
```

## Dependencias
- Issue #2.1 (PyTorch instalado)

## Referencia
Ver [FASE-2-TURBOQUANT.md](./docs/FASE-2-TURBOQUANT.md) sección 2.1

## Criterios de aceptación
- [ ] Cuantización funcional
- [ ] Error de cuantización < 5%
- [ ] Tests unitarios completos
- [ ] Benchmark de precisión

## Estimación
8 horas
```

---

### Issue 2.4: Implementar kernels CUDA optimizados

**Título**: `feat: implementar kernels CUDA para cuantización`

**Etiquetas**: `enhancement`, `phase-2`, `medium-priority`

**Descripción**:
```
## Objetivo
Implementar kernels CUDA para acelerar cuantización en GPU.

## Especificación
Crear:
- `core/turboquant/cuda/quantize.cu`: Kernel CUDA
- `core/turboquant/cuda/quantize_wrapper.cpp`: Wrapper C++
- Integración con PyTorch vía `torch.utils.cpp_extension`

## Kernels a implementar
- `quantize_4bit_kernel`: Cuantización de tensores
- `dequantize_4bit_kernel`: Dequantización de tensores

## Dependencias
- Issue #2.3 (cuantización CPU)
- CUDA 11.8+ instalado

## Referencia
Ver [FASE-2-TURBOQUANT.md](./docs/FASE-2-TURBOQUANT.md) sección 3.1

## Criterios de aceptación
- [ ] Kernels CUDA compilados
- [ ] Speedup > 5x vs CPU
- [ ] Tests de correctness
- [ ] Fallback a CPU si CUDA no disponible

## Estimación
10 horas
```

---

### Issue 2.5: Implementar caché de KV con eviction

**Título**: `feat: implementar caché de KV con políticas de eviction`

**Etiquetas**: `enhancement`, `phase-2`, `medium-priority`

**Descripción**:
```
## Objetivo
Implementar caché de KV con límites de memoria y políticas de eviction.

## Especificación
Crear `core/turboquant/kv_cache.py`:
- Clase `KVEvictionPolicy`
- Métodos:
  - `get(key)`: Obtener valor del caché
  - `put(key, value)`: Almacenar valor
  - `_evict_least_recent()`: Eliminar entrada LRU
  - `_get_memory_usage()`: Calcular uso de memoria

## Políticas de eviction
- LRU (Least Recently Used)
- LFU (Least Frequently Used)
- Límite de memoria configurable

## Dependencias
- Issue #2.1 (PyTorch instalado)

## Referencia
Ver [FASE-2-TURBOQUANT.md](./docs/FASE-2-TURBOQUANT.md) sección 4.1

## Criterios de aceptación
- [ ] Caché funcional con límite de memoria
- [ ] Políticas de eviction implementadas
- [ ] Tests de stress (memoria llena)
- [ ] Métricas de hit rate

## Estimación
8 horas
```

---

### Issue 2.6: Implementar compresor de conversación

**Título**: `feat: implementar compresor de historial conversacional`

**Etiquetas**: `enhancement`, `phase-2`, `medium-priority`

**Descripción**:
```
## Objetivo
Comprimir historial de conversación para reducir uso de memoria.

## Especificación
Crear `core/turboquant/conversation_compressor.py`:
- Clase `ConversationCompressor`
- Métodos:
  - `compress(messages)`: Comprime historial
  - `_is_critical(message)`: Determina si mensaje es crítico
  - `_summarize(messages)`: Resume mensajes no críticos

## Estrategia
1. Mantener últimos N mensajes completos
2. Resumir mensajes antiguos
3. Preservar mensajes críticos (con herramientas, decisiones)

## Dependencias
- Issue #2.5 (caché de KV)

## Referencia
Ver [FASE-2-TURBOQUANT.md](./docs/FASE-2-TURBOQUANT.md) sección 4.2

## Criterios de aceptación
- [ ] Compresor funcional
- [ ] Reducción de 50% en tamaño de historial
- [ ] Preservación de mensajes críticos
- [ ] Tests con conversaciones reales

## Estimación
8 horas
```

---

### Issue 2.7: Integrar cuantización en TurboQuantEngine

**Título**: `feat: integrar cuantización y optimizaciones en TurboQuantEngine`

**Etiquetas**: `enhancement`, `phase-2`, `medium-priority`

**Descripción**:
```
## Objetivo
Integrar todas las optimizaciones de Fase 2 en TurboQuantEngine.

## Especificación
Modificar `core/turboquant_engine.py`:
- Añadir soporte para cuantización de 4 bits
- Integrar caché de KV
- Integrar compresor de conversación
- Añadir métricas de performance

## Dependencias
- Issues #2.2, #2.3, #2.4, #2.5, #2.6

## Criterios de aceptación
- [ ] TurboQuantEngine con cuantización funcional
- [ ] Speedup 2-4x en inferencia
- [ ] Reducción de 30% en uso de RAM
- [ ] Tests de integración completos
- [ ] Benchmark de performance

## Estimación
6 horas
```

---

## Fase 3: Búsqueda Híbrida y Fusión de Clasificación (PRIORIDAD MEDIA-BAJA)

### Issue 3.1: Implementar normalizadores de scores

**Título**: `feat: implementar normalizadores de scores para fusión`

**Etiquetas**: `enhancement`, `phase-3`, `low-priority`

**Descripción**:
```
## Objetivo
Implementar normalizadores para unificar escalas de diferentes sistemas de búsqueda.

## Especificación
Crear `core/search/normalizers.py`:
- Clase `ScoreNormalizer`
- Métodos:
  - `min_max_normalize(scores)`: Normalización [0, 1]
  - `z_score_normalize(scores)`: Estandarización (media=0, std=1)

## Referencia
Ver [FASE-3-BUSQUEDA-HIBRIDA.md](./docs/FASE-3-BUSQUEDA-HIBRIDA.md) sección 1.1

## Criterios de aceptación
- [ ] Normalizadores implementados
- [ ] Tests unitarios completos
- [ ] Documentación de uso

## Estimación
4 horas
```

---

### Issue 3.2: Implementar fusión por promedio ponderado

**Título**: `feat: implementar fusión de resultados por promedio ponderado`

**Etiquetas**: `enhancement`, `phase-3`, `low-priority`

**Descripción**:
```
## Objetivo
Fusionar resultados de FAISS y Graphify usando promedio ponderado.

## Especificación
Crear `core/search/fusion.py`:
- Clase `WeightedFusion`
- Métodos:
  - `fuse(faiss_results, graph_results)`: Fusiona resultados
- Pesos configurables (default: FAISS 0.6, Graphify 0.4)

## Fórmula
```
score_final = w_faiss * score_faiss + w_graph * score_graph
```

## Dependencias
- Issue #3.1 (normalizadores)

## Referencia
Ver [FASE-3-BUSQUEDA-HIBRIDA.md](./docs/FASE-3-BUSQUEDA-HIBRIDA.md) sección 1.2

## Criterios de aceptación
- [ ] Fusión funcional
- [ ] Pesos configurables
- [ ] Tests con resultados de ejemplo
- [ ] Integración con `/query`

## Estimación
6 horas
```

---

### Issue 3.3: Implementar Reciprocal Rank Fusion

**Título**: `feat: implementar Reciprocal Rank Fusion (RRF)`

**Etiquetas**: `enhancement`, `phase-3`, `low-priority`

**Descripción**:
```
## Objetivo
Implementar RRF como método alternativo de fusión.

## Especificación
Añadir a `core/search/fusion.py`:
- Clase `ReciprocalRankFusion`
- Métodos:
  - `fuse(*result_lists)`: Fusiona múltiples listas

## Fórmula
```
score_RRF = Σ 1 / (k + rank_i)
```

## Referencia
Ver [FASE-3-BUSQUEDA-HIBRIDA.md](./docs/FASE-3-BUSQUEDA-HIBRIDA.md) sección 1.3
Paper: Cormack et al., 2009

## Criterios de aceptación
- [ ] RRF implementado
- [ ] Tests con múltiples listas
- [ ] Comparación con WeightedFusion
- [ ] Documentación de uso

## Estimación
6 horas
```

---

### Issue 3.4: Implementar clasificadores individuales

**Título**: `feat: implementar clasificadores BM25, FAISS, Graphify y Fidelity`

**Etiquetas**: `enhancement`, `phase-3`, `low-priority`

**Descripción**:
```
## Objetivo
Implementar 4 clasificadores individuales para ensemble.

## Especificación
Crear `core/search/classifiers.py`:
- `BM25Classifier`: Búsqueda por palabras clave
- `FAISSClassifier`: Búsqueda vectorial semántica
- `GraphifyClassifier`: Búsqueda por relaciones de grafo
- `FidelityClassifier`: Validación de calidad

## Dependencias
- `pip install rank-bm25`
- Issues #1.5 (FidelityChecker)

## Referencia
Ver [FASE-3-BUSQUEDA-HIBRIDA.md](./docs/FASE-3-BUSQUEDA-HIBRIDA.md) sección 2

## Criterios de aceptación
- [ ] 4 clasificadores implementados
- [ ] Tests unitarios para cada uno
- [ ] Scores normalizados [0, 1]
- [ ] Documentación de uso

## Estimación
26 horas (6+6+8+6)
```

---

### Issue 3.5: Implementar ensemble de clasificadores

**Título**: `feat: implementar ensemble de clasificadores para búsqueda`

**Etiquetas**: `enhancement`, `phase-3`, `low-priority`

**Descripción**:
```
## Objetivo
Combinar múltiples clasificadores para mejorar precisión.

## Especificación
Crear `core/search/ensemble.py`:
- Clase `EnsembleClassifier`
- Métodos:
  - `classify(query, candidates)`: Clasifica usando ensemble
- Pesos configurables por clasificador

## Dependencias
- Issue #3.4 (clasificadores individuales)

## Referencia
Ver [FASE-3-BUSQUEDA-HIBRIDA.md](./docs/FASE-3-BUSQUEDA-HIBRIDA.md) sección 2.1

## Criterios de aceptación
- [ ] Ensemble funcional
- [ ] Pesos configurables
- [ ] Mejora de precisión > 25%
- [ ] Tests de integración
- [ ] Benchmark de precisión

## Estimación
8 horas
```

---

### Issue 3.6: Implementar telemetría de búsquedas

**Título**: `feat: implementar telemetría detallada de búsquedas`

**Etiquetas**: `enhancement`, `phase-3`, `low-priority`

**Descripción**:
```
## Objetivo
Trackear métricas detalladas de todas las búsquedas.

## Especificación
Crear `core/search/telemetry.py`:
- Clase `SearchTelemetry`
- Métodos:
  - `record(query, results, timing)`: Registra métricas
  - `get_stats()`: Obtiene estadísticas agregadas
  - `export(path)`: Exporta a JSON

## Métricas a trackear
- Latencia total y por componente
- Número de resultados
- Score promedio
- Distribución de scores

## Referencia
Ver [FASE-3-BUSQUEDA-HIBRIDA.md](./docs/FASE-3-BUSQUEDA-HIBRIDA.md) sección 3.1

## Criterios de aceptación
- [ ] Telemetría funcional
- [ ] Integración en flujos de búsqueda
- [ ] Estadísticas agregadas
- [ ] Export a JSON
- [ ] Overhead < 10%

## Estimación
6 horas
```

---

### Issue 3.7: Crear dashboard de búsquedas

**Título**: `feat: crear dashboard de métricas de búsqueda`

**Etiquetas**: `enhancement`, `phase-3`, `low-priority`

**Descripción**:
```
## Objetivo
Crear tab de dashboard para visualizar métricas de búsqueda.

## Especificación
Crear `dashboard/tabs/tab_search.py`:
- Métricas principales (latencia, resultados, score)
- Gráficos de distribución
- Breakdown por clasificador
- Evolución temporal

## Dependencias
- Issue #3.6 (telemetría)

## Referencia
Ver [FASE-3-BUSQUEDA-HIBRIDA.md](./docs/FASE-3-BUSQUEDA-HIBRIDA.md) sección 3.2

## Criterios de aceptación
- [ ] Dashboard funcional en Streamlit
- [ ] Gráficos de métricas principales
- [ ] Filtros por fecha y tipo de búsqueda
- [ ] Integración con tabs existentes

## Estimación
8 horas
```

---

### Issue 3.8: Integrar búsqueda híbrida en comandos

**Título**: `feat: integrar búsqueda híbrida en /query y /queryhybrid`

**Etiquetas**: `enhancement`, `phase-3`, `low-priority`

**Descripción**:
```
## Objetivo
Integrar fusión de resultados y ensemble en comandos de búsqueda.

## Especificación
Modificar `interface/handlers/wiki.py`:
- `query_cmd()`: Usar fusión de FAISS + Graphify
- `queryhybrid_cmd()`: Usar ensemble completo

## Dependencias
- Issues #3.2, #3.3, #3.5, #3.6

## Criterios de aceptación
- [ ] Búsqueda híbrida funcional en /query
- [ ] Ensemble completo en /queryhybrid
- [ ] Telemetría integrada
- [ ] Mejora de precisión > 25%
- [ ] Tests de integración

## Estimación
8 horas
```

---

## Resumen de Issues

| Fase | Issues | Horas Totales | Prioridad |
|------|--------|---------------|-----------|
| Fase 1 | 8 issues | 56 horas | ALTA |
| Fase 2 | 7 issues | 64 horas | MEDIA |
| Fase 3 | 8 issues | 72 horas | MEDIA-BAJA |
| **Total** | **23 issues** | **192 horas** | - |

## Instrucciones para Crear Issues

1. Ve a https://github.com/VicenteVila/Asubarnipal/issues
2. Haz clic en "New issue"
3. Copia el título y descripción de cada issue
4. Añade las etiquetas correspondientes
5. Asigna el issue a ti mismo o al responsable

## Labels Sugeridos

Crear las siguientes labels en GitHub:
- `phase-1` (color: #e11d48)
- `phase-2` (color: #fb923c)
- `phase-3` (color: #4ade80)
- `high-priority` (color: #dc2626)
- `medium-priority` (color: #f59e0b)
- `low-priority` (color: #10b981)

---

**Última actualización**: 2026-06-10  
**Versión**: 1.0
