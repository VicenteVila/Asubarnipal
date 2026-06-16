# Fase 3: Búsqueda Híbrida y Fusión de Clasificación

**Prioridad**: 🟢 MEDIA-BAJA  
**Estado**: Pendiente  
**Estimación**: 2-3 semanas  
**Dependencias**: FidelityChecker (Fase 1), Graphify actualizado

## Objetivo

Combinar búsqueda vectorial (FAISS) con búsqueda por grafos (Graphify) y fusionar resultados mediante clasificadores ensemble, mejorando la precisión de búsqueda en 25-40%.

## Contexto

Actualmente Asubarnipal tiene dos sistemas de búsqueda separados:
1. **Búsqueda vectorial** (FAISS): Similaridad semántica basada en embeddings
2. **Búsqueda por grafos** (Graphify): Relaciones estructurales entre conceptos

**Problema:** Cada sistema tiene fortalezas y debilidades:
- FAISS: Bueno para similitud semántica, malo para relaciones complejas
- Graphify: Bueno para relaciones, malo para similitud semántica

**Solución:** Fusionar ambos sistemas para obtener lo mejor de cada uno.

## Especificación Técnica

### 1. Fusión de Resultados de Búsqueda

#### 1.1 Normalización de Scores

**Problema:** FAISS y Graphify usan escalas de scoring diferentes.

**Solución:** Normalizar scores a rango [0, 1] usando min-max scaling.

**Implementación:**
```python
class ScoreNormalizer:
    """Normaliza scores de diferentes fuentes a [0, 1]."""
    
    @staticmethod
    def min_max_normalize(scores: list[float], min_val: float = None, max_val: float = None) -> list[float]:
        """
        Normaliza scores usando min-max scaling.
        
        Args:
            scores: Lista de scores originales
            min_val: Valor mínimo (si None, usar min de scores)
            max_val: Valor máximo (si None, usar max de scores)
        
        Returns:
            Lista de scores normalizados [0, 1]
        """
        if not scores:
            return []
        
        if min_val is None:
            min_val = min(scores)
        if max_val is None:
            max_val = max(scores)
        
        # Evitar división por cero
        if max_val == min_val:
            return [0.5] * len(scores)
        
        normalized = [(s - min_val) / (max_val - min_val) for s in scores]
        return normalized
    
    @staticmethod
    def z_score_normalize(scores: list[float]) -> list[float]:
        """
        Normaliza scores usando z-score (estandarización).
        
        Returns:
            Lista de scores normalizados (media=0, std=1)
        """
        if not scores:
            return []
        
        import numpy as np
        arr = np.array(scores)
        mean = arr.mean()
        std = arr.std()
        
        if std == 0:
            return [0.0] * len(scores)
        
        normalized = ((arr - mean) / std).tolist()
        return normalized
```

#### 1.2 Fusión por Promedio Ponderado

**Estrategia:** Combinar scores de FAISS y Graphify usando pesos configurables.

**Fórmula:**
```
score_final = w_faiss * score_faiss + w_graph * score_graph
```

