import os
import streamlit as st
from dotenv import load_dotenv

load_dotenv()


st.set_page_config(
    page_title="AI Interview Agent",
    page_icon="🎙️",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
    .metric-card {
        background: #f8f9fa;
        border-radius: 10px;
        padding: 16px;
        border-left: 4px solid #4F8BF9;
        margin-bottom: 10px;
    }
    .score-badge {
        display: inline-block;
        padding: 4px 12px;
        border-radius: 20px;
        font-weight: bold;
        font-size: 14px;
    }
    .score-high { background: #d4edda; color: #155724; }
    .score-mid  { background: #fff3cd; color: #856404; }
    .score-low  { background: #f8d7da; color: #721c24; }
    .question-box {
        background: #1a2a3a;
        border-left: 5px solid #4F8BF9;
        padding: 16px 20px;
        border-radius: 8px;
        margin: 10px 0;
    }
    .question-box h4 {
        color: #e8f4fd !important;
        margin: 0;
        font-size: 16px;
        line-height: 1.6;
    }
    .stProgress > div > div { background-color: #4F8BF9; }
</style>
""", unsafe_allow_html=True)


GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "")
GROQ_API_KEY   = os.getenv("GROQ_API_KEY", "")


def init_session():
    defaults = {
        "cv_text":      None,
        "cv_data":      None,
        "questions":    None,
        "current_q":    0,
        "scores":       [],
        "answers":      [],
        "stage":        "upload",   # upload | analyse | interview | report
        "transcript":   "",
        "audio_key":    0,          # forces recorder widget reset
    }
    for key, val in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = val

init_session()


def score_class(score: int) -> str:
    if score >= 7:
        return "score-high"
    elif score >= 5:
        return "score-mid"
    return "score-low"


with st.sidebar:
    st.title("🎙️ AI Interview Agent")
    st.caption("Powered by Gemini + LangChain + Groq Whisper")

    st.divider()

    # API key inputs (fallback if .env not set)
    if not GROQ_API_KEY:  # Groq used for LLM + audio
        GROQ_API_KEY = st.text_input("Groq API Key (LLM + Audio)", key="groq_sidebar", type="password",
                                        help="Get free key at aistudio.google.com")
    if not GROQ_API_KEY:
        GROQ_API_KEY = st.text_input("Groq API Key (for audio transcription)", type="password",
                                      help="Get free key at console.groq.com")

    st.divider()

    stages = ["📄 Upload", "🔍 Analyse", "🎙️ Interview", "📊 Report"]
    stage_map = {"upload": 0, "analyse": 1, "interview": 2, "report": 3}
    current_stage_idx = stage_map.get(st.session_state.stage, 0)

    st.markdown("**Progress**")
    for i, s in enumerate(stages):
        if i < current_stage_idx:
            st.markdown(f"✅ {s}")
        elif i == current_stage_idx:
            st.markdown(f"▶️ **{s}**")
        else:
            st.markdown(f"⬜ {s}")

    st.divider()

    if st.button("🔄 Start over", use_container_width=True):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()

    st.divider()
    st.caption("Course topics: Prompt Engineering · LangChain · RAG · "
               "Content Classification · Evaluation · Responsible AI")


if st.session_state.stage == "upload":
    st.title("📄 Upload your CV")
    st.markdown("Upload your CV in PDF format. The system will analyse it and generate "
                "personalised interview questions based on your experience and skills.")

    col1, col2 = st.columns([2, 1])
    with col1:
        uploaded_file = st.file_uploader("Choose a PDF file", type=["pdf"],
                                          label_visibility="collapsed")

    if uploaded_file:
        st.success(f"✅ File uploaded: **{uploaded_file.name}** "
                   f"({round(uploaded_file.size / 1024, 1)} KB)")

        if not GROQ_API_KEY:  # Groq used for LLM + audio
            st.error("Please enter your Groq API key in the sidebar.")
        elif not GROQ_API_KEY:
            st.warning("Enter your Groq API key in the sidebar to enable audio transcription.")
        else:
            if st.button("🚀 Analyse CV & Start Interview", type="primary", use_container_width=True):
                with st.spinner("Parsing your CV..."):
                    try:
                        from cv_parser import extract_cv_text
                        cv_text = extract_cv_text(uploaded_file)
                        st.session_state.cv_text = cv_text
                    except Exception as e:
                        st.error(f"CV parsing failed: {e}")
                        st.stop()

                st.session_state.stage = "analyse"
                st.rerun()


elif st.session_state.stage == "analyse":
    st.title("🔍 Analysing your CV...")

    progress = st.progress(0, text="Starting analysis...")

    try:
        from cv_analyzer import analyze_cv
        from question_generator import generate_questions

        progress.progress(20, text="Building RAG index from your CV...")
        cv_data = analyze_cv(st.session_state.cv_text, GROQ_API_KEY)
        st.session_state.cv_data = cv_data

        progress.progress(60, text="Generating personalised questions...")
        questions = generate_questions(cv_data, GROQ_API_KEY)
        st.session_state.questions = questions

        progress.progress(100, text="Done!")

        # Show analysis summary
        st.success("✅ CV analysed successfully!")

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Name", cv_data.get("name", "N/A"))
        col2.metric("Role", cv_data.get("job_role", "N/A"))
        col3.metric("Level", cv_data.get("seniority", "N/A").capitalize())
        col4.metric("Experience", f"{cv_data.get('years_experience', 0)} yrs")

        with st.expander("📋 Full CV analysis", expanded=True):
            c1, c2 = st.columns(2)
            with c1:
                st.markdown("**Top skills**")
                for skill in cv_data.get("top_skills", []):
                    st.markdown(f"• {skill}")
                st.markdown("**Education**")
                st.write(cv_data.get("education", "N/A"))
            with c2:
                st.markdown("**Notable projects**")
                for proj in cv_data.get("notable_projects", []):
                    st.markdown(f"• {proj}")
                st.markdown("**Flagged skill gaps**")
                gaps = cv_data.get("skill_gaps", [])
                if gaps:
                    for gap in gaps:
                        st.markdown(f"• {gap}")
                else:
                    st.write("None identified")

        st.markdown(f"**{len(questions)} personalised questions generated** ✅")

        if st.button("▶️ Start Interview", type="primary", use_container_width=True):
            st.session_state.stage = "interview"
            st.session_state.current_q = 0
            st.rerun()

    except Exception as e:
        st.error(f"Analysis failed: {e}")
        st.exception(e)
        if st.button("⬅️ Go back"):
            st.session_state.stage = "upload"
            st.rerun()


elif st.session_state.stage == "interview":
    from audio_recorder_streamlit import audio_recorder
    from stt import transcribe_audio
    from scorer import score_answer

    questions = st.session_state.questions
    idx       = st.session_state.current_q
    total     = len(questions)
    cv_data   = st.session_state.cv_data

    # Header
    st.title("🎙️ Interview in Progress")
    col_name, col_role, col_prog = st.columns([2, 2, 3])
    col_name.markdown(f"**Candidate:** {cv_data.get('name', 'N/A')}")
    col_role.markdown(f"**Role:** {cv_data.get('job_role', 'N/A')} ({cv_data.get('seniority','').capitalize()})")
    col_prog.progress((idx) / total, text=f"Question {idx + 1} of {total}")

    st.divider()

    if idx < total:
        q = questions[idx]

        # Question display
        q_type  = q.get("type", "general").upper()
        q_topic = q.get("topic", "")
        q_text  = q.get("question", "")
        q_diff  = q.get("difficulty", "medium")

        col_badge1, col_badge2, col_badge3 = st.columns([1, 1, 4])
        col_badge1.markdown(f"**Type:** `{q_type}`")
        col_badge2.markdown(f"**Difficulty:** `{q_diff}`")
        if q_topic:
            col_badge3.markdown(f"**Topic:** {q_topic}")

        st.markdown(f"""
        <div class="question-box">
            <h4>Q{idx + 1}. {q_text}</h4>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("---")

        # Previous scores mini-view
        if st.session_state.scores:
            with st.expander(f"📊 Scores so far ({len(st.session_state.scores)} answered)"):
                for i, sc in enumerate(st.session_state.scores):
                    s = sc["score"]
                    css = score_class(s)
                    st.markdown(
                        f'Q{i+1}: <span class="score-badge {css}">{s}/10</span> — {sc.get("reasoning","")[:80]}...',
                        unsafe_allow_html=True
                    )

        # Audio recorder
        st.markdown("### 🎤 Record your answer")
        st.caption("Click the microphone to start recording. Click again to stop. "
                   "A 3-second pause will also stop recording automatically.")

        audio_bytes = audio_recorder(
            pause_threshold=3.0,
            sample_rate=16000,
            key=f"recorder_{idx}_{st.session_state.audio_key}",
        )

        # Text fallback
        st.markdown("**Or type your answer below:**")
        typed_answer = st.text_area("Type your answer here (optional fallback)",
                                     label_visibility="collapsed",
                                     height=120,
                                     key=f"text_answer_{idx}")

        col_submit, col_skip = st.columns([3, 1])

        with col_submit:
            submit_clicked = st.button("✅ Submit answer", type="primary", use_container_width=True)

        with col_skip:
            skip_clicked = st.button("⏭️ Skip", use_container_width=True)

        if submit_clicked or skip_clicked:
            answer_text = ""

            if skip_clicked:
                # Skipped questions always get score 0 — no LLM call
                answer_text = "[Skipped]"
                score_result = {
                    "score": 0,
                    "reasoning": "Question was skipped — no answer provided.",
                    "strengths": "N/A",
                    "improvements": "Make sure to attempt every question in a real interview.",
                    "red_flags": ["Question skipped"],
                    "keywords_detected": [],
                }
                st.session_state.answers.append({"question": q, "answer": answer_text})
                st.session_state.scores.append(score_result)
                st.warning("⏭️ Question skipped — scored 0/10")
                st.session_state.current_q += 1
                st.session_state.audio_key += 1
                if st.session_state.current_q >= total:
                    st.session_state.stage = "report"
                st.rerun()
            else:
                # Try audio first, then text fallback
                if audio_bytes and len(audio_bytes) > 1000:
                    if not GROQ_API_KEY:
                        st.error("Groq API key required for audio. Please type your answer instead.")
                        st.stop()
                    with st.spinner("🔄 Transcribing audio..."):
                        try:
                            answer_text = transcribe_audio(audio_bytes, GROQ_API_KEY)
                        except Exception as e:
                            st.warning(f"Audio transcription failed: {e}. Using typed answer.")
                            answer_text = typed_answer

                if not answer_text and typed_answer.strip():
                    answer_text = typed_answer.strip()

                if not answer_text:
                    st.warning("Please record or type an answer before submitting.")
                    st.stop()

            with st.spinner("🤖 Evaluating your answer..."):
                try:
                    score_result = score_answer(
                        question=q_text,
                        q_type=q.get("type", "general"),
                        answer=answer_text,
                        cv_data=cv_data,
                        api_key=GROQ_API_KEY,
                    )
                except Exception as e:
                    st.error(f"Scoring failed: {e}")
                    st.stop()

            # Save
            st.session_state.answers.append({"question": q, "answer": answer_text})
            st.session_state.scores.append(score_result)

            # Show instant feedback
            score_val = score_result["score"]
            css = score_class(score_val)
            st.markdown(f"""
            **Your answer:** _{answer_text[:200]}{'...' if len(answer_text) > 200 else ''}_

            Score: <span class="score-badge {css}">{score_val}/10</span>
            """, unsafe_allow_html=True)
            st.write("**Feedback:**", score_result.get("reasoning", ""))
            st.write("✅ **Strengths:**", score_result.get("strengths", ""))
            st.write("📈 **To improve:**", score_result.get("improvements", ""))
            if score_result.get("red_flags"):
                st.warning("⚠️ **Concerns noted:** " + ", ".join(score_result["red_flags"]))

            st.session_state.current_q += 1
            st.session_state.audio_key += 1  # reset recorder

            if st.session_state.current_q >= total:
                st.session_state.stage = "report"

            st.rerun()

    else:
        st.session_state.stage = "report"
        st.rerun()


elif st.session_state.stage == "report":
    from scorer import calculate_overall_score
    from report_generator import generate_pdf_report

    st.title("📊 Interview Complete — Full Report")

    scores   = st.session_state.scores
    answers  = st.session_state.answers
    cv_data  = st.session_state.cv_data
    questions = st.session_state.questions

    overall = calculate_overall_score(scores)

    score_val = overall["overall"]
    css = score_class(int(score_val))

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Overall Score", f"{score_val} / 10")
    col2.metric("Grade", overall["grade"])
    col3.metric("Highest Answer", f"{overall['highest_score']}/10")
    col4.metric("Lowest Answer",  f"{overall['lowest_score']}/10")

    st.markdown(f"""
    <div class="metric-card">
        <b>Verdict:</b>
        <span class="score-badge {css}">{overall['label']}</span>
        for <b>{cv_data.get('seniority','').capitalize()} {cv_data.get('job_role','')}</b>
    </div>
    """, unsafe_allow_html=True)

    if overall.get("red_flags"):
        st.error("⚠️ **Recurring concerns:** " + " · ".join(overall["red_flags"]))

    st.divider()

    st.subheader("📈 Score progression")
    chart_data = {f"Q{i+1}": sc["score"] for i, sc in enumerate(scores)}
    st.bar_chart(chart_data)

    st.divider()

    st.subheader("🔍 Question-by-question breakdown")

    for i, (ans, sc) in enumerate(zip(answers, scores)):
        q     = ans.get("question", {})
        s_val = sc["score"]
        css   = score_class(s_val)

        with st.expander(
            f"Q{i+1} [{q.get('type','').upper()}] — "
            f"{q.get('question','')[:70]}...  |  Score: {s_val}/10",
            expanded=False,
        ):
            st.markdown(f"**Full question:** {q.get('question','')}")
            st.markdown(f"**Your answer:** _{ans.get('answer', 'N/A')}_")
            st.markdown(f"**Score:** <span class='score-badge {css}'>{s_val}/10</span>",
                        unsafe_allow_html=True)
            st.markdown(f"**Reasoning:** {sc.get('reasoning','')}")
            col_a, col_b = st.columns(2)
            col_a.markdown(f"✅ **Strengths:** {sc.get('strengths','')}")
            col_b.markdown(f"📈 **To improve:** {sc.get('improvements','')}")
            if sc.get("red_flags"):
                st.warning("Concerns: " + ", ".join(sc["red_flags"]))
            if sc.get("keywords_detected"):
                st.caption("Keywords detected: " + ", ".join(sc["keywords_detected"]))

    st.divider()

    with st.expander("⚖️ Responsible AI & Transparency"):
        st.markdown("""
        **Bias & Fairness**
        - LLM scoring may reflect biases from training data — human review is recommended before any hiring decision.
        - Scores are relative to the candidate's stated seniority level, not an absolute standard.

        **Transparency**
        - All scoring rationale is shown explicitly so decisions can be challenged.
        - Question types and difficulty are labeled for candidate awareness.

        **Data Privacy**
        - No CV data or answers are stored beyond this browser session.
        - No data is sent to third parties beyond the AI API providers (Google, Groq).

        **Human Oversight**
        - This tool provides evaluation *support* only — it does not make hiring decisions.
        - Candidates should be informed when AI tools are used in their assessment.

        **Limitations**
        - Audio transcription accuracy depends on audio quality and accent.
        - The system cannot verify truthfulness of stated experience.
        """)

    st.divider()

    st.subheader("⬇️ Download Report")
    try:
        pdf_bytes = generate_pdf_report(cv_data, questions, answers, scores, overall)
        st.download_button(
            label="📥 Download PDF Report",
            data=pdf_bytes,
            file_name=f"interview_report_{cv_data.get('name','candidate').replace(' ','_')}.pdf",
            mime="application/pdf",
            type="primary",
            use_container_width=True,
        )
    except Exception as e:
        st.warning(f"PDF generation failed: {e}. Your results are still visible above.")

    if st.button("🔄 Start a new interview", use_container_width=True):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()
