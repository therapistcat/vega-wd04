import logging

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status

from app.core.security import require_roles
from app.schemas.detection_schema import DetectionResponse
from app.services.detection_service import get_detection_service

LOGGER = logging.getLogger(__name__)

router = APIRouter(tags=["detection"])


@router.post("/detect", response_model=DetectionResponse)
async def detect_objects(
    image: UploadFile = File(...),
    current_user: dict = Depends(require_roles(["citizen", "authority", "admin"])),
) -> DetectionResponse:
    _ = current_user
    if not image.content_type or not image.content_type.startswith("image/"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file must be an image",
        )

    raw = await image.read()
    if not raw:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Image is empty",
        )
    if len(raw) > 8 * 1024 * 1024:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Image exceeds 8MB",
        )

    service = get_detection_service()
    try:
        detections = await service.detect_bytes(raw)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        LOGGER.exception("Detection inference failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Detection inference failed",
        ) from exc

    return DetectionResponse.model_validate({"detections": detections})