**Implementación:**
```python
class WeightedFusion:
    """Fusión de resultados por promedio ponderado."""
    
    def __init__(self, w_faiss: float = 0.6, w_graph: float = 0.4):
        """
        Args:
            w_faiss: Peso para FAISS (default 0.6)
            w_graph: Peso para Graphify (default 0.4)
        """
        self.w_faiss = w_faiss
        self.w_graph = w_graph
        
        # Validar que sumen 1
        if abs(w_faiss + w_graph - 1.0) > 1e-6:
            raise ValueError("Los pesos deben sumar 1.0")
    
    def fuse(self, faiss_results: list[dict], graph_results: list[dict]) -> list[dict]:
        """
        Fusiona resultados de FAISS y Graphify.
        
        Args:
            faiss_results: Lista de resultados FAISS
                [{'id': str, 'score': float, 'content': str, ...}]
            graph_results: Lista de resultados Graphify
                [{'id': str, 'score': float, 'content': str, ...}]
        
        Returns:
            Lista de resultados fusionados, ordenados por score_final
        """
        # Crear diccionario de resultados por ID
        results_dict = {}
        
        # Procesar FAISS
        for r in faiss_results:
            id_ = r['id']
            if id_ not in results_dict:
                results_dict[id_] = {
                    'id': id_,
                    'content': r.get('content', ''),
                    'metadata': r.get('metadata', {}),
                    'score_faiss': 0.0,
                    'score_graph': 0.0
                }
            results_dict[id_]['score_faiss'] = r.get('score', 0.0)
        
        # Procesar Graphify
        for r in graph_results:
            id_ = r['id']
            if id_ not in results_dict:
                results_dict[id_] = {
                    'id': id_,
                    'content': r.get('content', ''),
                    'metadata': r.get('metadata', {}),
                    'score_faiss': 0.0,
                    'score_graph': 0.0
                }
            results_dict[id_]['score_graph'] = r.get('score', 0.0)
        
        # Calcular score final
        for r in results_dict.values():
            r['score_final'] = (
                self.w_faiss * r['score_faiss'] +
                self.w_graph * r['score_graph']
            )
        
        # Ordenar por score final
        fused = sorted(results_dict.values(), key=lambda x: x['score_final'], reverse=True)
        
        return fused
```

#### 1.3 Fusión por Reciprocal Rank Fusion (RRF)

**Estrategia:** Fusionar basándose en el ranking, no en los scores absolutos.

**Fórmula:**
```
score_RRF = Σ 1 / (k + rank_i)
```

**Donde:**
- `k`: constante (típicamente 60)
- `rank_i`: posición del documento en la lista i

**Ventajas:**
- No requiere normalización de scores
- Robusto a outliers
- Funciona bien con listas de diferentes longitudes

**Implementación:**
```python
class ReciprocalRankFusion:
    """Fusión por Reciprocal Rank Fusion (RRF)."""
    
    def __init__(self, k: int = 60):
        """
        Args:
            k: Constante RRF (default 60)
        """
        self.k = k
    
    def fuse(self, *result_lists: list[dict]) -> list[dict]:
        """
        Fusiona múltiples listas de resultados usando RRF.
        
        Args:
            *result_lists: Múltiples listas de resultados
                Cada resultado: {'id': str, 'content': str, ...}
        
        Returns:
            Lista de resultados fusionados, ordenados por score_RRF
        """
        scores_dict = {}
        results_dict = {}
        
        # Procesar cada lista
        for results in result_lists:
            for rank, r in enumerate(results):
                id_ = r['id']
                
                # Calcular score RRF
                rrf_score = 1.0 / (self.k + rank + 1)
                
                if id_ not in scores_dict:
                    scores_dict[id_] = 0.0
                    results_dict[id_] = {
                        'id': id_,
                        'content': r.get('content', ''),
                        'metadata': r.get('metadata', {})
                    }
                
                scores_dict[id_] += rrf_score
        
        # Añadir scores a resultados
        for id_, score in scores_dict.items():
            results_dict[id_]['score_rrf'] = score
        
        # Ordenar por score RRF
        fused = sorted(results_dict.values(), key=lambda x: x['score_rrf'], reverse=True)
        
        return fused
```

### 2. Fusión de Clasificadores

#### 2.1 Ensemble de Clasificadores

**Problema:** Un solo clasificador puede tener sesgos o errores sistemáticos.

**Solución:** Combinar múltiples clasificadores para mejorar precisión.

**Clasificadores a usar:**
1. **BM25**: Búsqueda por palabras clave
2. **FAISS**: Búsqueda vectorial semántica
3. **Graphify**: Búsqueda por relaciones de grafo
4. **FidelityChecker**: Validación de calidad

