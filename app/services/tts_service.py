from pathlib import Path
from piper import PiperVoice
import wave


class TTSService:
    def __init__(self):
        self.model_path = "models/es_AR-daniela-high.onnx"
        self.voice = PiperVoice.load(self.model_path)

    def text_to_speech(self, text: str, output_path: str):
        with wave.open(output_path, "wb") as wav_file:
            self.voice.synthesize_wav(text, wav_file)
