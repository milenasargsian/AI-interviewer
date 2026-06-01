"""Transparent, rubric-based scoring of interview answers.

Also flags answers that read as AI-generated / inauthentic vs. natural and
personal, since a real interview rewards genuine, first-hand responses.
"""

from llm_client import chat_json, lang_directive

_SYSTEM = (
    "You are a rigorous, fair interview evaluator. You score answers against "
    "a clear rubric, justify every score with evidence from the answer, and "
    "give concrete, actionable feedback. You are neither harsh nor lenient. "
    "You can also tell the difference between a natural, personal, first-hand "
    "answer and one that sounds generic or AI-generated."
)


def score_answer(question, answer, job_direction, cv_analysis=None, context=None,
                 interview_lang="en"):
    """Score one answer transparently against a rubric, plus authenticity."""
    cv_analysis = cv_analysis or {}
    context = context or {}
    role = cv_analysis.get("target_role", job_direction)

    if not answer or not answer.strip():
        return _empty("No answer was provided.")

    jd = context.get("jd_text", "")
    jd_line = (f"\n- Job description requirements: {jd.strip()[:1500]}"
               if jd and jd.strip() else "")

    prompt = f"""Evaluate the candidate's interview answer.

ROLE CONTEXT
- Target role: {role}
- Job direction: {job_direction}
- Industry: {context.get('industry', 'Not specified')}
- Seniority expected: {cv_analysis.get('seniority_level', 'Mid-level')}{jd_line}

QUESTION:
{question}

CANDIDATE'S ANSWER:
{answer}

PART 1 — QUALITY. Score each criterion 0-10 and justify with specifics:
- relevance: did it actually address the question?
- technical_accuracy: is the content correct and sound?
- clarity: structure and communication (e.g. STAR for behavioural).
- depth: concrete detail, reasoning, trade-offs, ownership.

PART 2 — AUTHENTICITY. Judge whether the answer sounds like a real person
speaking from first-hand experience versus generic, templated, or
AI-generated text. Signals of authenticity: specific personal details, real
project/tool names, natural spoken rhythm, minor imperfections, concrete
numbers, "I" ownership. Signals of AI/inauthentic: vague universal claims,
polished list-like structure, buzzword stacking, no personal specifics,
textbook phrasing.
- authenticity_score: 0-100 (100 = clearly genuine and personal)
- ai_likelihood: 0-100 (100 = very likely AI-generated/templated)
- authenticity_verdict: one of "Authentic", "Mostly authentic",
  "Possibly AI-assisted", "Likely AI-generated"
- authenticity_signals: 1-3 short observations supporting the verdict

The overall "score" must be the average of the four QUALITY criteria, rounded
to one decimal, on a 0-10 scale (authenticity does NOT change this number; it
is reported separately).

Return a JSON object:
{{
  "score": <number 0-10>,
  "criteria": {{"relevance": <0-10>, "technical_accuracy": <0-10>, "clarity": <0-10>, "depth": <0-10>}},
  "strengths": ["1-3 specific things done well"],
  "weaknesses": ["1-3 specific shortcomings"],
  "improvements": ["1-3 concrete, actionable ways to improve this answer"],
  "feedback": "2-3 sentence overall justification of the score",
  "authenticity_score": <0-100>,
  "ai_likelihood": <0-100>,
  "authenticity_verdict": "Authentic | Mostly authentic | Possibly AI-assisted | Likely AI-generated",
  "authenticity_signals": ["short observation", "..."]
}}
Return ONLY the JSON object.{lang_directive(interview_lang)}"""

    try:
        data = chat_json(prompt, system=_SYSTEM, temperature=0.2)
    except Exception as err:
        return _empty(f"Could not evaluate answer: {err}")

    return _normalise(data)


def _normalise(data):
    crit = data.get("criteria") or {}
    norm_crit = {}
    for key in ("relevance", "technical_accuracy", "clarity", "depth"):
        norm_crit[key] = _clamp10(crit.get(key, 0))

    # Recompute overall from criteria so the displayed score is always
    # consistent with the breakdown the candidate can see.
    overall = round(sum(norm_crit.values()) / 4, 1)

    for key in ("strengths", "weaknesses", "improvements", "authenticity_signals"):
        if not isinstance(data.get(key), list):
            data[key] = []

    verdict = data.get("authenticity_verdict", "Mostly authentic")
    if verdict not in {"Authentic", "Mostly authentic",
                       "Possibly AI-assisted", "Likely AI-generated"}:
        verdict = "Mostly authentic"

    return {
        "score": overall,
        "criteria": norm_crit,
        "strengths": data.get("strengths", []),
        "weaknesses": data.get("weaknesses", []),
        "improvements": data.get("improvements", []),
        "feedback": data.get("feedback", ""),
        "authenticity_score": _clamp100(data.get("authenticity_score", 70)),
        "ai_likelihood": _clamp100(data.get("ai_likelihood", 30)),
        "authenticity_verdict": verdict,
        "authenticity_signals": data.get("authenticity_signals", []),
    }


def _clamp10(value):
    try:
        return max(0, min(10, round(float(value), 1)))
    except (TypeError, ValueError):
        return 0


def _clamp100(value):
    try:
        return max(0, min(100, int(round(float(value)))))
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
        "authenticity_score": 0,
        "ai_likelihood": 0,
        "authenticity_verdict": "N/A",
        "authenticity_signals": [],
    }