**Implementación:**
```python
class EnsembleClassifier:
    """Ensemble de clasificadores para búsqueda híbrida."""
    
    def __init__(self):
        self.classifiers = {
            'bm25': BM25Classifier(),
            'faiss': FAISSClassifier(),
            'graphify': GraphifyClassifier(),
            'fidelity': FidelityClassifier()
        }
        self.weights = {
            'bm25': 0.2,
            'faiss': 0.4,
            'graphify': 0.3,
            'fidelity': 0.1
        }
    
    def classify(self, query: str, candidates: list[dict]) -> list[dict]:
        """
        Clasifica candidatos usando ensemble.
        
        Args:
            query: Query del usuario
            candidates: Lista de documentos candidatos
                [{'id': str, 'content': str, ...}]
        
        Returns:
            Lista de candidatos con scores de ensemble
        """
        # Obtener scores de cada clasificador
        scores = {}
        for name, classifier in self.classifiers.items():
            scores[name] = classifier.score(query, candidates)
        
        # Calcular score de ensemble
        for i, candidate in enumerate(candidates):
            ensemble_score = 0.0
            for name, weight in self.weights.items():
                ensemble_score += weight * scores[name][i]
            
            candidate['score_ensemble'] = ensemble_score
            candidate['scores_individual'] = {
                name: scores[name][i] for name in scores
            }
        
        # Ordenar por score de ensemble
        ranked = sorted(candidates, key=lambda x: x['score_ensemble'], reverse=True)
        
        return ranked
```

#### 2.2 Clasificador BM25

**Implementación:**
```python
from rank_bm25 import BM25Okapi

class BM25Classifier:
    """Clasificador basado en BM25."""
    
    def __init__(self):
        self.bm25 = None
        self.corpus = []
    
    def fit(self, documents: list[str]):
        """Entrena BM25 con corpus de documentos."""
        # Tokenizar documentos
        tokenized = [doc.lower().split() for doc in documents]
        self.bm25 = BM25Okapi(tokenized)
        self.corpus = documents
    
    def score(self, query: str, candidates: list[dict]) -> list[float]:
        """
        Calcula scores BM25 para candidatos.
        
        Returns:
            Lista de scores [0, 1]
        """
        if not self.bm25:
            return [0.0] * len(candidates)
        
        # Tokenizar query
        tokenized_query = query.lower().split()
        
        # Calcular scores
        scores = self.bm25.get_scores(tokenized_query)
        
        # Normalizar a [0, 1]
        max_score = max(scores) if max(scores) > 0 else 1.0
        normalized = [s / max_score for s in scores]
        
        return normalized
```

#### 2.3 Clasificador FAISS

**Implementación:**
```python
class FAISSClassifier:
    """Clasificador basado en FAISS."""
    
    def __init__(self, index_path: str):
        self.index_path = index_path
        self.index = None
        self.embeddings = None
    
    def load(self):
        """Carga índice FAISS."""
        import faiss
        self.index = faiss.read_index(self.index_path)
    
    def score(self, query: str, candidates: list[dict]) -> list[float]:
        """
        Calcula scores de similitud para candidatos.
        
        Returns:
            Lista de scores [0, 1]
        """
        if not self.index:
            return [0.0] * len(candidates)
        
        # Generar embedding de query
        from core.embeddings import get_embedding
        query_embedding = get_embedding(query)
        
        # Buscar en índice
        distances, indices = self.index.search(query_embedding, k=len(candidates))
        
        # Convertir distancias a similitudes
        # FAISS usa L2 distance, convertir a similitud [0, 1]
        similarities = [1.0 / (1.0 + d) for d in distances[0]]
        
        return similarities
```

#### 2.4 Clasificador Graphify

