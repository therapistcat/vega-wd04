from pydantic import BaseModel, Field


class DetectionItem(BaseModel):
    class_name: str = Field(alias="class")
    confidence: float
    bbox: list[float]

    model_config = {
        "populate_by_name": True,
    }


class DetectionResponse(BaseModel):
    detections: list[DetectionItem]
