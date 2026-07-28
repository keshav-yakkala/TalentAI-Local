"""
Resume Ingestion LangGraph — Node implementations.
Each node is a pure function: State → State (partial update dict).
Nodes are small, focused, and independently testable.
"""
from __future__ import annotations

import re
from typing import Any

from app.core.logging import get_logger
from app.graphs.resume_ingestion.state import ResumeIngestionState

logger = get_logger(__name__)


# ── Node: validate_file ───────────────────────────────────────────────────────


def validate_file(state: ResumeIngestionState) -> dict[str, Any]:
    """
    Validate the uploaded file type and basic integrity.
    Returns routing signal for next node.
    """
    supported = {"pdf", "docx", "txt"}
    file_type = state.file_type.lower().strip(".")

    if file_type not in supported:
        logger.warning("Unsupported file type", file_type=file_type, resume_id=state.resume_id)
        return {
            "current_status": "failed",
            "errors": [*state.errors, f"Unsupported file type: {file_type}"],
        }

    return {"current_status": "parsing", "file_type": file_type}


# ── Node: extract_text ────────────────────────────────────────────────────────


def extract_text(state: ResumeIngestionState) -> dict[str, Any]:
    """
    Extract raw text from the document file.
    Supports PDF (PyMuPDF), DOCX (python-docx), TXT.
    On failure, routes to fallback_parser.
    """
    logger.info("Extracting text", resume_id=state.resume_id, file_type=state.file_type)

    try:
        if state.file_type == "pdf":
            text = _extract_pdf(state.file_path)
        elif state.file_type == "docx":
            text = _extract_docx(state.file_path)
        elif state.file_type == "txt":
            text = _extract_txt(state.file_path)
        else:
            return {"errors": [*state.errors, "Unknown file type at extract stage"]}

        if not text or len(text.strip()) < 50:
            logger.warning("Extracted text too short", resume_id=state.resume_id, length=len(text or ""))
            return {
                "raw_text": text,
                "errors": [*state.errors, "Extracted text is suspiciously short — possible scanned PDF"],
                "current_status": "fallback_needed",
            }

        return {"raw_text": text, "current_status": "extracting"}

    except Exception as exc:
        logger.error("Text extraction failed", resume_id=state.resume_id, error=str(exc))
        return {
            "errors": [*state.errors, f"Text extraction error: {exc}"],
            "current_status": "fallback_needed",
        }


def _extract_pdf(file_path: str) -> str:
    """Extract text from PDF using PyMuPDF (fitz) — better than PyPDF2."""
    try:
        import fitz  # PyMuPDF
        doc = fitz.open(file_path)
        pages = [page.get_text() for page in doc]
        doc.close()
        return "\n".join(pages)
    except ImportError:
        # Fallback to PyPDF2 if PyMuPDF not installed
        import io
        import PyPDF2
        with open(file_path, "rb") as f:
            reader = PyPDF2.PdfReader(f)
            return "\n".join(page.extract_text() or "" for page in reader.pages)


def _extract_docx(file_path: str) -> str:
    """Extract text from DOCX using python-docx."""
    from docx import Document
    doc = Document(file_path)
    paragraphs = [para.text for para in doc.paragraphs if para.text.strip()]
    return "\n".join(paragraphs)


def _extract_txt(file_path: str) -> str:
    """Read plain text file."""
    with open(file_path, "r", encoding="utf-8", errors="replace") as f:
        return f.read()


# ── Node: fallback_parser ─────────────────────────────────────────────────────


def fallback_parser(state: ResumeIngestionState) -> dict[str, Any]:
    """
    Attempt alternative extraction when primary parser fails.
    For PDFs: try with pdfplumber as fallback.
    Future: OCR integration point.
    """
    logger.info("Attempting fallback parser", resume_id=state.resume_id)

    try:
        if state.file_type == "pdf":
            try:
                import pdfplumber
                with pdfplumber.open(state.file_path) as pdf:
                    text = "\n".join(
                        page.extract_text() or "" for page in pdf.pages
                    )
                if text and len(text.strip()) >= 50:
                    return {"raw_text": text, "current_status": "extracting"}
            except ImportError:
                pass

        # OCR interface placeholder — architecture supports it, implementation optional Phase 1
        logger.warning("All parsers failed, marking for human review", resume_id=state.resume_id)
        return {
            "current_status": "failed",
            "errors": [*state.errors, "All text extraction methods failed. Possibly scanned document."],
            "requires_human_review": True,
            "human_review_reason": "Text extraction failed — may be a scanned document requiring OCR",
        }

    except Exception as exc:
        return {
            "current_status": "failed",
            "errors": [*state.errors, f"Fallback parser error: {exc}"],
        }


# ── Node: clean_text ──────────────────────────────────────────────────────────


