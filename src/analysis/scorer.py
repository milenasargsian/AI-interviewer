"""Transparent, rubric-based scoring of interview answers.

Also flags answers that read as AI-generated / inauthentic vs. natural and
personal, since a real interview rewards genuine, first-hand responses.
"""

import re

from src.core.llm_client import chat_json, chat_text, lang_directive
from src.analysis.ai_detector import blend

_SYSTEM = (
    "You are a rigorous, fair interview evaluator. You score answers against "
    "a clear rubric, justify every score with evidence from the answer, and "
    "give concrete, actionable feedback. You are neither harsh nor lenient. "
    "You can also tell the difference between a natural, personal, first-hand "
    "answer and one that sounds generic or AI-generated."
)

_NON_ANSWER_PATTERNS = [
    r"i\s*(do\s*not|don'?t|did\s*not|didn'?t)\s*know",
    r"i\s*have\s*no\s*(idea|clue)",
    r"no\s*idea", r"not\s*sure", r"i'?m\s*not\s*sure",
    r"i\s*can'?t\s*answer", r"i\s*cannot\s*answer",
    r"i\s*don'?t\s*remember", r"i\s*forgot",
    r"^\s*(skip|pass|next|n/?a|none|nothing|idk|dunno|dk)\s*$",
    r"^\s*(no|nope|nah)\s*$",
]

def score_answer(question, answer, job_direction, cv_analysis=None, context=None,
                 interview_lang="en"):
    """Score one answer transparently against a rubric, plus authenticity."""
    cv_analysis = cv_analysis or {}
    context = context or {}
    role = cv_analysis.get("target_role", job_direction)

    if not answer or not answer.strip():
        return _empty("No answer was provided.")

    # A non-answer ("I don't know", "no idea", "pass"…) is always 0 — never send it to the model
    if _is_non_answer(answer):
        return _non_answer_score()

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

PART 1 — QUALITY. Score each criterion 0-10 using this OBJECTIVE anchored scale,
and justify each with a direct reference to the answer's content:
  0    = NON-ANSWER: "I don't know", "no idea", "skip", "pass", "I can't answer",
         blank, gibberish, or a refusal/admission of not knowing with NO actual
         attempt. ALL criteria = 0 and overall = 0. Do NOT award pity points.
  1-2  = attempted but essentially absent / wrong / off-topic
  3-4  = vague or generic; little substance
  5-6  = adequate; addresses the question but shallow or with gaps
  7-8  = strong; correct, specific, well-reasoned
  9-10 = excellent; precise, deep, with trade-offs and concrete evidence
Criteria:
- relevance: did it actually address THIS question?
- technical_accuracy: is the content correct and sound? (penalise factual errors)
- clarity: structure and communication (reward STAR for behavioural answers).
- depth: concrete detail, reasoning, trade-offs, ownership, real numbers.
Calibrate expectations to the stated seniority. Do not inflate: a generic answer
with no specifics cannot score above 5 on depth. Score only what is written —
never assume unstated knowledge. A candidate who merely says they don't know,
or gives no genuine attempt, scores 0 on every criterion (NOT 1).

PART 2 — AUTHENTICITY (AI-generated detection). Assess whether the answer reads
as a real person speaking from first-hand experience vs. generic/templated/
AI-generated text. Weigh concrete evidence, not surface polish alone:
  AUTHENTIC signals: specific personal details; real project/tool/company names;
    natural spoken rhythm and self-correction; concrete numbers/outcomes; first-
    person ownership ("I decided…"); honest uncertainty.
  AI/INAUTHENTIC signals: vague universal claims; suspiciously even, list-like
    structure; buzzword stacking; zero personal specifics; textbook phrasing;
    over-formal tone for a spoken answer; covers everything but commits to nothing.
Map ai_likelihood to the verdict CONSISTENTLY using these bands:
  0-24 -> "Authentic", 25-49 -> "Mostly authentic",
  50-74 -> "Possibly AI-assisted", 75-100 -> "Likely AI-generated".
Set authenticity_score = 100 - ai_likelihood. A short but clearly personal
answer is authentic; a long polished one with no specifics is suspicious.

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
        # temperature=0 -> deterministic, consistent, reproducible scoring.
        data = chat_json(prompt, system=_SYSTEM, temperature=0.0)

    except Exception as err:
        return _empty(f"Could not evaluate answer: {err}")

    return _normalise(data, answer)


