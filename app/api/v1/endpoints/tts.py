from fastapi import APIRouter, Depends
from fastapi.responses import FileResponse
from app.schemas.tts import TTSRequest
from app.services.tts_service import TTSService
from pathlib import Path
import uuid

router = APIRouter()


def get_tts_service():
    return TTSService()


@router.post("/tts")
async def text_to_speech(
    request: TTSRequest,
    service: TTSService = Depends(get_tts_service)
):
    output_file = Path("temp_audio") / f"{uuid.uuid4()}.wav"
    service.text_to_speech(request.text, str(output_file))

    return FileResponse(
        output_file,
        media_type="audio/wav",
        filename="speech.wav"
    )
