import React, { useState } from 'react';
import Badge from '../../components/ui/Badge';
import api from '../../utils/api';
import { SkeletonStats } from '../../components/Skeleton';
import { 
  FaCarSide, 
  FaClock, 
  FaCloudSun, 
  FaExclamationTriangle, 
  FaChartLine 
} from 'react-icons/fa';

export default function TrafficPrediction() {
    const [loading, setLoading] = useState(false);
    const [prediction, setPrediction] = useState(null);
    const [error, setError] = useState(null);

    const generateMockData = () => {
        const mockData = [];
        const now = new Date();
        for (let i = 0; i < 48; i++) {
            const time = new Date(now.getTime() + i * 60 * 60 * 1000);
            mockData.push({
                temp: 290 + Math.random() * 20, // 290K to 310K
                rain_1h: Math.random() > 0.8 ? Math.random() * 5 : 0,
                snow_1h: 0,
                clouds_all: Math.floor(Math.random() * 100),
                weather_main: ['Clear', 'Clouds', 'Rain'][Math.floor(Math.random() * 3)],
                is_holiday: false,
                is_weekend: time.getDay() === 0 || time.getDay() === 6,
                hour: time.getHours(),
                day_of_week: time.getDay(),
                month: time.getMonth() + 1
            });
        }
        return mockData;
    };

    const handlePredict = async () => {
        setLoading(true);
        setError(null);
        setPrediction(null);
        
        try {
            const data = generateMockData();
            const res = await api.post('/traffic/predict', { data });
            setPrediction(res.data);
        } catch (err) {
            console.error(err);
            setError("Failed to fetch prediction. Ensure backend is running.");
        } finally {
            setLoading(false);
        }
    };

    const getLevelColor = (level) => {
        switch (level) {
            case 'LOW': return '#4caf50';
            case 'MEDIUM': return '#ff9800';
            case 'HIGH': return '#f44336';
            default: return '#9e9e9e';
        }
    };

    return (
        <div className="page-container">
            <div className="analytics-head-panel" style={{ marginBottom: 30 }}>
                <div>
                    <h2 className="section-title" style={{ marginBottom: 8 }}>
                        <FaCarSide style={{ marginRight: 10, verticalAlign: 'middle' }} />
                        Traffic Congestion Prediction
                    </h2>
                    <p className="section-subtitle" style={{ marginBottom: 0 }}>
                        Predicting Mumbai's next-hour traffic volume using advanced LSTM neural networks based on weather and temporal patterns.
                    </p>
                </div>
            </div>

            <div className="stats-grid" style={{ marginBottom: 30 }}>
                <div className="stat-card blue">
                    <div className="stat-value">LSTM</div>
                    <div className="stat-label">Model Architecture</div>
                </div>
                <div className="stat-card green">
                    <div className="stat-value">24h</div>
                    <div className="stat-label">Sequence Length</div>
                </div>
                <div className="stat-card amber">
                    <div className="stat-value">85%</div>
                    <div className="stat-label">Accuracy Target</div>
                </div>
            </div>

            <div className="glass-card" style={{ textAlign: 'center', padding: '40px 20px' }}>
                {!prediction && !loading && (
                    <>
                        <div style={{ fontSize: '4rem', color: 'var(--primary-light)', marginBottom: 20, opacity: 0.7 }}>
                            <FaChartLine />
                        </div>
                        <h3>Ready to Predict?</h3>
                        <p style={{ color: 'var(--text-muted)', maxWidth: 500, margin: '0 auto 25px' }}>
                            Generate 48 hours of simulated weather and temporal data to see the predicted congestion level for the next hour.
                        </p>
                        <button className="primary-btn" onClick={handlePredict} style={{ padding: '12px 30px' }}>
                            Generate Data & Predict
                        </button>
                    </>
                )}

                {loading && (
                    <div style={{ padding: '20px' }}>
                        <SkeletonStats count={1} />
                        <p style={{ marginTop: 15 }}>Running inference...</p>
                    </div>
                )}

                {prediction && (
                    <div className="prediction-result fade-in">
                        <h4 style={{ textTransform: 'uppercase', letterSpacing: '1px', color: 'var(--text-muted)', marginBottom: 10 }}>
                            Next Hour Prediction
                        </h4>
                        <div style={{ 
                            fontSize: '3.5rem', 
                            fontWeight: 800, 
                            color: getLevelColor(prediction.congestion_level),
                            margin: '10px 0'
                        }}>
                            {prediction.congestion_level}
                        </div>
                        <div style={{ 
                            fontSize: '1.2rem', 
                            color: 'var(--text-light)',
                            marginBottom: 30
                        }}>
                            Estimated Volume Index: <strong>{prediction.prediction_value.toFixed(2)}</strong>
                        </div>
                        
                        <div style={{ 
                            display: 'flex', 
                            justifyContent: 'center', 
                            gap: '20px', 
                            flexWrap: 'wrap' 
                        }}>
                            <Badge borderColor={getLevelColor(prediction.congestion_level)} color="var(--text-light)">
                                {prediction.congestion_level === 'HIGH' ? <FaExclamationTriangle /> : <FaClock />} 
                                <span style={{ marginLeft: 8 }}>{prediction.congestion_level} Alert</span>
                            </Badge>
                        </div>

                        <button className="outline-btn" onClick={handlePredict} style={{ marginTop: 40 }}>
                            Re-run Simulation
                        </button>
                    </div>
                )}

                {error && (
                    <div style={{ color: '#f44336', marginTop: 20 }}>
                        <FaExclamationTriangle style={{ marginRight: 8 }} />
                        {error}
                    </div>
                )}
            </div>
            
            <div className="info-section" style={{ marginTop: 30 }}>
                <h4 className="section-title-sm">How it works</h4>
                <div className="glass-card" style={{ marginTop: 15, fontSize: '0.95rem', lineHeight: '1.6', color: 'var(--text-light)' }}>
                    Our system uses a Long Short-Term Memory (LSTM) network, a type of recurrent neural network capable of learning order dependence in sequence prediction problems. 
                    The model was trained on thousands of hours of historical traffic data in combination with local weather conditions (temperature, rain, cloud coverage) and seasonal variables.
                </div>
            </div>
        </div>
    );
}
