"""
Tests unitarios para los calculadores de score de calidad.
"""

import unittest
import sys
from pathlib import Path

# Agregar el directorio del proyecto al path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.wiki.quality_scorer import (
    QualityScorer,
    QualityScore,
    calculate_quality_score
)


class TestQualityScorer(unittest.TestCase):
    """Tests para QualityScorer."""
    
    def setUp(self):
        """Configuración inicial para cada test."""
        self.scorer = QualityScorer()
    
    def test_calculate_url_score_high_quality(self):
        """Test: URL de alta calidad (arXiv)."""
        metadata = {
            'url': 'https://arxiv.org/abs/1706.03762',
            'titulo': 'Attention Is All You Need',
            'autor': 'Vaswani et al.',
            'fecha_publicacion': '2017-06-12',
            'idioma': 'en',
            'tags': ['transformers', 'nlp', 'attention'],
            'descripcion': 'Paper seminal sobre Transformers',
            'dominio': 'arxiv.org',
            'content_length': 45000,
            'citas_extraidas': [{'texto': 'Cita 1'}, {'texto': 'Cita 2'}],
            'citas_verificadas': [{'texto': 'Cita 1', 'verificado': True}, {'texto': 'Cita 2', 'verificado': True}]
        }
        
        score = self.scorer.calculate_url_score(metadata)
        
        self.assertIsInstance(score, QualityScore)
        self.assertEqual(score.tipo, 'url')
        self.assertGreaterEqual(score.score, 70.0)  # Alta calidad
        self.assertTrue(score.metadata_completa)
        self.assertEqual(len(score.advertencias), 0)
        
        # Verificar factores
        self.assertIn('metadata_completeness', score.factores)
        self.assertIn('content_length', score.factores)
        self.assertIn('citation_quality', score.factores)
        self.assertIn('domain_authority', score.factores)
    
    def test_calculate_url_score_low_quality(self):
        """Test: URL de baja calidad (metadata incompleta)."""
        metadata = {
            'url': 'https://example.com/article',
            'titulo': 'Article',
            'content_length': 500,
            'dominio': 'example.com'
        }
        
        score = self.scorer.calculate_url_score(metadata)
        
        self.assertLess(score.score, 50.0)  # Baja calidad
        self.assertFalse(score.metadata_completa)
        self.assertGreater(len(score.advertencias), 0)
    
    def test_calculate_pdf_score_complete(self):
        """Test: PDF académico completo."""
        metadata = {
            'ruta_archivo': '/tmp/paper.pdf',
            'titulo': 'Attention Is All You Need',
            'autor': 'Vaswani et al.',
            'fecha_publicacion': '2017-06-12',
            'editorial': 'NeurIPS',
            'doi': '10.48550/arXiv.1706.03762',
            'isbn': None,
            'paginas': 15,
            'idioma': 'en',
            'tags': ['transformers', 'nlp'],
            'content_length': 45000,
            'citas_extraidas': [{'texto': 'Cita 1'}],
            'citas_verificadas': [{'texto': 'Cita 1', 'verificado': True}]
        }
        
        score = self.scorer.calculate_pdf_score(metadata)
        
        self.assertIsInstance(score, QualityScore)
        self.assertEqual(score.tipo, 'pdf')
        self.assertGreaterEqual(score.score, 80.0)  # Alta calidad
        self.assertTrue(score.metadata_completa)
        
        # Verificar factores específicos de PDF
        self.assertIn('academic_identifiers', score.factores)
        self.assertIn('document_structure', score.factores)
    
    def test_calculate_pdf_score_with_doi_and_isbn(self):
        """Test: PDF con DOI e ISBN."""
        metadata = {
            'ruta_archivo': '/tmp/book.pdf',
            'titulo': 'Deep Learning',
            'autor': 'Goodfellow et al.',
            'doi': '10.1234/book',
            'isbn': '978-0262035613',
            'paginas': 800,
            'content_length': 100000
        }
        
        score = self.scorer.calculate_pdf_score(metadata)
        
        # Debería tener score alto por identificadores académicos
        self.assertGreaterEqual(score.factores['academic_identifiers'], 100.0)
    
    def test_calculate_youtube_score_with_transcript(self):
        """Test: Video de YouTube con transcripción."""
        metadata = {
            'url': 'https://www.youtube.com/watch?v=test',
            'titulo': 'Transformers Explained',
            'canal': 'AI Channel',
            'fecha_publicacion': '2020-05-15',
            'duracion': 1800,
            'idioma': 'en',
            'tags': ['transformers', 'tutorial'],
            'descripcion': 'Tutorial sobre Transformers',
            'vistas': 100000,
            'likes': 5000,
            'tiene_subtitulos': True,
            'subtitulos_extraidos': True,
            'transcripcion': 'Transcripción completa...',
            'content_length': 25000,
            'citas_extraidas': [],
            'citas_verificadas': []
        }
        
        score = self.scorer.calculate_youtube_score(metadata)
        
        self.assertIsInstance(score, QualityScore)
        self.assertEqual(score.tipo, 'youtube')
        self.assertGreaterEqual(score.score, 85.0)  # Alta calidad
        
        # Verificar factores específicos de YouTube
        self.assertIn('content_availability', score.factores)
        self.assertIn('engagement_metrics', score.factores)
        self.assertGreaterEqual(score.factores['content_availability'], 100.0)
    
    def test_calculate_youtube_score_without_transcript(self):
        """Test: Video de YouTube sin transcripción."""
        metadata = {
            'url': 'https://www.youtube.com/watch?v=test',
            'titulo': 'Video',
            'canal': 'Channel',
            'vistas': 1000,
            'likes': 50,
            'tiene_subtitulos': False,
            'content_length': 500
        }
        
        score = self.scorer.calculate_youtube_score(metadata)
        
        # Debería tener score bajo por falta de contenido
        self.assertLess(score.factores['content_availability'], 50.0)
        self.assertGreater(len(score.advertencias), 0)
    
    def test_calculate_metadata_completeness(self):
        """Test: Calcular completitud de metadatos."""
        # URL completa
        metadata = {
            'url': 'https://example.com',
            'titulo': 'Title',
            'autor': 'Author',
            'fecha_publicacion': '2020-01-01',
            'idioma': 'en',
            'tags': ['tag1'],
            'descripcion': 'Description'
        }
        
        completeness = self.scorer._calculate_metadata_completeness(metadata, 'url')
        self.assertEqual(completeness, 100.0)
        
        # URL incompleta
        metadata_incomplete = {
            'url': 'https://example.com',
            'titulo': 'Title'
        }
        
        completeness = self.scorer._calculate_metadata_completeness(metadata_incomplete, 'url')
        self.assertLess(completeness, 50.0)
    
    def test_calculate_content_length_score(self):
        """Test: Calcular score por longitud de contenido."""
        # URL excelente
        score = self.scorer._calculate_content_length_score(15000, 'url')
        self.assertEqual(score, 100.0)
        
        # URL buena
        score = self.scorer._calculate_content_length_score(7000, 'url')
        self.assertEqual(score, 80.0)
        
        # URL aceptable
        score = self.scorer._calculate_content_length_score(2000, 'url')
        self.assertEqual(score, 60.0)
        
        # URL pobre
        score = self.scorer._calculate_content_length_score(500, 'url')
        self.assertEqual(score, 30.0)
    
    def test_calculate_citation_quality(self):
        """Test: Calcular calidad de citas."""
        # Sin citas
        metadata = {'citas_extraidas': [], 'citas_verificadas': []}
        score = self.scorer._calculate_citation_quality(metadata)
        self.assertEqual(score, 50.0)  # Score neutral
        
        # Todas verificadas
        metadata = {
            'citas_extraidas': [{'texto': '1'}, {'texto': '2'}],
            'citas_verificadas': [{'texto': '1'}, {'texto': '2'}]
        }
        score = self.scorer._calculate_citation_quality(metadata)
        self.assertGreaterEqual(score, 80.0)
        
        # Ninguna verificada
        metadata = {
            'citas_extraidas': [{'texto': '1'}, {'texto': '2'}],
            'citas_verificadas': []
        }
        score = self.scorer._calculate_citation_quality(metadata)
        self.assertLess(score, 50.0)
    
    def test_calculate_domain_authority(self):
        """Test: Calcular autoridad de dominio."""
        # Dominio de alta autoridad
        authority = self.scorer._calculate_domain_authority('arxiv.org')
        self.assertEqual(authority, 1.0)
        
        # Dominio de media autoridad
        authority = self.scorer._calculate_domain_authority('medium.com')
        self.assertGreater(authority, 0.6)
        self.assertLess(authority, 0.8)
        
        # Dominio desconocido
        authority = self.scorer._calculate_domain_authority('unknown-site.com')
        self.assertEqual(authority, 0.4)
        
        # Sin dominio
        authority = self.scorer._calculate_domain_authority('')
        self.assertEqual(authority, 0.3)
    
    def test_calculate_academic_identifiers(self):
        """Test: Calcular score por identificadores académicos."""
        # Con DOI
        metadata = {'doi': '10.1234/test', 'isbn': None}
        score = self.scorer._calculate_academic_identifiers(metadata)
        self.assertEqual(score, 50.0)
        
        # Con ISBN
        metadata = {'doi': None, 'isbn': '978-1234567890'}
        score = self.scorer._calculate_academic_identifiers(metadata)
        self.assertEqual(score, 50.0)
        
        # Con ambos
        metadata = {'doi': '10.1234/test', 'isbn': '978-1234567890'}
        score = self.scorer._calculate_academic_identifiers(metadata)
        self.assertEqual(score, 100.0)
        
        # Sin identificadores
        metadata = {'doi': None, 'isbn': None}
        score = self.scorer._calculate_academic_identifiers(metadata)
        self.assertEqual(score, 0.0)
    
    def test_calculate_document_structure(self):
        """Test: Calcular score por estructura de documento."""
        # Documento largo
        metadata = {'paginas': 20}
        score = self.scorer._calculate_document_structure(metadata)
        self.assertEqual(score, 100.0)
        
        # Documento medio
        metadata = {'paginas': 7}
        score = self.scorer._calculate_document_structure(metadata)
        self.assertEqual(score, 80.0)
        
        # Documento corto
        metadata = {'paginas': 3}
        score = self.scorer._calculate_document_structure(metadata)
        self.assertEqual(score, 60.0)
        
        # Sin páginas
        metadata = {'paginas': 0}
        score = self.scorer._calculate_document_structure(metadata)
        self.assertEqual(score, 0.0)
    
    def test_calculate_content_availability(self):
        """Test: Calcular disponibilidad de contenido (YouTube)."""
        # Todo disponible
        metadata = {
            'transcripcion': 'Transcripción',
            'tiene_subtitulos': True,
            'subtitulos_extraidos': True
        }
        score = self.scorer._calculate_content_availability(metadata)
        self.assertEqual(score, 100.0)
        
        # Solo subtítulos
        metadata = {
            'transcripcion': None,
            'tiene_subtitulos': True,
            'subtitulos_extraidos': False
        }
        score = self.scorer._calculate_content_availability(metadata)
        self.assertEqual(score, 30.0)
        
        # Nada disponible
        metadata = {
            'transcripcion': None,
            'tiene_subtitulos': False,
            'subtitulos_extraidos': False
        }
        score = self.scorer._calculate_content_availability(metadata)
        self.assertEqual(score, 0.0)
    
    def test_calculate_engagement_metrics(self):
        """Test: Calcular métricas de engagement (YouTube)."""
        # Alto engagement
        metadata = {'vistas': 1000000, 'likes': 50000}
        score = self.scorer._calculate_engagement_metrics(metadata)
        self.assertGreater(score, 80.0)
        
        # Medio engagement
        metadata = {'vistas': 10000, 'likes': 500}
        score = self.scorer._calculate_engagement_metrics(metadata)
        self.assertGreater(score, 40.0)
        self.assertLess(score, 80.0)
        
        # Sin vistas
        metadata = {'vistas': 0, 'likes': 0}
        score = self.scorer._calculate_engagement_metrics(metadata)
        self.assertEqual(score, 0.0)


