"""
Tests for security: cross-tenant data isolation.
These tests verify that vector retrieval queries CANNOT return
chunks from a different organization.

CRITICAL: These tests must pass before any production deployment.
"""
import pytest


class TestCrossTenantIsolation:
    """
    Verify that organization_id filtering is enforced at the data layer.
    This tests the architectural contract — actual DB tests require Phase 5.
    """

    def test_chunk_metadata_contains_org_id(self):
        """Every chunk must carry organization_id for retrieval filtering."""
        from app.ai.structured_outputs.resume import ResumeProfile, ProjectEntry
        from app.graphs.resume_ingestion.nodes import create_semantic_chunks
        from app.graphs.resume_ingestion.state import ResumeIngestionState

        org_a = "org-aaaaaaaa"
        org_b = "org-bbbbbbbb"

        profile = ResumeProfile(
            projects=[
                ProjectEntry(name="TalentAI", technologies=["Python", "FastAPI"]),
            ],
            extraction_confidence=0.9,
        )

        state_a = ResumeIngestionState(
            workflow_id="wf-1",
            organization_id=org_a,
            candidate_id="cand-1",
            resume_id="resume-1",
            file_path="/tmp/resume.pdf",
            file_type="pdf",
            structured_resume=profile,
        )

        result = create_semantic_chunks(state_a)
        for chunk in result["chunks"]:
            # Every chunk must be tagged with org_a's ID
            assert chunk["metadata"]["organization_id"] == org_a
            # No chunk should accidentally carry org_b
            assert chunk["metadata"]["organization_id"] != org_b

    def test_different_orgs_get_different_tags(self):
        """Chunks for org A and org B must carry different organization IDs."""
        from app.ai.structured_outputs.resume import ResumeProfile, SkillEntry
        from app.graphs.resume_ingestion.nodes import create_semantic_chunks
        from app.graphs.resume_ingestion.state import ResumeIngestionState

        profile = ResumeProfile(skills=[SkillEntry(name="Python")], extraction_confidence=0.9)

        def get_chunks(org_id: str):
            state = ResumeIngestionState(
                workflow_id="wf-test",
                organization_id=org_id,
                candidate_id="cand-1",
                resume_id="resume-1",
                file_path="/tmp/r.pdf",
                file_type="pdf",
                structured_resume=profile,
            )
            return create_semantic_chunks(state)["chunks"]

        chunks_a = get_chunks("org-alpha")
        chunks_b = get_chunks("org-beta")

        org_ids_a = {c["metadata"]["organization_id"] for c in chunks_a}
        org_ids_b = {c["metadata"]["organization_id"] for c in chunks_b}

        assert org_ids_a == {"org-alpha"}
        assert org_ids_b == {"org-beta"}
        assert org_ids_a.isdisjoint(org_ids_b), "CRITICAL: org IDs overlap — cross-tenant leak possible"


class TestEvalRemoval:
    """
    Verify that eval() is no longer used anywhere in the AI pipeline.
    The original agents.py used eval() on LLM output — a critical security vuln.
    """

    def test_llm_base_uses_json_not_eval(self):
        """LLM base provider must use json.loads, never eval."""
        import inspect
        import app.ai.llms.base as base_module

        source = inspect.getsource(base_module)
        assert "eval(" not in source, (
            "SECURITY: eval() found in LLM base module. "
            "Use json.loads() instead to prevent code injection from LLM output."
        )

    def test_ollama_provider_uses_json_not_eval(self):
        """Ollama provider must not use eval()."""
        import inspect
        import app.ai.llms.ollama_provider as provider_module

        source = inspect.getsource(provider_module)
        assert "eval(" not in source, (
            "SECURITY: eval() found in Ollama provider. Use json.loads() + Pydantic."
        )
