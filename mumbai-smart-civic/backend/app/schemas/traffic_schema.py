from pydantic import BaseModel
from typing import List

class TrafficInputItem(BaseModel):
    temp: float
    rain_1h: float
    snow_1h: float
    clouds_all: float
    weather_main: str
    is_holiday: bool
    is_weekend: bool

class TrafficPredictionRequest(BaseModel):
    data: List[TrafficInputItem]

class TrafficPredictionResponse(BaseModel):
    prediction_value: float
    congestion_level: str
