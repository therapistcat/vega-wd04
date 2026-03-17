from fastapi import APIRouter, HTTPException, Depends
from typing import List
from app.schemas.traffic_schema import TrafficPredictionRequest, TrafficPredictionResponse
from app.services.traffic_service import get_traffic_service, TrafficService

router = APIRouter(
    prefix="/traffic",
    tags=["traffic"]
)

@router.post("/predict", response_model=TrafficPredictionResponse)
async def predict_traffic(
    request: TrafficPredictionRequest,
    service: TrafficService = Depends(get_traffic_service)
):
    try:
        # The service expects a list of 24/48 items
        return service.predict_congestion(request.data)
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Prediction error: {str(e)}")
