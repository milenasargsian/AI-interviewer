"""Interview question generation tailored to the candidate and context.

Generates a balanced interview plan (technical, problem-solving, behavioural,
project-grounded, scenario, gap-probing), supports a real job description and
multiple languages, and can produce a single adaptive follow-up whose
difficulty adapts to how the candidate is performing.
"""

from llm_client import chat_json, lang_directive
from project_analyzer import project_brief

_SYSTEM = (
    "You are a world-class interviewer who designs sharp, realistic interview "
    "questions used at top companies. Your questions probe real competence, "
    "are tailored to the candidate, and mirror what a strong hiring panel "
    "would actually ask."
)

CATEGORIES = [
    "Technical", "Problem-Solving", "Behavioural", "Role-specific",
    "Project", "Scenario/Case", "Gap-probing",
]

# Difficulty ladder used for adaptive difficulty.
DIFFICULTY_LADDER = ["Easy", "Medium", "Hard", "Expert"]


def _jd_block(context):
    jd = (context or {}).get("jd_text", "")
    if jd and jd.strip():
        return f"\nTARGET JOB DESCRIPTION (tailor questions to THESE requirements):\n{jd.strip()[:3500]}\n"
    return ""


def generate_questions(cv_analysis, job_direction, context=None,
                       num_questions=8, project_summary=None, interview_lang="en"):
    """Generate a balanced, tailored interview plan."""
    context = context or {}
    industry = context.get("industry") or "Not specified"
    company_type = context.get("company_type") or "Not specified"
    company = context.get("company") or "Not specified"
    focus = context.get("interview_focus") or "Balanced (technical + behavioural)"
    extra_context = context.get("extra_context") or "None provided"

    seniority = cv_analysis.get("seniority_level", "Mid-level")
    has_project = bool(project_summary)
    interview_desc = context.get("interview_desc", "")
    persona = context.get("persona", "candidate")
    transferable = ", ".join(cv_analysis.get("transferable_skills", [])) or "N/A"
    persona_line = (
        "AUDIENCE: the CANDIDATE is practising — phrase questions like a real "
        "interviewer would, at a fair level for preparation."
        if persona == "candidate" else
        "AUDIENCE: a RECRUITER is screening this candidate — questions should "
        "expose real signal for a hire/no-hire decision.")

    prompt = f"""Design a {num_questions}-question interview PLAN for this candidate.

CANDIDATE PROFILE
- Name: {cv_analysis.get('full_name', 'Candidate')}
- Target role: {cv_analysis.get('target_role')}
- Seniority: {seniority}
- Key skills: {', '.join(cv_analysis.get('key_skills', [])) or 'N/A'}
- Strengths: {', '.join(cv_analysis.get('strengths', [])) or 'N/A'}
- Gaps/risks to probe: {', '.join(cv_analysis.get('gaps', [])) or 'N/A'}

INTERVIEW CONTEXT
- Job direction: {job_direction}
- Target industry: {industry}
- Company type: {company_type}
- Specific company: {company}
- Desired focus: {focus}
- Extra context from the user (treat as important): {extra_context}
- Interview description in the user's own words (honour tone & scope): {interview_desc or 'None'}
- Transferable skills (use these if the background is a stretch): {transferable}
- Fit note: {cv_analysis.get('fit_note', 'N/A')}
{persona_line}
{_jd_block(context)}
CANDIDATE'S SUBMITTED PROJECT (ask grounded questions about it if present):
{project_brief(project_summary)}

REQUIREMENTS
- If the CV is an imperfect match for the role, do NOT bail out: build a fair
  transition/stretch interview that leans on transferable skills and motivation,
  while still honestly testing the role's core requirements.
- Calibrate difficulty to the seniority level ({seniority}).
- BALANCE the interview across these categories: {', '.join(CATEGORIES)}.
  Do NOT spend the whole interview on one topic.
- Include at least 2 "Problem-Solving" questions: realistic problems the
  candidate must reason through (debugging, design choices, trade-offs,
  estimation, or a small case) — not trivia.
- {"Tailor several questions to the JD requirements above." if _jd_block(context) else ""}
- {"Include 2-3 'Project' questions grounded in the submitted project above." if has_project else "No project was submitted; skip the 'Project' category."}
- At least one question must directly probe a stated gap/risk.
- Honour the extra context by avoiding basics already covered and going deeper.
- Make every question specific to THIS candidate — never generic.
- Questions must be answerable verbally in 2-4 minutes.

Return a JSON object: {{"questions": [
  {{
    "category": "one of: {', '.join(CATEGORIES)}",
    "difficulty": "Easy | Medium | Hard",
    "question": "the full question text",
    "what_it_assesses": "one short sentence on what a strong answer demonstrates"
  }}
]}}
Return exactly {num_questions} questions, ordered to flow naturally (warm-up
first, harder problem-solving and scenarios in the middle, reflective last).{lang_directive(interview_lang)}"""

    try:
        data = chat_json(prompt, system=_SYSTEM, temperature=0.6)
        questions = data.get("questions", [])
        if isinstance(questions, list) and questions:
            return [_normalise(q) for q in questions][:num_questions]
    except Exception:
        pass

    return _fallback(cv_analysis, job_direction, num_questions)


