"""Librarian - Small model expert for library search and summarization."""

import logging
from typing import Dict, List, Optional

import config

logger = logging.getLogger(__name__)


class Librarian:
    """Small model expert: searches library and generates structured summaries."""

    def __init__(self, model: Optional[str] = None) -> None:
        self.model = model or "qwen2.5:1.5b"
        self.client = None
        self._init_client()

    def _init_client(self) -> None:
        """Initialize Ollama client."""
        try:
            from ollama import Client
            self.client = Client(config.OLLAMA_BASE_URL)
            logger.info(f"Librarian initialized with {self.model}")
        except ImportError:
            logger.warning("ollama not installed")
            self.client = None
        except Exception as e:
            logger.warning(f"Could not connect to Ollama: {e}")
            self.client = None

    def is_available(self) -> bool:
        """Check if librarian model is available."""
        if not self.client:
            return False
        try:
            self.client.generate(model=self.model, prompt="test", options={"timeout": 5})
            return True
        except Exception:
            return False

    def search_and_summarize(self, pregunta: str, limit: int = 8) -> Dict:
        """
        Search library and generate structured summary using small model.

        Args:
            pregunta: User's question
            limit: Number of results to retrieve

        Returns:
            dict with: resumen, refs, sources, total_found
        """
        if not self.client:
            return self._fallback_search(pregunta, limit)

        try:
            search_results = self._search_library(pregunta, limit)
            
            if not search_results:
                return {
                    "resumen": "No se encontró información en la biblioteca.",
                    "refs": [],
                    "sources": [],
                    "total_found": 0,
                }

            context_text = self._build_context(search_results, pregunta)

            summary_prompt = self._build_summary_prompt(pregunta, context_text)

            response = self.client.generate(
                model=self.model,
                prompt=summary_prompt,
                options={
                    "temperature": 0.3,
                    "num_predict": 2048,
                }
            )

            resumen = response.response.strip() if response.response else ""

            refs = self._extract_refs(search_results)
            sources = self._build_sources_list(search_results)

            return {
                "resumen": resumen,
                "refs": refs,
                "sources": sources,
                "total_found": len(search_results),
                "raw_results": search_results,
            }

        except Exception as e:
            logger.error(f"Librarian error: {e}", exc=e)
            return self._fallback_search(pregunta, limit)

    def _search_library(self, pregunta: str, limit: int) -> List[Dict]:
        """Search SQLite wiki using FTS5."""
        try:
            from core.wiki import Wiki
            wiki = Wiki()
            results = wiki.search(pregunta, limit)
            return results
        except Exception as e:
            logger.debug(f"Wiki search error: {e}")
            return []

    def _fallback_search(self, pregunta: str, limit: int) -> Dict:
        """Fallback when small model unavailable - return raw search."""
        results = self._search_library(pregunta, limit)

        if not results:
            return {
                "resumen": "No se encontró información en la biblioteca.",
                "refs": [],
                "sources": [],
                "total_found": 0,
            }

        context_parts = []
        for r in results[:5]:
            context_parts.append(f"## {r['name']}")
            context_parts.append(f"Tipo: {r.get('tipo', 'entity')}")
            content = r.get("content", "")[:800]
            context_parts.append(f"Contenido: {content}\n")

        return {
            "resumen": "\n".join(context_parts),
            "refs": self._extract_refs(results),
            "sources": self._build_sources_list(results),
            "total_found": len(results),
            "raw_results": results,
        }

    def _build_context(self, results: List[Dict], pregunta: str) -> str:
        """Build context string from search results."""
        context_parts = []

        for i, r in enumerate(results[:8], 1):
            name = r.get("name", "Sin título")
            tipo = r.get("tipo", "entity")
            content = r.get("content", "")[:1500]
            fuente = r.get("fuente", "")

            context_parts.append(f"[RESULTADO {i}]")
            context_parts.append(f"Título: {name}")
            context_parts.append(f"Tipo: {tipo}")
            if fuente:
                context_parts.append(f"Fuente: {fuente}")
            context_parts.append(f"Contenido:\n{content}")
            context_parts.append("")

        return "\n".join(context_parts)

    def _build_summary_prompt(self, pregunta: str, context: str) -> str:
        """Build prompt for the small model to generate summary."""
        return f"""Eres el Experto Bibliotecario de Asubarnipal. Tu rol es buscar en la biblioteca de conocimiento y generar resúmenes estructurados y precisos.

PREGUNTA DEL USUARIO: {pregunta}

RESULTADOS DE BÚSQUEDA:
{context}

===

Genera un RESUMEN ESTRUCTURADO siguiendo este formato:

## RESUMEN
[Explica en 2-4 párrafos lo que encontraste, respondiendo directamente a la pregunta. Usa información concreta de los resultados.]

## FUENTES RELEVANTES
[Lista cada fuente encontrada con:
- Nombre: ...
- Tipo: ...
- Contenido clave: ...]

## CONCEPTOS RELACIONADOS
[Lista conceptos mencionados en los resultados que el usuario podría querer explorar más]

## CITAS EXACTAS
[Copia fragmentos literales relevantes del contenido, indicando de qué fuente vienen]

===

Sé preciso. Cita fuentes concretas. No inventes información que no esté en los resultados.
Si no hay suficiente información, indica qué falta.
"""

    def _extract_refs(self, results: List[Dict]) -> List[Dict]:
        """Extract reference information from results."""
        refs = []
        for r in results[:8]:
            refs.append({
                "name": r.get("name", ""),
                "tipo": r.get("tipo", "entity"),
                "fuente": r.get("fuente", ""),
                "content_preview": (r.get("content", "") or "")[:200],
            })
        return refs

    def _build_sources_list(self, results: List[Dict]) -> List[str]:
        """Build list of source names."""
        sources = []
        seen = set()
        for r in results:
            name = r.get("name", "")
            if name and name not in seen:
                seen.add(name)
                tipo = r.get("tipo", "entity")
                fuente = r.get("fuente", "")
                if fuente:
                    sources.append(f"• {name} [{tipo}] — {fuente[:60]}")
                else:
                    sources.append(f"• {name} [{tipo}]")
        return sources

    def get_research_summary(self, pregunta: str, contexto: str) -> str:
        """
        Generate research summary for a specific context.
        Used by the analyst (large model) to frame the response.
        """
        if not self.client:
            return contexto[:2000]

        prompt = f"""Eres el Experto Bibliotecario. Resume este contexto para un analista:

PREGUNTA: {pregunta}

CONTEXTO:
{contexto[:4000]}

Responde con:
1. Tema principal encontrado
2. 3-5 puntos clave
3. Lagunas de información (qué falta)
4. Recomendación de enfoque para el análisis

Sé conciso. Máximo 300 palabras."""

        try:
            response = self.client.generate(
                model=self.model,
                prompt=prompt,
                options={"temperature": 0.2, "num_predict": 512}
            )
            return response.response.strip() if response.response else contexto[:2000]
        except Exception as e:
            logger.debug(f"Research summary error: {e}")
            return contexto[:2000]


def get_librarian(model: str = None) -> Librarian:
    """Get Librarian instance."""
    return Librarian(model)