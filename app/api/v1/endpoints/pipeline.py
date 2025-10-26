from fastapi import APIRouter, UploadFile, File, Depends, BackgroundTasks
from fastapi.responses import FileResponse
from app.services.pipeline_service import PipelineService
from pathlib import Path

router = APIRouter()


def get_pipeline_service():
    return PipelineService()


def cleanup_file(file_path: str):
    Path(file_path).unlink(missing_ok=True)


@router.post("/pipeline")
async def audio_pipeline(
    file: UploadFile = File(...),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    service: PipelineService = Depends(get_pipeline_service)
):
    output_file = await service.process_audio(file)

    background_tasks.add_task(cleanup_file, output_file)

    return FileResponse(
        output_file,
        media_type="audio/wav",
        filename="output.wav"
    )
