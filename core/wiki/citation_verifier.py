"""
Verificador de citas de documentos.

Este módulo proporciona funcionalidad para verificar citas contra APIs externas
(CrossRef, Google Scholar) y la base de datos local.
"""

import requests
import time
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from urllib.parse import quote

from core.wiki.citation_extractor import Citation


@dataclass
class VerificationResult:
    """Resultado de la verificación de una cita."""
    
    # Cita original
    citation: Citation
    
    # Resultado de verificación
    verificado: bool = False
    fuente_verificacion: Optional[str] = None  # crossref, google_scholar, local, none
    
    # Datos encontrados
    doi_encontrado: Optional[str] = None
    url_encontrada: Optional[str] = None
    titulo_encontrado: Optional[str] = None
    autores_encontrados: Optional[str] = None
    año_encontrado: Optional[int] = None
    
    # Métricas de confianza
    score_confianza: float = 0.0  # 0.0 - 1.0
    coincidencias: List[str] = None  # Lista de campos que coinciden
    
    # Metadatos
    tiempo_verificacion: float = 0.0  # Segundos
    error: Optional[str] = None
    
    def __post_init__(self):
        if self.coincidencias is None:
            self.coincidencias = []


class CitationVerifier:
    """
    Verificador de citas contra APIs externas y base de datos local.
    
    Ejemplo de uso:
        verifier = CitationVerifier()
        result = verifier.verify(citation)
    """
    
    # URLs de APIs
    CROSSREF_API_URL = 'https://api.crossref.org/works'
    
    def __init__(self, use_crossref: bool = True, use_local: bool = True):
        """
        Inicializa el verificador de citas.
        
        Args:
            use_crossref: Usar API de CrossRef para verificación
            use_local: Usar base de datos local para verificación
        """
        self.use_crossref = use_crossref
        self.use_local = use_local
        
        # Cache para evitar consultas repetidas
        self.cache = {}
    
    def verify(self, citation: Citation) -> VerificationResult:
        """
        Verifica una cita contra múltiples fuentes.
        
        Args:
            citation: Cita a verificar
        
        Returns:
            VerificationResult con el resultado de la verificación
        """
        start_time = time.time()
        
        # Verificar en cache
        cache_key = self._get_cache_key(citation)
        if cache_key in self.cache:
            result = self.cache[cache_key]
            result.tiempo_verificacion = time.time() - start_time
            return result
        
        # Intentar verificar con diferentes fuentes
        result = VerificationResult(citation=citation)
        
        # 1. Verificar con DOI si está disponible
        if citation.doi:
            doi_result = self._verify_with_doi(citation.doi)
            if doi_result.verificado:
                result = doi_result
                result.tiempo_verificacion = time.time() - start_time
                self.cache[cache_key] = result
                return result
        
        # 2. Verificar con CrossRef
        if self.use_crossref and not result.verificado:
            crossref_result = self._verify_with_crossref(citation)
            if crossref_result.verificado:
                result = crossref_result
                result.tiempo_verificacion = time.time() - start_time
                self.cache[cache_key] = result
                return result
        
        # 3. Verificar con base de datos local
        if self.use_local and not result.verificado:
            local_result = self._verify_with_local_db(citation)
            if local_result.verificado:
                result = local_result
                result.tiempo_verificacion = time.time() - start_time
                self.cache[cache_key] = result
                return result
        
        # No se pudo verificar
        result.tiempo_verificacion = time.time() - start_time
        self.cache[cache_key] = result
        return result
    
    def verify_batch(self, citations: List[Citation]) -> List[VerificationResult]:
        """
        Verifica múltiples citas.
        
        Args:
            citations: Lista de citas a verificar
        
        Returns:
            Lista de VerificationResult
        """
        results = []
        
        for citation in citations:
            result = self.verify(citation)
            results.append(result)
            
            # Pausa para no saturar APIs
            if self.use_crossref:
                time.sleep(0.1)  # 100ms entre consultas
        
        return results
    
    def _verify_with_doi(self, doi: str) -> VerificationResult:
        """
        Verifica una cita usando su DOI.
        
        Args:
            doi: DOI de la cita
        
        Returns:
            VerificationResult
        """
        result = VerificationResult(
            citation=Citation(texto_original='', doi=doi),
            fuente_verificacion='crossref'
        )
        
        try:
            # Normalizar DOI
            doi = doi.replace('https://doi.org/', '').replace('http://doi.org/', '')
            
            # Consultar CrossRef
            url = f'{self.CROSSREF_API_URL}/{quote(doi, safe="")}'
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                data = response.json().get('message', {})
                
                result.verificado = True
                result.doi_encontrado = doi
                result.titulo_encontrado = data.get('title', [''])[0] if data.get('title') else None
                result.año_encontrado = data.get('published-print', {}).get('date-parts', [[None]])[0][0]
                
                # Extraer autores
                authors = data.get('author', [])
                if authors:
                    result.autores_encontrados = ', '.join([
                        f"{a.get('family', '')}, {a.get('given', '')}"
                        for a in authors[:3]
                    ])
                
                result.score_confianza = 1.0
                result.coincidencias = ['doi', 'titulo', 'autores', 'año']
            
            elif response.status_code == 404:
                result.error = 'DOI no encontrado en CrossRef'
            else:
                result.error = f'Error en API de CrossRef: {response.status_code}'
        
        except requests.exceptions.Timeout:
            result.error = 'Timeout consultando CrossRef'
        except Exception as e:
            result.error = f'Error verificando DOI: {str(e)}'
        
        return result
    
    def _verify_with_crossref(self, citation: Citation) -> VerificationResult:
        """
        Verifica una cita buscando en CrossRef por título y autor.
        
        Args:
            citation: Cita a verificar
        
        Returns:
            VerificationResult
        """
        result = VerificationResult(
            citation=citation,
            fuente_verificacion='crossref'
        )
        
        try:
            # Construir query
            query_parts = []
            if citation.titulo:
                query_parts.append(citation.titulo)
            if citation.autores:
                query_parts.append(citation.autores)
            
            if not query_parts:
                result.error = 'No hay título ni autores para buscar'
                return result
            
            query = ' '.join(query_parts)
            
            # Consultar CrossRef
            params = {
                'query': query,
                'rows': 5
            }
            
            response = requests.get(
                self.CROSSREF_API_URL,
                params=params,
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                items = data.get('message', {}).get('items', [])
                
                if items:
                    # Buscar la mejor coincidencia
                    best_match = self._find_best_match(citation, items)
                    
                    if best_match:
                        result.verificado = True
                        result.doi_encontrado = best_match.get('DOI')
                        result.titulo_encontrado = best_match.get('title', [''])[0] if best_match.get('title') else None
                        result.año_encontrado = best_match.get('published-print', {}).get('date-parts', [[None]])[0][0]
                        
                        # Extraer autores
                        authors = best_match.get('author', [])
                        if authors:
                            result.autores_encontrados = ', '.join([
                                f"{a.get('family', '')}, {a.get('given', '')}"
                                for a in authors[:3]
                            ])
                        
                        # Calcular score de confianza
                        result.score_confianza = self._calculate_confidence_score(citation, best_match)
                        result.coincidencias = self._get_coincidencias(citation, best_match)
            
            else:
                result.error = f'Error en API de CrossRef: {response.status_code}'
        
        except requests.exceptions.Timeout:
            result.error = 'Timeout consultando CrossRef'
        except Exception as e:
            result.error = f'Error verificando con CrossRef: {str(e)}'
        
        return result
    
    def _verify_with_local_db(self, citation: Citation) -> VerificationResult:
        """
        Verifica una cita en la base de datos local.
        
        Args:
            citation: Cita a verificar
        
        Returns:
            VerificationResult
        """
        result = VerificationResult(
            citation=citation,
            fuente_verificacion='local'
        )
        
        try:
            # Importar aquí para evitar dependencias circulares
            from core.wiki import Wiki
            
            wiki = Wiki()
            
            # Buscar por título
            if citation.titulo:
                search_results = wiki.search(citation.titulo, limit=5)
                
                if search_results:
                    # Buscar la mejor coincidencia
                    for item in search_results:
                        if self._is_match(citation, item):
                            result.verificado = True
                            result.titulo_encontrado = item.get('name')
                            result.url_encontrada = item.get('url')
                            result.score_confianza = 0.8
                            result.coincidencias = ['titulo']
                            break
            
            if not result.verificado:
                result.error = 'Cita no encontrada en base de datos local'
        
        except Exception as e:
            result.error = f'Error verificando con base de datos local: {str(e)}'
        
        return result
    
    def _find_best_match(self, citation: Citation, items: List[Dict]) -> Optional[Dict]:
        """
        Encuentra la mejor coincidencia en una lista de resultados.
        
        Args:
            citation: Cita original
            items: Lista de resultados de CrossRef
        
        Returns:
            Mejor coincidencia o None
        """
        best_match = None
        best_score = 0.0
        
        for item in items:
            score = self._calculate_confidence_score(citation, item)
            
            if score > best_score and score >= 0.6:  # Umbral mínimo
                best_score = score
                best_match = item
        
        return best_match
    
    def _calculate_confidence_score(self, citation: Citation, item: Dict) -> float:
        """
        Calcula el score de confianza entre una cita y un resultado.
        
        Args:
            citation: Cita original
            item: Resultado de CrossRef
        
        Returns:
            Score de confianza (0.0 - 1.0)
        """
        score = 0.0
        total_weight = 0.0
        
        # Comparar título (peso: 0.4)
        if citation.titulo and item.get('title'):
            item_title = item['title'][0] if item['title'] else ''
            title_similarity = self._string_similarity(citation.titulo, item_title)
            score += title_similarity * 0.4
            total_weight += 0.4
        
        # Comparar año (peso: 0.3)
        if citation.año and item.get('published-print'):
            item_year = item['published-print'].get('date-parts', [[None]])[0][0]
            if item_year and citation.año == item_year:
                score += 1.0 * 0.3
            total_weight += 0.3
        
        # Comparar autores (peso: 0.3)
        if citation.autores and item.get('author'):
            item_authors = ', '.join([
                f"{a.get('family', '')}, {a.get('given', '')}"
                for a in item.get('author', [])[:3]
            ])
            author_similarity = self._string_similarity(citation.autores, item_authors)
            score += author_similarity * 0.3
            total_weight += 0.3
        
        return score / total_weight if total_weight > 0 else 0.0
    
    def _get_coincidencias(self, citation: Citation, item: Dict) -> List[str]:
        """
        Obtiene la lista de campos que coinciden.
        
        Args:
            citation: Cita original
            item: Resultado de CrossRef
        
        Returns:
            Lista de campos que coinciden
        """
        coincidencias = []
        
        # Verificar título
        if citation.titulo and item.get('title'):
            item_title = item['title'][0] if item['title'] else ''
            if self._string_similarity(citation.titulo, item_title) > 0.8:
                coincidencias.append('titulo')
        
        # Verificar año
        if citation.año and item.get('published-print'):
            item_year = item['published-print'].get('date-parts', [[None]])[0][0]
            if item_year and citation.año == item_year:
                coincidencias.append('año')
        
        # Verificar autores
        if citation.autores and item.get('author'):
            item_authors = ', '.join([
                f"{a.get('family', '')}, {a.get('given', '')}"
                for a in item.get('author', [])[:3]
            ])
            if self._string_similarity(citation.autores, item_authors) > 0.7:
                coincidencias.append('autores')
        
        # Verificar DOI
        if citation.doi and item.get('DOI'):
            if citation.doi == item['DOI']:
                coincidencias.append('doi')
        
        return coincidencias
    
    def _is_match(self, citation: Citation, item: Dict) -> bool:
        """
        Verifica si un item de la base de datos local coincide con la cita.
        
        Args:
            citation: Cita original
            item: Item de la base de datos local
        
        Returns:
            True si coincide, False en caso contrario
        """
        # Comparar título
        if citation.titulo and item.get('name'):
            if self._string_similarity(citation.titulo, item['name']) > 0.8:
                return True
        
        return False
    
    def _string_similarity(self, s1: str, s2: str) -> float:
        """
        Calcula la similitud entre dos strings (0.0 - 1.0).
        
        Args:
            s1: Primer string
            s2: Segundo string
        
        Returns:
            Similitud (0.0 - 1.0)
        """
        # Normalizar strings
        s1 = s1.lower().strip()
        s2 = s2.lower().strip()
        
        if not s1 or not s2:
            return 0.0
        
        # Calcular similitud simple basada en palabras comunes
        words1 = set(s1.split())
        words2 = set(s2.split())
        
        if not words1 or not words2:
            return 0.0
        
        intersection = words1.intersection(words2)
        union = words1.union(words2)
        
        return len(intersection) / len(union)
    
    def _get_cache_key(self, citation: Citation) -> str:
        """
        Genera una clave de cache para una cita.
        
        Args:
            citation: Cita
        
        Returns:
            Clave de cache
        """
        parts = []
        if citation.doi:
            parts.append(f'doi:{citation.doi}')
        if citation.titulo:
            parts.append(f'titulo:{citation.titulo[:50]}')
        if citation.autores:
            parts.append(f'autores:{citation.autores[:50]}')
        if citation.año:
            parts.append(f'año:{citation.año}')
        
        return '|'.join(parts) if parts else citation.texto_original[:100]
    
    def clear_cache(self):
        """Limpia el cache de verificaciones."""
        self.cache.clear()


def verify_citations(citations: List[Citation], use_crossref: bool = True) -> List[Dict]:
    """
    Función de conveniencia para verificar múltiples citas.
    
    Args:
        citations: Lista de citas a verificar
        use_crossref: Usar API de CrossRef
    
    Returns:
        Lista de resultados de verificación como diccionarios
    """
    verifier = CitationVerifier(use_crossref=use_crossref)
    results = verifier.verify_batch(citations)
    
    return [
        {
            'texto_original': r.citation.texto_original,
            'verificado': r.verificado,
            'fuente_verificacion': r.fuente_verificacion,
            'doi_encontrado': r.doi_encontrado,
            'titulo_encontrado': r.titulo_encontrado,
            'score_confianza': r.score_confianza,
            'coincidencias': r.coincidencias,
            'error': r.error
        }
        for r in results
    ]


__all__ = [
    'VerificationResult',
    'CitationVerifier',
    'verify_citations',
]
