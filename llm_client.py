"""Centralised LLM client and helpers (Groq).

All modules import from here so the API key, model selection and JSON
handling live in a single place. Groq is used because it is one of the
fastest inference providers available and the project is already keyed for
it — this is what makes the analysis fast without sacrificing quality.
"""

import os
import json
import time
from functools import lru_cache

from dotenv import load_dotenv
from groq import Groq

# Load environment variables from the conventional ``.env`` file and also
# from the legacy ``env`` file used by earlier versions of this project.
load_dotenv()
load_dotenv("env")

# ---------------------------------------------------------------------------
# Model configuration
# ---------------------------------------------------------------------------
# A 70B model gives strong, accurate analysis; Groq still returns it in a
# couple of seconds. All models can be overridden via environment variables.
TEXT_MODEL = os.getenv("GROQ_TEXT_MODEL", "llama-3.3-70b-versatile")
FAST_MODEL = os.getenv("GROQ_FAST_MODEL", "llama-3.1-8b-instant")
TRANSCRIBE_MODEL = os.getenv("GROQ_TRANSCRIBE_MODEL", "whisper-large-v3")

# Keep prompts fast and within context by trimming very long CVs.
MAX_CV_CHARS = int(os.getenv("MAX_CV_CHARS", "9000"))


@lru_cache(maxsize=1)
def get_client():
    """Return a cached Groq client, raising a clear error if unconfigured."""
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key or "your_actual_api_key" in api_key:
        raise RuntimeError(
            "GROQ_API_KEY is not configured. Create a file named '.env' "
            "next to the app with a line like:\n\nGROQ_API_KEY=gsk_...\n"
        )
    return Groq(api_key=api_key.strip().strip("'\""))


def chat_json(prompt, *, system=None, temperature=0.3, model=None, max_retries=2):
    """Call the chat API and return parsed JSON, with retries.

    Uses Groq's native JSON response mode so we never have to hand-parse
    markdown fences, which was a frequent source of failures before.
    """
    client = get_client()
    messages = [{
        "role": "system",
        "content": (system or "You are a precise assistant.")
        + " Always respond with a single valid JSON object and nothing else.",
    }, {"role": "user", "content": prompt}]

    # Try the primary model, then fall back to the fast model if the daily
    # token limit (429) on the big model is hit, so the app keeps working.
    models = _model_chain(model)
    last_err = None
    for mdl in models:
        for attempt in range(max_retries + 1):
            try:
                resp = client.chat.completions.create(
                    model=mdl,
                    messages=messages,
                    temperature=temperature,
                    response_format={"type": "json_object"},
                )
                return json.loads(resp.choices[0].message.content)
            except Exception as err:
                last_err = err
                if _is_rate_limit(err):
                    break  # don't retry same model; move to fallback
                time.sleep(0.6 * (attempt + 1))
    raise last_err


def chat_text(prompt, *, system=None, temperature=0.5, model=None):
    """Call the chat API and return free-form text (with model fallback)."""
    client = get_client()
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    last_err = None
    for mdl in _model_chain(model):
        try:
            resp = client.chat.completions.create(
                model=mdl, messages=messages, temperature=temperature)
            return resp.choices[0].message.content.strip()
        except Exception as err:
            last_err = err
            if not _is_rate_limit(err):
                raise
    raise last_err


def _model_chain(model):
    """Primary model first, then the fast model as a fallback (deduped)."""
    primary = model or TEXT_MODEL
    chain = [primary]
    if FAST_MODEL and FAST_MODEL != primary:
        chain.append(FAST_MODEL)
    return chain


def _is_rate_limit(err):
    """True if the error is a 429 / daily-token-limit error."""
    s = str(err).lower()
    return ("429" in s or "rate_limit" in s or "rate limit" in s
            or "tokens per day" in s or "tpd" in s)


_LANG_NAMES = {"en": "English", "hy": "Armenian", "ru": "Russian"}


def lang_directive(lang):
    """A sentence telling the model which language to write human-facing text in.

    JSON keys/structure stay as specified; only the *values* the candidate
    reads (questions, feedback, narrative) are translated.
    """
    name = _LANG_NAMES.get(lang or "en", "English")
    if name == "English":
        return ""
    return (f" Write ALL human-readable text values (questions, feedback, "
            f"summaries, narrative) in {name}. Keep every JSON key exactly as "
            f"specified in English.")


def trim_cv(text):
    """Trim CV text to keep requests fast without losing the substance."""
    if not text:
        return ""
    text = text.strip()
    if len(text) <= MAX_CV_CHARS:
        return text
    # Keep the top (contact + summary + recent experience) which carries
    # the most signal, plus a tail so nothing critical is silently dropped.
    head = text[: int(MAX_CV_CHARS * 0.8)]
    tail = text[-int(MAX_CV_CHARS * 0.2):]
    return head + "\n...\n" + tail
