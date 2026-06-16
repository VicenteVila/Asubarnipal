"""
Wrapper que integra SchemaValidator, CitationExtractor, CitationVerifier y QualityScorer
en las flows de ingesta de forma no invasiva.
"""

import logging
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from urllib.parse import urlparse

from core.wiki.validators import SchemaValidator, ValidationError, validate_ingest_data
from core.wiki.citation_extractor import CitationExtractor, Citation
from core.wiki.citation_verifier import CitationVerifier, VerificationResult
from core.wiki.quality_scorer import QualityScorer, QualityScore, calculate_quality_score

logger = logging.getLogger(__name__)


@dataclass
class IngestValidationResult:
    schema_valid: bool = True
    schema_errors: List[str] = None
    citations_extracted: int = 0
    citations_verified: int = 0
    citation_verification_rate: float = 0.0
    quality_score: float = 0.0
    quality_factors: Dict[str, float] = None
    quality_warnings: List[str] = None
    metadata_complete: bool = False

    def __post_init__(self):
        if self.schema_errors is None:
            self.schema_errors = []
        if self.quality_factors is None:
            self.quality_factors = {}
        if self.quality_warnings is None:
            self.quality_warnings = []

    def to_dict(self) -> Dict:
        return {
            "schema_valid": self.schema_valid,
            "schema_errors": self.schema_errors,
            "citations_extracted": self.citations_extracted,
            "citations_verified": self.citations_verified,
            "citation_verification_rate": self.citation_verification_rate,
            "quality_score": round(self.quality_score, 1),
            "quality_factors": {k: round(v, 1) for k, v in self.quality_factors.items()},
            "quality_warnings": self.quality_warnings,
            "metadata_complete": self.metadata_complete,
        }


class IngestValidator:
    def __init__(self, use_crossref: bool = True):
        self.extractor = CitationExtractor()
        self.verifier = CitationVerifier(use_crossref=use_crossref)
        self.scorer = QualityScorer()

    def process(
        self,
        content_type: str,
        metadata: Dict[str, Any],
        content: str = "",
    ) -> IngestValidationResult:
        result = IngestValidationResult()

        # 1. Schema validation
        try:
            schema_valid, schema_errors = validate_ingest_data(content_type, metadata, strict=False)[:2]
            result.schema_valid = schema_valid
            result.schema_errors = [str(e) for e in schema_errors]
        except Exception as e:
            logger.warning(f"Schema validation failed for {content_type}: {e}")
            result.schema_valid = False
            result.schema_errors = [f"Schema validation error: {e}"]

        # 2. Citation extraction & verification
        if content and len(content) > 200:
            try:
                citations = self.extractor.extract(content)
                result.citations_extracted = len(citations)

                if citations:
                    verification_results = self.verifier.verify_batch(citations)
                    result.citations_verified = sum(1 for vr in verification_results if vr.verificado)
                    result.citation_verification_rate = (
                        result.citations_verified / result.citations_extracted
                        if result.citations_extracted > 0 else 0.0
                    )

                    metadata["citas_extraidas"] = [c.to_dict() for c in citations]
                    metadata["citas_verificadas"] = [
                        {"texto_original": vr.citation.texto_original, "verificado": vr.verificado, "score_confianza": vr.score_confianza}
                        for vr in verification_results if vr.verificado
                    ]
            except Exception as e:
                logger.warning(f"Citation processing failed: {e}")

        # 3. Quality scoring
        try:
            quality_result = calculate_quality_score(content_type, metadata)
            result.quality_score = quality_result.score
            result.quality_factors = quality_result.factores
            result.quality_warnings = quality_result.advertencias
            result.metadata_complete = quality_result.metadata_completa
        except Exception as e:
            logger.warning(f"Quality scoring failed for {content_type}: {e}")
            result.quality_score = 50.0
            result.quality_warnings = [f"Quality scoring error: {e}"]

        return result


def build_ingest_metadata(
    content_type: str,
    base_data: Dict[str, Any],
) -> Dict[str, Any]:
    metadata = dict(base_data)

    if content_type == "url":
        url = metadata.get("url", metadata.get("fuente", ""))
        metadata.setdefault("url", url)
        metadata.setdefault("titulo", metadata.get("name", ""))
        metadata.setdefault("idioma", metadata.get("language_detected", "unknown"))
        metadata.setdefault("tags", metadata.get("concepts", []))
        metadata.setdefault("dominio", urlparse(url).netloc if url else "")
        metadata.setdefault("content_length", metadata.get("content_length", 0))

    elif content_type == "pdf":
        metadata.setdefault("titulo", metadata.get("name", ""))
        metadata.setdefault("ruta_archivo", metadata.get("fuente", ""))
        metadata.setdefault("paginas", metadata.get("pages_processed", 0))
        metadata.setdefault("content_length", metadata.get("content_length", 0))

    elif content_type == "youtube":
        url = metadata.get("url", metadata.get("fuente", ""))
        metadata.setdefault("url", url)
        metadata.setdefault("titulo", metadata.get("name", ""))
        metadata.setdefault("canal", metadata.get("uploader", ""))
        metadata.setdefault("duracion", metadata.get("duration_seconds", metadata.get("duration", 0)))
        metadata.setdefault("idioma", metadata.get("language_detected", "unknown"))
        metadata.setdefault("tags", metadata.get("concepts", []))
        metadata.setdefault("content_length", metadata.get("content_length", 0))
        metadata.setdefault("transcripcion", metadata.get("transcript_chars", 0) > 0)
        metadata.setdefault("tiene_subtitulos", metadata.get("has_transcript", False))
        metadata.setdefault("vistas", metadata.get("views", 0))

    return metadata
