"""AI Interview Agent — Streamlit application.

Flow: Upload CV  →  CV Analysis  →  Interview (Q&A with voice + Next button)
      →  Final Verdict / Report (PDF / DOCX / Markdown download).

Run with:  streamlit run app.py
"""

import streamlit as st

from cv_parser import extract_text_from_pdf
from cv_analyzer import analyze_cv
from question_generator import generate_questions
from scorer import score_answer
from report_generator import generate_report, report_to_markdown
from stt import transcribe_audio_bytes

# ---------------------------------------------------------------------------
# Page setup & styling
# ---------------------------------------------------------------------------
st.set_page_config(page_title="AI Interview Agent", page_icon="🤖", layout="wide")

st.markdown("""
<style>
    .stApp { background: #f7f9fc; }
    .hero {
        background: linear-gradient(135deg, #1E88E5 0%, #1565C0 100%);
        padding: 2rem 2.5rem; border-radius: 16px; color: #fff;
        margin-bottom: 1.5rem; box-shadow: 0 8px 24px rgba(21,101,192,0.25);
    }
    .hero h1 { margin: 0; font-size: 2.1rem; font-weight: 800; }
    .hero p  { margin: .4rem 0 0; opacity: .9; font-size: 1.05rem; }
    .card {
        background: #fff; padding: 1.4rem 1.6rem; border-radius: 14px;
        box-shadow: 0 2px 12px rgba(0,0,0,0.06); margin-bottom: 1rem;
    }
    .question-box {
        background: #f0f7ff; padding: 1.4rem 1.6rem; border-radius: 12px;
        border-left: 5px solid #1E88E5; margin: .5rem 0 1rem; font-size: 1.12rem;
    }
    .answer-box {
        background: #f4faf4; padding: 1.1rem 1.4rem; border-radius: 12px;
        border-left: 5px solid #43A047; margin: .5rem 0; white-space: pre-wrap;
    }
    .badge {
        display:inline-block; padding:.18rem .7rem; border-radius:999px;
        font-size:.78rem; font-weight:700; margin-right:.4rem;
    }
    .badge-cat  { background:#E3F2FD; color:#1565C0; }
    .badge-diff { background:#FFF3E0; color:#E65100; }
    .step-pill {
        display:inline-block; padding:.3rem .9rem; border-radius:999px;
        font-weight:600; font-size:.85rem; margin-right:.4rem;
        background:#eef2f7; color:#607089;
    }
    .step-pill.active { background:#1E88E5; color:#fff; }
    .stProgress > div > div > div { background-color:#1E88E5; }
</style>
""", unsafe_allow_html=True)

STAGES = [("upload", "1 · Upload"), ("analysis", "2 · Analysis"),
          ("interview", "3 · Interview"), ("report", "4 · Verdict")]


def init_state():
    defaults = {
        "stage": "upload", "cv_text": "", "cv_analysis": None,
        "questions": [], "current_question_idx": 0,
        "answers": [], "scores": [], "job_direction": "",
        "context": {}, "num_questions": 6, "report": None,
    }
    for k, v in defaults.items():
        st.session_state.setdefault(k, v)


