"""
Calculadores de score de calidad para diferentes tipos de contenido.

Este módulo proporciona funciones para calcular scores de calidad (0-100)
para URLs, PDFs y videos de YouTube basándose en metadatos y contenido.
"""

from typing import Dict, List, Optional
from dataclasses import dataclass


@dataclass
class QualityScore:
    """Representa el score de calidad de un contenido."""
    
    score: float  # 0-100
    tipo: str  # url, pdf, youtube
    factores: Dict[str, float]  # Desglose por factor
    metadata_completa: bool  # Si todos los campos requeridos están presentes
    advertencias: List[str]  # Lista de advertencias
    
    def __post_init__(self):
        # Asegurar que el score esté en rango válido
        self.score = max(0.0, min(100.0, self.score))
        
        if self.factores is None:
            self.factores = {}
        if self.advertencias is None:
            self.advertencias = []
    
    def to_dict(self) -> Dict:
        """Convierte el score a diccionario."""
        return {
            'score': self.score,
            'tipo': self.tipo,
            'factores': self.factores,
            'metadata_completa': self.metadata_completa,
            'advertencias': self.advertencias
        }


class QualityScorer:
    """
    Calculador de scores de calidad para diferentes tipos de contenido.
    
    Ejemplo de uso:
        scorer = QualityScorer()
        score = scorer.calculate_url_score(metadata)
    """
    
    # Pesos por factor para cada tipo de contenido
    WEIGHTS = {
        'url': {
            'metadata_completeness': 0.25,
            'content_length': 0.25,
            'citation_quality': 0.30,
            'domain_authority': 0.20
        },
        'pdf': {
            'metadata_completeness': 0.20,
            'content_length': 0.20,
            'citation_quality': 0.35,
            'academic_identifiers': 0.15,
            'document_structure': 0.10
        },
        'youtube': {
            'metadata_completeness': 0.25,
            'content_availability': 0.30,
            'content_length': 0.20,
            'engagement_metrics': 0.15,
            'citation_quality': 0.10
        }
    }
    
    # Dominios de alta autoridad
    TRUSTED_DOMAINS = {
        'arxiv.org': 1.0,
        'nature.com': 1.0,
        'science.org': 1.0,
        'ieee.org': 0.95,
        'acm.org': 0.95,
        'github.com': 0.85,
        'medium.com': 0.70,
        'towardsdatascience.com': 0.75,
        'wikipedia.org': 0.80,
        'stackoverflow.com': 0.75
    }
    
    def __init__(self):
        """Inicializa el calculador de scores."""
        pass
    
    def calculate_url_score(self, metadata: Dict) -> QualityScore:
        """
        Calcula el score de calidad para una URL.
        
        Args:
            metadata: Diccionario con metadatos de la URL
        
        Returns:
            QualityScore con el resultado
        """
        factores = {}
        advertencias = []
        
        # Factor 1: Completitud de metadatos (25%)
        metadata_score = self._calculate_metadata_completeness(metadata, 'url')
        factores['metadata_completeness'] = metadata_score
        
        # Factor 2: Longitud del contenido (25%)
        content_length = metadata.get('content_length', 0)
        content_score = self._calculate_content_length_score(content_length, 'url')
        factores['content_length'] = content_score
        
        # Factor 3: Calidad de citas (30%)
        citation_score = self._calculate_citation_quality(metadata)
        factores['citation_quality'] = citation_score
        
        # Factor 4: Autoridad del dominio (20%)
        domain = metadata.get('dominio', '')
        domain_score = self._calculate_domain_authority(domain)
        factores['domain_authority'] = domain_score
        
        # Calcular score final
        final_score = sum(
            factores[factor] * self.WEIGHTS['url'][factor]
            for factor in factores
        )
        
        # Generar advertencias
        if metadata_score < 70:
            advertencias.append('Metadatos incompletos')
        if content_length < 1000:
            advertencias.append('Contenido muy corto (<1000 caracteres)')
        if citation_score < 50:
            advertencias.append('Baja calidad de citas')
        if domain_score < 0.5:
            advertencias.append(f'Dominio de baja autoridad: {domain}')
        
        metadata_completa = metadata_score >= 90
        
        return QualityScore(
            score=final_score,
            tipo='url',
            factores=factores,
            metadata_completa=metadata_completa,
            advertencias=advertencias
        )
    
    def calculate_pdf_score(self, metadata: Dict) -> QualityScore:
        """
        Calcula el score de calidad para un PDF.
        
        Args:
            metadata: Diccionario con metadatos del PDF
        
        Returns:
            QualityScore con el resultado
        """
        factores = {}
        advertencias = []
        
        # Factor 1: Completitud de metadatos (20%)
        metadata_score = self._calculate_metadata_completeness(metadata, 'pdf')
        factores['metadata_completeness'] = metadata_score
        
        # Factor 2: Longitud del contenido (20%)
        content_length = metadata.get('content_length', 0)
        content_score = self._calculate_content_length_score(content_length, 'pdf')
        factores['content_length'] = content_score
        
        # Factor 3: Calidad de citas (35%)
        citation_score = self._calculate_citation_quality(metadata)
        factores['citation_quality'] = citation_score
        
        # Factor 4: Identificadores académicos (15%)
        academic_score = self._calculate_academic_identifiers(metadata)
        factores['academic_identifiers'] = academic_score
        
        # Factor 5: Estructura del documento (10%)
        structure_score = self._calculate_document_structure(metadata)
        factores['document_structure'] = structure_score
        
        # Calcular score final
        final_score = sum(
            factores[factor] * self.WEIGHTS['pdf'][factor]
            for factor in factores
        )
        
        # Generar advertencias
        if metadata_score < 70:
            advertencias.append('Metadatos incompletos')
        if content_length < 5000:
            advertencias.append('Contenido muy corto (<5000 caracteres)')
        if citation_score < 50:
            advertencias.append('Baja calidad de citas')
        if academic_score < 50:
            advertencias.append('Faltan identificadores académicos (DOI/ISBN)')
        if structure_score < 50:
            advertencias.append('Estructura del documento deficiente')
        
        metadata_completa = metadata_score >= 90
        
        return QualityScore(
            score=final_score,
            tipo='pdf',
            factores=factores,
            metadata_completa=metadata_completa,
            advertencias=advertencias
        )
    
    def calculate_youtube_score(self, metadata: Dict) -> QualityScore:
        """
        Calcula el score de calidad para un video de YouTube.
        
        Args:
            metadata: Diccionario con metadatos del video
        
        Returns:
            QualityScore con el resultado
        """
        factores = {}
        advertencias = []
        
        # Factor 1: Completitud de metadatos (25%)
        metadata_score = self._calculate_metadata_completeness(metadata, 'youtube')
        factores['metadata_completeness'] = metadata_score
        
        # Factor 2: Disponibilidad de contenido (30%)
        availability_score = self._calculate_content_availability(metadata)
        factores['content_availability'] = availability_score
        
        # Factor 3: Longitud del contenido (20%)
        content_length = metadata.get('content_length', 0)
        content_score = self._calculate_content_length_score(content_length, 'youtube')
        factores['content_length'] = content_score
        
        # Factor 4: Métricas de engagement (15%)
        engagement_score = self._calculate_engagement_metrics(metadata)
        factores['engagement_metrics'] = engagement_score
        
        # Factor 5: Calidad de citas (10%)
        citation_score = self._calculate_citation_quality(metadata)
        factores['citation_quality'] = citation_score
        
        # Calcular score final
        final_score = sum(
            factores[factor] * self.WEIGHTS['youtube'][factor]
            for factor in factores
        )
        
        # Generar advertencias
        if metadata_score < 70:
            advertencias.append('Metadatos incompletos')
        if availability_score < 50:
            advertencias.append('Contenido no disponible (sin transcripción/subtítulos)')
        if content_length < 3000:
            advertencias.append('Contenido muy corto (<3000 caracteres)')
        if engagement_score < 30:
            advertencias.append('Bajo engagement (vistas/likes)')
        if citation_score < 50:
            advertencias.append('Baja calidad de citas')
        
        metadata_completa = metadata_score >= 90
        
        return QualityScore(
            score=final_score,
            tipo='youtube',
            factores=factores,
            metadata_completa=metadata_completa,
            advertencias=advertencias
        )
    
    def _calculate_metadata_completeness(self, metadata: Dict, tipo: str) -> float:
        """
        Calcula la completitud de metadatos (0-100).
        
        Args:
            metadata: Diccionario con metadatos
            tipo: Tipo de contenido (url, pdf, youtube)
        
        Returns:
            Score de completitud (0-100)
        """
        # Campos requeridos por tipo
        required_fields = {
            'url': ['url', 'titulo', 'autor', 'fecha_publicacion', 'idioma', 'tags', 'descripcion'],
            'pdf': ['ruta_archivo', 'titulo', 'autor', 'fecha_publicacion', 'editorial', 'doi', 'isbn', 'paginas', 'idioma', 'tags'],
            'youtube': ['url', 'titulo', 'canal', 'fecha_publicacion', 'duracion', 'idioma', 'tags', 'descripcion']
        }
        
        fields = required_fields.get(tipo, [])
        if not fields:
            return 100.0
        
        present = sum(1 for field in fields if metadata.get(field) not in [None, '', []])
        return (present / len(fields)) * 100.0
    
    def _calculate_content_length_score(self, content_length: int, tipo: str) -> float:
        """
        Calcula el score basado en longitud del contenido (0-100).
        
        Args:
            content_length: Longitud del contenido en caracteres
            tipo: Tipo de contenido
        
        Returns:
            Score (0-100)
        """
        thresholds = {
            'url': {'excellent': 10000, 'good': 5000, 'acceptable': 1000},
            'pdf': {'excellent': 30000, 'good': 15000, 'acceptable': 5000},
            'youtube': {'excellent': 20000, 'good': 10000, 'acceptable': 3000}
        }
        
        t = thresholds.get(tipo, thresholds['url'])
        
        if content_length >= t['excellent']:
            return 100.0
        elif content_length >= t['good']:
            return 80.0
        elif content_length >= t['acceptable']:
            return 60.0
        else:
            return 30.0
    
    def _calculate_citation_quality(self, metadata: Dict) -> float:
        """
        Calcula la calidad de citas (0-100).
        
        Args:
            metadata: Diccionario con metadatos
        
        Returns:
            Score (0-100)
        """
        citas_extraidas = metadata.get('citas_extraidas', [])
        citas_verificadas = metadata.get('citas_verificadas', [])
        
        if not citas_extraidas:
            # Si no hay citas extraídas, score neutral
            return 50.0
        
        # Calcular porcentaje de verificación
        verification_rate = len(citas_verificadas) / len(citas_extraidas)
        
        # Bonus por cantidad de citas
        quantity_bonus = min(len(citas_extraidas) / 10.0, 1.0) * 20.0
        
        # Score base: 80% verificación + 20% cantidad
        base_score = verification_rate * 80.0
        
        return min(base_score + quantity_bonus, 100.0)
    
    def _calculate_domain_authority(self, domain: str) -> float:
        """
        Calcula la autoridad del dominio (0.0-1.0).
        
        Args:
            domain: Nombre del dominio
        
        Returns:
            Score (0.0-1.0)
        """
        if not domain:
            return 0.3  # Score bajo si no hay dominio
        
        # Normalizar dominio
        domain = domain.lower().replace('www.', '')
        
        # Buscar en dominios confiables
        for trusted_domain, authority in self.TRUSTED_DOMAINS.items():
            if trusted_domain in domain:
                return authority
        
        # Dominio no reconocido
        return 0.4
    
    def _calculate_academic_identifiers(self, metadata: Dict) -> float:
        """
        Calcula el score por identificadores académicos (0-100).
        
        Args:
            metadata: Diccionario con metadatos
        
        Returns:
            Score (0-100)
        """
        score = 0.0
        
        # DOI (50 puntos)
        if metadata.get('doi'):
            score += 50.0
        
        # ISBN (50 puntos)
        if metadata.get('isbn'):
            score += 50.0
        
        return score
    
    def _calculate_document_structure(self, metadata: Dict) -> float:
        """
        Calcula el score por estructura del documento (0-100).
        
        Args:
            metadata: Diccionario con metadatos
        
        Returns:
            Score (0-100)
        """
        paginas = metadata.get('paginas', 0)
        
        if paginas == 0:
            return 0.0
        
        # Score basado en número de páginas
        if paginas >= 10:
            return 100.0
        elif paginas >= 5:
            return 80.0
        elif paginas >= 2:
            return 60.0
        else:
            return 40.0
    
    def _calculate_content_availability(self, metadata: Dict) -> float:
        """
        Calcula la disponibilidad de contenido para YouTube (0-100).
        
        Args:
            metadata: Diccionario con metadatos
        
        Returns:
            Score (0-100)
        """
        score = 0.0
        
        # Transcripción disponible (50 puntos)
        if metadata.get('transcripcion'):
            score += 50.0
        
        # Subtítulos disponibles (30 puntos)
        if metadata.get('tiene_subtitulos'):
            score += 30.0
        
        # Subtítulos extraídos (20 puntos)
        if metadata.get('subtitulos_extraidos'):
            score += 20.0
        
        return score
    
    def _calculate_engagement_metrics(self, metadata: Dict) -> float:
        """
        Calcula el score por métricas de engagement (0-100).
        
        Args:
            metadata: Diccionario con metadatos
        
        Returns:
            Score (0-100)
        """
        vistas = metadata.get('vistas', 0)
        likes = metadata.get('likes', 0)
        
        if vistas == 0:
            return 0.0
        
        # Score basado en vistas (70 puntos)
        import math
        views_score = min(math.log10(max(vistas, 1)) / 6.0, 1.0) * 70.0
        
        # Score basado en ratio de likes (30 puntos)
        like_ratio = likes / vistas if vistas > 0 else 0
        likes_score = min(like_ratio * 100, 1.0) * 30.0
        
        return views_score + likes_score


def calculate_quality_score(tipo: str, metadata: Dict) -> QualityScore:
    """
    Función de conveniencia para calcular score de calidad.
    
    Args:
        tipo: Tipo de contenido (url, pdf, youtube)
        metadata: Diccionario con metadatos
    
    Returns:
        QualityScore con el resultado
    """
    scorer = QualityScorer()
    
    if tipo == 'url':
        return scorer.calculate_url_score(metadata)
    elif tipo == 'pdf':
        return scorer.calculate_pdf_score(metadata)
    elif tipo == 'youtube':
        return scorer.calculate_youtube_score(metadata)
    else:
        raise ValueError(f"Tipo de contenido no soportado: {tipo}")


__all__ = [
    'QualityScore',
    'QualityScorer',
    'calculate_quality_score',
]
