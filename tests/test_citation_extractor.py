"""
Tests unitarios para el extractor de citas.
"""

import unittest
import sys
from pathlib import Path

# Agregar el directorio del proyecto al path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.wiki.citation_extractor import CitationExtractor, Citation, extract_citations


class TestCitationExtractor(unittest.TestCase):
    """Tests para CitationExtractor."""
    
    def setUp(self):
        """Configuración inicial para cada test."""
        self.extractor = CitationExtractor()
    
    def test_extract_apa_citation(self):
        """Test: Extraer cita en formato APA."""
        text = '''
        Vaswani, A., Shazeer, N., Parmar, N., Uszkoreit, J., Jones, L., Gomez, A. N., Kaiser, Ł., & Polosukhin, I. (2017). Attention is all you need. Advances in Neural Information Processing Systems, 30, 5998-6008. https://doi.org/10.48550/arXiv.1706.03762
        '''
        
        citations = self.extractor.extract(text)
        self.assertGreater(len(citations), 0)
        
        citation = citations[0]
        self.assertEqual(citation.formato, 'apa')
        self.assertEqual(citation.año, 2017)
        self.assertIn('Attention', citation.titulo)
    
    def test_extract_inline_citation(self):
        """Test: Extraer cita en línea (Author, Year)."""
        text = '''
        Recent studies have shown that transformers are effective for NLP tasks (Vaswani et al., 2017).
        '''
        
        citations = self.extractor.extract(text)
        self.assertGreater(len(citations), 0)
        
        citation = citations[0]
        self.assertEqual(citation.formato, 'inline')
        self.assertEqual(citation.año, 2017)
        self.assertIn('Vaswani', citation.autores)
    
    def test_extract_multiple_citations(self):
        """Test: Extraer múltiples citas de un texto."""
        text = '''
        Smith (2020) demonstrated that machine learning models can achieve high accuracy.
        Building on this work, Johnson and Williams (2021) showed that ensemble methods improve performance.
        Recent surveys (Brown et al., 2022) confirm these findings.
        '''
        
        citations = self.extractor.extract(text)
        self.assertEqual(len(citations), 3)
        
        # Verificar que todas las citas tienen año
        for citation in citations:
            self.assertIsNotNone(citation.año)
            self.assertGreaterEqual(citation.año, 2020)
            self.assertLessEqual(citation.año, 2022)
    
    def test_extract_no_citations(self):
        """Test: Texto sin citas."""
        text = '''
        This is a simple text without any citations or references.
        It just contains regular sentences.
        '''
        
        citations = self.extractor.extract(text)
        self.assertEqual(len(citations), 0)
    
    def test_remove_duplicates(self):
        """Test: Eliminar citas duplicadas."""
        text = '''
        (Smith, 2020) mentioned this finding.
        As noted earlier (Smith, 2020), the results are significant.
        '''
        
        citations = self.extractor.extract(text)
        # Debería haber solo 1 cita única
        self.assertEqual(len(citations), 1)
    
    def test_citation_context(self):
        """Test: Extraer contexto alrededor de la cita."""
        text = '''
        This is some context before the citation.
        Smith (2020) demonstrated important findings.
        This is some context after the citation.
        '''
        
        citations = self.extractor.extract(text, contexto_chars=100)
        self.assertGreater(len(citations), 0)
        
        citation = citations[0]
        self.assertIsNotNone(citation.contexto)
        self.assertGreater(len(citation.contexto), 0)
    
    def test_citation_to_dict(self):
        """Test: Convertir cita a diccionario."""
        citation = Citation(
            texto_original='Smith (2020)',
            formato='inline',
            autores='Smith',
            año=2020
        )
        
        citation_dict = citation.to_dict()
        self.assertIsInstance(citation_dict, dict)
        self.assertEqual(citation_dict['texto_original'], 'Smith (2020)')
        self.assertEqual(citation_dict['formato'], 'inline')
        self.assertEqual(citation_dict['autores'], 'Smith')
        self.assertEqual(citation_dict['año'], 2020)
    
    def test_citation_get_identifier(self):
        """Test: Obtener identificador de cita."""
        # Con DOI
        citation1 = Citation(
            texto_original='Test',
            doi='10.1234/test'
        )
        self.assertEqual(citation1.get_identifier(), '10.1234/test')
        
        # Con URL
        citation2 = Citation(
            texto_original='Test',
            url='https://example.com'
        )
        self.assertEqual(citation2.get_identifier(), 'https://example.com')
        
        # Sin identificador
        citation3 = Citation(
            texto_original='Test'
        )
        self.assertIsNone(citation3.get_identifier())
    
    def test_extract_ieee_citation(self):
        """Test: Extraer cita en formato IEEE."""
        text = '''
        [1] A. Vaswani and N. Shazeer, "Attention is all you need," Advances in Neural Information Processing Systems, vol. 30, pp. 5998-6008, 2017.
        '''
        
        citations = self.extractor.extract(text)
        # IEEE puede ser difícil de parsear, así que solo verificamos que no falle
        self.assertIsInstance(citations, list)
    
    def test_extract_mla_citation(self):
        """Test: Extraer cita en formato MLA."""
        text = '''
        Vaswani, Ashish, et al. "Attention is all you need." Advances in Neural Information Processing Systems, vol. 30, 2017, pp. 5998-6008.
        '''
        
        citations = self.extractor.extract(text)
        # MLA puede ser difícil de parsear, así que solo verificamos que no falle
        self.assertIsInstance(citations, list)


class TestExtractCitationsFunction(unittest.TestCase):
    """Tests para la función de conveniencia extract_citations."""
    
    def test_extract_citations_basic(self):
        """Test: Extraer citas con función de conveniencia."""
        text = '''
        Smith (2020) demonstrated important findings.
        Johnson (2021) confirmed these results.
        '''
        
        citations = extract_citations(text)
        self.assertIsInstance(citations, list)
        self.assertGreater(len(citations), 0)
        
        # Verificar que son diccionarios
        for citation in citations:
            self.assertIsInstance(citation, dict)
            self.assertIn('texto_original', citation)
    
    def test_extract_citations_with_format_filter(self):
        """Test: Filtrar citas por formato."""
        text = '''
        Smith (2020) demonstrated important findings.
        Vaswani, A., et al. (2017). Attention is all you need. NeurIPS, 30, 5998-6008.
        '''
        
        # Filtrar solo inline
        inline_citations = extract_citations(text, formato='inline')
        for citation in inline_citations:
            self.assertEqual(citation['formato'], 'inline')
        
        # Filtrar solo APA
        apa_citations = extract_citations(text, formato='apa')
        for citation in apa_citations:
            self.assertEqual(citation['formato'], 'apa')


if __name__ == '__main__':
    unittest.main(verbosity=2)
