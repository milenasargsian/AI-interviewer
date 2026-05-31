import json
import re

from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage


def score_answer(question: str, q_type: str, answer: str, cv_data: dict, api_key: str) -> dict:
    """
    Score a candidate's answer using Groq LLM.
    Covers: evaluation framework + content detection/classification.
    """
    llm = ChatGroq(
        model="llama-3.1-8b-instant",
        groq_api_key=api_key,
        temperature=0.2,
    )

    prompt = f"""You are an expert interviewer evaluating a candidate's answer.
Be fair, specific, and constructive. Base your evaluation on the candidate's level.

CONTEXT:
- Candidate: {cv_data.get('name', 'Candidate')}
- Level: {cv_data.get('seniority', 'mid')} {cv_data.get('job_role', 'professional')}
- Question type: {q_type}

QUESTION: {question}

CANDIDATE'S ANSWER: {answer if answer.strip() else "[No answer provided]"}

Return ONLY valid JSON — no markdown, no backticks:
{{
  "score": <integer from 1 to 10>,
  "reasoning": "2-3 sentence explanation of the score",
  "strengths": "What the candidate did well",
  "improvements": "Specific advice to improve this answer",
  "red_flags": ["concern1", "concern2"],
  "keywords_detected": ["keyword1", "keyword2"]
}}

Score guide: 1-3=poor, 4-5=below expectations, 6-7=meets expectations, 8-9=strong, 10=exceptional
"""

    result = llm.invoke([HumanMessage(content=prompt)])
    raw = result.content

    json_match = re.search(r"\{.*\}", raw, re.DOTALL)
    if not json_match:
        return {
            "score": 0,
            "reasoning": "Could not evaluate answer.",
            "strengths": "N/A",
            "improvements": "N/A",
            "red_flags": [],
            "keywords_detected": [],
        }

    score_data = json.loads(json_match.group())
    score_data["score"] = max(1, min(10, int(score_data.get("score", 5))))
    score_data.setdefault("red_flags", [])
    score_data.setdefault("keywords_detected", [])
    score_data.setdefault("strengths", "")
    score_data.setdefault("improvements", "")
    score_data.setdefault("reasoning", "")

    return score_data


def calculate_overall_score(scores: list) -> dict:
    """Calculate weighted overall score from all question scores."""
    if not scores:
        return {"overall": 0, "breakdown": {}}

    average = round(sum(s["score"] for s in scores) / len(scores), 1)

    if average >= 8.5:
        grade, label = "A", "Exceptional candidate"
    elif average >= 7.0:
        grade, label = "B", "Strong candidate"
    elif average >= 5.5:
        grade, label = "C", "Meets basic expectations"
    elif average >= 4.0:
        grade, label = "D", "Below expectations"
    else:
        grade, label = "F", "Does not meet requirements"

    all_red_flags = []
    for s in scores:
        all_red_flags.extend(s.get("red_flags", []))

    return {
        "overall": average,
        "grade": grade,
        "label": label,
        "total_questions": len(scores),
        "red_flags": list(set(all_red_flags)),
        "highest_score": max(s["score"] for s in scores),
        "lowest_score": min(s["score"] for s in scores),
    }