**Implementación:**
```python
class GraphifyClassifier:
    """Clasificador basado en Graphify."""
    
    def __init__(self, graph_path: str):
        self.graph_path = graph_path
        self.graph = None
    
    def load(self):
        """Carga grafo de Graphify."""
        import json
        with open(self.graph_path, 'r') as f:
            self.graph = json.load(f)
    
    def score(self, query: str, candidates: list[dict]) -> list[float]:
        """
        Calcula scores basados en relaciones de grafo.
        
        Returns:
            Lista de scores [0, 1]
        """
        if not self.graph:
            return [0.0] * len(candidates)
        
        scores = []
        for candidate in candidates:
            # Buscar nodo en grafo
            node_id = candidate['id']
            node = self._find_node(node_id)
            
            if not node:
                scores.append(0.0)
                continue
            
            # Calcular score basado en conexiones
            connections = len(node.get('edges', []))
            centrality = self._calculate_centrality(node_id)
            
            # Combinar métricas
            score = 0.6 * min(connections / 10.0, 1.0) + 0.4 * centrality
            scores.append(score)
        
        return scores
    
    def _find_node(self, node_id: str) -> dict:
        """Busca nodo en grafo."""
        for node in self.graph.get('nodes', []):
            if node.get('id') == node_id:
                return node
        return None
    
    def _calculate_centrality(self, node_id: str) -> float:
        """Calcula centralidad del nodo."""
        # Implementación simplificada de degree centrality
        node = self._find_node(node_id)
        if not node:
            return 0.0
        
        connections = len(node.get('edges', []))
        total_nodes = len(self.graph.get('nodes', []))
        
        if total_nodes <= 1:
            return 0.0
        
        centrality = connections / (total_nodes - 1)
        return centrality
```

#### 2.5 Clasificador Fidelity

**Implementación:**
```python
class FidelityClassifier:
    """Clasificador basado en FidelityChecker."""
    
    def __init__(self):
        from tests.evaluation.fidelity_checker import FidelityChecker
        self.checker = FidelityChecker()
    
    def score(self, query: str, candidates: list[dict]) -> list[float]:
        """
        Calcula scores de calidad para candidatos.
        
        Returns:
            Lista de scores [0, 1]
        """
        scores = []
        for candidate in candidates:
            # Obtener métricas de calidad
            metrics = self.checker.get_quality_metrics(candidate)
            
            # Combinar métricas
            score = (
                0.4 * metrics.get('completeness', 0.0) +
                0.3 * metrics.get('accuracy', 0.0) +
                0.3 * metrics.get('relevance', 0.0)
            )
            
            scores.append(score)
        
        return scores
```

### 3. Telemetría Detallada de Búsquedas

#### 3.1 Métricas de Búsqueda

**Métricas a trackear:**
- Latencia de búsqueda (ms)
- Número de resultados
- Score promedio
- Distribución de scores
- Tiempo por clasificador
- Tasa de éxito (relevancia)

**Implementación:**
```python
class SearchTelemetry:
    """Telemetría detallada de búsquedas."""
    
    def __init__(self):
        self.metrics = []
    
    def record(self, query: str, results: list[dict], timing: dict):
        """
        Registra métricas de una búsqueda.
        
        Args:
            query: Query del usuario
            results: Resultados de la búsqueda
            timing: Tiempos de ejecución
                {
                    'total_ms': float,
                    'faiss_ms': float,
                    'graphify_ms': float,
                    'fusion_ms': float,
                    'classification_ms': float
                }
        """
        metric = {
            'timestamp': datetime.now().isoformat(),
            'query': query,
            'num_results': len(results),
            'avg_score': sum(r.get('score_ensemble', 0) for r in results) / len(results) if results else 0,
            'max_score': max(r.get('score_ensemble', 0) for r in results) if results else 0,
            'min_score': min(r.get('score_ensemble', 0) for r in results) if results else 0,
            'timing': timing
        }
        
        self.metrics.append(metric)
    
    def get_stats(self) -> dict:
        """Obtiene estadísticas agregadas."""
        if not self.metrics:
            return {}
        
        total_queries = len(self.metrics)
        avg_latency = sum(m['timing']['total_ms'] for m in self.metrics) / total_queries
        avg_results = sum(m['num_results'] for m in self.metrics) / total_queries
        avg_score = sum(m['avg_score'] for m in self.metrics) / total_queries
        
        return {
            'total_queries': total_queries,
            'avg_latency_ms': avg_latency,
            'avg_results_per_query': avg_results,
            'avg_score': avg_score,
            'p95_latency_ms': self._percentile([m['timing']['total_ms'] for m in self.metrics], 95),
            'p95_results': self._percentile([m['num_results'] for m in self.metrics], 95)
        }
    
    def _percentile(self, data: list[float], p: float) -> float:
        """Calcula percentil."""
        import numpy as np
        return np.percentile(data, p)
    
    def export(self, path: str):
        """Exporta métricas a JSON."""
        import json
        with open(path, 'w') as f:
            json.dump(self.metrics, f, indent=2)
```

