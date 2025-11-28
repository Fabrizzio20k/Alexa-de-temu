from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from app.services.mqtt_service import mqtt_service
from app.schemas.sensors import SensorData
import json
import asyncio


router = APIRouter()


@router.get("/sensors/stream")
async def stream_sensor_data():
    async def event_generator():
        print("🔴 New SSE client connected")
        try:
            while True:
                data = await asyncio.get_event_loop().run_in_executor(
                    None,
                    mqtt_service.get_data_blocking,
                    30
                )

                if data is None:
                    yield f"data: {json.dumps({'status': 'keepalive'})}\n\n"
                    print("💤 Keepalive sent")
                else:
                    json_data = json.dumps(data)
                    yield f"data: {json_data}\n\n"
                    print(f"📤 Data sent to client: {json_data}")

        except asyncio.CancelledError:
            print("🔵 SSE client disconnected")
        except Exception as e:
            print(f"❌ Stream error: {e}")

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


@router.get("/sensors/latest", response_model=SensorData)
async def get_latest_sensor_data():
    data = mqtt_service.get_latest_data()
    if data is None:
        return SensorData(
            temperatura=0.0,
            humedad=0.0,
            luz=0.0,
            ventilador=False,
            persianas=False,
            bulbs=False
        )
    return SensorData(**data)
