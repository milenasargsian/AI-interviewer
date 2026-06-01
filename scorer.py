"""Transparent, rubric-based scoring of interview answers."""

from llm_client import chat_json

_SYSTEM = (
    "You are a rigorous, fair interview evaluator. You score answers against "
    "a clear rubric, justify every score with evidence from the answer, and "
    "give concrete, actionable feedback. You are neither harsh nor lenient."
)


def score_answer(question, answer, job_direction, cv_analysis=None, context=None):
    """Score one answer transparently against a 4-criteria rubric (0-10 each)."""
    cv_analysis = cv_analysis or {}
    context = context or {}
    role = cv_analysis.get("target_role", job_direction)

    if not answer or not answer.strip():
        return _empty("No answer was provided.")

    prompt = f"""Evaluate the candidate's interview answer.

ROLE CONTEXT
- Target role: {role}
- Job direction: {job_direction}
- Industry: {context.get('industry', 'Not specified')}
- Seniority expected: {cv_analysis.get('seniority_level', 'Mid-level')}

QUESTION:
{question}

CANDIDATE'S ANSWER:
{answer}

Score each criterion from 0 to 10 and justify with specifics:
- relevance: did it actually address the question?
- technical_accuracy: is the content correct and sound?
- clarity: structure and communication (e.g. STAR for behavioural).
- depth: concrete detail, reasoning, trade-offs, ownership.

The overall "score" must be the average of the four criteria, rounded to
one decimal, on a 0-10 scale.

Return a JSON object:
{{
  "score": <number 0-10>,
  "criteria": {{
    "relevance": <0-10>,
    "technical_accuracy": <0-10>,
    "clarity": <0-10>,
    "depth": <0-10>
  }},
  "strengths": ["1-3 specific things done well"],
  "weaknesses": ["1-3 specific shortcomings"],
  "improvements": ["1-3 concrete, actionable ways to improve this answer"],
  "feedback": "2-3 sentence overall justification of the score"
}}
Return ONLY the JSON object."""

    try:
        data = chat_json(prompt, system=_SYSTEM, temperature=0.2)
    except Exception as err:
        return _empty(f"Could not evaluate answer: {err}")

    return _normalise(data)


def _normalise(data):
    crit = data.get("criteria") or {}
    norm_crit = {}
    for key in ("relevance", "technical_accuracy", "clarity", "depth"):
        norm_crit[key] = _clamp(crit.get(key, 0))

    # Recompute overall from criteria so the displayed score is always
    # consistent with the breakdown the candidate can see.
    overall = round(sum(norm_crit.values()) / 4, 1)

    for key in ("strengths", "weaknesses", "improvements"):
        if not isinstance(data.get(key), list):
            data[key] = []

    return {
        "score": overall,
        "criteria": norm_crit,
        "strengths": data.get("strengths", []),
        "weaknesses": data.get("weaknesses", []),
        "improvements": data.get("improvements", []),
        "feedback": data.get("feedback", ""),
    }


def _clamp(value):
    try:
        return max(0, min(10, round(float(value), 1)))
    except (TypeError, ValueError):
        return 0


def _empty(message):
    return {
        "score": 0,
        "criteria": {"relevance": 0, "technical_accuracy": 0, "clarity": 0, "depth": 0},
        "strengths": [],
        "weaknesses": [],
        "improvements": [],
        "feedback": message,
    }
