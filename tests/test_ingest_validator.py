"""Tests for IngestValidator integration wrapper."""

import pytest
from core.wiki.ingest_validator import (
    IngestValidator,
    IngestValidationResult,
    build_ingest_metadata,
)


class TestBuildIngestMetadata:
    def test_url_metadata(self):
        result = build_ingest_metadata("url", {
            "url": "https://example.com/article",
            "name": "Test Article",
            "language_detected": "en",
            "concepts": ["python", "testing"],
            "content_length": 5000,
            "descripcion": "A test article",
        })
        assert result["url"] == "https://example.com/article"
        assert result["titulo"] == "Test Article"
        assert result["dominio"] == "example.com"
        assert result["content_length"] == 5000

    def test_url_metadata_missing_fields(self):
        result = build_ingest_metadata("url", {"name": "Minimal"})
        assert result["titulo"] == "Minimal"
        assert result["url"] == ""
        assert result["dominio"] == ""

    def test_pdf_metadata(self):
        result = build_ingest_metadata("pdf", {
            "name": "Paper Title",
            "fuente": "/path/to/paper.pdf",
            "pages_processed": 10,
            "content_length": 50000,
        })
        assert result["titulo"] == "Paper Title"
        assert result["ruta_archivo"] == "/path/to/paper.pdf"
        assert result["paginas"] == 10

    def test_youtube_metadata(self):
        result = build_ingest_metadata("youtube", {
            "url": "https://youtube.com/watch?v=abc123",
            "name": "Cool Video",
            "uploader": "VideoCreator",
            "duration": 600,
            "views": 10000,
            "language_detected": "es",
            "concepts": ["tutorial", "python"],
            "content_length": 15000,
            "transcript_chars": 12000,
            "has_transcript": True,
        })
        assert result["url"] == "https://youtube.com/watch?v=abc123"
        assert result["titulo"] == "Cool Video"
        assert result["canal"] == "VideoCreator"
        assert result["duracion"] == 600
        assert result["vistas"] == 10000
        assert result["transcripcion"] is True


class TestIngestValidationResult:
    def test_defaults(self):
        r = IngestValidationResult()
        assert r.schema_valid is True
        assert r.schema_errors == []
        assert r.citations_extracted == 0
        assert r.quality_factors == {}
        assert r.quality_warnings == []

    def test_to_dict_keys(self):
        r = IngestValidationResult(
            schema_valid=False,
            schema_errors=["field 'url' is required"],
            citations_extracted=5,
            citations_verified=3,
            citation_verification_rate=0.6,
            quality_score=72.5,
            quality_factors={"content_length": 80.0},
            quality_warnings=["Contenido muy corto"],
            metadata_complete=False,
        )
        d = r.to_dict()
        assert d["schema_valid"] is False
        assert d["schema_errors"] == ["field 'url' is required"]
        assert d["citations_extracted"] == 5
        assert d["quality_score"] == 72.5
        assert "quality_factors" in d
        assert "quality_warnings" in d


class TestIngestValidator:
    def test_process_url_simple(self):
        validator = IngestValidator(use_crossref=False)
        result = validator.process("url", {
            "url": "https://example.com",
            "content_length": 5000,
            "titulo": "Test",
            "content_length": 5000,
            "dominio": "example.com",
            "tags": ["test"],
        }, content="Some sample text with enough length for extraction purposes. " * 50)
        assert isinstance(result, IngestValidationResult)
        assert result.quality_score >= 0

    def test_process_youtube_simple(self):
        validator = IngestValidator(use_crossref=False)
        result = validator.process("youtube", {
            "url": "https://youtube.com/watch?v=abc123",
            "titulo": "Test Video",
            "canal": "TestChannel",
            "duracion": 300,
            "content_length": 10000,
            "transcripcion": True,
            "vistas": 5000,
            "tags": ["tutorial"],
        }, content="Transcript content with enough text for processing. " * 30)
        assert isinstance(result, IngestValidationResult)
        assert result.quality_score >= 0

    def test_process_pdf_simple(self):
        validator = IngestValidator(use_crossref=False)
        result = validator.process("pdf", {
            "titulo": "Test Paper",
            "ruta_archivo": "/tmp/test.pdf",
            "paginas": 15,
            "content_length": 30000,
            "tags": ["academic"],
        }, content="PDF text content with enough length for proper analysis. " * 100)
        assert isinstance(result, IngestValidationResult)
        assert result.quality_score >= 0

    def test_process_empty_content(self):
        validator = IngestValidator(use_crossref=False)
        result = validator.process("url", {
            "url": "https://example.com",
            "content_length": 0,
        }, content="")
        assert result.citations_extracted == 0
        assert result.citations_verified == 0

    def test_process_invalid_type(self):
        validator = IngestValidator(use_crossref=False)
        result = validator.process("unknown_type", {
            "content_length": 1000,
        }, content="Some text")
        assert result.schema_valid is False
        assert len(result.schema_errors) > 0

    def test_process_url_with_citations(self):
        text = (
            "Recent studies show interesting results (Smith, 2020). "
            "According to Johnson (2019), the methodology was sound. "
            "This is consistent with prior work (Garcia & Lee, 2021)."
        )
        validator = IngestValidator(use_crossref=False)
        result = validator.process("url", {
            "url": "https://example.com/article",
            "titulo": "Research Article",
            "content_length": len(text),
            "dominio": "example.com",
            "tags": ["research"],
        }, content=text)
        assert result.citations_extracted >= 0
        assert result.citation_verification_rate >= 0
