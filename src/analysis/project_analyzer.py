"""Analyse an uploaded project so the interview can probe real, personal work.

Supports PDFs, plain-text/code files, notebooks and ZIP archives. We extract
a representative slice of text, then summarise it into the few things an
interviewer would actually want to dig into.
"""

import io
import os
import zipfile
import PyPDF2

from src.core.llm_client import chat_json

_TEXT_EXTS = {
    ".txt", ".md", ".rst", ".py", ".js", ".ts", ".tsx", ".jsx", ".java",
    ".c", ".cpp", ".h", ".hpp", ".cs", ".go", ".rb", ".php", ".rs", ".kt",
    ".swift", ".scala", ".sql", ".json", ".yaml", ".yml", ".toml", ".ipynb",
    ".html", ".css", ".sh", ".r", ".m", ".dart",
}

_SKIP_DIRS = {"node_modules", ".git", "venv", ".venv", "__pycache__",
              "dist", "build", ".next", "target"}

MAX_PROJECT_CHARS = 14000


def _read_text_bytes(data, name):
    try:
        return data.decode("utf-8", errors="ignore")
    except Exception:
        return ""


def _extract_pdf(data):
    reader = PyPDF2.PdfReader(io.BytesIO(data))
    return "\n".join((p.extract_text() or "") for p in reader.pages)


def _extract_zip(data):
    chunks = []
    with zipfile.ZipFile(io.BytesIO(data)) as zf:
        for info in zf.infolist():
            if info.is_dir():
                continue
            parts = set(info.filename.replace("\\", "/").split("/"))
            if parts & _SKIP_DIRS:
                continue
            ext = os.path.splitext(info.filename)[1].lower()
            if ext not in _TEXT_EXTS or info.file_size > 200_000:
                continue
            try:
                with zf.open(info) as fh:
                    chunks.append(f"\n# FILE: {info.filename}\n"
                                  + _read_text_bytes(fh.read(), info.filename))
            except Exception:
                continue
            if sum(len(c) for c in chunks) > MAX_PROJECT_CHARS:
                break
    return "\n".join(chunks)


def extract_project_text(uploaded_files):
    """Extract combined text from one or more uploaded project files."""
    if not uploaded_files:
        return ""
    if not isinstance(uploaded_files, (list, tuple)):
        uploaded_files = [uploaded_files]

    out = []
    for f in uploaded_files:
        name = getattr(f, "name", "file")
        ext = os.path.splitext(name)[1].lower()

        try:
            data = f.getvalue() if hasattr(f, "getvalue") else f.read()
        except Exception:
            continue

        if ext == ".pdf":
            text = _extract_pdf(data)
        elif ext == ".zip":
            text = _extract_zip(data)
        elif ext in _TEXT_EXTS:
            text = f"# FILE: {name}\n" + _read_text_bytes(data, name)
        else:
            text = _read_text_bytes(data, name)
        if text and text.strip():
            out.append(f"\n===== {name} =====\n{text.strip()}")

    combined = "\n".join(out).strip()
    return combined[:MAX_PROJECT_CHARS]


def summarize_project(project_text, job_direction=""):
    """Summarise extracted project text into interview-useful signals."""
    if not project_text or not project_text.strip():
        return None

    prompt = f"""You are reviewing a candidate's real project submission so an
interviewer can ask grounded, specific questions about it.

TARGET ROLE / DIRECTION: {job_direction or 'Not specified'}

PROJECT CONTENT (files/text, may be truncated):
{project_text}

Return a JSON object:
{{
  "title": "a short descriptive name for the project",
  "summary": "3-4 sentences on what the project does and how it is built",
  "tech_stack": ["concrete technologies/languages/frameworks actually used"],
  "key_components": ["3-6 notable modules, features or design decisions"],
  "strengths": ["2-4 things done well"],
  "concerns": ["2-4 weaknesses, risks or questionable choices worth probing"],
  "probe_topics": ["4-8 specific, project-grounded things an interviewer should ask about"]
}}
Base everything ONLY on the provided content. Be concrete and reference real
names from the project where possible."""

    try:
        data = chat_json(prompt, system="You are a meticulous senior engineer "
                         "reviewing a project submission.", temperature=0.2)
    except Exception:
        return None

    for key in ("tech_stack", "key_components", "strengths", "concerns", "probe_topics"):
        if not isinstance(data.get(key), list):
            data[key] = []

    data.setdefault("title", "Submitted project")
    data.setdefault("summary", "")

    return data


def project_brief(project_summary):
    """Compact text block describing the project, for prompts."""
    if not project_summary:
        return "None provided."
    p = project_summary

    return (
        f"Title: {p.get('title','')}\n"
        f"Summary: {p.get('summary','')}\n"
        f"Tech stack: {', '.join(p.get('tech_stack', [])) or 'N/A'}\n"
        f"Key components: {', '.join(p.get('key_components', [])) or 'N/A'}\n"
        f"Concerns to probe: {', '.join(p.get('concerns', [])) or 'N/A'}\n"
        f"Suggested probe topics: {', '.join(p.get('probe_topics', [])) or 'N/A'}"
    )
