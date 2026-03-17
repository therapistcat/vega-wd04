import React, { useEffect, useMemo, useRef, useState } from 'react';
import MapComponent from '../../components/MapComponent';
import HeatmapLayer from '../../components/HeatmapLayer';
import { SkeletonStats } from '../../components/Skeleton';
import api from '../../utils/api';
import { CircleMarker, Popup } from 'react-leaflet';

const DEFAULT_CENTER = { lat: 19.048728, lng: 72.910852 };

export default function Analytics() {
    const [points, setPoints] = useState([]);
    const [loading, setLoading] = useState(true);
    const [center, setCenter] = useState([DEFAULT_CENTER.lat, DEFAULT_CENTER.lng]);
    const [locationSource, setLocationSource] = useState('fallback');
    const centerRef = useRef(center);

    const requestUserLocation = () =>
        new Promise((resolve) => {
            if (!navigator.geolocation) {
                resolve([DEFAULT_CENTER.lat, DEFAULT_CENTER.lng]);
                return;
            }

            navigator.geolocation.getCurrentPosition(
                (position) => {
                    setLocationSource('live');
                    resolve([position.coords.latitude, position.coords.longitude]);
                },
                () => {
                    setLocationSource('fallback');
                    resolve([DEFAULT_CENTER.lat, DEFAULT_CENTER.lng]);
                },
                {
                    enableHighAccuracy: true,
                    timeout: 10000,
                    maximumAge: 0,
                },
            );
        });

    const fetchAnalytics = async (lat, lng, showLoader = false) => {
        if (showLoader) setLoading(true);
        try {
            const res = await api.get('/a/spatial-analytics', {
                params: {
                    lat: lat || undefined,
                    lng: lng || undefined,
                    radius_m: lat && lng ? 5000 : undefined,
                },
            });
            setPoints(Array.isArray(res.data) ? res.data : []);
        } catch {
            // Fallback points for demo/authority if API fails
            setPoints([
                { lat: 19.076, lng: 72.8777, intensity: 0.9 },
                { lat: 19.0544, lng: 72.8402, intensity: 0.75 },
                { lat: 19.0896, lng: 72.8656, intensity: 0.95 },
                { lat: 19.0178, lng: 72.8478, intensity: 0.55 },
                { lat: 19.1136, lng: 72.8697, intensity: 0.6 },
            ]);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        const bootstrap = async () => {
            const [lat, lng] = await requestUserLocation();
            const newCenter = [lat, lng];
            setCenter(newCenter);
            centerRef.current = newCenter;
            await fetchAnalytics(lat, lng, true);
        };
        bootstrap();
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
                    <p className="section-subtitle" style={{ marginBottom: 8 }}>
                        Real-time civic complaint density across Mumbai wards and high-traffic neighborhoods.
                    </p>
                    <div style={{ display: 'flex', gap: '8px', marginTop: '4px' }}>
                        <button 
                            type="button"
                            className="btn btn-primary-filled" 
                            onClick={async () => {
                                const [lat, lng] = await requestUserLocation();
                                const newCenter = [lat, lng];
                                setCenter(newCenter);
                                centerRef.current = newCenter;
                                await fetchAnalytics(lat, lng, true);
                            }}
                            style={{ padding: '6px 14px', fontSize: '12px', borderRadius: '8px', display: 'flex', alignItems: 'center', gap: '4px' }}
                        >
                            📍 Locate & Focus
                        </button>
                    </div>
                </div>
                <div className="analytics-head-chip-wrap">
                    <span className="analytics-head-chip">{locationSource === 'live' ? 'Localized View' : 'Mumbai Wide'}</span>
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
                    <MapComponent center={center} zoom={14}>
                        <CircleMarker
                            center={center}
                            radius={locationSource === 'live' ? 12 : 9}
                            pathOptions={{
                                color: locationSource === 'live' ? '#3b82f6' : '#065f46',
                                fillColor: locationSource === 'live' ? '#60a5fa' : '#10b981',
                                fillOpacity: 0.8,
                                weight: 3,
                                className: locationSource === 'live' ? 'user-location-pulse' : ''
                            }}
                        >
                            <Popup>Authority Location</Popup>
                        </CircleMarker>

                        {points.length > 0 && (
                            <HeatmapLayer
                                fitBoundsOnLoad={locationSource === 'fallback'}
                                fitBoundsOnUpdate={locationSource === 'fallback'}
                                points={points}
                                longitudeExtractor={(m) => m.lng}
                                latitudeExtractor={(m) => m.lat}
                                intensityExtractor={(m) => m.intensity}
                                radius={35}
                                blur={25}
                            />
                        )}
                    </MapComponent>
                )}
            </div>
        </div>
    );
}
