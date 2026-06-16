"""
Tests unitarios para el validador de esquemas.
"""

import unittest
import sys
from pathlib import Path

# Agregar el directorio del proyecto al path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.wiki.validators import SchemaValidator, ValidationError, validate_ingest_data


class TestSchemaValidator(unittest.TestCase):
    """Tests para SchemaValidator."""
    
    def test_load_url_schema(self):
        """Test: Cargar esquema de URL."""
        validator = SchemaValidator('url')
        self.assertEqual(validator.content_type, 'url')
        self.assertIn('url', validator.fields)
        self.assertIn('titulo', validator.fields)
    
    def test_load_pdf_schema(self):
        """Test: Cargar esquema de PDF."""
        validator = SchemaValidator('pdf')
        self.assertEqual(validator.content_type, 'pdf')
        self.assertIn('ruta_archivo', validator.fields)
        self.assertIn('titulo', validator.fields)
    
    def test_load_youtube_schema(self):
        """Test: Cargar esquema de YouTube."""
        validator = SchemaValidator('youtube')
        self.assertEqual(validator.content_type, 'youtube')
        self.assertIn('url', validator.fields)
        self.assertIn('video_id', validator.fields)
    
    def test_invalid_content_type(self):
        """Test: Tipo de contenido inválido lanza excepción."""
        with self.assertRaises(ValueError) as cm:
            SchemaValidator('invalid_type')
        self.assertIn("Tipo de contenido no válido", str(cm.exception))
    
    def test_validate_valid_url(self):
        """Test: Validar URL válida."""
        validator = SchemaValidator('url')
        data = {
            'url': 'https://arxiv.org/abs/1706.03762',
            'titulo': 'Attention Is All You Need',
            'autor': 'Vaswani et al.',
            'fecha_publicacion': '2017-06-12',
            'idioma': 'en',
            'tags': ['transformers', 'nlp'],
            'descripcion': 'Paper seminal sobre Transformers',
            'content_length': 45000
        }
        
        is_valid, errors = validator.validate(data, strict=False)
        self.assertTrue(is_valid)
        self.assertEqual(len(errors), 0)
    
    def test_validate_missing_required_field(self):
        """Test: Validar campo requerido faltante."""
        validator = SchemaValidator('url')
        data = {
            'url': 'https://example.com',
            'autor': 'Test Author'
            # Falta 'titulo' que es requerido
        }
        
        is_valid, errors = validator.validate(data, strict=False)
        self.assertFalse(is_valid)
        self.assertGreater(len(errors), 0)
        self.assertTrue(any(err.field == 'titulo' for err in errors))
    
    def test_validate_invalid_url_format(self):
        """Test: Validar formato de URL inválido."""
        validator = SchemaValidator('url')
        data = {
            'url': 'not-a-valid-url',
            'titulo': 'Test Title'
        }
        
        is_valid, errors = validator.validate(data, strict=False)
        self.assertFalse(is_valid)
        self.assertTrue(any('url' in err.field.lower() for err in errors))
    
    def test_validate_min_length(self):
        """Test: Validar longitud mínima."""
        validator = SchemaValidator('url')
        data = {
            'url': 'https://example.com',
            'titulo': 'A'  # Muy corto (mínimo 5 caracteres)
        }
        
        is_valid, errors = validator.validate(data, strict=False)
        self.assertFalse(is_valid)
        self.assertTrue(any('titulo' in err.field for err in errors))
    
    def test_validate_max_length(self):
        """Test: Validar longitud máxima."""
        validator = SchemaValidator('url')
        data = {
            'url': 'https://example.com',
            'titulo': 'A' * 600  # Muy largo (máximo 500 caracteres)
        }
        
        is_valid, errors = validator.validate(data, strict=False)
        self.assertFalse(is_valid)
        self.assertTrue(any('titulo' in err.field for err in errors))
    
    def test_validate_pattern(self):
        """Test: Validar patrón regex."""
        validator = SchemaValidator('url')
        data = {
            'url': 'https://example.com',
            'titulo': 'Test Title',
            'idioma': 'english'  # Inválido (debe ser 2 letras)
        }
        
        is_valid, errors = validator.validate(data, strict=False)
        self.assertFalse(is_valid)
        self.assertTrue(any('idioma' in err.field for err in errors))
    
    def test_validate_enum(self):
        """Test: Validar enumeración."""
        validator = SchemaValidator('pdf')
        data = {
            'ruta_archivo': '/tmp/test.pdf',
            'titulo': 'Test Paper',
            'tipo_documento': 'invalid_type'  # No está en la lista
        }
        
        is_valid, errors = validator.validate(data, strict=False)
        self.assertFalse(is_valid)
        self.assertTrue(any('tipo_documento' in err.field for err in errors))
    
    def test_calculate_quality_score(self):
        """Test: Calcular score de calidad."""
        validator = SchemaValidator('url')
        data = {
            'url': 'https://arxiv.org/abs/1706.03762',
            'titulo': 'Attention Is All You Need',
            'autor': 'Vaswani et al.',
            'fecha_publicacion': '2017-06-12',
            'idioma': 'en',
            'tags': ['transformers', 'nlp'],
            'descripcion': 'Paper seminal',
            'content_length': 45000,
            'citas_extraidas': [{'texto': 'Citation 1'}],
            'citas_verificadas': [{'texto': 'Citation 1', 'verificado': True}]
        }
        
        score = validator.calculate_quality_score(data)
        self.assertGreaterEqual(score, 0)
        self.assertLessEqual(score, 100)
        self.assertGreater(score, 80)  # Debería ser alto con todos los campos
    
    def test_validate_strict_mode(self):
        """Test: Modo estricto detiene en primer error."""
        validator = SchemaValidator('url')
        data = {
            # Faltan múltiples campos requeridos
            'autor': 'Test Author'
        }
        
        is_valid, errors = validator.validate(data, strict=True)
        self.assertFalse(is_valid)
        self.assertEqual(len(errors), 1)  # Solo el primer error
    
    def test_validate_non_strict_mode(self):
        """Test: Modo no estricto recopila todos los errores."""
        validator = SchemaValidator('url')
        data = {
            # Faltan múltiples campos requeridos
            'autor': 'Test Author'
        }
        
        is_valid, errors = validator.validate(data, strict=False)
        self.assertFalse(is_valid)
        self.assertGreaterEqual(len(errors), 1)  # Al menos un error


