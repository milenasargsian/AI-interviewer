"""AI Interview Agent — Streamlit application.

Features: CV + JD matching, optional project upload, balanced & adaptive
questions (with adaptive difficulty), problem-solving, voice in (Whisper) and
voice out (TTS), authenticity / AI-answer detection, graded verdict with
PDF/DOCX/Markdown export, resume-after-refresh, candidate comparison, and a
trilingual UI / interview (English · Armenian · Russian).

Run with:  python -m streamlit run app.py

Project layout (modules are grouped into the ``src`` package by responsibility):
  src.core      — llm_client, cv_parser, name_utils
  src.analysis  — cv_analyzer, project_analyzer, question_generator, scorer, ai_detector
  src.reporting — report_generator, report_export
  src.media     — stt, tts
  src.services  — i18n, storage
"""

import streamlit as st

from src.core.cv_parser import extract_text_from_pdf
from src.analysis.cv_analyzer import analyze_cv
from src.analysis.question_generator import (generate_questions, generate_followup,
                                             adapt_difficulty, DIFFICULTY_LADDER)
from src.analysis.scorer import score_answer, model_answer
from src.reporting.report_generator import generate_report, report_to_markdown
from src.media.stt import transcribe_audio_bytes
from src.analysis.project_analyzer import extract_project_text, summarize_project
from src.media.tts import synthesize_ex
from src.services.i18n import t, LANGUAGES
from src.services import storage

st.set_page_config(page_title="AI Interview Agent", page_icon="🤖", layout="wide")

