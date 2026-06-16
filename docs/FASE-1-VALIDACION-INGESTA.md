# Fase 1: Validación Estricta de Ingesta

**Prioridad**: 🔴 ALTA  
**Estado**: Pendiente  
**Estimación**: 2-3 semanas  
**Dependencias**: FidelityChecker (ya implementado)

## Objetivo

Implementar ontologías rígidas durante la ingesta para garantizar calidad y consistencia de datos, resolviendo el problema de calidad identificado con FidelityChecker.

## Contexto

El FidelityChecker reveló que las respuestas del agente tienen un score de fidelidad de ~70/100, principalmente debido a:
- Citas huérfanas (no verificadas)
- Metadatos incompletos
- Falta de validación de fuentes
- Inconsistencias en esquemas de datos

## Especificación Técnica

### 1. Esquemas de Validación por Tipo de Fuente

#### 1.1 URLs (artículos, blogs, documentación)

**Esquema requerido:**
```yaml
tipo: url
titulo: string (required, max 200 chars)
autor: string (optional)
fecha_publicacion: date (optional)
fecha_ingesta: datetime (auto)
url_original: string (required, valid URL)
dominio: string (auto-extracted)
content_length: integer (auto, min 100 chars)
idioma: string (auto-detected)
tags: list[string] (required, min 1)
resumen: string (required, 100-500 chars)
citas_verificadas: list[string] (optional)
score_calidad: integer (auto, 0-100)
```

**Validaciones:**
- URL accesible (HTTP 200)
- Contenido mínimo de 100 caracteres
- Al menos 1 tag obligatorio
- Resumen generado automáticamente
- Score de calidad calculado

#### 1.2 PDFs (papers, libros, reportes)

**Esquema requerido:**
```yaml
tipo: pdf
titulo: string (required, max 300 chars)
autores: list[string] (required, min 1)
fecha_publicacion: date (optional)
editorial: string (optional)
doi: string (optional, valid DOI format)
isbn: string (optional, valid ISBN)
paginas: integer (auto, min 1)
fecha_ingesta: datetime (auto)
ruta_archivo: string (required)
content_length: integer (auto)
idioma: string (auto-detected)
tags: list[string] (required, min 2)
resumen: string (required, 200-1000 chars)
citas_extraidas: list[string] (auto)
citas_verificadas: list[string] (optional)
referencias_bibliograficas: list[string] (auto)
score_calidad: integer (auto, 0-100)
```

**Validaciones:**
- Archivo PDF válido
- Al menos 1 autor
- Extracción de texto exitosa
- Mínimo 2 tags
- Referencias bibliográficas extraídas

#### 1.3 YouTube (videos, conferencias, tutoriales)

**Esquema requerido:**
```yaml
tipo: youtube
titulo: string (required, auto from YouTube API)
canal: string (required, auto)
fecha_publicacion: date (required, auto)
duracion: integer (required, auto, en segundos)
url_original: string (required, valid YouTube URL)
video_id: string (required, auto-extracted)
transcripcion_disponible: boolean (auto)
transcripcion_completa: boolean (auto)
fecha_ingesta: datetime (auto)
content_length: integer (auto)
idioma: string (auto-detected)
tags: list[string] (required, min 2)
resumen: string (required, 200-800 chars)
momentos_clave: list[timestamp] (optional)
score_calidad: integer (auto, 0-100)
```

**Validaciones:**
- Video accesible vía YouTube API
- Transcripción disponible (o extraída vía Whisper)
- Duración > 60 segundos
- Mínimo 2 tags

### 2. Validación Bidireccional de Citas

#### 2.1 Extracción de Citas

**Proceso:**
1. Durante la ingesta, extraer todas las citas del texto
2. Identificar formato (APA, MLA, Chicago, etc.)
3. Parsear componentes (autor, año, título, fuente)
4. Almacenar en campo `citas_extraidas`

**Implementación:**
```python
def extraer_citas(texto: str) -> list[dict]:
    """
    Extrae citas del texto y las estructura.
    
    Returns:
        Lista de diccionarios con:
        - texto_original: str
        - formato: str (apa, mla, chicago, etc.)
        - autor: str (si se puede extraer)
        - año: int (si se puede extraer)
        - titulo: str (si se puede extraer)
        - fuente: str (si se puede extraer)
    """
    pass
```

#### 2.2 Verificación de Citas

**Proceso:**
1. Para cada cita extraída, buscar en:
   - Base de datos local (wiki.db)
   - Google Scholar API (si está disponible)
   - CrossRef API (para DOIs)
