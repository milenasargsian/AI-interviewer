"""Final interview verdict / report generation.

Produces a structured report object. Numeric results are computed locally so
a report is ALWAYS produced, and an AI narrative is layered on top.
"""

from datetime import datetime

from llm_client import chat_text

_SYSTEM = (
    "You are a senior hiring manager writing the final evaluation of an "
    "interview. You are objective, specific and decisive, and you ground "
    "every statement in the candidate's actual answers."
)


def _recommendation(avg_10):
    if avg_10 >= 8.5:
        return "Strong Hire"
    if avg_10 >= 7.0:
        return "Hire"
    if avg_10 >= 5.5:
        return "Lean Hire"
    if avg_10 >= 4.0:
        return "Lean No-Hire"
    return "No Hire"


def generate_report(cv_analysis, questions, answers, scores, job_direction, context=None):
    """Build a structured report dict (consumed by report_export)."""
    context = context or {}

    valid_scores = [s.get("score", 0) for s in scores] if scores else []
    avg_10 = round(sum(valid_scores) / len(valid_scores), 1) if valid_scores else 0.0

    per_question = []
    for i in range(len(answers)):
        q = questions[i] if i < len(questions) else {}
        q_text = q.get("question", "") if isinstance(q, dict) else str(q)
        s = scores[i] if i < len(scores) else {}
        per_question.append({
            "index": i + 1,
            "category": q.get("category", "") if isinstance(q, dict) else "",
            "question": q_text,
            "answer": answers[i],
            "score": s.get("score", 0),
            "criteria": s.get("criteria", {}),
            "strengths": s.get("strengths", []),
            "weaknesses": s.get("weaknesses", []),
            "improvements": s.get("improvements", []),
            "feedback": s.get("feedback", ""),
        })

    recommendation = _recommendation(avg_10)

    # --- AI narrative (executive summary + verdict). Degrades gracefully. ---
    qa_summary = "\n".join(
        f"Q{p['index']} [{p['category']}] {p['question']}\n"
        f"Answer: {p['answer']}\nScore: {p['score']}/10 — {p['feedback']}\n"
        for p in per_question
    )

    narrative_prompt = f"""Write the narrative section of a final interview report.

Candidate: {cv_analysis.get('full_name', 'Candidate')}
Target role: {cv_analysis.get('target_role')}
Seniority: {cv_analysis.get('seniority_level', 'N/A')}
Job direction: {job_direction}
Industry / Company: {context.get('industry', 'N/A')} / {context.get('company', 'N/A')}
Overall interview score: {avg_10}/10
Preliminary recommendation: {recommendation}

Interview transcript with per-answer scores:
{qa_summary}

Write in Markdown with these sections:
## Executive Summary  (3-4 sentences)
## Key Strengths Demonstrated  (bullet list, evidence-based)
## Areas for Improvement  (bullet list, specific and actionable)
## Hiring Recommendation  (state the recommendation and justify it)
## Final Verdict  (one decisive paragraph)

Be concrete and reference the candidate's actual answers."""

    try:
        narrative_md = chat_text(narrative_prompt, system=_SYSTEM, temperature=0.4)
    except Exception as err:
        narrative_md = (
            f"## Executive Summary\n\n_AI narrative unavailable ({err})._\n\n"
            f"The candidate achieved an overall score of {avg_10}/10, "
            f"corresponding to a recommendation of **{recommendation}**."
        )

    return {
        "candidate": cv_analysis.get("full_name", "Candidate"),
        "role": cv_analysis.get("target_role", job_direction),
        "seniority": cv_analysis.get("seniority_level", "N/A"),
        "job_direction": job_direction,
        "industry": context.get("industry", "Not specified"),
        "company_type": context.get("company_type", "Not specified"),
        "company": context.get("company", "Not specified"),
        "overall_score": avg_10,
        "recommendation": recommendation,
        "match_score": cv_analysis.get("match_score", 0),
        "narrative_md": narrative_md,
        "per_question": per_question,
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
    }


def report_to_markdown(report):
    """Render the full report as Markdown (used for on-screen + .md export)."""
    lines = [
        f"# Interview Report — {report['candidate']}",
        "",
        f"**Date:** {report['generated_at']}  ",
        f"**Target role:** {report['role']} ({report['seniority']})  ",
        f"**Job direction:** {report['job_direction']}  ",
        f"**Industry / Company type / Company:** {report['industry']} / "
        f"{report['company_type']} / {report['company']}  ",
        f"**CV–Role match:** {report['match_score']}%  ",
        "",
        f"## Overall Result",
        f"- **Overall interview score:** {report['overall_score']}/10",
        f"- **Recommendation:** {report['recommendation']}",
        "",
        report["narrative_md"],
        "",
        "## Question-by-Question Breakdown",
    ]
    for p in report["per_question"]:
        crit = p.get("criteria", {})
        crit_str = ", ".join(f"{k.replace('_', ' ')}: {v}/10" for k, v in crit.items())
        lines += [
            "",
            f"### Q{p['index']} [{p['category']}] — {p['score']}/10",
            f"**Question:** {p['question']}",
            "",
            f"**Answer:** {p['answer']}",
            "",
            f"**Criteria:** {crit_str}" if crit_str else "",
            f"**Strengths:** {'; '.join(p['strengths']) or '—'}",
            f"**Weaknesses:** {'; '.join(p['weaknesses']) or '—'}",
            f"**How to improve:** {'; '.join(p['improvements']) or '—'}",
            f"**Feedback:** {p['feedback']}",
        ]
    return "\n".join(l for l in lines if l is not None)