CUSTOM_CSS = (
"<style>"
"@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&family=Sora:wght@600;700;800&display=swap');"
":root{"
"--indigo-50:#EEF2FF;--indigo-100:#E0E7FF;--indigo-300:#A5B4FC;"
"--indigo-500:#6366F1;--indigo-600:#4F46E5;--indigo-700:#4338CA;"
"--violet-500:#8B5CF6;--violet-600:#7C3AED;"
"--ink:#0F172A;--slate-600:#475569;--slate-400:#94A3B8;"
"--line:#E7EAF3;--canvas:#F7F8FC;--surface:#FFFFFF;"
"--success:#10B981;--success-bg:#ECFDF5;--warning:#F59E0B;--warning-bg:#FFFBEB;"
"--danger:#EF4444;--danger-bg:#FEF2F2;"
"--shadow-sm:0 1px 2px rgba(15,23,42,.06);--shadow-md:0 6px 20px rgba(15,23,42,.08);"
"--shadow-lg:0 18px 48px rgba(79,70,229,.18);--radius:18px;}"
"html,body,[class*=\"css\"]{font-family:'Inter',system-ui,sans-serif;}"
".stApp{background:radial-gradient(1100px 480px at 100% -8%,#EEF0FF 0%,rgba(238,240,255,0) 60%),radial-gradient(900px 460px at -8% 0%,#F2EBFF 0%,rgba(242,235,255,0) 55%),var(--canvas);}"
".block-container{padding-top:2.2rem;max-width:1180px;}"
"h1,h2,h3,h4{font-family:'Sora','Inter',sans-serif;color:var(--ink);letter-spacing:-.01em;}"
".hero{position:relative;overflow:hidden;background:linear-gradient(125deg,#4F46E5 0%,#6366F1 42%,#8B5CF6 100%);padding:2.4rem 2.6rem;border-radius:24px;color:#fff;margin-bottom:1.6rem;box-shadow:var(--shadow-lg);}"
".hero::after{content:'';position:absolute;inset:0;background:radial-gradient(420px 200px at 88% -20%,rgba(255,255,255,.28),transparent 70%),radial-gradient(360px 220px at 8% 120%,rgba(255,255,255,.16),transparent 70%);pointer-events:none;}"
".hero h1{margin:0;font-size:1.85rem;font-weight:800;color:#fff;}"
".hero p{margin:.45rem 0 0;opacity:.92;font-size:.98rem;max-width:780px;line-height:1.5;}"
".hero .pill{display:inline-block;margin-top:1rem;margin-right:.5rem;background:rgba(255,255,255,.16);border:1px solid rgba(255,255,255,.28);color:#fff;padding:.32rem .8rem;border-radius:999px;font-size:.78rem;font-weight:600;}"
".card{background:var(--surface);padding:1.5rem 1.7rem;border-radius:var(--radius);box-shadow:var(--shadow-md);border:1px solid var(--line);margin-bottom:1rem;transition:transform .18s ease,box-shadow .18s ease;}"
".card:hover{transform:translateY(-2px);box-shadow:var(--shadow-lg);}"
".question-box{background:linear-gradient(180deg,#fff,#FBFAFF);padding:1.3rem 1.5rem;border-radius:var(--radius);border:1px solid var(--indigo-100);border-left:5px solid var(--indigo-500);margin:.6rem 0 1.1rem;font-size:1.02rem;line-height:1.55;color:var(--ink);box-shadow:var(--shadow-sm);font-weight:500;word-break:break-word;}"
".answer-box{background:var(--success-bg);padding:1.15rem 1.5rem;border-radius:14px;border:1px solid #C7F0DD;border-left:5px solid var(--success);margin:.5rem 0;white-space:pre-wrap;color:#0B3B2E;line-height:1.6;}"
".badge{display:inline-block;padding:.24rem .8rem;border-radius:999px;font-size:.74rem;font-weight:700;margin-right:.45rem;letter-spacing:.02em;border:1px solid transparent;}"
".badge-cat{background:var(--indigo-50);color:var(--indigo-700);border-color:var(--indigo-100);}"
".badge-diff{background:var(--warning-bg);color:#B45309;border-color:#FDE9C8;}"
".badge-follow{background:#F3EEFF;color:var(--violet-600);border-color:#E6DBFF;}"
".badge-auth-good{background:var(--success-bg);color:#047857;border-color:#C7F0DD;}"
".badge-auth-warn{background:var(--warning-bg);color:#B45309;border-color:#FDE9C8;}"
".badge-auth-bad{background:var(--danger-bg);color:#B91C1C;border-color:#FBD5D5;}"
".step-pill{display:inline-block;padding:.42rem 1rem;border-radius:999px;font-weight:600;font-size:.84rem;margin-right:.5rem;margin-bottom:.4rem;background:#fff;color:var(--slate-600);border:1px solid var(--line);box-shadow:var(--shadow-sm);transition:all .15s ease;}"
".step-pill.active{background:linear-gradient(120deg,var(--indigo-600),var(--violet-600));color:#fff;border-color:transparent;box-shadow:0 6px 16px rgba(99,102,241,.32);}"
".stButton > button{border-radius:12px;font-weight:600;font-family:'Inter',sans-serif;border:1px solid var(--line);transition:all .15s ease;padding:.5rem 1.05rem;}"
".stButton > button:hover{transform:translateY(-1px);box-shadow:var(--shadow-md);}"
".stButton > button[kind=\"primary\"]{background:linear-gradient(120deg,var(--indigo-600),var(--violet-600));border:none;color:#fff;box-shadow:0 8px 20px rgba(99,102,241,.30);}"
".stButton > button[kind=\"primary\"]:hover{filter:brightness(1.05);box-shadow:0 12px 26px rgba(99,102,241,.40);}"
".stDownloadButton > button{border-radius:12px;font-weight:600;border:1px solid var(--indigo-100);}"
".stTextInput input,.stTextArea textarea,.stSelectbox div[data-baseweb=\"select\"]{border-radius:12px !important;}"
".stTextInput input:focus,.stTextArea textarea:focus{border-color:var(--indigo-500) !important;box-shadow:0 0 0 3px rgba(99,102,241,.15) !important;}"
"[data-testid=\"stMetric\"]{background:var(--surface);border:1px solid var(--line);border-radius:16px;padding:1rem 1.1rem;box-shadow:var(--shadow-sm);}"
"[data-testid=\"stMetricValue\"]{color:var(--indigo-700);font-family:'Sora',sans-serif;font-weight:700;font-size:1.45rem;line-height:1.2;word-break:break-word;}"
"[data-testid=\"stMetricLabel\"]{color:var(--slate-600);font-weight:600;}"
".stProgress > div > div > div{background:linear-gradient(90deg,var(--indigo-500),var(--violet-500)) !important;}"
"section[data-testid=\"stSidebar\"]{background:linear-gradient(180deg,#FFFFFF 0%,#FBFAFF 100%);border-right:1px solid var(--line);}"
"section[data-testid=\"stSidebar\"] h2,section[data-testid=\"stSidebar\"] h3{color:var(--indigo-700);}"
"[data-testid=\"stExpander\"]{border:1px solid var(--line);border-radius:14px;box-shadow:var(--shadow-sm);}"
"[data-testid=\"stDataFrame\"]{border-radius:14px;overflow:hidden;border:1px solid var(--line);}"
"[data-testid=\"stAlert\"]{border-radius:14px;}"
"#MainMenu{visibility:hidden;}footer{visibility:hidden;}[data-testid=\"stDecoration\"]{display:none;}"
".main .block-container > div{animation:fadeUp .4s ease both;}"
"@keyframes fadeUp{from{opacity:0;transform:translateY(8px);}to{opacity:1;transform:none;}}"
"</style>"
)
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)


def init_state():
    defaults = {
        "stage": "upload", "cv_text": "", "cv_analysis": None,
        "questions": [], "current_question_idx": 0,
        "answers": [], "scores": [], "job_direction": "",
        "context": {}, "num_questions": 10, "report": None,
        "project_summary": None, "adaptive": True,
        "ui_lang": "en", "interview_lang": "en", "auto_read": False,
        "jd_text": "", "difficulty_level": 1, "app_mode": "new",
        "report_saved": False, "persona": "candidate",
    }
    for k, v in defaults.items():
        st.session_state.setdefault(k, v)


def persist():
    """Save resumable state after meaningful changes."""
    storage.save_resume(st.session_state)


