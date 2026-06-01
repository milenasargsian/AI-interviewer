"""CV analysis: extract candidate profile, target role and fit."""

from llm_client import chat_json, trim_cv
from cv_parser import get_header_lines
from name_utils import resolve_name, split_first_last

_SYSTEM = (
    "You are a senior technical recruiter and career advisor with 15+ years "
    "of experience screening CVs across many industries. You are precise, "
    "evidence-based and never invent facts that are not in the CV."
)


def analyze_cv(cv_text, job_direction):
    """Analyse a CV and return a structured, normalised profile."""

    header_lines = get_header_lines(cv_text)
    trimmed = trim_cv(cv_text)

    prompt = f"""Analyse the following CV for a candidate targeting the job
direction: "{job_direction}".

Use ONLY evidence present in the CV. The candidate's name normally appears
in the first lines (the header). Extract it exactly as written; do not
translate, abbreviate or reorder it.

CV HEADER (first lines, for the name):
{header_lines}

FULL CV TEXT:
{trimmed}

Return a JSON object with EXACTLY these keys:
{{
  "first_name": "given name only",
  "last_name": "family name only",
  "full_name": "the complete name as it appears",
  "target_role": "the single most suitable, specific job title for this candidate (e.g. 'Backend Software Engineer', not just 'Engineer'), grounded in their experience, skills and education and aligned with the job direction",
  "seniority_level": "one of: Intern, Junior, Mid-level, Senior, Lead, Principal/Manager",
  "years_of_experience": "approximate total relevant years as a number (use 0 if none)",
  "match_score": <integer 0-100 expressing how well the CV fits the target role>,
  "match_rationale": "2-3 sentences explaining the match score with concrete evidence",
  "key_skills": ["the 6-10 most relevant skills/tools actually shown in the CV"],
  "strengths": ["4-6 concrete strengths for the target role, each citing CV evidence"],
  "gaps": ["3-5 specific gaps or risks for the target role"],
  "summary": "a concise 2-3 sentence professional summary of the candidate"
}}

Be specific and realistic. Avoid vague or generic titles."""

    try:
        data = chat_json(prompt, system=_SYSTEM, temperature=0.2)
    except Exception as err:
        return {
            "full_name": resolve_name(header_lines=header_lines),
            "first_name": "",
            "last_name": "",
            "target_role": job_direction,
            "seniority_level": "N/A",
            "years_of_experience": 0,
            "match_score": 0,
            "match_rationale": f"Analysis failed: {err}",
            "key_skills": [],
            "strengths": [],
            "gaps": [],
            "summary": "",
        }

    # --- Normalise the name so it is always clean and correctly cased ---
    full = resolve_name(
        model_full=data.get("full_name"),
        model_first=data.get("first_name"),
        model_last=data.get("last_name"),
        header_lines=header_lines,
    )
    first, last = split_first_last(full)
    data["full_name"] = full
    data["first_name"] = first
    data["last_name"] = last
    # Backwards-compatible alias used elsewhere in the app.
    data["name"] = full

    # --- Defensive defaults / clamping ---
    try:
        data["match_score"] = max(0, min(100, int(round(float(data.get("match_score", 0))))))
    except (TypeError, ValueError):
        data["match_score"] = 0
    for key in ("key_skills", "strengths", "gaps"):
        if not isinstance(data.get(key), list):
            data[key] = []
    data.setdefault("seniority_level", "N/A")
    data.setdefault("target_role", job_direction)
    data.setdefault("summary", "")
    data.setdefault("match_rationale", "")

    return data
