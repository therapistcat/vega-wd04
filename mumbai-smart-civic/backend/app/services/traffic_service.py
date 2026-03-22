import os
import joblib
import numpy as np
import logging
from typing import List
from pathlib import Path
from app.core.config import settings
from app.schemas.traffic_schema import TrafficInputItem, TrafficPredictionResponse

logger = logging.getLogger(__name__)

class TrafficService:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(TrafficService, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
            
        self.model = None
        self.scaler_X = None
        self.scaler_y = None
        self.model_loaded = False
        
        # Paths to model files
        # Note: Using relative path from the app root
        model_dir = Path("backend/app/ml_models/traffic congestion")
        self.model_path = model_dir / "traffic_model.pkl"
        self.scaler_X_path = model_dir / "scaler_X.pkl"
        self.scaler_y_path = model_dir / "scaler_y.pkl"
        
        self.load_models()
        self._initialized = True

    def load_models(self):
        try:
            if self.model_path.exists() and self.scaler_X_path.exists() and self.scaler_y_path.exists():
                self.model = joblib.load(self.model_path)
                self.scaler_X = joblib.load(self.scaler_X_path)
                self.scaler_y = joblib.load(self.scaler_y_path)
                self.model_loaded = True
                logger.info("Traffic model and scalers loaded successfully.")
            else:
                logger.error(f"Traffic model files not found at {self.model_path}")
        except Exception as e:
            logger.error(f"Error loading traffic model: {str(e)}")

    def predict_congestion(self, items: List[TrafficInputItem]) -> TrafficPredictionResponse:
        if len(items) < 24:
            raise ValueError(f"Expected at least 24 hours of data, got {len(items)}")
        
        # Take the last 24 items if more are provided
        if len(items) > 24:
            items = items[-24:]

        # Preprocessing: Extract the 7 features
        # Training features: ['temp', 'rain_1h', 'snow_1h', 'clouds_all', 'hour', 'day_of_week', 'month']
        feature_data = []
        for i, item in enumerate(items):
            # Derive index-based features or use defaults
            hour = getattr(item, 'hour', i % 24)
            # Map is_weekend if day_of_week is missing
            is_weekend = getattr(item, 'is_weekend', False)
            day = getattr(item, 'day_of_week', 6 if is_weekend else 0)
            month = getattr(item, 'month', 1)
            
            feature_data.append([
                float(item.temp),
                float(item.rain_1h),
                float(item.snow_1h),
                float(item.clouds_all),
                float(hour),
                float(day),
                float(month)
            ])

        X = np.array(feature_data)
        
        # Safety checks for loaded models/scalers
        if not self.model_loaded or self.scaler_X is None or self.model is None or self.scaler_y is None:
             logger.warning("Models not fully loaded. Using fallback prediction values.")
             return TrafficPredictionResponse(
                prediction_value=4000.0,
                congestion_level="MEDIUM"
            )

        try:
            # Scale features
            X_scaled = self.scaler_X.transform(X)
            # Reshape for LSTM: (batch_size, sequence_length, features)
            X_reshaped = X_scaled.reshape(1, X_scaled.shape[0], X_scaled.shape[1])
            
            # Predict
            prediction_scaled = self.model.predict(X_reshaped)
            # Inverse scale prediction
            prediction = self.scaler_y.inverse_transform(prediction_scaled)[0][0]
            
            # Map to level using percentage of trained range
            y_max = getattr(self.scaler_y, 'data_max_', [8000])[0]
            y_min = getattr(self.scaler_y, 'data_min_', [0])[0]
            y_range = y_max - y_min
            
            percentage = (float(prediction) - float(y_min)) / float(y_range) if y_range != 0 else 0
            
            if percentage <= 0.33:
                level = "LOW"
            elif percentage <= 0.66:
                level = "MEDIUM"
            else:
                level = "HIGH"
                
            return TrafficPredictionResponse(
                prediction_value=float(prediction),
                congestion_level=level
            )
        except Exception as e:
            logger.error(f"Prediction logic error: {str(e)}")
            raise RuntimeError(f"Failed to process prediction: {str(e)}")

def get_traffic_service() -> TrafficService:
    return TrafficService()