def stepper():
    pills = ""
    for key, label in STAGES:
        active = "active" if st.session_state.stage == key else ""
        pills += f'<span class="step-pill {active}">{label}</span>'
    st.markdown(pills, unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Stage 1 — Upload
# ---------------------------------------------------------------------------
def upload_stage():
    st.markdown("### 📄 Step 1 — Upload CV & set the interview context")

    with st.container():
        col1, col2 = st.columns(2)
        with col1:
            job_direction = st.text_input(
                "🎯 Job direction *",
                value=st.session_state.job_direction,
                placeholder="e.g. Backend Software Engineer, Data Scientist")
            industry = st.text_input(
                "🏭 Target industry",
                value=st.session_state.context.get("industry", ""),
                placeholder="e.g. Fintech, Healthcare, E-commerce")
        with col2:
            company_type = st.selectbox(
                "🏢 Company type",
                ["Not specified", "Startup", "Scale-up", "Enterprise / Corporate",
                 "Big Tech (FAANG-style)", "Consultancy / Agency", "Public sector / NGO"],
                index=0)
            company = st.text_input(
                "⭐ Specific company (optional)",
                value=st.session_state.context.get("company", ""),
                placeholder="e.g. Google, Stripe, a local bank")

        c1, c2 = st.columns(2)
        with c1:
            interview_focus = st.selectbox(
                "🧭 Interview focus",
                ["Balanced (technical + behavioural)", "Mostly technical",
                 "Mostly behavioural", "System design / scenarios",
                 "Leadership / management"])
        with c2:
            num_questions = st.slider("❓ Number of questions", 4, 10, 6)

        uploaded_file = st.file_uploader("Upload your CV (PDF)", type=["pdf"])

    # Figure out what (if anything) is still missing, for a clear message.
    missing = []
    if not job_direction.strip():
        missing.append("a job direction")
    if uploaded_file is None:
        missing.append("a CV (PDF)")

    # Button is always clickable; we validate on click so it never feels stuck.
    if st.button("🚀 Analyze CV", type="primary"):
        if missing:
            st.warning("Please provide " + " and ".join(missing) + " before analyzing.")
        else:
            try:
                with st.spinner("Extracting text from CV…"):
                    cv_text = extract_text_from_pdf(uploaded_file)
                if not cv_text.strip():
                    st.error("Could not read any text from this PDF. "
                             "It may be a scanned image — please upload a text-based PDF.")
                    return
                st.session_state.cv_text = cv_text
                st.session_state.job_direction = job_direction.strip()
                st.session_state.num_questions = num_questions
                st.session_state.context = {
                    "industry": industry.strip(),
                    "company_type": company_type,
                    "company": company.strip(),
                    "interview_focus": interview_focus,
                }
                with st.spinner("Analyzing CV with AI…"):
                    st.session_state.cv_analysis = analyze_cv(cv_text, job_direction.strip())
                st.session_state.stage = "analysis"
                st.rerun()
            except Exception as err:
                st.error(f"Something went wrong: {err}")

    if missing:
        st.caption("Still needed before analysis: " + " and ".join(missing) + ".")
    else:
        st.caption("Ready — click **Analyze CV** to continue.")


# ---------------------------------------------------------------------------
# Stage 2 — Analysis
# ---------------------------------------------------------------------------
def analysis_stage():
    a = st.session_state.cv_analysis
    st.markdown("### 📊 Step 2 — CV Analysis")

    top = st.columns([2, 1, 1])
    with top[0]:
        st.markdown(f"<div class='card'><h3 style='margin:0'>👤 {a.get('full_name','Candidate')}</h3>"
                    f"<p style='margin:.3rem 0 0;color:#555'>{a.get('summary','')}</p></div>",
                    unsafe_allow_html=True)
    with top[1]:
        st.metric("🎯 Target role", a.get("target_role", "N/A"))
        st.caption(f"Seniority: {a.get('seniority_level','N/A')} · "
                   f"~{a.get('years_of_experience',0)} yrs")
    with top[2]:
        st.metric("CV–Role match", f"{a.get('match_score',0)}%")
        st.progress(min(100, int(a.get("match_score", 0))) / 100)

    if a.get("match_rationale"):
        st.info(f"**Why this match score:** {a['match_rationale']}")

    cols = st.columns(3)
    with cols[0]:
        st.markdown("#### 🛠 Key skills")
        for s in a.get("key_skills", []):
            st.markdown(f"- {s}")
    with cols[1]:
        st.markdown("#### 💪 Strengths")
        for s in a.get("strengths", []):
            st.markdown(f"- {s}")
    with cols[2]:
        st.markdown("#### ⚠️ Gaps")
        for g in a.get("gaps", []):
            st.markdown(f"- {g}")

    st.divider()
    cols = st.columns([1, 1, 4])
    with cols[0]:
        if st.button("⬅️ Back"):
            st.session_state.stage = "upload"
            st.rerun()
    with cols[1]:
        if st.button("➡️ Start interview", type="primary"):
            with st.spinner("Generating tailored interview questions…"):
                st.session_state.questions = generate_questions(
                    a, st.session_state.job_direction,
                    context=st.session_state.context,
                    num_questions=st.session_state.num_questions)
            st.session_state.current_question_idx = 0
            st.session_state.answers = []
            st.session_state.scores = []
            st.session_state.stage = "interview"
            st.rerun()


# ---------------------------------------------------------------------------
# Stage 3 — Interview
# ---------------------------------------------------------------------------
def interview_stage():
    questions = st.session_state.questions
    idx = st.session_state.current_question_idx
    total = len(questions)

    if idx >= total:
        st.session_state.stage = "report"
        st.rerun()
        return

    st.markdown("### 💬 Step 3 — Interview")
    st.progress(idx / total)
    st.caption(f"Question {idx + 1} of {total}")

    q = questions[idx]
    st.markdown(
        f"<div class='question-box'>"
        f"<span class='badge badge-cat'>{q.get('category','')}</span>"
        f"<span class='badge badge-diff'>{q.get('difficulty','')}</span><br><br>"
        f"{q.get('question','')}</div>", unsafe_allow_html=True)
    if q.get("what_it_assesses"):
        st.caption(f"💡 Assesses: {q['what_it_assesses']}")

    answered = idx < len(st.session_state.answers)

    if not answered:
        _answer_panel(idx, q)
    else:
        _evaluation_panel(idx, q, total)

    _previous_answers(idx)


def _answer_panel(idx, q):
    answer_key = f"answer_{idx}"

    # --- Voice answer (browser recording -> Whisper) ---
    if hasattr(st, "audio_input"):
        audio = st.audio_input("🎤 Record a voice answer (optional)", key=f"audio_{idx}")
        if audio is not None:
            if st.button("📝 Transcribe voice → answer", key=f"transcribe_{idx}"):
                with st.spinner("Transcribing your answer…"):
                    text, err = transcribe_audio_bytes(audio.getvalue(),
                                                        filename=f"answer_{idx}.wav")
                if err:
                    st.error(err)
                else:
                    st.session_state[answer_key] = text
                    st.success("Transcribed. Review or edit your answer below, then submit.")
                    st.rerun()
    else:
        st.caption("ℹ️ Voice input needs Streamlit ≥ 1.31. Type your answer below.")

    st.text_area("✍️ Your answer", key=answer_key, height=170,
                 placeholder="Type your answer, or record and transcribe it above.")

    if st.button("✅ Submit answer", type="primary", key=f"submit_{idx}"):
        final_answer = st.session_state.get(answer_key, "").strip()
        if not final_answer:
            st.warning("Please provide an answer (typed or transcribed) before submitting.")
            return
        with st.spinner("Evaluating your answer…"):
            score = score_answer(
                q.get("question", ""), final_answer,
                st.session_state.job_direction,
                cv_analysis=st.session_state.cv_analysis,
                context=st.session_state.context)
        st.session_state.answers.append(final_answer)
        st.session_state.scores.append(score)
        st.rerun()  # stays on this question, now showing the evaluation


def _evaluation_panel(idx, q, total):
    answer = st.session_state.answers[idx]
    score = st.session_state.scores[idx]

    st.markdown("#### 🗣 Your answer")
    st.markdown(f"<div class='answer-box'>{answer}</div>", unsafe_allow_html=True)

    st.markdown(f"#### 📋 Evaluation — **{score.get('score',0)}/10**")
    crit = score.get("criteria", {})
    if crit:
        cc = st.columns(len(crit))
        for col, (name, val) in zip(cc, crit.items()):
            col.metric(name.replace("_", " ").title(), f"{val}/10")

    cols = st.columns(3)
    with cols[0]:
        st.markdown("**✅ Strengths**")
        for s in score.get("strengths", []) or ["—"]:
            st.markdown(f"- {s}")
    with cols[1]:
        st.markdown("**⚠️ Weaknesses**")
        for w in score.get("weaknesses", []) or ["—"]:
            st.markdown(f"- {w}")
    with cols[2]:
        st.markdown("**🚀 How to improve**")
        for i in score.get("improvements", []) or ["—"]:
            st.markdown(f"- {i}")

    if score.get("feedback"):
        st.info(score["feedback"])

    st.divider()
    is_last = idx == total - 1
    if is_last:
        if st.button("🏁 Finish & generate report", type="primary", key=f"finish_{idx}"):
            st.session_state.current_question_idx = idx + 1
            st.session_state.report = None
            st.session_state.stage = "report"
            st.rerun()
    else:
        st.caption("Read the answer and feedback above. When ready, continue.")
        if st.button("➡️ Next question", type="primary", key=f"next_{idx}"):
            st.session_state.current_question_idx = idx + 1
            st.rerun()


def _previous_answers(idx):
    if idx == 0:
        return
    st.divider()
    st.markdown("#### 📝 Previous questions")
    for i in range(idx):
        q = st.session_state.questions[i]
        sc = st.session_state.scores[i] if i < len(st.session_state.scores) else {}
        with st.expander(f"Q{i+1} [{q.get('category','')}] — {sc.get('score',0)}/10"):
            st.markdown(f"**Q:** {q.get('question','')}")
            st.markdown(f"**A:** {st.session_state.answers[i]}")
            if sc.get("feedback"):
                st.caption(sc["feedback"])


# ---------------------------------------------------------------------------
# Stage 4 — Report / Verdict
# ---------------------------------------------------------------------------
def report_stage():
    st.markdown("### 📈 Step 4 — Final Verdict & Report")

    if not st.session_state.answers:
        st.warning("No answers were recorded, so there is nothing to evaluate.")
        if st.button("⬅️ Back to interview"):
            st.session_state.stage = "interview"
            st.rerun()
        return

    if st.session_state.report is None:
        with st.spinner("Compiling the final verdict…"):
            st.session_state.report = generate_report(
                st.session_state.cv_analysis,
                st.session_state.questions,
                st.session_state.answers,
                st.session_state.scores,
                st.session_state.job_direction,
                context=st.session_state.context)

    report = st.session_state.report

    top = st.columns(3)
    top[0].metric("Overall score", f"{report['overall_score']}/10")
    top[1].metric("Recommendation", report["recommendation"])
    top[2].metric("CV–Role match", f"{report['match_score']}%")

    st.divider()
    md = report_to_markdown(report)
    st.markdown(md)

    st.divider()
    st.markdown("#### 📥 Download report")
    _download_buttons(report, md)

    if st.button("🔄 Start a new interview"):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()


def _download_buttons(report, md):
    from report_export import build_pdf, build_docx, filename

    cols = st.columns(3)

    # PDF
    with cols[0]:
        try:
            pdf_bytes = build_pdf(report)
            st.download_button("⬇️ PDF", data=pdf_bytes,
                               file_name=filename(report, "pdf"),
                               mime="application/pdf", use_container_width=True)
        except Exception as err:
            st.button("PDF unavailable", disabled=True, use_container_width=True)
            st.caption(f"PDF export needs `reportlab` ({err})")

    # DOCX
    with cols[1]:
        try:
            docx_bytes = build_docx(report)
            st.download_button(
                "⬇️ Word (DOCX)", data=docx_bytes,
                file_name=filename(report, "docx"),
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                use_container_width=True)
        except Exception as err:
            st.button("DOCX unavailable", disabled=True, use_container_width=True)
            st.caption(f"DOCX export needs `python-docx` ({err})")

    # Markdown
    with cols[2]:
        st.download_button("⬇️ Markdown", data=md.encode("utf-8"),
                           file_name=filename(report, "md"),
                           mime="text/markdown", use_container_width=True)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    init_state()

    st.markdown(
        "<div class='hero'><h1>🤖 AI Interview Agent</h1>"
        "<p>CV-based intelligent interviewing — analysis, tailored questions, "
        "transparent scoring and a downloadable verdict.</p></div>",
        unsafe_allow_html=True)
    stepper()

    with st.sidebar:
        st.header("📋 Session")
        st.write(f"**Stage:** {st.session_state.stage}")
        if st.session_state.cv_analysis:
            st.write(f"**Candidate:** {st.session_state.cv_analysis.get('full_name','—')}")
            st.write(f"**Role:** {st.session_state.cv_analysis.get('target_role','—')}")
        st.divider()
        if st.button("🔄 Reset / Start over"):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()

    stage = st.session_state.stage
    if stage == "upload":
        upload_stage()
    elif stage == "analysis":
        analysis_stage()
    elif stage == "interview":
        interview_stage()
    elif stage == "report":
        report_stage()


if __name__ == "__main__":
    main()
