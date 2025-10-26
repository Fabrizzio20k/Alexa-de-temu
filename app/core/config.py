from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    PROJECT_NAME: str = "Whisper API"
    TEMP_AUDIO_DIR: str = "temp_audio"
    WHISPER_MODEL_SIZE: str = "base"
    WHISPER_DEVICE: str = "cpu"
    WHISPER_COMPUTE_TYPE: str = "int8"

    class Config:
        env_file = ".env"


settings = Settings()
