from pathlib import Path
from app.services.whisper_service import WhisperService
from app.services.tts_service import TTSService
from app.services.llm_service import LLMService
from fastapi import UploadFile
import uuid


class PipelineService:
    def __init__(self):
        self.whisper_service = WhisperService()
        self.tts_service = TTSService()
        self.llm_service = LLMService()
        self.temp_dir = Path("temp_audio")
        self.temp_dir.mkdir(exist_ok=True)

    async def process_audio(self, file: UploadFile, context: dict) -> dict:
        transcription = await self.whisper_service.transcribe_audio(file)

        context['request'] = transcription

        llm_response = self.llm_service.generate_smart_home_response(context)

        output_file = self.temp_dir / f"{uuid.uuid4()}.wav"
        self.tts_service.text_to_speech(
            llm_response['answer'], str(output_file))

        return {
            "transcription": transcription,
            "answer": llm_response['answer'],
            "audio_file": str(output_file),
            "ventilador": llm_response['ventilador'],
            "persianas": llm_response['persianas'],
            "bulbs": llm_response['bulbs']
        }