def stepper():
    steps = [("upload", t("step_upload")), ("analysis", t("step_analysis")),
             ("interview", t("step_interview")), ("report", t("step_verdict"))]
    pills = ""
    for key, label in steps:
        active = "active" if st.session_state.stage == key else ""
        pills += f'<span class="step-pill {active}">{label}</span>'
    st.markdown(pills, unsafe_allow_html=True)


def info_card(label, value, sub=""):
    """A metric-style card whose value WRAPS (unlike st.metric, which clips).

    Use for long text values like role titles so words are never cut with '…'.
    """
    sub_html = (f"<div style='font-size:.76rem;color:#94A3B8;margin-top:.3rem'>{sub}</div>"
                if sub else "")
    st.markdown(
        f"<div style='background:#fff;border:1px solid #E7EAF3;border-radius:16px;"
        f"padding:.85rem 1rem;box-shadow:0 1px 2px rgba(15,23,42,.06)'>"
        f"<div style='font-size:.78rem;color:#475569;font-weight:600'>{label}</div>"
        f"<div style='font-family:Sora,sans-serif;font-weight:700;color:#4338CA;"
        f"font-size:1.05rem;line-height:1.3;margin-top:.2rem;word-break:break-word;"
        f"white-space:normal'>{value}</div>{sub_html}</div>",
        unsafe_allow_html=True)


def play_tts(text):
    """Render an audio player for a question if read-aloud is enabled."""
    if not st.session_state.get("auto_read"):
        return
    with st.spinner("Generating audio…"):
        audio, err = synthesize_ex(text, st.session_state.get("interview_lang", "en"))
    if audio:
        st.audio(audio, format="audio/mp3")
    else:
        st.caption(f"🔇 Voice output unavailable — {err}. Check your internet connection.")


# ---------------------------------------------------------------------------
# Stage 1 — Upload
# ---------------------------------------------------------------------------
def upload_stage():
    st.markdown(f"### {t('upload_title')}")

    # Offer to resume a saved interview.
    rs = storage.resume_summary()
    if rs and rs["stage"] in ("analysis", "interview", "report"):
        with st.container():
            st.info(f"↩️ Saved interview found: **{rs['candidate']}** — "
                    f"{rs['role']} ({rs['progress']} answered).")
            rc = st.columns([1, 1, 4])
            if rc[0].button(t("resume_prev"), type="primary"):
                _do_resume()
            if rc[1].button("🗑️ Discard"):
                storage.clear_resume()
                st.rerun()

    col1, col2 = st.columns(2)
    with col1:
        job_direction = st.text_input(t("job_direction"),
                                      value=st.session_state.job_direction,
                                      placeholder="e.g. Backend Software Engineer")
        industry = st.text_input(t("industry"),
                                 value=st.session_state.context.get("industry", ""),
                                 placeholder="e.g. Fintech, Healthcare")
    with col2:
        company_type = st.selectbox(
            t("company_type"),
            ["Not specified", "Startup", "Scale-up", "Enterprise / Corporate",
             "Big Tech (FAANG-style)", "Consultancy / Agency", "Public sector / NGO"])
        company = st.text_input(t("company"),
                                value=st.session_state.context.get("company", ""),
                                placeholder="e.g. Google, Stripe")

    c1, c2, c3 = st.columns(3)
    with c1:
        interview_focus = st.selectbox(
            t("interview_focus"),
            ["Balanced (technical + behavioural)", "Mostly technical",
             "Mostly behavioural", "System design / scenarios",
             "Leadership / management"])
    with c2:
        lang_label = st.selectbox(t("interview_language"), list(LANGUAGES.keys()),
                                  index=list(LANGUAGES.values()).index(
                                      st.session_state.interview_lang)
                                  if st.session_state.interview_lang in LANGUAGES.values() else 0)
        interview_lang = LANGUAGES[lang_label]
    with c3:
        num_questions = st.slider(t("num_questions"), 4, 25,
                                  st.session_state.num_questions)

    adaptive = st.checkbox(t("adaptive_cb"), value=True)

    interview_desc = st.text_area(
        t("interview_desc"), value=st.session_state.context.get("interview_desc", ""),
        height=90, placeholder=t("interview_desc_ph"))
    jd_text = st.text_area(t("jd_label"), value=st.session_state.jd_text, height=110,
                           placeholder="Paste the full job posting here…")
    extra_context = st.text_area(
        t("extra_context"), value=st.session_state.context.get("extra_context", ""),
        height=80,
        placeholder="e.g. Second interview — already submitted a payments project; go deeper.")

    u1, u2 = st.columns(2)
    with u1:
        uploaded_file = st.file_uploader(t("upload_cv"), type=["pdf"])
    with u2:
        project_files = st.file_uploader(
            t("upload_project"),
            type=["pdf", "zip", "txt", "md", "py", "js", "ts", "ipynb",
                  "java", "cpp", "c", "go", "rb", "sql", "json"],
            accept_multiple_files=True)

    missing = []
    if not job_direction.strip():
        missing.append("a job direction")
    if uploaded_file is None:
        missing.append("a CV (PDF)")

    if st.button(t("analyze_cv"), type="primary"):
        if missing:
            st.warning("Please provide " + " and ".join(missing) + ".")
        else:
            try:
                with st.spinner("Extracting text from CV…"):
                    cv_text = extract_text_from_pdf(uploaded_file)
                if not cv_text.strip():
                    st.error("Could not read any text from this PDF (scanned image?).")
                    return

                st.session_state.cv_text = cv_text
                st.session_state.job_direction = job_direction.strip()
                st.session_state.num_questions = num_questions
                st.session_state.adaptive = adaptive
                st.session_state.interview_lang = interview_lang
                st.session_state.jd_text = jd_text.strip()
                st.session_state.difficulty_level = 1
                st.session_state.context = {
                    "industry": industry.strip(), "company_type": company_type,
                    "company": company.strip(), "interview_focus": interview_focus,
                    "extra_context": extra_context.strip(),
                    "jd_text": jd_text.strip(),
                    "interview_desc": interview_desc.strip(),
                    "persona": st.session_state.persona,
                }

                st.session_state.project_summary = None
                if project_files:
                    with st.spinner("Analyzing your project…"):
                        ptext = extract_project_text(project_files)
                        if ptext:
                            st.session_state.project_summary = summarize_project(
                                ptext, job_direction.strip())

                with st.spinner("Analyzing CV with AI…"):
                    st.session_state.cv_analysis = analyze_cv(
                        cv_text, job_direction.strip(),
                        jd_text=jd_text.strip(), interview_lang=interview_lang,
                        interview_desc=interview_desc.strip(),
                        persona=st.session_state.persona)
                st.session_state.stage = "analysis"
                persist()
                st.rerun()
            except Exception as err:
                st.error(f"Something went wrong: {err}")

    st.caption("Still needed: " + " and ".join(missing) + "." if missing
               else "Ready — click Analyze CV to continue.")


