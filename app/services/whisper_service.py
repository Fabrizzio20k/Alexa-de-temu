from pathlib import Path
from fastapi import UploadFile
import shutil
from app.modelos.whisper_detector import WhisperDetector
from app.core.config import settings


class WhisperService:
    def __init__(self):
        self.detector = WhisperDetector(
            model_size=settings.WHISPER_MODEL_SIZE,
            device=settings.WHISPER_DEVICE,
            compute_type=settings.WHISPER_COMPUTE_TYPE
        )
        self.temp_dir = Path(settings.TEMP_AUDIO_DIR)
        self.temp_dir.mkdir(exist_ok=True)

    async def transcribe_audio(self, file: UploadFile) -> str:
        temp_file = self.temp_dir / file.filename

        with open(temp_file, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        transcription = self.detector.getCleanTranscription(str(temp_file))
        temp_file.unlink()

        return transcription
