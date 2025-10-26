from faster_whisper import WhisperModel


class WhisperDetector:
    def __init__(self, model_size="base", device="cpu", compute_type="int8"):
        self.model = WhisperModel(
            model_size, device=device, compute_type=compute_type)

    def getCleanTranscription(self, audio_path):
        segments, info = self.model.transcribe(
            audio_path,
            vad_filter=True,
            vad_parameters=dict(min_silence_duration_ms=500)
        )
        full_text = " ".join([segment.text for segment in segments])
        return full_text