class TestQualityScore(unittest.TestCase):
    """Tests para QualityScore."""
    
    def test_initialization(self):
        """Test: Inicialización de QualityScore."""
        score = QualityScore(
            score=85.5,
            tipo='url',
            factores={'metadata': 90.0, 'content': 80.0},
            metadata_completa=True,
            advertencias=[]
        )
        
        self.assertEqual(score.score, 85.5)
        self.assertEqual(score.tipo, 'url')
        self.assertTrue(score.metadata_completa)
        self.assertEqual(len(score.advertencias), 0)
    
    def test_score_clamping(self):
        """Test: El score se limita a 0-100."""
        # Score muy alto
        score = QualityScore(score=150.0, tipo='url', factores={}, metadata_completa=True, advertencias=[])
        self.assertEqual(score.score, 100.0)
        
        # Score negativo
        score = QualityScore(score=-10.0, tipo='url', factores={}, metadata_completa=True, advertencias=[])
        self.assertEqual(score.score, 0.0)
    
    def test_to_dict(self):
        """Test: Convertir QualityScore a diccionario."""
        score = QualityScore(
            score=85.5,
            tipo='url',
            factores={'metadata': 90.0},
            metadata_completa=True,
            advertencias=['Warning 1']
        )
        
        score_dict = score.to_dict()
        
        self.assertIsInstance(score_dict, dict)
        self.assertEqual(score_dict['score'], 85.5)
        self.assertEqual(score_dict['tipo'], 'url')
        self.assertIn('factores', score_dict)
        self.assertIn('metadata_completa', score_dict)
        self.assertIn('advertencias', score_dict)


