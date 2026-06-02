"""Speech-to-text using Groq Whisper.

We transcribe audio recorded in the browser (via ``st.audio_input``) rather
than reading a server-side microphone. This is accurate, works when the app
is deployed, and avoids fragile PyAudio/driver issues on Windows. Passing the
``language`` (e.g. 'hy', 'ru', 'en') improves accuracy for that language.
"""

import io

from src.core.llm_client import get_client, TRANSCRIBE_MODEL


def transcribe_audio_bytes(audio_bytes, filename="answer.wav", language=None):
    """Transcribe raw audio bytes. Returns (text, error_message)."""
    if not audio_bytes:
        return "", "No audio was recorded."

    client = get_client()
    audio_file = io.BytesIO(audio_bytes)
    audio_file.name = filename  # the SDK needs a filename hint

    try:
        kwargs = {"model": TRANSCRIBE_MODEL, "file": audio_file,
                  "response_format": "text"}
        if language:
            kwargs["language"] = language
        result = client.audio.transcriptions.create(**kwargs)
        text = result if isinstance(result, str) else getattr(result, "text", "")
        return (text or "").strip(), None
    except Exception as err:
        return "", f"Transcription failed: {err}"
