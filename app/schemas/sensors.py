from pydantic import BaseModel


class SensorData(BaseModel):
    temperatura: float
    humedad: float
    luz: float
    ventilador: bool
    persianas: bool
    bulbs: bool
