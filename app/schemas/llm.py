from pydantic import BaseModel


class SmartHomeRequest(BaseModel):
    request: str


class SmartHomeResponse(BaseModel):
    answer: str
    ventilador: bool
    persianas: bool
    bulbs: bool