2. Marcar como verificada si se encuentra coincidencia
3. Almacenar en campo `citas_verificadas`

**Implementación:**
```python
def verificar_cita(cita: dict) -> dict:
    """
    Verifica si una cita existe y es accesible.
    
    Returns:
        Diccionario con:
        - verificada: bool
        - fuente_verificacion: str (local, scholar, crossref, none)
        - url_acceso: str (si está disponible)
        - coincidencias: list[str]
    """
    pass
```

#### 2.3 Métricas de Citas

**Cálculos:**
```python
def calcular_metricas_citas(entidad: dict) -> dict:
    """
    Calcula métricas de calidad de citas.
    
    Returns:
        - total_citas: int
        - citas_verificadas: int
        - porcentaje_verificacion: float (0-100)
        - citas_huerfanas: int (no verificadas)
        - score_citas: int (0-100)
    """
    total = len(entidad.get('citas_extraidas', []))
    verificadas = len(entidad.get('citas_verificadas', []))
    
    if total == 0:
        return {
            'total_citas': 0,
            'citas_verificadas': 0,
            'porcentaje_verificacion': 100.0,
            'citas_huerfanas': 0,
            'score_citas': 100
        }
    
    porcentaje = (verificadas / total) * 100
    huerfanas = total - verificadas
    
    # Score basado en porcentaje de verificación
    if porcentaje >= 90:
        score = 100
    elif porcentaje >= 75:
        score = 85
    elif porcentaje >= 50:
        score = 70
    else:
        score = 50
    
    return {
        'total_citas': total,
        'citas_verificadas': verificadas,
        'porcentaje_verificacion': porcentaje,
        'citas_huerfanas': huerfanas,
        'score_citas': score
    }
```

### 3. Métricas de Completitud y Calidad

#### 3.1 Score de Calidad por Tipo

**URLs:**
```python
def calcular_score_url(entidad: dict) -> int:
    """
    Calcula score de calidad para URLs (0-100).
    
    Factores:
    - Metadatos completos (30 puntos)
    - Contenido sustancial (30 puntos)
    - Tags relevantes (20 puntos)
    - Resumen de calidad (20 puntos)
    """
    score = 0
    
    # Metadatos completos (30 puntos)
    if entidad.get('titulo'):
        score += 10
    if entidad.get('autor'):
        score += 10
    if entidad.get('fecha_publicacion'):
        score += 10
    
    # Contenido sustancial (30 puntos)
    content_length = entidad.get('content_length', 0)
    if content_length >= 5000:
        score += 30
    elif content_length >= 2000:
        score += 20
    elif content_length >= 1000:
        score += 10
    
    # Tags relevantes (20 puntos)
    tags = entidad.get('tags', [])
    if len(tags) >= 5:
        score += 20
    elif len(tags) >= 3:
        score += 15
    elif len(tags) >= 1:
        score += 10
    
    # Resumen de calidad (20 puntos)
    resumen = entidad.get('resumen', '')
    if 200 <= len(resumen) <= 500:
        score += 20
    elif 100 <= len(resumen) < 200:
        score += 10
    
    return min(score, 100)
```

**PDFs:**
```python
def calcular_score_pdf(entidad: dict) -> int:
    """
    Calcula score de calidad para PDFs (0-100).
    
    Factores:
    - Metadatos académicos (25 puntos)
    - Extracción exitosa (25 puntos)
    - Referencias bibliográficas (25 puntos)
    - Citas verificadas (25 puntos)
    """
    score = 0
    
    # Metadatos académicos (25 puntos)
    if entidad.get('autores'):
        score += 10
    if entidad.get('doi') or entidad.get('isbn'):
        score += 10
    if entidad.get('editorial'):
        score += 5
    
    # Extracción exitosa (25 puntos)
    content_length = entidad.get('content_length', 0)
    paginas = entidad.get('paginas', 0)
    if content_length >= 10000 and paginas >= 5:
        score += 25
    elif content_length >= 5000 and paginas >= 3:
        score += 15
    
    # Referencias bibliográficas (25 puntos)
    refs = entidad.get('referencias_bibliograficas', [])
    if len(refs) >= 20:
        score += 25
    elif len(refs) >= 10:
        score += 20
    elif len(refs) >= 5:
        score += 10
    
    # Citas verificadas (25 puntos)
    metricas_citas = calcular_metricas_citas(entidad)
    score += int(metricas_citas['score_citas'] * 0.25)
    
    return min(score, 100)
```

