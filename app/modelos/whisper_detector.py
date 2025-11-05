import subprocess
from pathlib import Path
import re


class WhisperDetector:
    def __init__(self, whisper_cli_path: Path, model_path: Path):
        self.whisper_cli_path = whisper_cli_path
        self.model_path = model_path

    def getCleanTranscription(self, audio_path: str) -> str:
        result = subprocess.run([
            str(self.whisper_cli_path),
            "-m", str(self.model_path),
            "-f", audio_path,
            "--threads", "8",
            "--language", "es"
        ], capture_output=True, text=True)

        if result.returncode != 0:
            raise RuntimeError(f"Error transcribiendo audio: {result.stderr}")

        lines = []
        for line in result.stdout.strip().split("\n"):
            match = re.match(r"\[[^\]]+\]\s+(.*)", line)
            if match:
                lines.append(match.group(1).strip())

        transcription = " ".join(lines)
        return transcription