class TestCalculateQualityScoreFunction(unittest.TestCase):
    """Tests para la función de conveniencia calculate_quality_score."""
    
    def test_calculate_url_score(self):
        """Test: Calcular score de URL."""
        metadata = {
            'url': 'https://arxiv.org/abs/1706.03762',
            'titulo': 'Test',
            'content_length': 10000
        }
        
        score = calculate_quality_score('url', metadata)
        self.assertIsInstance(score, QualityScore)
        self.assertEqual(score.tipo, 'url')
    
    def test_calculate_pdf_score(self):
        """Test: Calcular score de PDF."""
        metadata = {
            'ruta_archivo': '/tmp/test.pdf',
            'titulo': 'Test',
            'paginas': 10
        }
        
        score = calculate_quality_score('pdf', metadata)
        self.assertIsInstance(score, QualityScore)
        self.assertEqual(score.tipo, 'pdf')
    
    def test_calculate_youtube_score(self):
        """Test: Calcular score de YouTube."""
        metadata = {
            'url': 'https://youtube.com/watch?v=test',
            'titulo': 'Test',
            'vistas': 1000
        }
        
        score = calculate_quality_score('youtube', metadata)
        self.assertIsInstance(score, QualityScore)
        self.assertEqual(score.tipo, 'youtube')
    
    def test_invalid_type(self):
        """Test: Tipo inválido lanza excepción."""
        with self.assertRaises(ValueError) as cm:
            calculate_quality_score('invalid', {})
        
        self.assertIn("Tipo de contenido no soportado", str(cm.exception))


if __name__ == '__main__':
    unittest.main(verbosity=2)
