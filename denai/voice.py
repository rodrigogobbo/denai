"""Voice transcription via Whisper — optional feature."""

from __future__ import annotations

import tempfile
from pathlib import Path

from .logging_config import get_logger

log = get_logger("voice")

# Whisper is optional
try:
    import whisper  # type: ignore[import-untyped]

    WHISPER_AVAILABLE = True
except ImportError:
    WHISPER_AVAILABLE = False

_model = None


def get_whisper_model(size: str = "base"):
    """Lazy-load whisper model. Sizes: tiny, base, small, medium, large."""
    global _model
    if _model is None:
        log.info("Carregando modelo Whisper '%s'...", size)
        _model = whisper.load_model(size)
        log.info("Modelo Whisper carregado.")
    return _model


async def transcribe(audio_bytes: bytes, language: str = "pt") -> dict:
    """Transcribe audio bytes to text."""
    if not WHISPER_AVAILABLE:
        return {
            "error": "Whisper não instalado. Execute: pip install openai-whisper",
            "text": "",
        }

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        f.write(audio_bytes)
        tmp_path = f.name

    try:
        model = get_whisper_model()
        result = model.transcribe(tmp_path, language=language)
        text = result["text"].strip()
        detected = result.get("language", language)
        log.info("Transcrição: %d chars, idioma=%s", len(text), detected)
        return {"text": text, "language": detected}
    except Exception as e:
        log.error("Erro na transcrição: %s", e)
        return {"error": str(e), "text": ""}
    finally:
        Path(tmp_path).unlink(missing_ok=True)