def _do_resume():
    data = storage.load_resume()
    if data:
        for k, v in data.items():
            if not k.startswith("_"):
                st.session_state[k] = v
        st.rerun()


# ---------------------------------------------------------------------------
# Stage 2 — Analysis
# ---------------------------------------------------------------------------
def analysis_stage():
    a = st.session_state.cv_analysis
    st.markdown(f"### {t('analysis_title')}")

    top = st.columns([2, 1, 1])
    with top[0]:
        st.markdown(f"<div class='card'><h3 style='margin:0'>👤 {a.get('full_name','Candidate')}</h3>"
                    f"<p style='margin:.3rem 0 0;color:#555'>{a.get('summary','')}</p></div>",
                    unsafe_allow_html=True)
    with top[1]:
        info_card(t("target_role"), a.get("target_role", "N/A"),
                  sub=f"{a.get('seniority_level','N/A')} · "
                      f"~{a.get('years_of_experience',0)} yrs")
    with top[2]:
        st.metric(t("cv_match"), f"{a.get('match_score',0)}%")
        st.progress(min(100, int(a.get("match_score", 0))) / 100)

    if a.get("match_rationale"):
        st.info(f"**{t('why_match')}:** {a['match_rationale']}")

    # Mismatch-friendly framing: show how a stretch/transition is handled.
    if a.get("fit_note"):
        st.warning(f"🧭 {a['fit_note']}")
    if a.get("transferable_skills"):
        st.markdown("**🔁 Transferable skills:** "
                    + ", ".join(a["transferable_skills"]))

    if a.get("jd_requirements"):
        with st.expander("📋 Parsed job-description requirements"):
            for r in a["jd_requirements"]:
                st.markdown(f"- {r}")

    cols = st.columns(3)
    for col, title, items in [
        (cols[0], t("key_skills"), a.get("key_skills", [])),
        (cols[1], t("strengths"), a.get("strengths", [])),
        (cols[2], t("gaps"), a.get("gaps", [])),
    ]:
        with col:
            st.markdown(f"#### {title}")
            for s in items:
                st.markdown(f"- {s}")

    ps = st.session_state.project_summary
    if ps:
        st.divider()
        st.markdown(f"#### 📦 {t('project')}: {ps.get('title','')}")
        st.write(ps.get("summary", ""))
        pcols = st.columns(2)
        with pcols[0]:
            st.markdown("**Tech stack:** " + (", ".join(ps.get("tech_stack", [])) or "—"))
        with pcols[1]:
            st.markdown("**Will probe:**")
            for tp in ps.get("probe_topics", []):
                st.markdown(f"- {tp}")

    st.divider()
    cols = st.columns([1, 1, 4])
    if cols[0].button(t("back")):
        st.session_state.stage = "upload"
        st.rerun()
    if cols[1].button(t("start_interview"), type="primary"):
        with st.spinner("Generating tailored interview questions…"):
            st.session_state.questions = generate_questions(
                a, st.session_state.job_direction, context=st.session_state.context,
                num_questions=st.session_state.num_questions,
                project_summary=st.session_state.project_summary,
                interview_lang=st.session_state.interview_lang)
        st.session_state.current_question_idx = 0
        st.session_state.answers = []
        st.session_state.scores = []
        st.session_state.difficulty_level = 1
        st.session_state.stage = "interview"
        persist()
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

    st.markdown(f"### {t('interview_title')}")
    st.progress(idx / total)
    st.caption(t("question_of", a=idx + 1, b=total))

    q = questions[idx]
    follow = ("<span class='badge badge-follow'>↳ follow-up</span>"
              if q.get("is_followup") else "")
    st.markdown(
        f"<div class='question-box'>"
        f"<span class='badge badge-cat'>{q.get('category','')}</span>"
        f"<span class='badge badge-diff'>{q.get('difficulty','')}</span>{follow}<br><br>"
        f"{q.get('question','')}</div>", unsafe_allow_html=True)
    if q.get("what_it_assesses"):
        st.caption(f"💡 {q['what_it_assesses']}")

    # Voice output of the question.
    play_tts(q.get("question", ""))
    if not st.session_state.get("auto_read"):
        if st.button(t("read_aloud"), key=f"read_{idx}"):
            with st.spinner("Generating audio…"):
                audio, err = synthesize_ex(q.get("question", ""),
                                           st.session_state.interview_lang)
            if audio:
                st.audio(audio, format="audio/mp3")
            else:
                st.caption(f"🔇 Voice output unavailable — {err}. Check your internet connection.")

    answered = idx < len(st.session_state.answers)
    if not answered:
        _answer_panel(idx, q, total)
    else:
        _evaluation_panel(idx, q, total)

    _previous_answers(idx)


