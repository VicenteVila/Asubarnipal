"""
Validador de esquemas para ingesta de contenido.

Este módulo proporciona funcionalidad para validar datos contra esquemas YAML
definidos en core/wiki/schemas/.
"""

import re
import yaml
from datetime import datetime, date
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from urllib.parse import urlparse

from core.wiki.schemas import get_schema_path, SCHEMA_MAP


class ValidationError(Exception):
    """Excepción lanzada cuando la validación falla."""
    
    def __init__(self, field: str, message: str, value: Any = None):
        self.field = field
        self.message = message
        self.value = value
        super().__init__(f"Error en campo '{field}': {message}")


class SchemaValidator:
    """
    Validador de datos contra esquemas YAML.
    
    Ejemplo de uso:
        validator = SchemaValidator('url')
        is_valid, errors = validator.validate(data)
    """
    
    def __init__(self, content_type: str):
        """
        Inicializa el validador para un tipo de contenido.
        
        Args:
            content_type: Tipo de contenido ('url', 'pdf', 'youtube')
        """
        self.content_type = content_type
        self.schema = self._load_schema()
        self.fields = self.schema.get('fields', {})
        self.cross_validations = self.schema.get('cross_validations', [])
        self.quality_config = self.schema.get('quality_config', {})
    
    def _load_schema(self) -> Dict[str, Any]:
        """Carga el esquema YAML desde el archivo."""
        schema_path = get_schema_path(self.content_type)
        with open(schema_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    
    def validate(self, data: Dict[str, Any], strict: bool = True) -> Tuple[bool, List[ValidationError]]:
        """
        Valida datos contra el esquema.
        
        Args:
            data: Diccionario con los datos a validar
            strict: Si es True, falla en el primer error. Si es False, recopila todos los errores.
        
        Returns:
            Tupla (is_valid, errors) donde:
                - is_valid: True si todos los datos son válidos
                - errors: Lista de ValidationError con los errores encontrados
        """
        errors = []
        
        # Validar campos individuales
        for field_name, field_schema in self.fields.items():
            value = data.get(field_name)
            field_errors = self._validate_field(field_name, value, field_schema)
            
            if field_errors:
                if strict:
                    return False, field_errors
                errors.extend(field_errors)
        
        # Validaciones cruzadas
        if not errors or not strict:
            cross_errors = self._validate_cross(data)
            if cross_errors:
                if strict:
                    return False, cross_errors
                errors.extend(cross_errors)
        
        return len(errors) == 0, errors
    
    def _validate_field(
        self,
        field_name: str,
        value: Any,
        field_schema: Dict[str, Any]
    ) -> List[ValidationError]:
        """
        Valida un campo individual contra su esquema.
        
        Args:
            field_name: Nombre del campo
            value: Valor del campo
            field_schema: Esquema del campo
        
        Returns:
            Lista de ValidationError (vacía si el campo es válido)
        """
        errors = []
        
        # Verificar si el campo es requerido
        required = field_schema.get('required', False)
        if required and (value is None or value == ''):
            errors.append(ValidationError(
                field_name,
                f"Campo requerido no proporcionado",
                value
            ))
            return errors
        
        # Si el valor es None y no es requerido, no validar más
        if value is None:
            return errors
        
        # Aplicar validaciones
        validations = field_schema.get('validations', [])
        for validation in validations:
            error = self._apply_validation(field_name, value, validation)
            if error:
                errors.append(error)
                break  # Detener en el primer error del campo
        
        return errors
    
    def _apply_validation(
        self,
        field_name: str,
        value: Any,
        validation: Dict[str, Any]
    ) -> Optional[ValidationError]:
        """
        Aplica una validación específica a un valor.
        
        Args:
            field_name: Nombre del campo
            value: Valor a validar
            validation: Definición de la validación
        
        Returns:
            ValidationError si la validación falla, None si pasa
        """
        validation_type = validation.get('type')
        message = validation.get('message', f"Validación '{validation_type}' falló")
        
        # Validación de formato
        if validation_type == 'format':
            format_type = validation.get('format')
            if format_type == 'url':
                if not self._is_valid_url(value):
                    return ValidationError(field_name, message, value)
            elif format_type == 'date':
                if not self._is_valid_date(value):
                    return ValidationError(field_name, message, value)
            elif format_type == 'datetime':
                if not self._is_valid_datetime(value):
                    return ValidationError(field_name, message, value)
        
        # Validación de longitud
        elif validation_type == 'min_length':
            min_len = validation.get('value', 0)
            if len(str(value)) < min_len:
                return ValidationError(field_name, message, value)
        
        elif validation_type == 'max_length':
            max_len = validation.get('value', float('inf'))
            if len(str(value)) > max_len:
                return ValidationError(field_name, message, value)
        
        # Validación de rango numérico
        elif validation_type == 'min_value':
            min_val = validation.get('value', float('-inf'))
            if value < min_val:
                return ValidationError(field_name, message, value)
        
        elif validation_type == 'max_value':
            max_val = validation.get('value', float('inf'))
            if value > max_val:
                return ValidationError(field_name, message, value)
        
        # Validación de patrón regex
        elif validation_type == 'pattern':
            pattern = validation.get('pattern', '')
            if not re.match(pattern, str(value)):
                return ValidationError(field_name, message, value)
        
        # Validación de enumeración
        elif validation_type == 'enum':
            allowed_values = validation.get('values', [])
            if value not in allowed_values:
                return ValidationError(field_name, message, value)
        
        # Validación de existencia de archivo
        elif validation_type == 'file_exists':
            if not Path(value).exists():
                return ValidationError(field_name, message, value)
        
        # Validación de extensión de archivo
        elif validation_type == 'file_extension':
            expected_ext = validation.get('extension', '')
            if not str(value).endswith(expected_ext):
                return ValidationError(field_name, message, value)
        
        # Validación de fecha máxima
        elif validation_type == 'max_date':
            max_date_value = validation.get('value')
            if max_date_value == 'today':
                max_date_value = date.today()
            elif isinstance(max_date_value, str):
                max_date_value = date.fromisoformat(max_date_value)
            
            if isinstance(value, str):
                value = date.fromisoformat(value)
            
            if value > max_date_value:
                return ValidationError(field_name, message, value)
        
        # Validación de arrays
        elif validation_type == 'min_items':
            min_items = validation.get('value', 0)
            if not isinstance(value, list) or len(value) < min_items:
                return ValidationError(field_name, message, value)
        
        elif validation_type == 'max_items':
            max_items = validation.get('value', float('inf'))
            if not isinstance(value, list) or len(value) > max_items:
                return ValidationError(field_name, message, value)
        
        return None
    
    def _validate_cross(self, data: Dict[str, Any]) -> List[ValidationError]:
        """
        Aplica validaciones cruzadas entre campos.
        
        Args:
            data: Diccionario con todos los datos
        
        Returns:
            Lista de ValidationError
        """
        errors = []
        
        for cross_val in self.cross_validations:
            name = cross_val.get('name', 'unknown')
            condition = cross_val.get('condition', '')
            rule = cross_val.get('rule', '')
            message = cross_val.get('message', f"Validación cruzada '{name}' falló")
            
            # Evaluar condición
            if self._evaluate_condition(condition, data):
                # Evaluar regla
                if not self._evaluate_rule(rule, data):
                    errors.append(ValidationError(name, message, None))
        
        return errors
    
    def _evaluate_condition(self, condition: str, data: Dict[str, Any]) -> bool:
        """
        Evalúa una condición para determinar si aplicar una validación cruzada.
        
        Args:
            condition: Expresión de condición (ej: "field1 AND field2")
            data: Diccionario con los datos
        
        Returns:
            True si la condición se cumple
        """
        if not condition:
            return True
        
        # Parser simple para condiciones
        # Soporta: "field1 AND field2", "field1 OR field2", "field1"
        condition = condition.strip()
        
        if ' AND ' in condition:
            parts = condition.split(' AND ')
            return all(self._field_is_truthy(part.strip(), data) for part in parts)
        elif ' OR ' in condition:
            parts = condition.split(' OR ')
            return any(self._field_is_truthy(part.strip(), data) for part in parts)
        else:
            return self._field_is_truthy(condition, data)
    
    def _field_is_truthy(self, field_name: str, data: Dict[str, Any]) -> bool:
        """Verifica si un campo tiene un valor truthy."""
        value = data.get(field_name)
        return value is not None and value != '' and value != 0
    
    def _evaluate_rule(self, rule: str, data: Dict[str, Any]) -> bool:
        """
        Evalúa una regla de validación cruzada.
        
        Args:
            rule: Expresión de regla (ej: "field1 <= field2")
            data: Diccionario con los datos
        
        Returns:
            True si la regla se cumple
        """
        # Parser simple para reglas
        # Soporta: "field1 <= field2", "field1 == field2", etc.
        
        if '<=' in rule:
            parts = rule.split('<=')
            left = self._get_field_value(parts[0].strip(), data)
            right = self._get_field_value(parts[1].strip(), data)
            return left <= right
        
        elif '>=' in rule:
            parts = rule.split('>=')
            left = self._get_field_value(parts[0].strip(), data)
            right = self._get_field_value(parts[1].strip(), data)
            return left >= right
        
        elif '==' in rule:
            parts = rule.split('==')
            left = self._get_field_value(parts[0].strip(), data)
            right = self._get_field_value(parts[1].strip(), data)
            return left == right
        
        return True
    
    def _get_field_value(self, field_expr: str, data: Dict[str, Any]) -> Any:
        """
        Obtiene el valor de un campo o expresión.
        
        Args:
            field_expr: Nombre del campo o expresión (ej: "fecha_publicacion", "today")
            data: Diccionario con los datos
        
        Returns:
            Valor del campo
        """
        field_expr = field_expr.strip()
        
        if field_expr == 'today':
            return date.today()
        elif field_expr.startswith('"') and field_expr.endswith('"'):
            return field_expr[1:-1]
        else:
            return data.get(field_expr)
    
    def _is_valid_url(self, url: str) -> bool:
        """Verifica si una URL es válida."""
        try:
            result = urlparse(url)
            return all([result.scheme, result.netloc])
        except:
            return False
    
    def _is_valid_date(self, date_str: str) -> bool:
        """Verifica si una fecha es válida (formato YYYY-MM-DD)."""
        try:
            date.fromisoformat(date_str)
            return True
        except:
            return False
    
    def _is_valid_datetime(self, datetime_str: str) -> bool:
        """Verifica si un datetime es válido (formato ISO 8601)."""
        try:
            datetime.fromisoformat(datetime_str.replace('Z', '+00:00'))
            return True
        except:
            return False
    
    def calculate_quality_score(self, data: Dict[str, Any]) -> float:
        """
        Calcula el score de calidad basado en la configuración del esquema.
        
        Args:
            data: Diccionario con los datos validados
        
        Returns:
            Score de calidad (0-100)
        """
        if not self.quality_config:
            return 0.0
        
        factors = self.quality_config.get('factors', [])
        total_score = 0.0
        total_weight = 0.0
        
        for factor in factors:
            name = factor.get('name')
            weight = factor.get('weight', 0)
            
            factor_score = self._calculate_factor_score(name, factor, data)
            total_score += factor_score * weight
            total_weight += weight
        
        if total_weight == 0:
            return 0.0
        
        return min(100.0, max(0.0, total_score / total_weight))
    
    def _calculate_factor_score(
        self,
        name: str,
        factor: Dict[str, Any],
        data: Dict[str, Any]
    ) -> float:
        """
        Calcula el score de un factor específico.
        
        Args:
            name: Nombre del factor
            factor: Configuración del factor
            data: Diccionario con los datos
        
        Returns:
            Score del factor (0-100)
        """
        # Factor de completitud de metadatos
        if name == 'metadata_completeness':
            fields = factor.get('fields', [])
            if not fields:
                return 100.0
            
            present = sum(1 for f in fields if data.get(f) is not None and data.get(f) != '')
            return (present / len(fields)) * 100.0
        
        # Factor de longitud de contenido
        elif name == 'content_length':
            content_length = data.get('content_length', 0)
            thresholds = factor.get('thresholds', {})
            
            if content_length >= thresholds.get('excellent', 10000):
                return 100.0
            elif content_length >= thresholds.get('good', 5000):
                return 80.0
            elif content_length >= thresholds.get('acceptable', 1000):
                return 60.0
            else:
                return 30.0
        
        # Factor de calidad de citas
        elif name == 'citation_quality':
            citas_extraidas = len(data.get('citas_extraidas', []))
            citas_verificadas = len(data.get('citas_verificadas', []))
            
            if citas_extraidas == 0:
                return 100.0 if citas_verificadas == 0 else 0.0
            
            return (citas_verificadas / citas_extraidas) * 100.0
        
        # Por defecto, score máximo
        return 100.0


def validate_ingest_data(
    content_type: str,
    data: Dict[str, Any],
    strict: bool = True
) -> Tuple[bool, List[ValidationError], float]:
    """
    Función de conveniencia para validar datos de ingesta.
    
    Args:
        content_type: Tipo de contenido ('url', 'pdf', 'youtube')
        data: Diccionario con los datos a validar
        strict: Si es True, falla en el primer error
    
    Returns:
        Tupla (is_valid, errors, quality_score)
    """
    validator = SchemaValidator(content_type)
    is_valid, errors = validator.validate(data, strict=strict)
    quality_score = validator.calculate_quality_score(data) if is_valid else 0.0
    
    return is_valid, errors, quality_score


__all__ = [
    'ValidationError',
    'SchemaValidator',
    'validate_ingest_data',
]
