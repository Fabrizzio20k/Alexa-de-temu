from fastapi import FastAPI
from app.core.config import settings
from app.api.v1.router import api_router
from app.core.model_downloader import ensure_models

ensure_models()

app = FastAPI(title=settings.PROJECT_NAME)

app.include_router(api_router, prefix="/api/v1")