def _answer_panel(idx, q, total):
    answer_key = f"answer_{idx}"
    if hasattr(st, "audio_input"):
        audio = st.audio_input(t("record_voice"), key=f"audio_{idx}")
        if audio is not None and st.button(t("transcribe"), key=f"transcribe_{idx}"):
            with st.spinner("Transcribing…"):
                text, err = transcribe_audio_bytes(
                    audio.getvalue(), filename=f"answer_{idx}.wav",
                    language=st.session_state.interview_lang)
            if err:
                st.error(err)
            else:
                st.session_state[answer_key] = text
                st.success("Transcribed — review/edit below, then submit.")
                st.rerun()
    else:
        st.caption("ℹ️ Voice input needs Streamlit ≥ 1.31.")

    st.text_area(t("your_answer"), key=answer_key, height=170)

    b1, b2 = st.columns([3, 1])
    submit = b1.button(t("submit"), type="primary", key=f"submit_{idx}",
                       use_container_width=True)
    skip = b2.button(t("skip"), key=f"skip_{idx}", use_container_width=True)

    if skip:
        st.session_state.answers.append("")
        st.session_state.scores.append(_skipped_score())
        if st.session_state.adaptive:
            recent = [s.get("score", 0) for s in st.session_state.scores]
            st.session_state.difficulty_level = adapt_difficulty(
                st.session_state.difficulty_level, recent)
        # Skipping goes straight to the next question (no evaluation panel).
        if idx == total - 1:
            st.session_state.current_question_idx = idx + 1
            st.session_state.report = None
            st.session_state.report_saved = False
            st.session_state.stage = "report"
        else:
            _advance_to_next(idx)
        persist()
        st.rerun()

    if submit:
        final_answer = st.session_state.get(answer_key, "").strip()
        if not final_answer:
            st.warning("Please provide an answer, or use Skip.")
            return
        with st.spinner("Evaluating…"):
            score = score_answer(
                q.get("question", ""), final_answer, st.session_state.job_direction,
                cv_analysis=st.session_state.cv_analysis,
                context=st.session_state.context,
                interview_lang=st.session_state.interview_lang)
        st.session_state.answers.append(final_answer)
        st.session_state.scores.append(score)
        # Adapt difficulty for upcoming questions.
        if st.session_state.adaptive:
            recent = [s.get("score", 0) for s in st.session_state.scores]
            st.session_state.difficulty_level = adapt_difficulty(
                st.session_state.difficulty_level, recent)
        persist()
        st.rerun()


def _skipped_score():
    """A zero score record for a skipped question."""
    return {
        "score": 0,
        "criteria": {"relevance": 0, "technical_accuracy": 0, "clarity": 0, "depth": 0},
        "strengths": [], "weaknesses": ["Question was skipped — no answer given."],
        "improvements": ["Attempt every question; even a partial answer scores higher than 0."],
        "feedback": t("skipped"),
        "authenticity_score": 0, "ai_likelihood": 0,
        "authenticity_verdict": "N/A", "authenticity_signals": [], "skipped": True,
    }


def _auth_badge(verdict):
    cls = "badge-auth-good"
    if verdict == "Possibly AI-assisted":
        cls = "badge-auth-warn"
    elif verdict == "Likely AI-generated":
        cls = "badge-auth-bad"
    return f"<span class='badge {cls}'>🔍 {verdict}</span>"