#### 3.2 Dashboard de Búsquedas

**Implementación:**
```python
class SearchDashboard:
    """Dashboard de métricas de búsqueda."""
    
    def __init__(self, telemetry: SearchTelemetry):
        self.telemetry = telemetry
    
    def render(self):
        """Renderiza dashboard en Streamlit."""
        import streamlit as st
        
        st.header("🔍 Métricas de Búsqueda")
        
        stats = self.telemetry.get_stats()
        
        if not stats:
            st.info("No hay datos de búsqueda aún")
            return
        
        # Métricas principales
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Total Queries", stats['total_queries'])
        
        with col2:
            st.metric("Latencia Promedio", f"{stats['avg_latency_ms']:.1f} ms")
        
        with col3:
            st.metric("Resultados/Query", f"{stats['avg_results_per_query']:.1f}")
        
        with col4:
            st.metric("Score Promedio", f"{stats['avg_score']:.2f}")
        
        # Gráficos
        st.subheader("Distribución de Latencia")
        latencies = [m['timing']['total_ms'] for m in self.telemetry.metrics]
        st.histogram(latencies, bins=20)
        
        st.subheader("Distribución de Scores")
        scores = [m['avg_score'] for m in self.telemetry.metrics]
        st.histogram(scores, bins=20)
        
        # Breakdown por clasificador
        st.subheader("Tiempo por Clasificador")
        timing_data = {
            'FAISS': [m['timing']['faiss_ms'] for m in self.telemetry.metrics],
            'Graphify': [m['timing']['graphify_ms'] for m in self.telemetry.metrics],
            'Fusion': [m['timing']['fusion_ms'] for m in self.telemetry.metrics],
            'Classification': [m['timing']['classification_ms'] for m in self.telemetry.metrics]
        }
        st.bar_chart(timing_data)
```

## Tareas de Implementación

### Semana 1: Fusión de Resultados

- [ ] **Tarea 1.1**: Implementar normalizadores de scores
  - Archivo: `core/search/normalizers.py`
  - Clases: `ScoreNormalizer`
  - Estimación: 4 horas

- [ ] **Tarea 1.2**: Implementar fusión por promedio ponderado
  - Archivo: `core/search/fusion.py`
  - Clase: `WeightedFusion`
  - Estimación: 6 horas

- [ ] **Tarea 1.3**: Implementar Reciprocal Rank Fusion
  - Archivo: `core/search/fusion.py`
  - Clase: `ReciprocalRankFusion`
  - Estimación: 6 horas

- [ ] **Tarea 1.4**: Integrar fusión en `/query` y `/queryhybrid`
  - Archivo: `interface/handlers/wiki.py`
  - Modificar: `query_cmd()`, `queryhybrid_cmd()`
  - Estimación: 8 horas

### Semana 2: Fusión de Clasificadores

- [ ] **Tarea 2.1**: Implementar clasificador BM25
  - Archivo: `core/search/classifiers.py`
  - Clase: `BM25Classifier`
  - Dependencia: `pip install rank-bm25`
  - Estimación: 6 horas

- [ ] **Tarea 2.2**: Implementar clasificador FAISS
  - Archivo: `core/search/classifiers.py`
  - Clase: `FAISSClassifier`
  - Estimación: 6 horas

- [ ] **Tarea 2.3**: Implementar clasificador Graphify
  - Archivo: `core/search/classifiers.py`
  - Clase: `GraphifyClassifier`
  - Estimación: 8 horas

