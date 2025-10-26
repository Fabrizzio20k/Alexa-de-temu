from fastapi import APIRouter
from app.api.v1.endpoints import transcribe, tts, pipeline, llm

api_router = APIRouter()
api_router.include_router(transcribe.router, tags=["transcription"])
api_router.include_router(tts.router, tags=["tts"])
api_router.include_router(pipeline.router, tags=["pipeline"])
api_router.include_router(llm.router, tags=["llm"])
