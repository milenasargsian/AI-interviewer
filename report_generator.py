"""Final interview verdict / report generation.

Produces a structured report object. Numeric results are computed locally so
a report is ALWAYS produced, and an AI narrative is layered on top.
"""

from datetime import datetime

from llm_client import chat_text, lang_directive

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


def _letter_grade(avg_10):
    """Map a 0-10 score to an academic-style letter grade."""
    if avg_10 >= 9.0:
        return "A+"
    if avg_10 >= 8.5:
        return "A"
    if avg_10 >= 8.0:
        return "A-"
    if avg_10 >= 7.5:
        return "B+"
    if avg_10 >= 7.0:
        return "B"
    if avg_10 >= 6.5:
        return "B-"
    if avg_10 >= 6.0:
        return "C+"
    if avg_10 >= 5.5:
        return "C"
    if avg_10 >= 5.0:
        return "C-"
    if avg_10 >= 4.0:
        return "D"
    return "F"


def generate_report(cv_analysis, questions, answers, scores, job_direction,
                    context=None, interview_lang="en"):
    """Build a structured report dict (consumed by report_export)."""
    context = context or {}

    valid_scores = [s.get("score", 0) for s in scores] if scores else []
    avg_10 = round(sum(valid_scores) / len(valid_scores), 1) if valid_scores else 0.0

    # Aggregate authenticity across the interview.
    auth_scores = [s.get("authenticity_score") for s in scores
                   if isinstance(s.get("authenticity_score"), (int, float))]
    ai_scores = [s.get("ai_likelihood") for s in scores
                 if isinstance(s.get("ai_likelihood"), (int, float))]
    avg_auth = round(sum(auth_scores) / len(auth_scores)) if auth_scores else None
    avg_ai = round(sum(ai_scores) / len(ai_scores)) if ai_scores else None

    if avg_ai is None:
        authenticity_overall = "N/A"
    elif avg_ai >= 65:
        authenticity_overall = "Likely AI-generated"
    elif avg_ai >= 45:
        authenticity_overall = "Possibly AI-assisted"
    elif avg_ai >= 25:
        authenticity_overall = "Mostly authentic"
    else:
        authenticity_overall = "Authentic"

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
            "authenticity_verdict": s.get("authenticity_verdict", "N/A"),
            "ai_likelihood": s.get("ai_likelihood"),
        })

    recommendation = _recommendation(avg_10)
    grade = _letter_grade(avg_10)

    # --- AI narrative (executive summary + verdict). Degrades gracefully. ---
    qa_summary = "\n".join(
        f"Q{p['index']} [{p['category']}] {p['question']}\n"
        f"Answer: {p['answer']}\nScore: {p['score']}/10 — {p['feedback']} "
        f"(authenticity: {p['authenticity_verdict']})\n"
        for p in per_question
    )

    narrative_prompt = f"""Write the narrative section of a final interview report.

Candidate: {cv_analysis.get('full_name', 'Candidate')}
Target role: {cv_analysis.get('target_role')}
Seniority: {cv_analysis.get('seniority_level', 'N/A')}
Job direction: {job_direction}
Industry / Company: {context.get('industry', 'N/A')} / {context.get('company', 'N/A')}
Overall interview score: {avg_10}/10  (Grade: {grade})
Preliminary recommendation: {recommendation}
Overall answer authenticity: {authenticity_overall} (avg AI-likelihood {avg_ai if avg_ai is not None else 'N/A'}/100)

Interview transcript with per-answer scores:
{qa_summary}

Write in Markdown with these sections:
## Executive Summary  (3-4 sentences)
## Key Strengths Demonstrated  (bullet list, evidence-based)
## Areas for Improvement  (bullet list, specific and actionable)
## Authenticity Assessment  (2-3 sentences on how genuine/personal the answers were, and any AI-generated concerns)
## Hiring Recommendation  (state the recommendation and grade, and justify it)
## Final Verdict  (one decisive paragraph)

Be concrete and reference the candidate's actual answers.{lang_directive(interview_lang)}"""

    try:
        narrative_md = chat_text(narrative_prompt, system=_SYSTEM, temperature=0.4)
    except Exception as err:
        narrative_md = (
            f"## Executive Summary\n\n_AI narrative unavailable ({err})._\n\n"
            f"The candidate achieved an overall score of {avg_10}/10 (grade {grade}), "
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
        "grade": grade,
        "recommendation": recommendation,
        "match_score": cv_analysis.get("match_score", 0),
        "authenticity_overall": authenticity_overall,
        "avg_authenticity": avg_auth,
        "avg_ai_likelihood": avg_ai,
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
        f"- **Grade:** {report['grade']}",
        f"- **Recommendation:** {report['recommendation']}",
        f"- **Answer authenticity:** {report['authenticity_overall']}"
        + (f" (avg AI-likelihood {report['avg_ai_likelihood']}/100)"
           if report.get("avg_ai_likelihood") is not None else ""),
        "",
        report["narrative_md"],
        "",
        "## Question-by-Question Breakdown",
    ]
    for p in report["per_question"]:
        crit = p.get("criteria", {})
        crit_str = ", ".join(f"{k.replace('_', ' ')}: {v}/10" for k, v in crit.items())
        auth = p.get("authenticity_verdict", "N/A")
        ai_like = p.get("ai_likelihood")
        auth_str = auth + (f" (AI-likelihood {ai_like}/100)" if ai_like is not None else "")
        lines += [
            "",
            f"### Q{p['index']} [{p['category']}] — {p['score']}/10",
            f"**Question:** {p['question']}",
            "",
            f"**Answer:** {p['answer']}",
            "",
            f"**Criteria:** {crit_str}" if crit_str else "",
            f"**Authenticity:** {auth_str}",
            f"**Strengths:** {'; '.join(p['strengths']) or '—'}",
            f"**Weaknesses:** {'; '.join(p['weaknesses']) or '—'}",
            f"**How to improve:** {'; '.join(p['improvements']) or '—'}",
            f"**Feedback:** {p['feedback']}",
        ]
    return "\n".join(l for l in lines if l is not None)