**YouTube:**
```python
def calcular_score_youtube(entidad: dict) -> int:
    """
    Calcula score de calidad para YouTube (0-100).
    
    Factores:
    - Metadatos completos (25 puntos)
    - Transcripción disponible (35 puntos)
    - Duración sustancial (20 puntos)
    - Tags relevantes (20 puntos)
    """
    score = 0
    
    # Metadatos completos (25 puntos)
    if entidad.get('titulo'):
        score += 10
    if entidad.get('canal'):
        score += 10
    if entidad.get('fecha_publicacion'):
        score += 5
    
    # Transcripción disponible (35 puntos)
    if entidad.get('transcripcion_completa'):
        score += 35
    elif entidad.get('transcripcion_disponible'):
        score += 20
    
    # Duración sustancial (20 puntos)
    duracion = entidad.get('duracion', 0)
    if duracion >= 1800:  # 30+ minutos
        score += 20
    elif duracion >= 600:  # 10+ minutos
        score += 15
    elif duracion >= 300:  # 5+ minutos
        score += 10
    
    # Tags relevantes (20 puntos)
    tags = entidad.get('tags', [])
    if len(tags) >= 5:
        score += 20
    elif len(tags) >= 3:
        score += 15
    elif len(tags) >= 2:
        score += 10
    
    return min(score, 100)
```

### 4. Integración con FidelityChecker

#### 4.1 Validación Pre-Ingesta

**Flujo:**
```python
def validar_antes_de_ingesta(datos: dict, tipo: str) -> tuple[bool, str, int]:
    """
    Valida datos antes de ingestar.
    
    Returns:
        - valido: bool
        - mensaje: str (razón si no es válido)
        - score_estimado: int (0-100)
    """
    # Validar esquema
    esquema_valido, mensaje = validar_esquema(datos, tipo)
    if not esquema_valido:
        return False, mensaje, 0
    
    # Calcular score estimado
    if tipo == 'url':
        score = calcular_score_url(datos)
    elif tipo == 'pdf':
        score = calcular_score_pdf(datos)
    elif tipo == 'youtube':
        score = calcular_score_youtube(datos)
    else:
        return False, f"Tipo no soportado: {tipo}", 0
    
    # Rechazar si score < 50
    if score < 50:
        return False, f"Score de calidad muy bajo: {score}/100", score
    
    return True, "Validación exitosa", score
```

#### 4.2 Validación Post-Ingesta

**Flujo:**
```python
def validar_despues_de_ingesta(entidad_id: int) -> dict:
    """
    Valida entidad después de ingestar y actualiza métricas.
    
    Returns:
        Diccionario con resultados de validación
    """
    # Obtener entidad
    entidad = obtener_entidad(entidad_id)
    
    # Verificar citas
    metricas_citas = calcular_metricas_citas(entidad)
    
    # Calcular score final
    if entidad['tipo'] == 'url':
        score = calcular_score_url(entidad)
    elif entidad['tipo'] == 'pdf':
        score = calcular_score_pdf(entidad)
    elif entidad['tipo'] == 'youtube':
        score = calcular_score_youtube(entidad)
    
    # Actualizar en base de datos
    actualizar_score_calidad(entidad_id, score)
    
    # Generar reporte
    return {
        'entidad_id': entidad_id,
        'tipo': entidad['tipo'],
        'score_calidad': score,
        'metricas_citas': metricas_citas,
        'valido': score >= 70,
        'recomendaciones': generar_recomendaciones(entidad, score)
    }
```

## Tareas de Implementación

### Semana 1: Esquemas y Validación Básica

- [ ] **Tarea 1.1**: Definir esquemas YAML para cada tipo de fuente
  - Archivo: `core/wiki/schemas/url.yaml`
  - Archivo: `core/wiki/schemas/pdf.yaml`
  - Archivo: `core/wiki/schemas/youtube.yaml`
  - Estimación: 4 horas

- [ ] **Tarea 1.2**: Implementar validador de esquemas
  - Archivo: `core/wiki/validators.py`
  - Funciones: `validar_esquema()`, `validar_antes_de_ingesta()`
  - Estimación: 6 horas

- [ ] **Tarea 1.3**: Integrar validación en flujos de ingesta existentes
  - Archivo: `core/wiki/ingest.py`
  - Modificar: `ingest_url()`, `ingest_pdf()`, `_ingest_youtube()`
  - Estimación: 8 horas