def _ai_detection_panel(score):
    """Visual AI-answer detection: verdict badge + gauge bar + signals."""
    verdict = score.get("authenticity_verdict", "N/A")
    ai = int(score.get("ai_likelihood", 0))
    # Gauge colour by risk.
    if ai >= 75:
        bar = "#EF4444"
    elif ai >= 50:
        bar = "#F59E0B"
    elif ai >= 25:
        bar = "#84CC16"
    else:
        bar = "#10B981"
    st.markdown(
        f"<div style='background:#fff;border:1px solid var(--line,#E7EAF3);"
        f"border-radius:14px;padding:.8rem 1rem;margin:.3rem 0 .6rem'>"
        f"<div style='display:flex;justify-content:space-between;align-items:center;"
        f"flex-wrap:wrap;gap:.4rem;margin-bottom:.5rem'>"
        f"<span style='font-weight:700;font-size:.9rem;color:#475569'>🔍 {t('ai_detection')}</span>"
        f"{_auth_badge(verdict)}</div>"
        f"<div style='background:#EEF0F5;border-radius:999px;height:10px;overflow:hidden'>"
        f"<div style='width:{ai}%;height:100%;background:{bar};border-radius:999px'></div></div>"
        f"<div style='display:flex;justify-content:space-between;font-size:.74rem;"
        f"color:#94A3B8;margin-top:.25rem'>"
        f"<span>Authentic ({score.get('authenticity_score',0)}/100)</span>"
        f"<span>AI-likelihood {ai}/100</span></div></div>",
        unsafe_allow_html=True)
    sigs = score.get("authenticity_signals", [])
    if sigs:
        with st.expander("Why this verdict?"):
            for s in sigs:
                st.caption(f"• {s}")
            heur = score.get("ai_signals", {})
            if heur:
                st.caption("Stylometric signals: " + ", ".join(
                    f"{k}={v}" for k, v in heur.items()))


def _evaluation_panel(idx, q, total):
    answer = st.session_state.answers[idx]
    score = st.session_state.scores[idx]

    if score.get("skipped"):
        st.markdown(f"#### {t('your_answer_h')}")
        st.warning(f"⏭ {t('skipped')}")
        st.divider()
        if idx == total - 1:
            if st.button(t("finish"), type="primary", key=f"finish_{idx}"):
                st.session_state.current_question_idx = idx + 1
                st.session_state.report = None
                st.session_state.report_saved = False
                st.session_state.stage = "report"
                persist()
                st.rerun()
        elif st.button(t("next_question"), type="primary", key=f"next_{idx}"):
            _advance_to_next(idx)
            persist()
            st.rerun()
        return

    st.markdown(f"#### {t('your_answer_h')}")
    st.markdown(f"<div class='answer-box'>{answer}</div>", unsafe_allow_html=True)

    verdict = score.get("authenticity_verdict", "N/A")
    ai_like = score.get("ai_likelihood")
    if verdict and verdict != "N/A" and ai_like is not None:
        _ai_detection_panel(score)

    st.markdown(f"#### {t('evaluation')} — **{score.get('score',0)}/10**")
    crit = score.get("criteria", {})
    if crit:
        cc = st.columns(len(crit))
        for col, (name, val) in zip(cc, crit.items()):
            col.metric(name.replace("_", " ").title(), f"{val}/10")

    cols = st.columns(3)
    with cols[0]:
        st.markdown(f"**{t('strengths')}**")
        for s in score.get("strengths", []) or ["—"]:
            st.markdown(f"- {s}")
    with cols[1]:
        st.markdown(f"**{t('weaknesses')}**")
        for w in score.get("weaknesses", []) or ["—"]:
            st.markdown(f"- {w}")
    with cols[2]:
        st.markdown(f"**{t('improve')}**")
        for i in score.get("improvements", []) or ["—"]:
            st.markdown(f"- {i}")

    if score.get("feedback"):
        st.info(score["feedback"])

    # Best possible answer (coaching). Generated on demand and cached.
    best_key = f"best_{idx}"
    if st.button(t("show_best"), key=f"showbest_{idx}"):
        if best_key not in st.session_state:
            with st.spinner("Crafting the best possible answer…"):
                st.session_state[best_key] = model_answer(
                    q.get("question", ""), st.session_state.job_direction,
                    cv_analysis=st.session_state.cv_analysis,
                    context=st.session_state.context,
                    interview_lang=st.session_state.interview_lang)
    if best_key in st.session_state:
        st.markdown(f"##### {t('best_answer')}")
        st.success(st.session_state[best_key])

    if st.session_state.adaptive:
        st.caption(f"🎚 Next difficulty: "
                   f"**{DIFFICULTY_LADDER[st.session_state.difficulty_level]}** "
                   f"(adapts to your performance).")

    st.divider()
    if idx == total - 1:
        if st.button(t("finish"), type="primary", key=f"finish_{idx}"):
            st.session_state.current_question_idx = idx + 1
            st.session_state.report = None
            st.session_state.report_saved = False
            st.session_state.stage = "report"
            persist()
            st.rerun()
    else:
        if st.button(t("next_question"), type="primary", key=f"next_{idx}"):
            _advance_to_next(idx)
            persist()
            st.rerun()


