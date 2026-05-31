import tempfile
import os


def transcribe_audio(audio_bytes: bytes, api_key: str) -> str:
    """
    Transcribe audio using Groq's free Whisper API.
    No local model download needed — runs in the cloud.

    Args:
        audio_bytes: Raw audio bytes from audio_recorder_streamlit
        api_key: Groq API key (free at console.groq.com)

    Returns:
        Transcribed text string
    """
    try:
        from groq import Groq
    except ImportError:
        raise ImportError("Run: pip install groq")

    if not audio_bytes:
        return ""

    client = Groq(api_key=api_key)

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        f.write(audio_bytes)
        tmp_path = f.name

    try:
        with open(tmp_path, "rb") as audio_file:
            transcription = client.audio.transcriptions.create(
                model="whisper-large-v3",
                file=audio_file,
                response_format="text",
                language="en",
            )
        text = transcription if isinstance(transcription, str) else transcription.text
        return text.strip()

    except Exception as e:
        raise RuntimeError(f"Transcription failed: {str(e)}")

    finally:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
