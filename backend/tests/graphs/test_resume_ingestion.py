"""
Tests for resume ingestion LangGraph nodes.
Each node is tested independently — small, focused, deterministic.
"""
import pytest

from app.graphs.resume_ingestion.nodes import (
    clean_text,
    detect_sections,
    validate_file,
)
from app.graphs.resume_ingestion.state import ResumeIngestionState


def _make_state(**kwargs) -> ResumeIngestionState:
    defaults = {
        "workflow_id": "test-workflow-1",
        "organization_id": "org-1",
        "candidate_id": "cand-1",
        "resume_id": "resume-1",
        "file_path": "/tmp/test_resume.pdf",
        "file_type": "pdf",
    }
    defaults.update(kwargs)
    return ResumeIngestionState(**defaults)


# ── validate_file tests ───────────────────────────────────────────────────────


class TestValidateFile:
    def test_valid_pdf(self):
        state = _make_state(file_type="pdf")
        result = validate_file(state)
        assert result["current_status"] == "parsing"

    def test_valid_docx(self):
        state = _make_state(file_type="docx")
        result = validate_file(state)
        assert result["current_status"] == "parsing"

    def test_valid_txt(self):
        state = _make_state(file_type="txt")
        result = validate_file(state)
        assert result["current_status"] == "parsing"

    def test_unsupported_file_type(self):
        state = _make_state(file_type="exe")
        result = validate_file(state)
        assert result["current_status"] == "failed"
        assert any("Unsupported" in e for e in result["errors"])

    def test_extension_with_dot(self):
        state = _make_state(file_type=".pdf")
        result = validate_file(state)
        assert result["current_status"] == "parsing"


# ── clean_text tests ──────────────────────────────────────────────────────────


class TestCleanText:
    def test_normalizes_extra_newlines(self):
        state = _make_state(raw_text="Line 1\n\n\n\n\nLine 2")
        result = clean_text(state)
        assert "\n\n\n" not in result["cleaned_text"]

    def test_strips_whitespace(self):
        state = _make_state(raw_text="  hello   world  ")
        result = clean_text(state)
        assert result["cleaned_text"] == "hello   world"

    def test_handles_empty_text(self):
        state = _make_state(raw_text=None)
        result = clean_text(state)
        assert "errors" in result
        assert len(result["errors"]) > 0


# ── detect_sections tests ─────────────────────────────────────────────────────


class TestDetectSections:
    def test_detects_experience_section(self):
        text = "Work Experience\nDeveloper at ACME Corp\n\nEducation\nBS Computer Science"
        state = _make_state(cleaned_text=text)
        result = detect_sections(state)
        assert "experience" in result["sections"]
        assert "education" in result["sections"]

    def test_detects_skills_section(self):
        text = "Technical Skills\nPython, FastAPI, PostgreSQL"
        state = _make_state(cleaned_text=text)
        result = detect_sections(state)
        assert "skills" in result["sections"]

    def test_handles_no_sections(self):
        text = "Random text with no section headers"
        state = _make_state(cleaned_text=text)
        result = detect_sections(state)
        # Should return an "other" catch-all section
        assert isinstance(result["sections"], dict)


# ── Retry count safety tests ──────────────────────────────────────────────────


class TestRetryLogic:
    """
    Verify that retry_count / max_retries prevents infinite loops.
    Rule #8: Every LangGraph loop must have retry limits.
    """

    def test_can_retry_returns_true_when_under_limit(self):
        state = _make_state(retry_count=0, max_retries=3)
        assert state.can_retry() is True

    def test_can_retry_returns_false_at_limit(self):
        state = _make_state(retry_count=3, max_retries=3)
        assert state.can_retry() is False

    def test_can_retry_returns_false_over_limit(self):
        state = _make_state(retry_count=5, max_retries=3)
        assert state.can_retry() is False


# ── Security: cross-tenant isolation ─────────────────────────────────────────


class TestChunkMetadataIsolation:
    """
    Verify that chunks always contain organization_id and candidate_id.
    Every chunk must carry tenant context for vector retrieval filtering.
    A retrieval query MUST filter by both — tested here at chunk creation.
    """

    def test_chunks_contain_organization_id(self):
        from app.graphs.resume_ingestion.nodes import create_semantic_chunks
        from app.ai.structured_outputs.resume import ResumeProfile, SkillEntry

        profile = ResumeProfile(
            skills=[SkillEntry(name="Python")],
            extraction_confidence=0.9,
        )
        state = _make_state(
            structured_resume=profile,
            organization_id="org-abc",
            candidate_id="cand-xyz",
        )
        result = create_semantic_chunks(state)
        for chunk in result["chunks"]:
            assert chunk["metadata"]["organization_id"] == "org-abc", (
                "SECURITY: chunk missing organization_id — cross-tenant retrieval would be possible"
            )
            assert chunk["metadata"]["candidate_id"] == "cand-xyz"