def adapt_difficulty(current_level, recent_scores):
    """Return a new difficulty index based on recent answer performance.

    ``current_level`` is an index into DIFFICULTY_LADDER. Strong answers push
    harder; weak answers ease off. Uses the average of the last two scores.
    """
    if not recent_scores:
        return current_level
    window = recent_scores[-2:]
    avg = sum(window) / len(window)
    if avg >= 8.0:
        current_level = min(current_level + 1, len(DIFFICULTY_LADDER) - 1)
    elif avg <= 4.5:
        current_level = max(current_level - 1, 0)
    return current_level


def generate_followup(previous_question, previous_answer, cv_analysis,
                      job_direction, context=None, project_summary=None,
                      asked_categories=None, target_difficulty="Medium",
                      interview_lang="en"):
    """Generate ONE adaptive follow-up grounded in the candidate's last answer.

    ``target_difficulty`` lets the caller raise/lower difficulty based on how
    the candidate has been performing.
    """
    context = context or {}
    asked_categories = asked_categories or []

    counts = {c: asked_categories.count(c) for c in CATEGORIES}
    underused = sorted(CATEGORIES, key=lambda c: counts.get(c, 0))[:3]

    prompt = f"""You are mid-interview. Decide the single best NEXT question.

ROLE: {cv_analysis.get('target_role')} ({cv_analysis.get('seniority_level','Mid-level')})
JOB DIRECTION: {job_direction}
EXTRA CONTEXT: {context.get('extra_context') or 'None'}
{_jd_block(context)}
PROJECT: {project_brief(project_summary)}

PREVIOUS QUESTION:
{previous_question}

CANDIDATE'S ANSWER:
{previous_answer}

CATEGORIES ALREADY USED (with counts): {counts}
UNDER-USED CATEGORIES TO CONSIDER: {', '.join(underused)}
TARGET DIFFICULTY FOR THE NEXT QUESTION: {target_difficulty}

RULES
- If the answer opened an interesting or weak thread, ask a natural, deeper
  follow-up that builds on what they actually said.
- BUT do not over-focus on one topic: if this thread is exhausted, pivot to an
  under-used category to keep the interview balanced.
- Set the question's difficulty to about "{target_difficulty}" (the candidate's
  recent performance warrants this level).
- Keep it answerable verbally in 2-4 minutes.

Return a JSON object:
{{
  "category": "one of: {', '.join(CATEGORIES)}",
  "difficulty": "Easy | Medium | Hard | Expert",
  "question": "the next question",
  "what_it_assesses": "one short sentence",
  "is_followup": true/false
}}{lang_directive(interview_lang)}"""

    try:
        data = chat_json(prompt, system=_SYSTEM, temperature=0.5)
        q = _normalise(data)
        q["is_followup"] = bool(data.get("is_followup", False))
        if q["question"]:
            return q
    except Exception:
        pass
    return None


def _normalise(q):
    if isinstance(q, str):
        q = {"question": q}
    return {
        "category": q.get("category", "General"),
        "difficulty": q.get("difficulty", "Medium"),
        "question": (q.get("question") or "").strip(),
        "what_it_assesses": q.get("what_it_assesses", ""),
    }


def _fallback(cv_analysis, job_direction, num_questions):
    role = cv_analysis.get("target_role", job_direction)
    base = [
        {"category": "Behavioural", "difficulty": "Medium",
         "question": "Walk me through your most impactful project and your specific contribution."},
        {"category": "Problem-Solving", "difficulty": "Medium",
         "question": "A feature you shipped is suddenly 10x slower in production. How do you diagnose and fix it?"},
        {"category": "Technical", "difficulty": "Medium",
         "question": "Describe a hard technical problem you solved and the trade-offs you weighed."},
        {"category": "Problem-Solving", "difficulty": "Hard",
         "question": "How would you design a system to handle 1M requests/day for this role's domain?"},
        {"category": "Role-specific", "difficulty": "Medium",
         "question": f"What does excellent work look like in a {role} role, and how do you achieve it?"},
        {"category": "Scenario/Case", "difficulty": "Hard",
         "question": "How would you approach your first 90 days in this role?"},
        {"category": "Gap-probing", "difficulty": "Medium",
         "question": "Tell me about a skill you are actively developing and how you are closing the gap."},
        {"category": "Behavioural", "difficulty": "Medium",
         "question": "Describe a time you disagreed with a teammate. How did you resolve it?"},
    ]
    out = [_normalise(q) for q in base]
    while len(out) < num_questions:
        out.append(out[len(out) % len(base)])
    return out[:num_questions]
