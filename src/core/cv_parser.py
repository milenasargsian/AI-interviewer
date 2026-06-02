"""PDF text extraction for CVs."""

import re
import PyPDF2


def extract_text_from_pdf(uploaded_file):
    """Extract and lightly normalise text from an uploaded PDF file."""
    reader = PyPDF2.PdfReader(uploaded_file)
    chunks = []
    for page in reader.pages:
        try:
            chunks.append(page.extract_text() or "")
        except Exception:
            chunks.append("")
    text = "\n".join(chunks)

    # Normalise whitespace so prompts and the name detector behave well.
    text = text.replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def get_header_lines(text, n=10):
    """Return the first ``n`` non-empty lines, used as name candidates."""
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    return lines[:n]
