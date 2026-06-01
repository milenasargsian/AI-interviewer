"""Text-to-speech for reading interview questions aloud.

Uses gTSS (Google Text-to-Speech) which supports English, Armenian (hy) and
Russian (ru), needs no API key, and returns MP3 bytes that Streamlit can play
with ``st.audio``. Degrades gracefully if the package/network is unavailable.
"""

import io
from functools import lru_cache

_GTTS_LANG = {"en": "en", "hy": "hy", "ru": "ru"}


@lru_cache(maxsize=64)
def synthesize(text, lang="en"):
    """Return MP3 bytes for ``text`` in ``lang``, or None on failure.

    Cached so re-rendering the same question doesn't re-synthesize.
    """
    text = (text or "").strip()
    if not text:
        return None
    try:
        from gtts import gTTS
    except Exception:
        return None
    try:
        tts = gTTS(text=text[:600], lang=_GTTS_LANG.get(lang, "en"))
        buf = io.BytesIO()
        tts.write_to_fp(buf)
        buf.seek(0)
        return buf.getvalue()
    except Exception:
        return None
