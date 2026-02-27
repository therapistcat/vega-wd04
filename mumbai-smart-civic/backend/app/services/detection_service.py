from __future__ import annotations

import logging
import threading
from pathlib import Path
from typing import Any

from fastapi.concurrency import run_in_threadpool

from app.core.config import BASE_DIR, settings

LOGGER = logging.getLogger(__name__)


class DetectionService:
    _instance: "DetectionService | None" = None
    _instance_lock = threading.Lock()

    def __init__(self) -> None:
        self._model: Any = None
        self._enabled = False
        self._model_path = Path(settings.model_path)
        if not self._model_path.is_absolute():
            self._model_path = (BASE_DIR / self._model_path).resolve()
        self._device = "cpu"
        self._names: dict[int, str] = {0: "garbage", 1: "pothole"}
        self._load_lock = threading.Lock()

    @classmethod
    def instance(cls) -> "DetectionService":
        with cls._instance_lock:
            if cls._instance is None:
                cls._instance = cls()
        return cls._instance

    @property
    def enabled(self) -> bool:
        return self._enabled

    def _class_conf_threshold(self, class_name: str) -> float:
        name = str(class_name or "").strip().lower()
        if name == "garbage" and settings.detection_conf_threshold_garbage is not None:
            return float(settings.detection_conf_threshold_garbage)
        if name == "pothole" and settings.detection_conf_threshold_pothole is not None:
            return float(settings.detection_conf_threshold_pothole)
        return float(settings.detection_conf_threshold)

    def _predict_conf_floor(self) -> float:
        values: list[float] = [float(settings.detection_conf_threshold)]
        if settings.detection_conf_threshold_garbage is not None:
            values.append(float(settings.detection_conf_threshold_garbage))
        if settings.detection_conf_threshold_pothole is not None:
            values.append(float(settings.detection_conf_threshold_pothole))
        return max(0.001, min(values))

    def load_model(self) -> None:
        if self._enabled:
            return
        with self._load_lock:
            if self._enabled:
                return

            if not self._model_path.exists():
                LOGGER.warning("Detection model not found at %s. Detection disabled.", self._model_path)
                self._enabled = False
                return

            try:
                from ultralytics import YOLO
                import torch

                self._device = "cuda" if torch.cuda.is_available() else "cpu"
                model = YOLO(str(self._model_path))
                model.to(self._device)
                self._model = model

                raw_names = getattr(model, "names", None)
                if isinstance(raw_names, dict) and raw_names:
                    self._names = {int(k): str(v) for k, v in raw_names.items()}
                elif isinstance(raw_names, list) and raw_names:
                    self._names = {idx: str(name) for idx, name in enumerate(raw_names)}

                self._enabled = True
                LOGGER.info(
                    "Detection model loaded from %s on %s",
                    self._model_path,
                    self._device,
                )
            except Exception:
                LOGGER.exception("Failed to load detection model from %s", self._model_path)
                self._enabled = False
                self._model = None

    def _predict(self, image_bgr: Any) -> list[dict[str, Any]]:
        if not self._enabled or self._model is None:
            return []

        results = self._model.predict(
            source=image_bgr,
            conf=self._predict_conf_floor(),
            iou=settings.detection_iou_threshold,
            max_det=settings.detection_max_det,
            verbose=False,
            device=self._device,
        )
        if not results:
            return []

        boxes = results[0].boxes
        if boxes is None:
            return []

        detections: list[dict[str, Any]] = []
        xyxy = boxes.xyxy.cpu().tolist()
        confs = boxes.conf.cpu().tolist()
        classes = boxes.cls.cpu().tolist()

        for idx, bbox in enumerate(xyxy):
            class_idx = int(classes[idx])
            class_name = self._names.get(class_idx, str(class_idx))
            confidence = float(confs[idx])
            if confidence < self._class_conf_threshold(class_name):
                continue
            detections.append(
                {
                    "class": class_name,
                    "confidence": round(confidence, 4),
                    "bbox": [round(float(v), 2) for v in bbox],
                }
            )
        detections.sort(key=lambda row: float(row.get("confidence", 0.0)), reverse=True)
        return detections

    async def detect_bytes(self, raw: bytes) -> list[dict[str, Any]]:
        self.load_model()
        if not self._enabled:
            return []

        try:
            import cv2
            import numpy as np
        except Exception as exc:
            raise RuntimeError("opencv-python-headless and numpy are required for detection") from exc

        arr = np.frombuffer(raw, dtype=np.uint8)
        image = cv2.imdecode(arr, cv2.IMREAD_COLOR)
        if image is None:
            raise ValueError("Invalid image bytes")
        return await run_in_threadpool(self._predict, image)

    async def detect_path(self, image_path: str | Path) -> list[dict[str, Any]]:
        self.load_model()
        if not self._enabled:
            return []

        try:
            import cv2
        except Exception as exc:
            raise RuntimeError("opencv-python-headless is required for detection") from exc

        image = cv2.imread(str(image_path))
        if image is None:
            raise ValueError(f"Unable to load image from {image_path}")
        return await run_in_threadpool(self._predict, image)


def get_detection_service() -> DetectionService:
    return DetectionService.instance()
