from fastapi import APIRouter, UploadFile, File, Depends
from fastapi.responses import FileResponse
from app.services.pipeline_service import PipelineService

router = APIRouter()


def get_pipeline_service():
    return PipelineService()


@router.post("/pipeline")
async def audio_pipeline(
    file: UploadFile = File(...),
    service: PipelineService = Depends(get_pipeline_service)
):
    output_file = await service.process_audio(file)

    return FileResponse(
        output_file,
        media_type="audio/wav",
        filename="output.wav"
    )