### Semana 2: Validación de Citas

- [ ] **Tarea 2.1**: Implementar extractor de citas
  - Archivo: `core/wiki/citation_extractor.py`
  - Funciones: `extraer_citas()`, `parsear_cita()`
  - Estimación: 8 horas

- [ ] **Tarea 2.2**: Implementar verificador de citas
  - Archivo: `core/wiki/citation_verifier.py`
  - Funciones: `verificar_cita()`, `verificar_citas_batch()`
  - Integraciones: CrossRef API, Google Scholar (opcional)
  - Estimación: 10 horas

- [ ] **Tarea 2.3**: Calcular métricas de citas
  - Archivo: `core/wiki/citation_metrics.py`
  - Funciones: `calcular_metricas_citas()`
  - Estimación: 4 horas

### Semana 3: Métricas de Calidad e Integración

- [ ] **Tarea 3.1**: Implementar calculadores de score por tipo
  - Archivo: `core/wiki/quality_scorer.py`
  - Funciones: `calcular_score_url()`, `calcular_score_pdf()`, `calcular_score_youtube()`
  - Estimación: 6 horas

- [ ] **Tarea 3.2**: Integrar con FidelityChecker
  - Archivo: `tests/evaluation/fidelity_checker.py`
  - Añadir: Validación de metadatos y citas
  - Estimación: 6 horas

- [ ] **Tarea 3.3**: Añadir comandos de validación
  - Archivo: `interface/handlers/wiki.py`
  - Comandos: `/validar <id>`, `/calidad <id>`, `/citas <id>`
  - Estimación: 6 horas

- [ ] **Tarea 3.4**: Crear dashboard de calidad
  - Archivo: `dashboard/tabs/tab_calidad.py`
  - Mostrar: Scores, citas verificadas, métricas
  - Estimación: 8 horas

## Criterios de Aceptación

### Funcionales

- [ ] Todas las ingestas pasan por validación de esquema
- [ ] Score de calidad calculado automáticamente para cada entidad
- [ ] Citas extraídas y verificadas durante la ingesta
- [ ] Métricas de citas disponibles en dashboard
- [ ] Comandos de validación funcionales

### No Funcionales

- [ ] Validación no añade más de 2 segundos a la ingesta
- [ ] Score de calidad promedio > 80/100
- [ ] Porcentaje de citas verificadas > 75%
- [ ] 0 citas huérfanas en nuevas ingestas

### Testing

- [ ] Tests unitarios para validadores (cobertura > 90%)
- [ ] Tests de integración con flujos de ingesta
- [ ] Tests de performance (validación < 2s)
- [ ] Validación manual de 10 ingestas de cada tipo

## Riesgos y Mitigaciones

| Riesgo | Probabilidad | Impacto | Mitigación |
|--------|--------------|---------|------------|
| APIs externas no disponibles | Media | Alto | Implementar fallbacks y caché |
| Validación muy lenta | Baja | Alto | Optimizar y paralelizar |
| Falsos negativos en citas | Media | Medio | Ajustar umbrales de similitud |
| Esquemas muy restrictivos | Media | Medio | Permitir configuración flexible |

## Dependencias

- **FidelityChecker**: Ya implementado, usar como base
- **CrossRef API**: Para verificación de DOIs (gratuita)
- **Google Scholar API**: Opcional, para verificación adicional
- **PyYAML**: Para definición de esquemas

## Recursos Necesarios

- **Desarrollo**: 1 desarrollador, 2-3 semanas
- **Testing**: 1 tester, 1 semana
- **Infraestructura**: APIs externas (CrossRef, opcionalmente Google Scholar)

## Métricas de Éxito

| Métrica | Actual | Objetivo | Medición |
|---------|--------|----------|----------|
| Score de calidad promedio | ~70/100 | 85+/100 | Dashboard de calidad |
| Porcentaje de citas verificadas | ~40% | 80%+ | Métricas de citas |
| Citas huérfanas | ~60% | <10% | Métricas de citas |
| Tiempo de validación | N/A | <2s | Logs de performance |

## Referencias

- **Análisis completo**: [Arquitectura-comparativa.pdf](./Arquitectura-comparativa.pdf) (páginas 7-8)
- **FidelityChecker**: `tests/evaluation/fidelity_checker.py`
- **Repositorios de referencia**: GraphRAG, Research-Agent-CLI

---

**Última actualización**: 2026-06-10  
**Versión**: 1.0  
**Autor**: Análisis arquitectónico comparativo
