"""
Extractor de citas de documentos.

Este módulo proporciona funcionalidad para extraer citas de texto en diferentes
formatos académicos (APA, MLA, Chicago, IEEE).
"""

import re
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, asdict


@dataclass
class Citation:
    """Representa una cita extraída de un documento."""
    
    # Texto original de la cita
    texto_original: str
    
    # Formato detectado (apa, mla, chicago, ieee, unknown)
    formato: str = 'unknown'
    
    # Componentes extraídos
    autores: Optional[str] = None
    año: Optional[int] = None
    titulo: Optional[str] = None
    fuente: Optional[str] = None  # Journal, book, conference, etc.
    volumen: Optional[str] = None
    numero: Optional[str] = None
    paginas: Optional[str] = None
    doi: Optional[str] = None
    url: Optional[str] = None
    
    # Metadatos adicionales
    contexto: Optional[str] = None  # Texto alrededor de la cita
    pagina: Optional[int] = None  # Página donde se encontró
    timestamp: Optional[str] = None  # Para videos (HH:MM:SS)
    
    # Verificación
    verificado: bool = False
    fuente_verificacion: Optional[str] = None  # crossref, google_scholar, local
    
    def to_dict(self) -> Dict:
        """Convierte la cita a diccionario."""
        return asdict(self)
    
    def get_identifier(self) -> Optional[str]:
        """Obtiene el identificador principal (DOI o URL)."""
        return self.doi or self.url


