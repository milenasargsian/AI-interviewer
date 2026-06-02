"""Text-to-speech for reading interview questions aloud.

Uses gTTS (Google Text-to-Speech) which supports English, Armenian (hy) and
Russian (ru), needs no API key, and returns MP3 bytes that Streamlit can play
with ``st.audio``. Degrades gracefully if the package/network is unavailable.
"""

import io

_GTTS_LANG = {"en": "en", "hy": "hy", "ru": "ru"}

# Cache ONLY successful syntheses (keyed by text+lang). We must never cache a
# failure, otherwise a single offline moment would permanently disable audio.
_CACHE = {}


def synthesize_ex(text, lang="en"):
    """Return (mp3_bytes, error). On success error is None; on failure bytes is None."""
    text = (text or "").strip()
    if not text:
        return None, "empty text"

    key = (text[:600], lang)
    if key in _CACHE:
        return _CACHE[key], None

    try:
        from gtts import gTTS
    except Exception as err:
        return None, f"gTTS not installed ({err})"

    try:
        tts = gTTS(text=text[:600], lang=_GTTS_LANG.get(lang, "en"))
        buf = io.BytesIO()
        tts.write_to_fp(buf)
        data = buf.getvalue()
        _CACHE[key] = data  # cache success only
        return data, None
    except Exception as err:
        return None, f"network/synthesis error ({err})"


def synthesize(text, lang="en"):
    """Return MP3 bytes for ``text`` in ``lang``, or None on failure."""
    data, _ = synthesize_ex(text, lang)
    return data
