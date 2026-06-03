"""Robust human-name normalisation.

Fixes the common problems seen after CV extraction: ALL-CAPS surnames,
lowercase surnames, first and last name merged together (``JohnDoe``),
stray symbols/emails, and inconsistent casing.
"""

import re

_PARTICLES = {
    "de", "da", "di", "van", "von", "der", "den", "del", "della", "la",
    "le", "el", "du", "dos", "das", "bin", "ibn", "al", "y",
}

_SUFFIX_MAP = {
    "jr": "Jr.", "sr": "Sr.", "ii": "II", "iii": "III", "iv": "IV",
    "v": "V", "phd": "PhD", "md": "MD", "msc": "MSc", "bsc": "BSc",
}


def _split_camel(token):
    """Split merged names like ``JohnDoe`` -> ``John Doe``."""
    return re.sub(r"(?<=[a-z])(?=[A-Z])", " ", token)


def _cap(part):
    return part[:1].upper() + part[1:].lower() if part else part


def _cap_word(word):
    """Capitalise a single word, preserving hyphens and apostrophes."""
    # Handles hyphenated names (Anne-Marie) and apostrophes (O'Brien, D'Angelo).
    segments = word.split("-")

    out_segments = []
    for seg in segments:
        out_segments.append("'".join(_cap(p) for p in seg.split("'")))

    return "-".join(out_segments)


def format_full_name(raw):
    """Return a cleanly formatted full name, or ''."""
    if not raw or not isinstance(raw, str):
        return ""

    # Drop emails, phones, labels.
    name = re.split(r"[\n\r|,;:/\\]", raw)[0]
    name = re.sub(r"\S+@\S+", " ", name)            # emails
    name = re.sub(r"[^A-Za-zÀ-ɏ'\-.\s]", " ", name)  # keep letters/accents

    # Split merged camel-case tokens, then collapse whitespace.
    name = " ".join(_split_camel(t) for t in name.split())
    tokens = [t for t in name.split() if t]
    if not tokens:
        return ""

    n = len(tokens)
    out = []
    for i, token in enumerate(tokens):
        low = token.lower().strip(".")

        if low in _SUFFIX_MAP:
            out.append(_SUFFIX_MAP[low])

        elif low in _PARTICLES and 0 < i < n - 1:
            out.append(low)

        else:
            out.append(_cap_word(token))

    return " ".join(out).strip()


def split_first_last(full_name):
    """Split a formatted full name into (first, last)."""
    parts = [p for p in full_name.split() if p]

    if not parts:
        return "", ""

    if len(parts) == 1:
        return parts[0], ""

    core = [p for p in parts if p.lower().strip(".") not in _SUFFIX_MAP]
    if len(core) <= 1:
        return parts[0], ""

    return core[0], " ".join(core[1:])


def resolve_name(model_full=None, model_first=None, model_last=None, header_lines=None):
    """Reconcile name fields from the model and CV header into one clean name.

    Preference order: explicit full name -> first+last -> first non-empty
    header line that looks like a name.
    """
    candidate = ""
    if model_full and model_full.strip().lower() not in {"n/a", "unknown", ""}:
        candidate = model_full

    elif (model_first or model_last):
        candidate = f"{model_first or ''} {model_last or ''}"

    formatted = format_full_name(candidate)
    if formatted:
        return formatted

    for line in header_lines or []:
        if any(ch.isdigit() for ch in line):
            continue

        words = line.split()
        if 1 < len(words) <= 4 and "@" not in line:
            formatted = format_full_name(line)
            if formatted:
                return formatted

    return formatted or "Candidate"