def _normalise(data, answer=""):
    crit = data.get("criteria") or {}
    norm_crit = {}
    for key in ("relevance", "technical_accuracy", "clarity", "depth"):
        norm_crit[key] = _clamp10(crit.get(key, 0))

    overall = round(sum(norm_crit.values()) / 4, 1)

    for key in ("strengths", "weaknesses", "improvements", "authenticity_signals"):
        if not isinstance(data.get(key), list):
            data[key] = []

    # AI-detection
    llm_ai = _clamp100(data.get("ai_likelihood", 50))
    ai, heur_signals = blend(llm_ai, answer)
    verdict = _verdict_from_ai(ai)
    authenticity = 100 - ai

    return {
        "score": overall,
        "criteria": norm_crit,
        "strengths": data.get("strengths", []),
        "weaknesses": data.get("weaknesses", []),
        "improvements": data.get("improvements", []),
        "feedback": data.get("feedback", ""),
        "authenticity_score": authenticity,
        "ai_likelihood": ai,
        "ai_likelihood_llm": llm_ai,
        "ai_signals": heur_signals,
        "authenticity_verdict": verdict,
        "authenticity_signals": data.get("authenticity_signals", []),
    }


def _verdict_from_ai(ai_likelihood):
    if ai_likelihood >= 75:
        return "Likely AI-generated"
    if ai_likelihood >= 50:
        return "Possibly AI-assisted"
    if ai_likelihood >= 25:
        return "Mostly authentic"
    return "Authentic"


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
        "ai_likelihood_llm": 0,
        "ai_signals": {},
        "authenticity_verdict": "N/A",
        "authenticity_signals": [],
    }


def _is_non_answer(answer):
    """True if the answer is essentially a non-answer / 'I don't know'."""
    text = (answer or "").strip().lower()
    if len(text) < 2:
        return True

    core = re.sub(r"[\s\.\!\?\,]+$", "", text)
    for pat in _NON_ANSWER_PATTERNS:
        if re.search(pat, core):
            # If the answer is short
            if len(core.split()) <= 8:
                return True
    return False


def _non_answer_score():
    return {
        "score": 0,
        "criteria": {"relevance": 0, "technical_accuracy": 0, "clarity": 0, "depth": 0},
        "strengths": [],
        "weaknesses": ["The candidate did not attempt the question (e.g. \"I don't know\")."],
        "improvements": ["Even a partial attempt or thinking out loud scores higher "
                         "than admitting no knowledge. Share what you DO know and "
                         "reason from there."],
        "feedback": "No genuine attempt was made, so this answer scores 0/10.",
        "authenticity_score": 0,
        "ai_likelihood": 0,
        "ai_likelihood_llm": 0,
        "ai_signals": {},
        "authenticity_verdict": "N/A",
        "authenticity_signals": [],
    }


_MODEL_SYSTEM = (
    "You are an expert interview coach. You write exemplary spoken answers that "
    "a strong candidate could realistically give — specific, structured and "
    "natural, never generic filler."
)


def model_answer(question, job_direction, cv_analysis=None, context=None,
                 interview_lang="en"):
    """Generate a 'best possible answer' to a question, for coaching.

    Returns markdown: a concise model answer plus why it works. Grounded in
    the candidate's real background so it is attainable, not generic.
    """
    cv_analysis = cv_analysis or {}
    context = context or {}
    role = cv_analysis.get("target_role", job_direction)

    prompt = f"""Write the BEST realistic answer a strong candidate could give to
this interview question, as a model for someone preparing.

ROLE: {role} ({cv_analysis.get('seniority_level', 'Mid-level')})
CANDIDATE BACKGROUND (ground the answer in this so it is attainable):
- Key skills: {', '.join(cv_analysis.get('key_skills', [])) or 'N/A'}
- Strengths: {', '.join(cv_analysis.get('strengths', [])) or 'N/A'}

QUESTION:
{question}

Write in Markdown:
**Model answer:** a concise, natural spoken answer (use STAR for behavioural
questions; show reasoning/trade-offs for technical or problem-solving ones).
Keep it realistic — about 120-200 words, first person, with concrete specifics.

**Why it works:** 2-3 short bullets on what makes this answer strong.

Do not be generic or stuff buzzwords.{lang_directive(interview_lang)}"""

    try:
        return chat_text(prompt, system=_MODEL_SYSTEM, temperature=0.4)
    except Exception as err:
        return f"_Could not generate a model answer ({err})._"