class CitationExtractor:
    """
    Extractor de citas de documentos.
    
    Ejemplo de uso:
        extractor = CitationExtractor()
        citations = extractor.extract(text)
    """
    
    # Patrones regex para diferentes formatos de citas
    PATTERNS = {
        'apa': [
            # APA: Author, A. A., & Author, B. B. (Year). Title. Source, volume(issue), pages. DOI
            r'([A-Z][a-z]+(?:,\s*[A-Z]\.?\s*(?:&\s*[A-Z][a-z]+(?:,\s*[A-Z]\.?\s*)*)*)?)\s*\((\d{4})\)\.\s*([^\.]+)\.\s*([^,]+)(?:,\s*(\d+)(?:\((\d+)\))?,\s*([0-9\-]+))?(?:\.\s*(https?://doi\.org/[^\s]+))?',
        ],
        'mla': [
            # MLA: Author. "Title." Source, vol. X, no. Y, Year, pp. Z-Z.
            r'([A-Z][a-z]+(?:,\s*[A-Z][a-z]+)*)\.\s*"([^"]+)"\.\s*([^,]+)(?:,\s*vol\.\s*(\d+))?(?:,\s*no\.\s*(\d+))?,\s*(\d{4})(?:,\s*pp\.\s*([0-9\-]+))?',
        ],
        'chicago': [
            # Chicago: Author. "Title." Source Volume, no. Issue (Year): Pages.
            r'([A-Z][a-z]+(?:,\s*[A-Z][a-z]+)*)\.\s*"([^"]+)"\.\s*([^\d]+)\s*(\d+)?(?:,\s*no\.\s*(\d+))?\s*\((\d{4})\):\s*([0-9\-]+)',
        ],
        'ieee': [
            # IEEE: [1] A. Author and B. Author, "Title," Source, vol. X, no. Y, pp. Z-Z, Month Year.
            r'\[(\d+)\]\s*([A-Z]\.\s*[A-Z][a-z]+(?:\s+and\s+[A-Z]\.\s*[A-Z][a-z]+)*)\s*,\s*"([^"]+)"\s*,\s*([^,]+)(?:,\s*vol\.\s*(\d+))?(?:,\s*no\.\s*(\d+))?(?:,\s*pp\.\s*([0-9\-]+))?(?:,\s*\w+\s+(\d{4}))?',
        ],
        'inline': [
            # Citas en línea: (Author, Year) o (Author & Author, Year)
            r'\(([A-Z][a-z]+(?:\s*(?:&|and)\s*[A-Z][a-z]+)?(?:\s+et\s+al\.?)?,\s*(\d{4})[a-z]?)\)',
            # Citas en línea: Author (Year)
            r'([A-Z][a-z]+(?:\s+et\s+al\.?)?)\s*\((\d{4})[a-z]?\)',
        ]
    }
    
    def __init__(self):
        """Inicializa el extractor de citas."""
        self.compiled_patterns = {}
        for format_name, patterns in self.PATTERNS.items():
            self.compiled_patterns[format_name] = [
                re.compile(pattern, re.MULTILINE | re.IGNORECASE)
                for pattern in patterns
            ]
    
    def extract(self, text: str, contexto_chars: int = 200) -> List[Citation]:
        """
        Extrae todas las citas de un texto.
        
        Args:
            text: Texto del documento
            contexto_chars: Número de caracteres de contexto alrededor de cada cita
        
        Returns:
            Lista de Citation objects
        """
        citations = []
        
        # Extraer citas de cada formato
        for format_name, patterns in self.compiled_patterns.items():
            for pattern in patterns:
                matches = pattern.finditer(text)
                
                for match in matches:
                    citation = self._parse_match(match, format_name, text, contexto_chars)
                    if citation:
                        citations.append(citation)
        
        # Eliminar duplicados (basado en texto original)
        unique_citations = self._remove_duplicates(citations)
        
        return unique_citations
    
    def _parse_match(
        self,
        match: re.Match,
        format_name: str,
        full_text: str,
        contexto_chars: int
    ) -> Optional[Citation]:
        """
        Parsea un match de regex en un objeto Citation.
        
        Args:
            match: Match de regex
            format_name: Nombre del formato (apa, mla, etc.)
            full_text: Texto completo del documento
            contexto_chars: Caracteres de contexto
        
        Returns:
            Citation object o None si no se puede parsear
        """
        try:
            texto_original = match.group(0)
            
            # Extraer contexto
            start = max(0, match.start() - contexto_chars)
            end = min(len(full_text), match.end() + contexto_chars)
            contexto = full_text[start:end]
            
            citation = Citation(
                texto_original=texto_original,
                formato=format_name,
                contexto=contexto
            )
            
            # Parsear componentes según el formato
            if format_name == 'apa':
                citation = self._parse_apa(match, citation)
            elif format_name == 'mla':
                citation = self._parse_mla(match, citation)
            elif format_name == 'chicago':
                citation = self._parse_chicago(match, citation)
            elif format_name == 'ieee':
                citation = self._parse_ieee(match, citation)
            elif format_name == 'inline':
                citation = self._parse_inline(match, citation)
            
            return citation
        
        except Exception as e:
            # Si hay error parseando, devolver cita básica
            return Citation(
                texto_original=match.group(0),
                formato=format_name,
                contexto=full_text[max(0, match.start() - contexto_chars):min(len(full_text), match.end() + contexto_chars)]
            )
    
    def _parse_apa(self, match: re.Match, citation: Citation) -> Citation:
        """Parsea una cita en formato APA."""
        groups = match.groups()
        
        if len(groups) >= 1:
            citation.autores = groups[0]
        if len(groups) >= 2:
            citation.año = int(groups[1])
        if len(groups) >= 3:
            citation.titulo = groups[2]
        if len(groups) >= 4:
            citation.fuente = groups[3]
        if len(groups) >= 5 and groups[4]:
            citation.volumen = groups[4]
        if len(groups) >= 6 and groups[5]:
            citation.numero = groups[5]
        if len(groups) >= 7 and groups[6]:
            citation.paginas = groups[6]
        if len(groups) >= 8 and groups[7]:
            citation.doi = groups[7]
        
        return citation
    
    def _parse_mla(self, match: re.Match, citation: Citation) -> Citation:
        """Parsea una cita en formato MLA."""
        groups = match.groups()
        
        if len(groups) >= 1:
            citation.autores = groups[0]
        if len(groups) >= 2:
            citation.titulo = groups[1]
        if len(groups) >= 3:
            citation.fuente = groups[2]
        if len(groups) >= 4 and groups[3]:
            citation.volumen = groups[3]
        if len(groups) >= 5 and groups[4]:
            citation.numero = groups[4]
        if len(groups) >= 6:
            citation.año = int(groups[5])
        if len(groups) >= 7 and groups[6]:
            citation.paginas = groups[6]
        
        return citation
    
    def _parse_chicago(self, match: re.Match, citation: Citation) -> Citation:
        """Parsea una cita en formato Chicago."""
        groups = match.groups()
        
        if len(groups) >= 1:
            citation.autores = groups[0]
        if len(groups) >= 2:
            citation.titulo = groups[1]
        if len(groups) >= 3:
            citation.fuente = groups[2]
        if len(groups) >= 4 and groups[3]:
            citation.volumen = groups[3]
        if len(groups) >= 5 and groups[4]:
            citation.numero = groups[4]
        if len(groups) >= 6:
            citation.año = int(groups[5])
        if len(groups) >= 7 and groups[6]:
            citation.paginas = groups[6]
        
        return citation
    
    def _parse_ieee(self, match: re.Match, citation: Citation) -> Citation:
        """Parsea una cita en formato IEEE."""
        groups = match.groups()
        
        if len(groups) >= 2:
            citation.autores = groups[1]
        if len(groups) >= 3:
            citation.titulo = groups[2]
        if len(groups) >= 4:
            citation.fuente = groups[3]
        if len(groups) >= 5 and groups[4]:
            citation.volumen = groups[4]
        if len(groups) >= 6 and groups[5]:
            citation.numero = groups[5]
        if len(groups) >= 7 and groups[6]:
            citation.paginas = groups[6]
        if len(groups) >= 8 and groups[7]:
            citation.año = int(groups[7])
        
        return citation
    
    def _parse_inline(self, match: re.Match, citation: Citation) -> Citation:
        """Parsea una cita en línea (Author, Year)."""
        groups = match.groups()
        
        if len(groups) >= 1:
            citation.autores = groups[0]
        if len(groups) >= 2:
            citation.año = int(groups[1])
        
        return citation
    
    def _remove_duplicates(self, citations: List[Citation]) -> List[Citation]:
        """
        Elimina citas duplicadas basándose en el texto original.
        
        Args:
            citations: Lista de citas
        
        Returns:
            Lista de citas únicas
        """
        seen = set()
        unique = []
        
        for citation in citations:
            # Normalizar texto para comparación
            normalized = citation.texto_original.strip().lower()
            
            if normalized not in seen:
                seen.add(normalized)
                unique.append(citation)
        
        return unique
    
    def extract_from_pdf(self, pdf_path: str) -> List[Citation]:
        """
        Extrae citas de un archivo PDF.
        
        Args:
            pdf_path: Ruta al archivo PDF
        
        Returns:
            Lista de Citation objects
        """
        try:
            import fitz  # PyMuPDF
            
            doc = fitz.open(pdf_path)
            all_citations = []
            
            for page_num, page in enumerate(doc, 1):
                text = page.get_text()
                citations = self.extract(text)
                
                # Agregar número de página
                for citation in citations:
                    citation.pagina = page_num
                
                all_citations.extend(citations)
            
            doc.close()
            return all_citations
        
        except ImportError:
            raise ImportError("PyMuPDF (fitz) no está instalado. Ejecuta: pip install PyMuPDF")
        except Exception as e:
            raise Exception(f"Error extrayendo citas del PDF: {e}")
    
    def extract_from_url(self, url: str) -> List[Citation]:
        """
        Extrae citas de una página web.
        
        Args:
            url: URL de la página web
        
        Returns:
            Lista de Citation objects
        """
        try:
            import requests
            from bs4 import BeautifulSoup
            
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Extraer texto de párrafos
            paragraphs = soup.find_all('p')
            text = '\n\n'.join([p.get_text() for p in paragraphs])
            
            return self.extract(text)
        
        except ImportError:
            raise ImportError("requests y beautifulsoup4 no están instalados. Ejecuta: pip install requests beautifulsoup4")
        except Exception as e:
            raise Exception(f"Error extrayendo citas de la URL: {e}")


def extract_citations(text: str, formato: Optional[str] = None) -> List[Dict]:
    """
    Función de conveniencia para extraer citas.
    
    Args:
        text: Texto del documento
        formato: Formato específico a extraer (opcional)
    
    Returns:
        Lista de citas como diccionarios
    """
    extractor = CitationExtractor()
    citations = extractor.extract(text)
    
    # Filtrar por formato si se especifica
    if formato:
        citations = [c for c in citations if c.formato == formato]
    
    return [c.to_dict() for c in citations]


__all__ = [
    'Citation',
    'CitationExtractor',
    'extract_citations',
]
