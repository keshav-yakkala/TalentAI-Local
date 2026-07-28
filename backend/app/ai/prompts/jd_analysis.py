"""JD analysis prompt — versioned."""

JD_ANALYSIS_PROMPT_VERSION = "v1"


def build_jd_analysis_prompt(jd_text: str) -> str:
    return f"""Analyze the following job description and extract structured requirements.

Job Description:
---
{jd_text[:8000]}
---

Extract:
1. All required technical skills (must-have for the role)
2. All preferred/bonus technical skills (nice-to-have)
3. Minimum years of experience required
4. Education requirements
5. Domain knowledge areas (e.g., fintech, healthcare, e-commerce)
6. Soft skills mentioned
7. Key responsibilities (as short bullet points)
8. Job title and seniority level

For extraction_confidence:
- 0.9+: JD is detailed and well-structured
- 0.7-0.9: Good JD with most information present
- 0.5-0.7: JD is vague or incomplete
- Below 0.5: Very little actionable information extracted

Be precise. Do NOT add skills not mentioned in the JD."""


def build_skill_matching_prompt(
    jd_analysis_json: str,
    resume_profile_json: str,
    resume_chunks_context: str,
) -> str:
    return f"""You are an expert technical recruiter evaluating a candidate against a job description.

Job Requirements:
{jd_analysis_json}

Candidate Profile:
{resume_profile_json}

Relevant Resume Evidence:
{resume_chunks_context}

For each required and preferred skill, determine:
1. Was the skill found in the resume? (true/false)
2. What is the evidence? (exact quote from resume or profile)
3. What proficiency level is demonstrated?
4. Your confidence in this assessment (0.0-1.0)

For experience, projects, and education evaluation:
- Base your scores ONLY on verified resume evidence
- Do NOT assume skills not explicitly mentioned
- Score 0-100 for each category

CRITICAL: If you cannot find evidence for a skill, mark found=false.
Do not infer skills from job titles alone."""
