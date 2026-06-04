# 🤖 AI Interview Agent

**A CV-based AI agent that conducts realistic, adaptive job interviews — and grades them.**

It reads a candidate's CV (and, optionally, a real job description and a code
project), figures out the best-fit role, runs an adaptive voice/text interview
with problem-solving questions, scores every answer transparently, flags
AI-generated answers, shows the ideal answer, and produces a graded, downloadable
verdict.

You can find the deployed app here: https://ai-interviewer-llm.streamlit.app/

---

## 1. What it does & who it's for

### What it does
The AI Interview Agent:

1. **Analyzes** the CV (optionally against a real job description and an uploaded
   project), extracting the candidate, the best-fit role, seniority, skills,
   strengths, gaps, and a CV–role match score with a written feedback.
2. **Generates** a balanced, tailored interview — technical, problem-solving,
   behavioural, scenario and gap-probing questions — and **adapts** them to the
   candidate's answers.
3. **Evaluates** every answer on a transparent **0–10 rubric**, flags
   **AI-generated answers**, and can show the **best possible answer** as coaching.
4. **Delivers** a final verdict: overall score, **letter grade (A–F)**, hire
   recommendation, and a report downloadable as **PDF / Word / Markdown**.

It supports **voice input & output**, three languages (**English · Հայերեն ·
Русский**), and two distinct modes.


### Who it's for

| User | Mode | What they get |
|------|------|---------------|
| 🎓 **Candidates / job-seekers** | *Candidate (practice)* | Realistic practice, transparent feedback, the ideal answer, and a readiness plan — great for nervous candidates and career-switchers. |
| 🧑‍💼 **Recruiters / interviewers** | *Interviewer (evaluate)* | Consistent, rubric-based scoring, an objective hire/no-hire verdict, AI-answer flags, and candidate comparison & ranking. |

---

## 2. Getting started (setup & installation)

> **Prerequisite:** Python **3.10 or newer**.

```bash
pip install -r requirements.txt

(python -m) streamlit run app.py
```

Then open the URL it prints — usually **http://localhost:8501**.