def clean_text(state: ResumeIngestionState) -> dict[str, Any]:
    """Clean and normalize extracted raw text."""
    if not state.raw_text:
        return {"errors": [*state.errors, "No raw text available to clean"]}

    text = state.raw_text
    # Normalize whitespace
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\r\n", "\n", text)
    # Remove null bytes / control characters
    text = "".join(ch for ch in text if ch.isprintable() or ch in "\n\t")
    text = text.strip()

    return {"cleaned_text": text}


# ── Node: detect_sections ─────────────────────────────────────────────────────


def detect_sections(state: ResumeIngestionState) -> dict[str, Any]:
    """
    Heuristically detect resume sections (experience, education, skills, etc.)
    without an LLM call — fast and deterministic.
    """
    if not state.cleaned_text:
        return {"errors": [*state.errors, "No cleaned text for section detection"]}

    section_patterns = {
        "experience": r"(?i)(work\s+experience|employment\s+history|professional\s+experience|experience)",
        "education": r"(?i)(education|academic\s+background|qualifications)",
        "skills": r"(?i)(skills|technical\s+skills|core\s+competencies|technologies)",
        "projects": r"(?i)(projects|personal\s+projects|side\s+projects)",
        "certifications": r"(?i)(certifications|certificates|licenses)",
        "research": r"(?i)(research|publications|papers)",
        "achievements": r"(?i)(achievements|awards|honors|accomplishments)",
        "summary": r"(?i)(summary|objective|profile|about\s+me)",
    }

    text = state.cleaned_text
    lines = text.split("\n")
    sections: dict[str, str] = {}
    current_section = "other"
    current_lines: list[str] = []

    for line in lines:
        matched = False
        for section_name, pattern in section_patterns.items():
            if re.match(pattern, line.strip()):
                if current_lines:
                    sections[current_section] = "\n".join(current_lines)
                current_section = section_name
                current_lines = []
                matched = True
                break
        if not matched:
            current_lines.append(line)

    if current_lines:
        sections[current_section] = "\n".join(current_lines)

    logger.debug("Sections detected", sections=list(sections.keys()), resume_id=state.resume_id)
    return {"sections": sections}


# ── Node: extract_structured_resume ──────────────────────────────────────────


async def extract_structured_resume(state: ResumeIngestionState) -> dict[str, Any]:
    """
    Use LLM to extract a fully structured ResumeProfile from the cleaned text.
    Validates output with Pydantic — retries handled by graph conditional routing.
    """
    from app.ai.llms.factory import get_llm_provider
    from app.ai.prompts.resume_extraction import build_extraction_prompt
    from app.ai.structured_outputs.resume import ResumeProfile
    from app.core.exceptions import LLMOutputValidationError, LLMProviderError

    logger.info("Extracting structured resume", resume_id=state.resume_id, retry=state.retry_count)

    try:
        llm = get_llm_provider()
        prompt = build_extraction_prompt(state.cleaned_text or state.raw_text or "")
        result: ResumeProfile = await llm.structured_generate(prompt, ResumeProfile)

        return {
            "structured_resume": result,
            "extraction_confidence": result.extraction_confidence,
            "current_status": "validating",
        }

    except (LLMOutputValidationError, LLMProviderError) as exc:
        logger.warning("Structured extraction failed", resume_id=state.resume_id, error=str(exc))
        return {
            "errors": [*state.errors, str(exc)],
            "extraction_confidence": 0.0,
        }


# ── Node: validate_extraction ─────────────────────────────────────────────────


def validate_extraction(state: ResumeIngestionState) -> dict[str, Any]:
    """
    Validate extraction quality. Routes based on confidence threshold.
    Confidence < 0.4 → human review
    Confidence < 0.7 → retry (if retries remain)
    Confidence >= 0.7 → proceed to chunking
    """
    profile = state.structured_resume
    errors = []

    if not profile:
        return {"extraction_confidence": 0.0, "validation_errors": ["No structured data extracted"]}

    # Check minimum viable data
    if not profile.personal_information.full_name:
        errors.append("Could not extract candidate name")
    if not profile.skills:
        errors.append("No skills extracted")
    if not profile.experience and not profile.education:
        errors.append("No experience or education extracted")

    confidence = profile.extraction_confidence
    if errors:
        # Reduce confidence if validation found issues
        confidence = max(0.0, confidence - 0.2 * len(errors))

    return {
        "extraction_confidence": confidence,
        "validation_errors": errors,
    }


# ── Node: retry_extraction ────────────────────────────────────────────────────


def retry_extraction(state: ResumeIngestionState) -> dict[str, Any]:
    """Increment retry counter before looping back to extract_structured_resume."""
    new_count = state.retry_count + 1
    logger.info("Retrying extraction", resume_id=state.resume_id, attempt=new_count)
    return {"retry_count": new_count, "current_status": "extracting"}


# ── Node: human_review_required ──────────────────────────────────────────────


