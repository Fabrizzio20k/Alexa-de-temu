from pathlib import Path
from app.services.whisper_service import WhisperService
from app.services.tts_service import TTSService
from fastapi import UploadFile
import uuid


class PipelineService:
    def __init__(self):
        self.whisper_service = WhisperService()
        self.tts_service = TTSService()
        self.temp_dir = Path("temp_audio")
        self.temp_dir.mkdir(exist_ok=True)

    async def process_audio(self, file: UploadFile) -> str:
        transcription = await self.whisper_service.transcribe_audio(file)

        output_file = self.temp_dir / f"{uuid.uuid4()}.wav"
        self.tts_service.text_to_speech(transcription, str(output_file))

        return str(output_file)