**API key.** To use your own free key, create `.env` file and
paste a key from [console.groq.com](https://console.groq.com).

> 💡 **Windows note:** if `streamlit` is "not recognized," always use the
> `python -m streamlit run app.py` form shown above.

> ⚠️ **After editing any file other than `app.py`,** do a full restart
> (Ctrl+C, then re-run) — Streamlit caches imported modules, so the "Rerun"
> button alone is not enough.

---

## 3. Feature walkthrough

### Stage 1 — Upload & context
- **Job direction** (required) and **CV (PDF)** (required).
- Optional: **target industry**, **company type / specific company**, a pasted
  **job description**, a free-text **description of the interview**, and a **project**
  (PDF / ZIP repo / code files) to be quizzed on.
- Choose the **interview language**, **number of questions (4–25)**, and whether
  the interview is **adaptive**.

### Stage 2 — Analysis
- Shows the extracted **candidate name**, **target role**,
  seniority, **match score + rationale**, key skills, strengths, gaps.
- For an imperfect fit, it shows **transferable skills** and a **fit note**
  instead of failing.
- If a project was uploaded, a **project summary** with topics it will probe.

### Stage 3 — Interview
- Each question shows its **category** and **difficulty** (and "↳ follow-up" when
  adaptive). There is **read aloud** option to hear the question.
- Answer by **typing or voice** (record is transcribed with Whisper).
- **Submit** to see full evaluation: 4 criterias: 
    * strengths 
    * weaknesses, 
    * how to improve
    * **AI-answer detection gauge**.
- **💡 Show the best possible answer** for coaching.
- **Next question** (adaptive) or **⏭ Skip** (scores 0 and moves on).

### Stage 4 — Verdict & report
- **Overall score**, **letter grade**, **recommendation**, authenticity
  summary, score-by-category and progression charts.
- **Download** the full report as **PDF / DOCX / Markdown**.

### Cross-cutting features
- **Candidate vs Interviewer mode** (sidebar) — changes question style and report tone.
- **Compare candidates** — a ranked table of all saved interviews.
- **Resume** — an interrupted interview can be continued after a refresh.
- **Trilingual** — UI **and** interview content in EN / HY / RU.

---

## 4. System architecture overview

### The four-stage pipeline
```
        ┌──────────┐     ┌───────────┐     ┌────────────┐     ┌───────────┐
 CV ──┐ │   [1]    │     │    [2]    │     │    [3]     │     │    [4]    │
 JD ──┼▶│ ANALYZE  │ ──▶ │ GENERATE  │ ──▶ │   SCORE    │ ──▶ │  VERDICT  │
 proj ┘ │ role·fit │     │ questions │     │ +detect AI │     │ grade A–F │
        │ transfer │     │ (adaptive)│     │ +best ans. │     │  PDF/DOCX │
        └──────────┘     └───────────┘     └────────────┘     └───────────┘
```

### Module layout
```
AI-interviewer/
├── app.py                      # Streamlit UI, flow controller, all 4 stages
├── requirements.txt         
├── README.md                   
├── .env
├── .streamlit/config.toml      # Theme
└── src/
    ├── core/                   # Foundations
    │   ├── llm_client.py           # Groq gateway: chat, JSON mode, language, rate-limit fallback
    │   ├── cv_parser.py            # PDF text extraction
    │   └── name_utils.py           # Candidate-name normalisation
    ├── analysis/               # The "brains"
    │   ├── cv_analyzer.py          # CV -> structured profile, role & fit
    │   ├── project_analyzer.py     # Analyse an uploaded project (PDF/ZIP/code)
    │   ├── question_generator.py   # Balanced + adaptive question generation
    │   ├── scorer.py               # Rubric scoring, AI-detection, model answers
    │   └── ai_detector.py          # Hybrid stylometric AI-generated-text detector
    ├── reporting/              # Output
    │   ├── report_generator.py     # Final verdict, grade & narrative
    │   └── report_export.py        # PDF / DOCX export
    ├── media/                  # Voice
    │   ├── stt.py                  # Speech-to-text (Whisper)
    │   └── tts.py                  # Text-to-speech (gTTS)
    └── services/              # Cross-cutting
        ├── i18n.py                 # EN / HY / RU translations
        └── storage.py              # Resume + candidate comparison
```

---

## 5. Prompt templates used

The system uses three core prompt templates plus a language directive. (Full
text lives in the corresponding module; these are the structures.)

### 5.1 CV analysis — `src/analysis/cv_analyzer.py`
```
You are a senior technical recruiter. Analyse the CV for the job direction
"{job_direction}" [and this JOB DESCRIPTION: {jd_text}].

Rules:
- Use ONLY evidence present in the CV (reduces hallucination).
- Read the name from the header lines; do not translate or reorder it.
- If the CV does NOT fit the role, do NOT refuse — give an honest match score,
  list transferable skills, and write a fair "fit note" (transition interview).

Return a JSON object with EXACTLY these keys:
{ first_name, last_name, full_name, target_role, seniority_level,
  years_of_experience, match_score (0-100), match_rationale, key_skills[],
  strengths[], gaps[], transferable_skills[], fit_note, jd_requirements[], summary }
```

### 5.2 Question generation — `src/analysis/question_generator.py`
```
Design a {N}-question interview PLAN for this candidate.
[CANDIDATE PROFILE: role, seniority, skills, strengths, gaps]
[CONTEXT: industry, company, focus, user description, JD, project]

Requirements:
- Balance across categories: Technical, Problem-Solving, Behavioural,
  Role-specific, Project, Scenario/Case, Gap-probing (never one topic only).
- Include >= 2 Problem-Solving questions.
- Ground questions in the CV / JD / project; calibrate difficulty to seniority.

Return JSON: { "questions": [ { category, difficulty, question, what_it_assesses } ] }
```

### 5.3 Answer scoring — `src/analysis/scorer.py`
```
Evaluate the candidate's answer. Score each criterion 0-10 on this scale:
  0    = NON-ANSWER ("I don't know", refusal, blank) → all criteria 0
  1-2  = attempted but absent / wrong
  3-4  = vague, little substance
  5-6  = adequate but shallow
  7-8  = strong, specific, well-reasoned
  9-10 = excellent, deep, with trade-offs
Criteria: relevance, technical_accuracy, clarity, depth.
Also assess AUTHENTICITY (AI-generated vs genuine) with an ai_likelihood 0-100.

Return JSON: { score, criteria{...}, strengths[], weaknesses[], improvements[],
               feedback, ai_likelihood, authenticity_verdict, authenticity_signals[] }
```

### 5.4 Language directive — `src/core/llm_client.py`
A one-line suffix appended to any prompt to localise output without duplicating
templates:
```
Write ALL human-readable text values (questions, feedback, summaries, narrative)
in {Armenian|Russian}. Keep every JSON key exactly as specified in English.
```

---

## 6. Configuration

All configuration is via `.env`:

| Variable | Purpose | Default |
|----------|---------|---------|
| `GROQ_API_KEY` | **Required.** Free key from console.groq.com | — |
| `GROQ_TEXT_MODEL` | Main reasoning model | `llama-3.3-70b-versatile` |
| `GROQ_FAST_MODEL` | Fallback model (used on rate-limit) | `llama-3.1-8b-instant` |
| `GROQ_TRANSCRIBE_MODEL` | Speech-to-text model | `whisper-large-v3` |
| `MAX_CV_CHARS` | CV trim budget (keeps requests fast) | `9000` |

---

## 7. Limitations & edge cases

- **Scanned-image PDFs** yield no text. This is detected and warned the user, but the OCR isn't run - upload a text-based PDF.
- **AI-answer detection is a signal, not proof.** It blends stylometry with the
  LLM and is consistent, but it has **no formally measured accuracy**. Short answers are hardest to judge — so detect as human, never accuse.
- **Daily API quota.** The free tier caps the 70B model's tokens per day. On a
  `429` the app auto-falls-back to the fast model; otherwise wait ~1h or add a
  fresh key.
- **Text-to-speech needs internet** (gTTS), and the synthetic voices are robotic,
  especially for Armenian. The interview still works fully without audio.
- **Scoring is an LLM's judgement** — anchored and deterministic with 0 temperature 0,
  but it can occasionally be harsh or lenient on edge cases.
- **Non-answer guard nuance:** "I don't know" scores 0, but a *real* answer that
  begins "I don't know the exact syntax, but I'd use a hash map…" is correctly
  kept and scored normally.

---

## 8. Troubleshooting

| Symptom | Cause & fix |
|---------|-------------|
| `ImportError` after editing a file | Streamlit caches modules. **Fully restart** (Ctrl+C, then re-run). |
| `Error 429 / rate limit` | Daily token quota reached — the app auto-falls-back; otherwise wait ~1h or add a fresh key in `.env`. |
| `Voice output unavailable` | TTS (gTTS) needs an internet connection. |
| Page won't load / connection refused | Wait for `Local URL: …` in the terminal, then open it; keep the terminal open while using the app. |
| "Could not read any text from this PDF" | The CV is a scanned image — upload a text-based PDF. |

---

## 9. Tech stack

| Library | Version | Used for |
|---------|---------|----------|
| streamlit | 1.58.0 | Web UI framework |
| groq | 1.4.0 | LLM + Whisper API client (Llama 3.3 70B, Whisper) |
| PyPDF2 | 3.0.1 | CV / project PDF text extraction |
| reportlab | 4.5.1 | PDF report export |
| python-docx | 1.2.0 | Word (DOCX) report export |
| gTTS | 2.5.4 | Text-to-speech |
