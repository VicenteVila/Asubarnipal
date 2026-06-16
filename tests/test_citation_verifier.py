"""
Tests unitarios para el verificador de citas.
"""

import unittest
import sys
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

# Agregar el directorio del proyecto al path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.wiki.citation_extractor import Citation
from core.wiki.citation_verifier import (
    CitationVerifier,
    VerificationResult,
    verify_citations
)


class TestCitationVerifier(unittest.TestCase):
    """Tests para CitationVerifier."""
    
    def setUp(self):
        """Configuración inicial para cada test."""
        self.verifier = CitationVerifier(use_crossref=False, use_local=False)
    
    def test_initialization(self):
        """Test: Inicialización del verificador."""
        verifier = CitationVerifier(use_crossref=True, use_local=True)
        self.assertTrue(verifier.use_crossref)
        self.assertTrue(verifier.use_local)
        self.assertIsInstance(verifier.cache, dict)
    
    def test_verify_citation_basic(self):
        """Test: Verificar cita básica."""
        citation = Citation(
            texto_original='Smith (2020)',
            formato='inline',
            autores='Smith',
            año=2020
        )
        
        result = self.verifier.verify(citation)
        self.assertIsInstance(result, VerificationResult)
        self.assertFalse(result.verificado)  # Sin APIs habilitadas
    
    def test_verify_with_doi(self):
        """Test: Verificar cita con DOI."""
        citation = Citation(
            texto_original='Test',
            doi='10.1234/test'
        )
        
        # Mock de la API de CrossRef
        with patch('requests.get') as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                'message': {
                    'DOI': '10.1234/test',
                    'title': ['Test Paper'],
                    'author': [{'family': 'Smith', 'given': 'John'}],
                    'published-print': {'date-parts': [[2020]]}
                }
            }
            mock_get.return_value = mock_response
            
            verifier = CitationVerifier(use_crossref=True, use_local=False)
            result = verifier.verify(citation)
            
            self.assertTrue(result.verificado)
            self.assertEqual(result.fuente_verificacion, 'crossref')
            self.assertEqual(result.doi_encontrado, '10.1234/test')
    
    def test_verify_batch(self):
        """Test: Verificar múltiples citas."""
        citations = [
            Citation(texto_original='Cita 1', año=2020),
            Citation(texto_original='Cita 2', año=2021),
            Citation(texto_original='Cita 3', año=2022)
        ]
        
        results = self.verifier.verify_batch(citations)
        self.assertEqual(len(results), 3)
        self.assertIsInstance(results[0], VerificationResult)
    
    def test_cache_functionality(self):
        """Test: Funcionalidad de cache."""
        citation = Citation(texto_original='Test', doi='10.1234/test')
        
        # Primera verificación
        result1 = self.verifier.verify(citation)
        
        # Segunda verificación (debería usar cache)
        result2 = self.verifier.verify(citation)
        
        # Ambas deberían ser el mismo objeto (desde cache)
        self.assertEqual(result1.citation.texto_original, result2.citation.texto_original)
    
    def test_clear_cache(self):
        """Test: Limpiar cache."""
        citation = Citation(texto_original='Test')
        self.verifier.verify(citation)
        
        self.assertGreater(len(self.verifier.cache), 0)
        
        self.verifier.clear_cache()
        self.assertEqual(len(self.verifier.cache), 0)
    
    def test_string_similarity(self):
        """Test: Calcular similitud entre strings."""
        # Strings idénticos
        sim1 = self.verifier._string_similarity('hello world', 'hello world')
        self.assertEqual(sim1, 1.0)
        
        # Strings similares
        sim2 = self.verifier._string_similarity('hello world', 'hello there')
        self.assertGreater(sim2, 0.0)
        self.assertLess(sim2, 1.0)
        
        # Strings diferentes
        sim3 = self.verifier._string_similarity('hello', 'goodbye')
        self.assertEqual(sim3, 0.0)
        
        # Strings vacíos
        sim4 = self.verifier._string_similarity('', 'test')
        self.assertEqual(sim4, 0.0)
    
    def test_calculate_confidence_score(self):
        """Test: Calcular score de confianza."""
        citation = Citation(
            texto_original='Test',
            titulo='Attention is all you need',
            autores='Vaswani',
            año=2017
        )
        
        item = {
            'title': ['Attention is all you need'],
            'author': [{'family': 'Vaswani', 'given': 'Ashish'}],
            'published-print': {'date-parts': [[2017]]}
        }
        
        score = self.verifier._calculate_confidence_score(citation, item)
        self.assertGreaterEqual(score, 0.0)
        self.assertLessEqual(score, 1.0)
        self.assertGreater(score, 0.5)  # Debería ser alto con coincidencias
    
    def test_get_coincidencias(self):
        """Test: Obtener lista de coincidencias."""
        citation = Citation(
            texto_original='Test',
            titulo='Attention is all you need',
            año=2017
        )
        
        item = {
            'title': ['Attention is all you need'],
            'published-print': {'date-parts': [[2017]]}
        }
        
        coincidencias = self.verifier._get_coincidencias(citation, item)
        self.assertIsInstance(coincidencias, list)
        self.assertIn('titulo', coincidencias)
        self.assertIn('año', coincidencias)
    
    def test_get_cache_key(self):
        """Test: Generar clave de cache."""
        citation1 = Citation(texto_original='Test 1', doi='10.1234/test1')
        citation2 = Citation(texto_original='Test 2', doi='10.1234/test2')
        
        key1 = self.verifier._get_cache_key(citation1)
        key2 = self.verifier._get_cache_key(citation2)
        
        self.assertNotEqual(key1, key2)
        self.assertIn('doi:', key1)


class TestVerificationResult(unittest.TestCase):
    """Tests para VerificationResult."""
    
    def test_initialization(self):
        """Test: Inicialización de VerificationResult."""
        citation = Citation(texto_original='Test')
        result = VerificationResult(citation=citation)
        
        self.assertEqual(result.citation, citation)
        self.assertFalse(result.verificado)
        self.assertIsNone(result.fuente_verificacion)
        self.assertEqual(result.score_confianza, 0.0)
        self.assertIsInstance(result.coincidencias, list)
    
    def test_initialization_with_values(self):
        """Test: Inicialización con valores."""
        citation = Citation(texto_original='Test')
        result = VerificationResult(
            citation=citation,
            verificado=True,
            fuente_verificacion='crossref',
            doi_encontrado='10.1234/test',
            score_confianza=0.95,
            coincidencias=['doi', 'titulo']
        )
        
        self.assertTrue(result.verificado)
        self.assertEqual(result.fuente_verificacion, 'crossref')
        self.assertEqual(result.doi_encontrado, '10.1234/test')
        self.assertEqual(result.score_confianza, 0.95)
        self.assertEqual(len(result.coincidencias), 2)


class TestVerifyCitationsFunction(unittest.TestCase):
    """Tests para la función de conveniencia verify_citations."""
    
    def test_verify_citations_basic(self):
        """Test: Verificar citas con función de conveniencia."""
        citations = [
            Citation(texto_original='Cita 1', año=2020),
            Citation(texto_original='Cita 2', año=2021)
        ]
        
        results = verify_citations(citations, use_crossref=False)
        self.assertEqual(len(results), 2)
        
        # Verificar que son diccionarios
        for result in results:
            self.assertIsInstance(result, dict)
            self.assertIn('texto_original', result)
            self.assertIn('verificado', result)
            self.assertIn('score_confianza', result)


if __name__ == '__main__':
    unittest.main(verbosity=2)
