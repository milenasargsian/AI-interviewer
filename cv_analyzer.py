"""CV analysis: extract candidate profile, target role and fit.

When a real job description (JD) is provided, the match is computed against the
actual posting rather than just a role title.
"""

from llm_client import chat_json, trim_cv, lang_directive
from cv_parser import get_header_lines
from name_utils import resolve_name, split_first_last

_SYSTEM = (
    "You are a senior technical recruiter and career advisor with 15+ years "
    "of experience screening CVs across many industries. You are precise, "
    "evidence-based and never invent facts that are not in the CV."
)


def analyze_cv(cv_text, job_direction, jd_text="", interview_lang="en",
               interview_desc="", persona="candidate"):
    """Analyse a CV and return a structured, normalised profile.

    Robust to CV/role mismatch: instead of failing, it identifies transferable
    skills and frames the interview as a realistic transition/stretch case.
    """

    header_lines = get_header_lines(cv_text)
    trimmed = trim_cv(cv_text)

    jd_block = ""
    if jd_text and jd_text.strip():
        jd_block = f"""
TARGET JOB DESCRIPTION (match the candidate against THIS, not just the title):
{jd_text.strip()[:4000]}
"""

    desc_block = ""
    if interview_desc and interview_desc.strip():
        desc_block = (f"\nINTERVIEW DESCRIPTION FROM THE USER (honour this framing "
                      f"when judging fit and tone):\n{interview_desc.strip()[:1500]}\n")

    prompt = f"""Analyse the following CV for a candidate targeting the job
direction: "{job_direction}".
{jd_block}{desc_block}
IMPORTANT — handle imperfect fit gracefully. If the CV does NOT closely match
the target role, do NOT refuse or just declare a mismatch. Instead: give an
honest match_score, identify TRANSFERABLE skills, and treat it as a realistic
career-transition / stretch interview. Always produce a usable analysis.

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
  "target_role": "the single most suitable, specific job title for this candidate (e.g. 'Backend Software Engineer', not just 'Engineer'), grounded in their experience, skills and education{' and aligned with the job description above' if jd_block else ' and aligned with the job direction'}",
  "seniority_level": "one of: Intern, Junior, Mid-level, Senior, Lead, Principal/Manager",
  "years_of_experience": "approximate total relevant years as a number (use 0 if none)",
  "match_score": <integer 0-100 expressing how well the CV fits the {'job description' if jd_block else 'target role'}>,
  "match_rationale": "2-3 sentences explaining the match score with concrete evidence{', referencing specific JD requirements that are met or missing' if jd_block else ''}",
  "key_skills": ["the 6-10 most relevant skills/tools actually shown in the CV"],
  "strengths": ["4-6 concrete strengths for the target role, each citing CV evidence"],
  "gaps": ["3-5 specific gaps or risks for the target role{' versus the JD requirements' if jd_block else ''}"],
  "transferable_skills": ["3-6 skills from the CV that transfer to the target role, even if the background differs"],
  "fit_note": "1-2 sentences: how strong the fit is and, if it's a transition/stretch, how to frame the interview fairly",
  "jd_requirements": [{'"the key requirements parsed from the JD" ' if jd_block else ''}],
  "summary": "a concise 2-3 sentence professional summary of the candidate"
}}

Be specific and realistic. Avoid vague or generic titles.{lang_directive(interview_lang)}"""

    try:
        data = chat_json(prompt, system=_SYSTEM, temperature=0.2)
    except Exception as err:
        return {
            "full_name": resolve_name(header_lines=header_lines),
            "first_name": "", "last_name": "",
            "target_role": job_direction, "seniority_level": "N/A",
            "years_of_experience": 0, "match_score": 0,
            "match_rationale": f"Analysis failed: {err}",
            "key_skills": [], "strengths": [], "gaps": [],
            "transferable_skills": [], "fit_note": "",
            "jd_requirements": [], "summary": "",
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
    data["name"] = full  # backwards-compatible alias

    # --- Defensive defaults / clamping ---
    try:
        data["match_score"] = max(0, min(100, int(round(float(data.get("match_score", 0))))))
    except (TypeError, ValueError):
        data["match_score"] = 0
    for key in ("key_skills", "strengths", "gaps", "jd_requirements",
                "transferable_skills"):
        if not isinstance(data.get(key), list):
            data[key] = []
    data.setdefault("seniority_level", "N/A")
    data.setdefault("target_role", job_direction)
    data.setdefault("summary", "")
    data.setdefault("match_rationale", "")
    data.setdefault("fit_note", "")

    return data
