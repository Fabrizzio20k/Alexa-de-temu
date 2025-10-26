from fastapi import APIRouter, Depends
from app.schemas.llm import SmartHomeRequest, SmartHomeResponse
from app.services.llm_service import LLMService

router = APIRouter()


def get_llm_service():
    return LLMService()


@router.post("/smart-home", response_model=SmartHomeResponse)
async def smart_home(
    request: SmartHomeRequest,
    service: LLMService = Depends(get_llm_service)
):
    context = request.model_dump()
    result = service.generate_smart_home_response(context)
    return SmartHomeResponse(**result)
