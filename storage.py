"""Local persistence: resume an in-progress interview, and save finished
candidate reports for comparison/ranking.

Everything is stored as JSON under a local ``.sessions`` folder next to the
app. No external services; data never leaves the machine.
"""

import os
import json
import time
import glob

_BASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".sessions")
_RESUME = os.path.join(_BASE, "_resume.json")
_CANDIDATES_DIR = os.path.join(_BASE, "candidates")

# Session keys that make up a resumable interview.
_RESUME_KEYS = [
    "stage", "cv_text", "cv_analysis", "questions", "current_question_idx",
    "answers", "scores", "job_direction", "context", "num_questions",
    "report", "project_summary", "adaptive", "difficulty_level",
    "ui_lang", "interview_lang", "auto_read", "jd_text",
]


def _ensure_dirs():
    os.makedirs(_CANDIDATES_DIR, exist_ok=True)


# ---------------------------------------------------------------------------
# Resume support
# ---------------------------------------------------------------------------
def save_resume(state):
    """Persist the resumable subset of session state to disk."""
    try:
        _ensure_dirs()
        data = {k: state.get(k) for k in _RESUME_KEYS if k in state}
        data["_saved_at"] = time.time()
        with open(_RESUME, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)
    except Exception:
        pass  # persistence is best-effort, never breaks the app


def load_resume():
    """Return the saved resume dict, or None."""
    try:
        with open(_RESUME, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def has_resume():
    return os.path.exists(_RESUME)


def clear_resume():
    try:
        os.remove(_RESUME)
    except Exception:
        pass


def resume_summary():
    """Short human description of the saved interview, for the resume button."""
    data = load_resume()
    if not data:
        return None
    cv = data.get("cv_analysis") or {}
    answered = len(data.get("answers") or [])
    total = len(data.get("questions") or [])
    return {
        "candidate": cv.get("full_name", "Candidate"),
        "role": cv.get("target_role", data.get("job_direction", "")),
        "stage": data.get("stage", "upload"),
        "progress": f"{answered}/{total}",
    }


# ---------------------------------------------------------------------------
# Candidate comparison
# ---------------------------------------------------------------------------
def save_candidate(report):
    """Save a finished report as a candidate record for later comparison."""
    try:
        _ensure_dirs()
        record = {
            "candidate": report.get("candidate", "Candidate"),
            "role": report.get("role", ""),
            "seniority": report.get("seniority", ""),
            "overall_score": report.get("overall_score", 0),
            "grade": report.get("grade", "N/A"),
            "recommendation": report.get("recommendation", ""),
            "match_score": report.get("match_score", 0),
            "authenticity_overall": report.get("authenticity_overall", "N/A"),
            "avg_ai_likelihood": report.get("avg_ai_likelihood"),
            "company": report.get("company", ""),
            "industry": report.get("industry", ""),
            "generated_at": report.get("generated_at", ""),
            "saved_at": time.time(),
            "report": report,  # full report kept for drill-down/re-export
        }
        fname = f"{int(time.time()*1000)}_{_slug(record['candidate'])}.json"
        with open(os.path.join(_CANDIDATES_DIR, fname), "w", encoding="utf-8") as f:
            json.dump(record, f, ensure_ascii=False)
        return True
    except Exception:
        return False


def list_candidates():
    """Return saved candidate records, ranked best-first by overall score."""
    _ensure_dirs()
    records = []
    for path in glob.glob(os.path.join(_CANDIDATES_DIR, "*.json")):
        try:
            with open(path, "r", encoding="utf-8") as f:
                rec = json.load(f)
                rec["_path"] = path
                records.append(rec)
        except Exception:
            continue
    records.sort(key=lambda r: (r.get("overall_score", 0),
                                r.get("match_score", 0)), reverse=True)
    return records


def delete_candidate(path):
    try:
        os.remove(path)
        return True
    except Exception:
        return False


def clear_candidates():
    for path in glob.glob(os.path.join(_CANDIDATES_DIR, "*.json")):
        try:
            os.remove(path)
        except Exception:
            pass


def _slug(text):
    import re
    return re.sub(r"[^A-Za-z0-9]+", "_", text or "candidate").strip("_")[:40] or "candidate"
