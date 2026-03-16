import React, { useEffect, useMemo, useState } from 'react';
import MapComponent from '../../components/MapComponent';
import HeatmapLayer from '../../components/HeatmapLayer';
import { SkeletonStats } from '../../components/Skeleton';
import api from '../../utils/api';

export default function Analytics() {
    const [points, setPoints] = useState([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        (async () => {
            try {
                const res = await api.get('/a/spatial-analytics');
                setPoints(Array.isArray(res.data) ? res.data : []);
            } catch {
                setPoints([
                    { lat: 19.076, lng: 72.8777, intensity: 0.9 },
                    { lat: 19.0544, lng: 72.8402, intensity: 0.75 },
                    { lat: 19.0896, lng: 72.8656, intensity: 0.95 },
                    { lat: 19.0178, lng: 72.8478, intensity: 0.55 },
                    { lat: 19.1136, lng: 72.8697, intensity: 0.6 },
                    { lat: 19.033, lng: 72.8454, intensity: 0.85 },
                    { lat: 19.0628, lng: 72.8736, intensity: 0.7 },
                    { lat: 19.099, lng: 72.8481, intensity: 1.0 },
                ]);
            } finally {
                setLoading(false);
            }
        })();
    }, []);

    const avg = useMemo(() => (
        points.length > 0
            ? (points.reduce((sum, point) => sum + point.intensity, 0) / points.length).toFixed(2)
            : '-'
    ), [points]);

    const peak = useMemo(() => (
        points.length > 0
            ? Math.max(...points.map((point) => point.intensity)).toFixed(2)
            : '-'
    ), [points]);

    return (
        <div className="page-container">
            <div className="analytics-head-panel">
                <div>
                    <h2 className="section-title" style={{ marginBottom: 8 }}>Spatial Analytics</h2>
                    <p className="section-subtitle" style={{ marginBottom: 0 }}>
                        Real-time civic complaint density across Mumbai wards and high-traffic neighborhoods.
                    </p>
                </div>
                <div className="analytics-head-chip-wrap">
                    <span className="analytics-head-chip">Mumbai Mode</span>
                    <span className="analytics-head-chip">Live Heat Intensity</span>
                </div>
            </div>

            {loading ? (
                <SkeletonStats count={3} />
            ) : (
                <div className="stats-grid">
                    <div className="stat-card blue">
                        <div className="stat-value">{points.length}</div>
                        <div className="stat-label">Data Points</div>
                    </div>
                    <div className="stat-card green">
                        <div className="stat-value">{avg}</div>
                        <div className="stat-label">Avg Intensity</div>
                    </div>
                    <div className="stat-card amber">
                        <div className="stat-value">{peak}</div>
                        <div className="stat-label">Peak Intensity</div>
                    </div>
                </div>
            )}

            <div className="glass-card table-glass-container" style={{ padding: 0, height: 500, overflow: 'hidden', marginTop: 24, border: '1px solid var(--glass-border-subtle)' }}>
                {loading ? (
                    <div className="skeleton" style={{ width: '100%', height: '100%' }} />
                ) : (
                    <MapComponent>
                        {points.length > 0 && (
                            <HeatmapLayer
                                fitBoundsOnLoad
                                fitBoundsOnUpdate
                                points={points}
                                longitudeExtractor={(m) => m.lng}
                                latitudeExtractor={(m) => m.lat}
                                intensityExtractor={(m) => m.intensity}
                            />
                        )}
                    </MapComponent>
                )}
            </div>
        </div>
    );
}