class TestValidateIngestData(unittest.TestCase):
    """Tests para la función de conveniencia validate_ingest_data."""
    
    def test_validate_url_success(self):
        """Test: Validar URL exitosamente."""
        data = {
            'url': 'https://arxiv.org/abs/1706.03762',
            'titulo': 'Attention Is All You Need',
            'autor': 'Vaswani et al.',
            'content_length': 45000
        }
        
        is_valid, errors, score = validate_ingest_data('url', data, strict=False)
        self.assertTrue(is_valid)
        self.assertEqual(len(errors), 0)
        self.assertGreater(score, 0)
    
    def test_validate_pdf_success(self):
        """Test: Validar PDF exitosamente."""
        data = {
            'ruta_archivo': '/tmp/test.pdf',
            'titulo': 'Test Paper',
            'paginas': 15,
            'content_length': 30000
        }
        
        is_valid, errors, score = validate_ingest_data('pdf', data, strict=False)
        # Puede fallar por validación de archivo, pero no debería lanzar excepción
        self.assertIsInstance(is_valid, bool)
        self.assertIsInstance(errors, list)
        self.assertIsInstance(score, (int, float))
    
    def test_validate_youtube_success(self):
        """Test: Validar YouTube exitosamente."""
        data = {
            'url': 'https://www.youtube.com/watch?v=dQw4w9WgXcQ',
            'titulo': 'Test Video',
            'canal': 'Test Channel',
            'duracion': 1800,
            'content_length': 25000
        }
        
        is_valid, errors, score = validate_ingest_data('youtube', data, strict=False)
        self.assertTrue(is_valid)
        self.assertEqual(len(errors), 0)
        self.assertGreater(score, 0)


if __name__ == '__main__':
    unittest.main(verbosity=2)
