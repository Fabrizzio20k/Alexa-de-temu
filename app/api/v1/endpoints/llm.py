from fastapi import APIRouter, Depends, HTTPException
from app.schemas.llm import SmartHomeRequest, SmartHomeResponse
from app.services.llm_service import LLMService
from app.services.mqtt_service import mqtt_service

router = APIRouter()


def get_llm_service():
    return LLMService()


@router.post("/smart-home", response_model=SmartHomeResponse)
async def smart_home(
    request: SmartHomeRequest,
    service: LLMService = Depends(get_llm_service)
):
    sensor_data = mqtt_service.get_latest_data()

    if sensor_data is None:
        raise HTTPException(
            status_code=503,
            detail="No hay datos de sensores disponibles. Espere a que el ESP32 publique datos."
        )

    context = {
        "request": request.request,
        "temperature": sensor_data.get("temperatura", 20.0),
        "light_quantity": sensor_data.get("luz", 20.0),
        "humidity": sensor_data.get("humedad", 20.0),
        "ventilador": sensor_data.get("ventilador", True),
        "persianas": sensor_data.get("persianas", True),
        "bulbs": sensor_data.get("bulbs", True)
    }

    result = service.generate_smart_home_response(context)
    return SmartHomeResponse(**result)
