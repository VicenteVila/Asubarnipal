"""
Módulo de esquemas de validación para ingesta de contenido.

Este módulo contiene los esquemas YAML que definen la estructura y validaciones
para diferentes tipos de contenido (URLs, PDFs, YouTube).
"""

import os
from pathlib import Path

# Directorio de esquemas
SCHEMAS_DIR = Path(__file__).parent

# Rutas a los esquemas
URL_SCHEMA = SCHEMAS_DIR / "url.yaml"
PDF_SCHEMA = SCHEMAS_DIR / "pdf.yaml"
YOUTUBE_SCHEMA = SCHEMAS_DIR / "youtube.yaml"

# Mapeo de tipos a esquemas
SCHEMA_MAP = {
    "url": URL_SCHEMA,
    "pdf": PDF_SCHEMA,
    "youtube": YOUTUBE_SCHEMA,
}


def get_schema_path(content_type: str) -> Path:
    """
    Obtiene la ruta al esquema YAML para un tipo de contenido.
    
    Args:
        content_type: Tipo de contenido ('url', 'pdf', 'youtube')
    
    Returns:
        Path al archivo YAML del esquema
    
    Raises:
        ValueError: Si el tipo de contenido no es válido
    """
    if content_type not in SCHEMA_MAP:
        raise ValueError(
            f"Tipo de contenido no válido: {content_type}. "
            f"Tipos válidos: {list(SCHEMA_MAP.keys())}"
        )
    return SCHEMA_MAP[content_type]


def list_schemas() -> list:
    """
    Lista todos los esquemas disponibles.
    
    Returns:
        Lista de tipos de contenido disponibles
    """
    return list(SCHEMA_MAP.keys())


__all__ = [
    "SCHEMAS_DIR",
    "URL_SCHEMA",
    "PDF_SCHEMA",
    "YOUTUBE_SCHEMA",
    "SCHEMA_MAP",
    "get_schema_path",
    "list_schemas",
]