def _advance_to_next(idx):
    next_idx = idx + 1
    if st.session_state.adaptive and next_idx < len(st.session_state.questions):
        asked = [qq.get("category", "") for qq in st.session_state.questions[:next_idx]]
        target_diff = DIFFICULTY_LADDER[st.session_state.difficulty_level]
        with st.spinner("Thinking about the best next question…"):
            follow = generate_followup(
                st.session_state.questions[idx].get("question", ""),
                st.session_state.answers[idx], st.session_state.cv_analysis,
                st.session_state.job_direction, context=st.session_state.context,
                project_summary=st.session_state.project_summary,
                asked_categories=asked, target_difficulty=target_diff,
                interview_lang=st.session_state.interview_lang)
        if follow and follow.get("question"):
            st.session_state.questions[next_idx] = follow
    st.session_state.current_question_idx = next_idx


def _previous_answers(idx):
    if idx == 0:
        return
    st.divider()
    st.markdown(f"#### {t('prev_questions')}")
    for i in range(idx):
        q = st.session_state.questions[i]
        sc = st.session_state.scores[i] if i < len(st.session_state.scores) else {}
        with st.expander(f"Q{i+1} [{q.get('category','')}] — {sc.get('score',0)}/10"):
            st.markdown(f"**Q:** {q.get('question','')}")
            ans = st.session_state.answers[i]
            st.markdown(f"**A:** {ans if ans else '_(skipped)_'}")
            if sc.get("feedback"):
                st.caption(sc["feedback"])


# ---------------------------------------------------------------------------
# Stage 4 — Report / Verdict
# ---------------------------------------------------------------------------
def report_stage():
    st.markdown(f"### {t('report_title')}")

    if not st.session_state.answers:
        st.warning("No answers were recorded.")
        if st.button(t("back")):
            st.session_state.stage = "interview"
            st.rerun()
        return

    if st.session_state.report is None:
        with st.spinner("Compiling the final verdict…"):
            st.session_state.report = generate_report(
                st.session_state.cv_analysis, st.session_state.questions,
                st.session_state.answers, st.session_state.scores,
                st.session_state.job_direction, context=st.session_state.context,
                interview_lang=st.session_state.interview_lang,
                persona=st.session_state.persona)

    report = st.session_state.report

    # Save to candidate comparison store once.
    if not st.session_state.report_saved:
        storage.save_candidate(report)
        st.session_state.report_saved = True
        storage.clear_resume()  # interview is complete

    # Color-coded verdict banner (green / amber / red by score).
    sc10 = report.get("overall_score", 0)
    if sc10 >= 7:
        g1, g2 = "#10B981", "#059669"
    elif sc10 >= 5:
        g1, g2 = "#F59E0B", "#D97706"
    else:
        g1, g2 = "#EF4444", "#DC2626"
    st.markdown(
        f"<div style='background:linear-gradient(120deg,{g1},{g2});color:#fff;"
        f"padding:1.5rem 1.8rem;border-radius:20px;margin:.4rem 0 1.2rem;"
        f"box-shadow:0 14px 34px rgba(16,185,129,.22);display:flex;"
        f"justify-content:space-between;align-items:center;flex-wrap:wrap;gap:1rem'>"
        f"<div><div style='font-size:.78rem;opacity:.9;font-weight:600;"
        f"text-transform:uppercase;letter-spacing:.05em'>{t('recommendation')}</div>"
        f"<div style='font-family:Sora,sans-serif;font-size:1.45rem;font-weight:800'>"
        f"{report['recommendation']}</div></div>"
        f"<div style='text-align:center'><div style='font-size:.75rem;opacity:.9'>"
        f"{t('overall')}</div><div style='font-size:1.9rem;font-weight:800;"
        f"font-family:Sora,sans-serif;line-height:1'>{sc10}<span style='font-size:1rem;"
        f"opacity:.8'>/10</span></div></div>"
        f"<div style='text-align:center'><div style='font-size:.75rem;opacity:.9'>"
        f"{t('grade')}</div><div style='font-size:1.9rem;font-weight:800;"
        f"font-family:Sora,sans-serif;line-height:1'>{report.get('grade','N/A')}</div></div>"
        f"</div>", unsafe_allow_html=True)

    top = st.columns(3)
    with top[0]:
        info_card(t("cv_match"), f"{report.get('match_score',0)}%")
    with top[1]:
        info_card(t("authenticity"), report.get("authenticity_overall", "N/A"))
    with top[2]:
        info_card(t("questions_label"), len(report.get("per_question", [])))

    _category_breakdown()

    st.divider()
    md = report_to_markdown(report)
    st.markdown(md)

    st.divider()
    st.markdown(f"#### {t('download')}")
    _download_buttons(report, md)

    if st.button(t("new_interview")):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()


def _category_breakdown():
    """Per-category average scores + score progression chart."""
    qs, scs = st.session_state.questions, st.session_state.scores
    if not scs:
        return
    by_cat = {}
    for i, sc in enumerate(scs):
        cat = qs[i].get("category", "General") if i < len(qs) else "General"
        by_cat.setdefault(cat, []).append(sc.get("score", 0))

    st.divider()
    cc = st.columns(2)
    with cc[0]:
        st.markdown("**📊 Score by category**")
        st.bar_chart({c: round(sum(v) / len(v), 1) for c, v in by_cat.items()})
    with cc[1]:
        st.markdown("**📈 Score progression**")
        st.line_chart({"score": [s.get("score", 0) for s in scs]})


