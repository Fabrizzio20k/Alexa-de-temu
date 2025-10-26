from fastapi import APIRouter, UploadFile, File, Depends
from app.schemas.transcription import TranscriptionResponse
from app.services.whisper_service import WhisperService

router = APIRouter()


def get_whisper_service():
    return WhisperService()


@router.post("/transcribe", response_model=TranscriptionResponse)
async def transcribe_audio(
    file: UploadFile = File(...),
    service: WhisperService = Depends(get_whisper_service)
):
    text = await service.transcribe_audio(file)
    return TranscriptionResponse(text=text)
