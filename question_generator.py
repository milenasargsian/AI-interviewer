"""Interview question generation tailored to the candidate and context."""

from llm_client import chat_json

_SYSTEM = (
    "You are a world-class interviewer who designs sharp, realistic interview "
    "questions used at top companies. Your questions probe real competence, "
    "are tailored to the candidate, and mirror what a strong hiring panel "
    "would actually ask."
)


def generate_questions(cv_analysis, job_direction, context=None, num_questions=6):
    """Generate tailored interview questions.

    ``context`` may contain: industry, company_type, company, interview_focus.
    Returns a list of dicts: {category, difficulty, question, what_it_assesses}.
    """
    context = context or {}
    industry = context.get("industry") or "Not specified"
    company_type = context.get("company_type") or "Not specified"
    company = context.get("company") or "Not specified"
    focus = context.get("interview_focus") or "Balanced (technical + behavioural)"

    seniority = cv_analysis.get("seniority_level", "Mid-level")

    prompt = f"""Design {num_questions} interview questions for this candidate.

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

REQUIREMENTS
- Calibrate difficulty to the seniority level ({seniority}).
- Make questions specific to THIS candidate's background and the target
  role/industry/company — not generic. Where a specific company is given,
  reflect its known domain, scale and interview style.
- Include a balanced mix across these categories: "Technical",
  "Behavioural", "Role-specific", "Scenario/Case", "Gap-probing".
- At least one question should directly probe a stated gap/risk.
- Questions must be answerable verbally in 2-4 minutes.

Return a JSON object: {{"questions": [
  {{
    "category": "one of the categories above",
    "difficulty": "Easy | Medium | Hard",
    "question": "the full question text",
    "what_it_assesses": "one short sentence on what a strong answer demonstrates"
  }}
]}}
Return exactly {num_questions} questions."""

    try:
        data = chat_json(prompt, system=_SYSTEM, temperature=0.6)
        questions = data.get("questions", [])
        if isinstance(questions, list) and questions:
            return [_normalise(q) for q in questions][:num_questions]
    except Exception:
        pass

    # Fallback so the interview can always proceed.
    role = cv_analysis.get("target_role", job_direction)
    return [
        _normalise({"category": "Behavioural", "difficulty": "Medium",
                    "question": "Walk me through your most impactful project and your specific contribution."}),
        _normalise({"category": "Role-specific", "difficulty": "Medium",
                    "question": f"What does excellent work look like in a {role} role, and how do you achieve it?"}),
        _normalise({"category": "Technical", "difficulty": "Medium",
                    "question": "Describe a hard technical problem you solved and the trade-offs you weighed."}),
        _normalise({"category": "Scenario/Case", "difficulty": "Hard",
                    "question": "How would you approach your first 90 days in this role?"}),
        _normalise({"category": "Gap-probing", "difficulty": "Medium",
                    "question": "Tell me about a skill you are actively developing and how you are closing the gap."}),
        _normalise({"category": "Behavioural", "difficulty": "Medium",
                    "question": "Describe a time you disagreed with a teammate. How did you resolve it?"}),
    ][:num_questions]


def _normalise(q):
    if isinstance(q, str):
        q = {"question": q}
    return {
        "category": q.get("category", "General"),
        "difficulty": q.get("difficulty", "Medium"),
        "question": q.get("question", "").strip(),
        "what_it_assesses": q.get("what_it_assesses", ""),
    }
