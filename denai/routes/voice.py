"""Rota de transcrição de voz."""

from __future__ import annotations

from fastapi import APIRouter, File, UploadFile

from ..voice import WHISPER_AVAILABLE, transcribe

router = APIRouter()

MAX_AUDIO_SIZE = 25 * 1024 * 1024  # 25 MB


@router.get("/api/voice/status")
async def voice_status():
    """Verifica se o Whisper está disponível."""
    return {"available": WHISPER_AVAILABLE}


@router.post("/api/voice/transcribe")
async def voice_transcribe(audio: UploadFile = File(...)):
    """Transcreve áudio para texto via Whisper."""
    if not WHISPER_AVAILABLE:
        return {"error": "Whisper não instalado. Execute: pip install openai-whisper", "text": ""}
    audio_bytes = await audio.read()
    if len(audio_bytes) > MAX_AUDIO_SIZE:
        return {"error": "Arquivo muito grande (máximo 25MB)", "text": ""}
    return await transcribe(audio_bytes)
