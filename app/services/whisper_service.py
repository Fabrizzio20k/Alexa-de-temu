import subprocess
from pathlib import Path
from fastapi import UploadFile
import shutil
from app.modelos.whisper_detector import WhisperDetector


def convert_to_wav(input_audio: Path, output_wav: Path):
    subprocess.run([
        "ffmpeg",
        "-i", str(input_audio),
        "-ar", "16000",
        "-ac", "1",
        "-c:a", "pcm_s16le",
        str(output_wav)
    ], check=True)


class WhisperService:
    def __init__(self):
        self.detector = WhisperDetector(
            whisper_cli_path=Path("whisper.cpp/build/bin/whisper-cli"),
            model_path=Path("whisper.cpp/models/ggml-medium.bin")
        )
        self.temp_dir = Path("temp_audio")
        self.temp_dir.mkdir(exist_ok=True, parents=True)

    async def transcribe_audio(self, file: UploadFile) -> str:
        orig_file = self.temp_dir / file.filename

        with open(orig_file, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        if orig_file.suffix.lower() == ".opus":
            wav_file = self.temp_dir / (orig_file.stem + ".wav")
            convert_to_wav(orig_file, wav_file)
            transcription = self.detector.getCleanTranscription(str(wav_file))
            wav_file.unlink()
        else:
            transcription = self.detector.getCleanTranscription(str(orig_file))

        orig_file.unlink()
        return transcription
