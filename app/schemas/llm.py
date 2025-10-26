from pydantic import BaseModel
from datetime import datetime
import pytz


class SmartHomeRequest(BaseModel):
    request: str
    temperature: float
    light_quantity: int
    humidity: float
    ventilador: bool
    persianas: bool
    bulbs: bool


class SmartHomeResponse(BaseModel):
    answer: str
    ventilador: bool
    persianas: bool
    bulbs: bool
