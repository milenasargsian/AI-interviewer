from fpdf import FPDF
from datetime import datetime


class InterviewReport(FPDF):
    def header(self):
        self.set_font("Helvetica", "B", 14)
        self.set_text_color(40, 40, 40)
        self.cell(0, 10, "AI Interview Assessment Report", align="C", new_x="LMARGIN", new_y="NEXT")
        self.set_font("Helvetica", "", 9)
        self.set_text_color(120, 120, 120)
        self.cell(0, 6, f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}", align="C", new_x="LMARGIN", new_y="NEXT")
        self.ln(4)

    def footer(self):
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(150, 150, 150)
        self.cell(0, 10, f"Page {self.page_no()} | AI-generated report — human review recommended", align="C")


def generate_pdf_report(cv_data: dict, questions: list, answers: list, scores: list, overall: dict) -> bytes:
    """Generate a downloadable PDF interview report."""
    pdf = InterviewReport()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_margins(20, 20, 20)

    pdf.set_font("Helvetica", "B", 12)
    pdf.set_text_color(30, 30, 30)
    pdf.cell(0, 8, "Candidate Summary", new_x="LMARGIN", new_y="NEXT")
    pdf.set_draw_color(200, 200, 200)
    pdf.line(20, pdf.get_y(), 190, pdf.get_y())
    pdf.ln(3)

    pdf.set_font("Helvetica", "", 10)
    fields = [
        ("Name", cv_data.get("name", "N/A")),
        ("Role", cv_data.get("job_role", "N/A")),
        ("Seniority", cv_data.get("seniority", "N/A").capitalize()),
        ("Experience", f"{cv_data.get('years_experience', 0)} years"),
        ("Education", cv_data.get("education", "N/A")),
        ("Top Skills", ", ".join(cv_data.get("top_skills", []))),
    ]
    for label, value in fields:
        pdf.set_font("Helvetica", "B", 10)
        pdf.cell(45, 7, f"{label}:")
        pdf.set_font("Helvetica", "", 10)
        # Handle long text
        pdf.multi_cell(0, 7, str(value), new_x="LMARGIN", new_y="NEXT")

    pdf.ln(4)

    # --- Overall score ---
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 8, "Overall Assessment", new_x="LMARGIN", new_y="NEXT")
    pdf.line(20, pdf.get_y(), 190, pdf.get_y())
    pdf.ln(3)

    score_val = overall.get("overall", 0)
    grade = overall.get("grade", "N/A")
    label = overall.get("label", "")

    pdf.set_font("Helvetica", "B", 18)
    pdf.set_text_color(50, 100, 200)
    pdf.cell(0, 12, f"{score_val} / 10  —  Grade: {grade}", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "I", 10)
    pdf.set_text_color(80, 80, 80)
    pdf.cell(0, 6, label, new_x="LMARGIN", new_y="NEXT")
    pdf.set_text_color(30, 30, 30)
    pdf.ln(2)

    pdf.set_font("Helvetica", "", 10)
    pdf.cell(60, 6, f"Questions answered: {overall.get('total_questions', 0)}")
    pdf.cell(60, 6, f"Highest: {overall.get('highest_score', 0)}/10")
    pdf.cell(60, 6, f"Lowest: {overall.get('lowest_score', 0)}/10")
    pdf.ln(8)

    if overall.get("red_flags"):
        pdf.set_font("Helvetica", "B", 10)
        pdf.set_text_color(180, 50, 50)
        pdf.cell(0, 6, "Red Flags:", new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", "", 10)
        pdf.set_text_color(30, 30, 30)
        for flag in overall["red_flags"]:
            pdf.cell(0, 6, f"  • {flag}", new_x="LMARGIN", new_y="NEXT")
        pdf.ln(4)

    pdf.set_font("Helvetica", "B", 12)
    pdf.set_text_color(30, 30, 30)
    pdf.cell(0, 8, "Question-by-Question Breakdown", new_x="LMARGIN", new_y="NEXT")
    pdf.line(20, pdf.get_y(), 190, pdf.get_y())
    pdf.ln(3)

    for i, (ans, sc) in enumerate(zip(answers, scores)):
        q = ans.get("question", {})
        q_text = q.get("question", "N/A")
        q_type = q.get("type", "").upper()
        answer_text = ans.get("answer", "No answer")

        # Question header
        pdf.set_font("Helvetica", "B", 10)
        pdf.set_fill_color(240, 240, 245)
        pdf.cell(0, 7, f"Q{i+1} [{q_type}]  —  Score: {sc['score']}/10", fill=True, new_x="LMARGIN", new_y="NEXT")

        pdf.set_font("Helvetica", "", 10)
        pdf.multi_cell(0, 6, f"Question: {q_text}", new_x="LMARGIN", new_y="NEXT")
        pdf.ln(1)

        pdf.set_font("Helvetica", "I", 9)
        pdf.set_text_color(80, 80, 80)
        answer_preview = answer_text[:200] + ("..." if len(answer_text) > 200 else "")
        pdf.multi_cell(0, 5, f"Answer: {answer_preview}", new_x="LMARGIN", new_y="NEXT")

        pdf.set_font("Helvetica", "", 9)
        pdf.set_text_color(30, 30, 30)
        pdf.multi_cell(0, 5, f"Feedback: {sc.get('reasoning', '')}", new_x="LMARGIN", new_y="NEXT")

        if sc.get("improvements"):
            pdf.set_text_color(100, 80, 0)
            pdf.multi_cell(0, 5, f"To improve: {sc['improvements']}", new_x="LMARGIN", new_y="NEXT")
            pdf.set_text_color(30, 30, 30)

        pdf.ln(4)

    pdf.add_page()
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 8, "Responsible AI Transparency Notice", new_x="LMARGIN", new_y="NEXT")
    pdf.line(20, pdf.get_y(), 190, pdf.get_y())
    pdf.ln(3)
    pdf.set_font("Helvetica", "", 10)
    notices = [
        "This report was generated by an AI system and should be reviewed by a human recruiter before making hiring decisions.",
        "AI scoring may reflect biases present in the underlying language model's training data.",
        "No candidate data is stored beyond the current session.",
        "All scoring rationale is shown explicitly to enable human oversight and challenge.",
        "The system does not make hiring recommendations — it provides structured evaluation support only.",
        "Candidates should be informed that AI tools were used in their assessment process.",
    ]
    for notice in notices:
        pdf.multi_cell(0, 6, f"• {notice}", new_x="LMARGIN", new_y="NEXT")
        pdf.ln(1)

    return bytes(pdf.output())
