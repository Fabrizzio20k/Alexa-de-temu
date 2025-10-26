from fastapi import APIRouter, UploadFile, File, Depends, BackgroundTasks, Body
from fastapi.responses import FileResponse
from app.services.pipeline_service import PipelineService
from pathlib import Path
from pydantic import BaseModel

router = APIRouter()


class DeviceContext(BaseModel):
    temperature: float
    light_quantity: float
    humidity: float
    ventilador: bool
    persianas: bool
    bulbs: bool


def get_pipeline_service():
    return PipelineService()


def cleanup_file(file_path: str):
    Path(file_path).unlink(missing_ok=True)


@router.post("/pipeline")
async def audio_pipeline(
    file: UploadFile = File(...),
    temperature: float = Body(...),
    light_quantity: float = Body(...),
    humidity: float = Body(...),
    ventilador: bool = Body(...),
    persianas: bool = Body(...),
    bulbs: bool = Body(...),
    service: PipelineService = Depends(get_pipeline_service)
):
    context = {
        "temperature": temperature,
        "light_quantity": light_quantity,
        "humidity": humidity,
        "ventilador": ventilador,
        "persianas": persianas,
        "bulbs": bulbs
    }

    result = await service.process_audio(file, context)

    return {
        "transcription": result['transcription'],
        "answer": result['answer'],
        "audio_filename": Path(result['audio_file']).name,
        "ventilador": result['ventilador'],
        "persianas": result['persianas'],
        "bulbs": result['bulbs']
    }


@router.get("/audio/{filename}")
async def get_audio(filename: str, background_tasks: BackgroundTasks):
    file_path = Path("temp_audio") / filename

    if not file_path.exists():
        return {"error": "File not found"}

    background_tasks.add_task(cleanup_file, str(file_path))

    return FileResponse(
        file_path,
        media_type="audio/wav",
        filename="output.wav"
    )