- [ ] **Tarea 2.4**: Implementar clasificador Fidelity
  - Archivo: `core/search/classifiers.py`
  - Clase: `FidelityClassifier`
  - Estimación: 6 horas

- [ ] **Tarea 2.5**: Implementar ensemble de clasificadores
  - Archivo: `core/search/ensemble.py`
  - Clase: `EnsembleClassifier`
  - Estimación: 8 horas

### Semana 3: Telemetría y Testing

- [ ] **Tarea 3.1**: Implementar telemetría de búsquedas
  - Archivo: `core/search/telemetry.py`
  - Clase: `SearchTelemetry`
  - Estimación: 6 horas

- [ ] **Tarea 3.2**: Implementar dashboard de búsquedas
  - Archivo: `dashboard/tabs/tab_search.py`
  - Clase: `SearchDashboard`
  - Estimación: 8 horas

- [ ] **Tarea 3.3**: Tests unitarios
  - Archivo: `tests/test_search_fusion.py`
  - Cobertura: >90%
  - Estimación: 6 horas

- [ ] **Tarea 3.4**: Tests de integración
  - Archivo: `tests/test_search_integration.py`
  - Validar: búsqueda híbrida completa
  - Estimación: 6 horas

- [ ] **Tarea 3.5**: Benchmark de precisión
  - Archivo: `tests/benchmark_search_precision.py`
  - Medir: precisión, recall, F1
  - Estimación: 6 horas

## Criterios de Aceptación

### Funcionales

- [ ] Fusión de FAISS y Graphify funcional
- [ ] Ensemble de 4 clasificadores operativo
- [ ] Telemetría detallada de búsquedas
- [ ] Dashboard de métricas de búsqueda
- [ ] Integración completa en `/query` y `/queryhybrid`

### No Funcionales

- [ ] Precisión de búsqueda mejorada en 25-40%
- [ ] Latencia < 2s para queries complejas
- [ ] Throughput > 5 queries/segundo
- [ ] Telemetría completa sin overhead > 10%

### Testing

- [ ] Tests unitarios (cobertura > 90%)
- [ ] Tests de integración (10+ escenarios)
- [ ] Benchmark de precisión (dataset de prueba)
- [ ] Validación manual de 20 queries

## Riesgos y Mitigaciones

| Riesgo | Probabilidad | Impacto | Mitigación |
|--------|--------------|---------|------------|
| Overhead de fusión | Media | Medio | Optimizar y usar caché |
| Clasificadores inconsistentes | Media | Alto | Ajustar pesos dinámicamente |
| Telemetría muy verbosa | Baja | Bajo | Implementar sampling |
| Degradación de latencia | Media | Alto | Optimizar y paralelizar |

## Dependencias

- **rank-bm25**: Librería BM25
- **FAISS**: Búsqueda vectorial (ya instalado)
- **Graphify**: Búsqueda por grafos (ya instalado)
- **FidelityChecker**: Validación de calidad (Fase 1)

## Recursos Necesarios

- **Desarrollo**: 1 desarrollador, 2-3 semanas
- **Testing**: 1 tester, 1 semana
- **Dataset**: Dataset de evaluación de búsqueda (crear)

## Métricas de Éxito

| Métrica | Actual | Objetivo | Medición |
|---------|--------|----------|----------|
| Precisión de búsqueda | ~65% | ~90% | Benchmark |
| Recall@10 | ~60% | ~85% | Benchmark |
| F1 Score | ~62% | ~87% | Benchmark |
| Latencia P95 | ~3s | <2s | Telemetría |

## Referencias

- **Análisis completo**: [Arquitectura-comparativa.pdf](./Arquitectura-comparativa.pdf) (páginas 9-10)
- **FAISS**: `core/vector_store.py`
- **Graphify**: `core/graphify_integration.py`
- **FidelityChecker**: `tests/evaluation/fidelity_checker.py`
- **Reciprocal Rank Fusion**: Cormack et al., 2009

---

**Última actualización**: 2026-06-10  
**Versión**: 1.0  
**Autor**: Análisis arquitectónico comparativo