def human_review_required(state: ResumeIngestionState) -> dict[str, Any]:
    """Mark the workflow as requiring human review and halt."""
    logger.warning(
        "Routing to human review",
        resume_id=state.resume_id,
        confidence=state.extraction_confidence,
        errors=state.errors,
    )
    return {
        "current_status": "human_review_required",
        "requires_human_review": True,
        "human_review_reason": (
            f"Extraction confidence {state.extraction_confidence:.2f} below threshold "
            f"after {state.retry_count} retries. Errors: {'; '.join(state.validation_errors)}"
        ),
    }


# ── Node: create_semantic_chunks ─────────────────────────────────────────────


def create_semantic_chunks(state: ResumeIngestionState) -> dict[str, Any]:
    """
    Create section-aware semantic chunks from the structured resume.
    Each project and major experience entry gets its own chunk.
    Character-based chunking is used only as a fallback within long sections.
    """
    from app.core.config import settings

    profile = state.structured_resume
    if not profile:
        return {"errors": [*state.errors, "No structured resume for chunking"]}

    chunks = []
    chunk_size = settings.RAG_CHUNK_SIZE
    chunk_overlap = settings.RAG_CHUNK_OVERLAP

    def _add_chunk(section_type: str, content: str, metadata: dict) -> None:
        if len(content) <= chunk_size:
            chunks.append({
                "section_type": section_type,
                "content": content,
                "metadata": {
                    "organization_id": state.organization_id,
                    "candidate_id": state.candidate_id,
                    "resume_id": state.resume_id,
                    **metadata,
                },
            })
        else:
            # Recursive character chunking for long sections
            start = 0
            while start < len(content):
                end = min(start + chunk_size, len(content))
                chunks.append({
                    "section_type": section_type,
                    "content": content[start:end],
                    "metadata": {
                        "organization_id": state.organization_id,
                        "candidate_id": state.candidate_id,
                        "resume_id": state.resume_id,
                        "chunk_part": True,
                        **metadata,
                    },
                })
                start += chunk_size - chunk_overlap

    # Profile summary
    if profile.summary:
        _add_chunk("profile_summary", profile.summary, {"section": "summary"})

    # Skills as a group
    if profile.skills:
        skills_text = ", ".join(s.name for s in profile.skills)
        _add_chunk("skills", skills_text, {"skills": [s.name for s in profile.skills]})

    # Each experience as separate chunk
    for exp in profile.experience:
        content = f"{exp.title or ''} at {exp.company or ''}\n{exp.description or ''}"
        _add_chunk("experience", content.strip(), {
            "company": exp.company,
            "title": exp.title,
            "technologies": exp.technologies_used,
        })

    # Each project as separate chunk
    for proj in profile.projects:
        content = f"{proj.name or ''}: {proj.description or ''}\nTech: {', '.join(proj.technologies)}"
        _add_chunk("project", content.strip(), {
            "project_name": proj.name,
            "skills": proj.technologies,
        })

    # Education
    for edu in profile.education:
        content = f"{edu.degree or ''} in {edu.field_of_study or ''} from {edu.institution or ''}"
        _add_chunk("education", content.strip(), {"institution": edu.institution})

    # Certifications
    for cert in profile.certifications:
        _add_chunk("certification", cert.name, {"issuer": cert.issuer})

    logger.info("Chunks created", resume_id=state.resume_id, count=len(chunks))
    return {"chunks": chunks, "current_status": "embedding"}


# ── Node: generate_embeddings ─────────────────────────────────────────────────


async def generate_embeddings(state: ResumeIngestionState) -> dict[str, Any]:
    """
    Generate semantic embeddings for each chunk.
    Uses the configured EmbeddingProvider.
    """
    # TODO Phase 5: Implement EmbeddingService
    logger.info("Generating embeddings (stub)", resume_id=state.resume_id, chunk_count=len(state.chunks))
    return {"embedding_status": "completed"}


# ── Node: store_vectors ───────────────────────────────────────────────────────


async def store_vectors(state: ResumeIngestionState) -> dict[str, Any]:
    """Store chunk embeddings in pgvector with mandatory tenant filters."""
    # TODO Phase 5: Implement pgvector storage with organization_id filtering
    logger.info("Storing vectors (stub)", resume_id=state.resume_id)
    return {}


# ── Node: store_structured_data ───────────────────────────────────────────────


async def store_structured_data(state: ResumeIngestionState) -> dict[str, Any]:
    """Persist structured resume data (skills, experience, projects) to PostgreSQL."""
    # TODO Phase 4: Implement DB persistence
    logger.info("Storing structured data (stub)", resume_id=state.resume_id)
    return {"current_status": "completed"}


# ── Node: mark_failed ─────────────────────────────────────────────────────────


def mark_failed(state: ResumeIngestionState) -> dict[str, Any]:
    """Terminal failure node — marks the resume as failed and logs."""
    logger.error(
        "Resume ingestion failed",
        resume_id=state.resume_id,
        errors=state.errors,
    )
    return {"current_status": "failed"}