def _download_buttons(report, md):
    from src.reporting.report_export import build_pdf, build_docx, filename
    cols = st.columns(3)
    with cols[0]:
        try:
            st.download_button("⬇️ PDF", data=build_pdf(report),
                               file_name=filename(report, "pdf"),
                               mime="application/pdf", use_container_width=True)
        except Exception as err:
            st.caption(f"PDF export error: {err}")
    with cols[1]:
        try:
            st.download_button(
                "⬇️ Word (DOCX)", data=build_docx(report),
                file_name=filename(report, "docx"),
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                use_container_width=True)
        except Exception as err:
            st.caption(f"DOCX export error: {err}")
    with cols[2]:
        st.download_button("⬇️ Markdown", data=md.encode("utf-8"),
                           file_name=filename(report, "md"),
                           mime="text/markdown", use_container_width=True)


# ---------------------------------------------------------------------------
# Compare candidates
# ---------------------------------------------------------------------------
def compare_stage():
    st.markdown(f"### {t('compare_title')}")
    records = storage.list_candidates()
    if not records:
        st.info(t("no_saved"))
        return

    rows = []
    for i, r in enumerate(records, 1):
        rows.append({
            t("rank"): i,
            t("candidate"): r.get("candidate", ""),
            t("role"): r.get("role", ""),
            t("overall"): r.get("overall_score", 0),
            t("grade"): r.get("grade", ""),
            t("recommendation"): r.get("recommendation", ""),
            t("cv_match"): f"{r.get('match_score', 0)}%",
            t("authenticity"): r.get("authenticity_overall", "N/A"),
        })
    st.dataframe(rows, use_container_width=True, hide_index=True)

    st.bar_chart({r.get("candidate", f"#{i}"): r.get("overall_score", 0)
                  for i, r in enumerate(records, 1)})

    with st.expander("🔎 Drill into a candidate's full report"):
        names = [f"{i}. {r.get('candidate','')} ({r.get('overall_score',0)}/10)"
                 for i, r in enumerate(records, 1)]
        pick = st.selectbox("Candidate", names)
        chosen = records[names.index(pick)]
        st.markdown(report_to_markdown(chosen["report"]))

    st.divider()
    if st.button("🗑️ Clear all saved candidates"):
        storage.clear_candidates()
        st.rerun()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    init_state()

    with st.sidebar:
        # UI language selector (controls the whole interface).
        ui_label = st.selectbox(
            "🌐 " + t("language"), list(LANGUAGES.keys()),
            index=list(LANGUAGES.values()).index(st.session_state.ui_lang)
            if st.session_state.ui_lang in LANGUAGES.values() else 0)
        new_ui = LANGUAGES[ui_label]
        if new_ui != st.session_state.ui_lang:
            st.session_state.ui_lang = new_ui
            st.rerun()

        st.divider()
        # Persona: candidate (practice) vs interviewer (evaluate).
        persona_label = st.radio(
            t("persona"), [t("persona_candidate"), t("persona_interviewer")],
            index=0 if st.session_state.persona == "candidate" else 1)
        st.session_state.persona = ("candidate"
                                    if persona_label == t("persona_candidate")
                                    else "interviewer")
        st.caption(t("candidate_hint") if st.session_state.persona == "candidate"
                   else t("interviewer_hint"))

        st.divider()
        mode = st.radio(t("mode"), [t("mode_new"), t("mode_compare")])
        st.session_state.app_mode = "compare" if mode == t("mode_compare") else "new"

        st.divider()
        st.header("📋 " + t("session"))
        if st.session_state.cv_analysis:
            st.write(f"**{t('candidate')}:** {st.session_state.cv_analysis.get('full_name','—')}")
            st.write(f"**{t('role')}:** {st.session_state.cv_analysis.get('target_role','—')}")
        if st.session_state.project_summary:
            st.write(f"**{t('project')}:** {st.session_state.project_summary.get('title','—')}")
        st.write(f"**{t('adaptive_state')}:** {'on' if st.session_state.adaptive else 'off'}")
        st.session_state.auto_read = st.checkbox(
            t("auto_read"), value=st.session_state.get("auto_read", False))
        st.divider()
        if st.button(t("reset")):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            storage.clear_resume()
            st.rerun()

    st.markdown(
        f"<div class='hero'><h1>🤖 AI Interview Agent</h1>"
        f"<p>{t('app_subtitle')}</p>"
        f"<span class='pill'>🎯 CV + JD matching</span>"
        f"<span class='pill'>🧩 Adaptive difficulty</span>"
        f"<span class='pill'>🔍 AI-answer detection</span>"
        f"<span class='pill'>🔊 Voice in & out</span>"
        f"<span class='pill'>🌐 EN · HY · RU</span>"
        f"</div>", unsafe_allow_html=True)

    if st.session_state.app_mode == "compare":
        compare_stage()
        return

    stepper()
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
