"""
Resume extraction prompt — versioned.
Migrated from inline string in agents.py; now centralized and versioned.
"""

RESUME_EXTRACTION_PROMPT_VERSION = "v1"


def build_extraction_prompt(resume_text: str) -> str:
    """Build the structured resume extraction prompt."""
    return f"""You are an expert resume parser. Extract ALL information from the following resume into a structured format.

CRITICAL RULES:
1. Extract ONLY what is explicitly stated in the resume
2. Do NOT infer, guess, or fabricate any information
3. If a field is not present, use null
4. For extraction_confidence, score 0.0-1.0 based on how complete and readable the resume is

Resume Text:
---
{resume_text[:6000]}
---

Extract the information and provide extraction_confidence as a float between 0.0 and 1.0.
A confidence of 0.9+ means the resume is clearly formatted with complete information.
A confidence below 0.5 means significant information is missing or the text is corrupted."""
