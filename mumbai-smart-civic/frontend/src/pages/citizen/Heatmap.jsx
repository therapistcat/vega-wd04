import React, { useEffect, useMemo, useRef, useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { Circle, CircleMarker, Popup, useMapEvents } from 'react-leaflet';
import MapComponent from '../../components/MapComponent';
import HeatmapLayer from '../../components/HeatmapLayer';
import NearbyIssueClusterLayer from '../../components/NearbyIssueClusterLayer';
import MapLegend from '../../components/MapLegend';
import ReportDetailsModal from '../../components/ReportDetailsModal';
import api from '../../utils/api';

const DEFAULT_CENTER = { lat: 19.048728, lng: 72.910852 };
const REFRESH_INTERVAL_MS = 15000;

function toErrorMessage(err, fallback = 'Unable to load heatmap data') {
    const detail = err?.response?.data?.detail;
    if (typeof detail === 'string' && detail.trim()) return detail;
    if (Array.isArray(detail) && detail.length > 0) {
        const first = detail[0];
        if (typeof first === 'string') return first;
        if (first && typeof first === 'object' && typeof first.msg === 'string') return first.msg;
    }
    return fallback;
}

function sanitizePoints(rawPoints) {
    if (!Array.isArray(rawPoints)) return [];
    return rawPoints
        .map((item) => {
            const lat = Number(item?.lat);
            const lng = Number(item?.lng);
            const intensity = Number(item?.intensity);
            if (!Number.isFinite(lat) || !Number.isFinite(lng)) return null;
            if (lat < -90 || lat > 90 || lng < -180 || lng > 180) return null;
            return {
                lat,
                lng,
                intensity: Number.isFinite(intensity) ? Math.min(1, Math.max(0.05, intensity)) : 0.4,
            };
        })
        .filter(Boolean);
}

function formatDistance(distance) {
    const meters = Number(distance || 0);
    if (meters >= 1000) return `${(meters / 1000).toFixed(2)} km`;
    return `${Math.round(meters)} m`;
}

function MapClickCapture({ onClick }) {
    useMapEvents({
        click(event) {
            onClick?.(event.latlng);
        },
    });
    return null;
}

export default function Heatmap() {
    const navigate = useNavigate();
    const location = useLocation();
    const [points, setPoints] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState('');
    const [center, setCenter] = useState([DEFAULT_CENTER.lat, DEFAULT_CENTER.lng]);
    const [lastUpdated, setLastUpdated] = useState(null);
    const [locationSource, setLocationSource] = useState('fallback');
    const [areaQuery, setAreaQuery] = useState('');
    const [areaStatus, setAreaStatus] = useState('');
    const [areaLoading, setAreaLoading] = useState(false);
    const [areaData, setAreaData] = useState({
        summary: { total_reports: 0, open_count: 0, in_progress_count: 0, resolved_count: 0 },
        reports: [],
    });
    const [selectedReport, setSelectedReport] = useState(null);
    const [showReportModal, setShowReportModal] = useState(false);
    const [detailsLoading, setDetailsLoading] = useState(false);
    const [nearbyIssues, setNearbyIssues] = useState([]);
    const [nearbyLoading, setNearbyLoading] = useState(false);
    const [clickedPoint, setClickedPoint] = useState(null);
    const [nearbyRadius, setNearbyRadius] = useState(2000);
    const centerRef = useRef(center);

    const fetchHeatmap = async (lat, lng, showLoader = false) => {
        if (showLoader) setLoading(true);
        try {
            const res = await api.get('/c/spatial-analytics', {
                params: {
                    lat: lat || undefined,
                    lng: lng || undefined,
                    radius_m: lat && lng ? 5000 : undefined,
                    window_hours: 720,
                },
            });
            const livePoints = sanitizePoints(res.data);
            setPoints(livePoints);
            setLastUpdated(new Date());
            setError('');
        } catch (err) {
            setError(toErrorMessage(err));
            setPoints([]);
        } finally {
            setLoading(false);
        }
    };

    const fetchNearbyIssues = async (lat, lng, radius = nearbyRadius) => {
        setNearbyLoading(true);
        try {
            const res = await api.get('/issues/nearby', {
                params: { lat, lng, radius },
            });
            setNearbyIssues(Array.isArray(res.data) ? res.data : []);
            setError('');
        } catch (err) {
            setNearbyIssues([]);
            setError(toErrorMessage(err, 'Unable to load nearby issues'));
        } finally {
            setNearbyLoading(false);
        }
    };

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

    useEffect(() => {
        let disposed = false;

        const bootstrap = async () => {
            const [lat, lng] = await requestUserLocation();
            if (disposed) return;

            const newCenter = [lat, lng];
            centerRef.current = newCenter;
            setCenter(newCenter);
            await fetchHeatmap(lat, lng, true);
        };

        bootstrap();

        const interval = setInterval(() => {
            const [lat, lng] = centerRef.current;
            fetchHeatmap(lat, lng, false);
        }, REFRESH_INTERVAL_MS);

        return () => {
            disposed = true;
            clearInterval(interval);
        };
    }, []);

    useEffect(() => {
        const params = new URLSearchParams(location.search);
        const lat = Number(params.get('lat'));
        const lng = Number(params.get('lng'));
        const radius = Number(params.get('radius') || 2000);
        if (Number.isFinite(lat) && Number.isFinite(lng)) {
            const nextCenter = [lat, lng];
            setCenter(nextCenter);
            centerRef.current = nextCenter;
            setClickedPoint({ lat, lng });
            setNearbyRadius(radius);
        }
    }, [location.search]);

    useEffect(() => {
        if (clickedPoint?.lat && clickedPoint?.lng) {
            fetchNearbyIssues(clickedPoint.lat, clickedPoint.lng, nearbyRadius);
        }
    }, [clickedPoint, nearbyRadius]);

    const loadAreaReports = async () => {
        setAreaLoading(true);
        try {
            const res = await api.get('/c/reports/by-area', {
                params: {
                    area: areaQuery || undefined,
                    status: areaStatus || undefined,
                    limit: 120,
                },
            });
            const payload = res.data || {};
            const reports = Array.isArray(payload.reports) ? payload.reports : [];
            setAreaData({
                summary: payload.summary || { total_reports: 0, open_count: 0, in_progress_count: 0, resolved_count: 0 },
                reports,
            });
            setSelectedReport(null);
        } catch (err) {
            setError(toErrorMessage(err, 'Unable to fetch area reports'));
            setAreaData({
                summary: { total_reports: 0, open_count: 0, in_progress_count: 0, resolved_count: 0 },
                reports: [],
            });
            setSelectedReport(null);
        } finally {
            setAreaLoading(false);
        }
    };

    const openReportDetails = async (reportId) => {
        setDetailsLoading(true);
        try {
            const res = await api.get(`/c/reports/${reportId}`);
            setSelectedReport(res.data || null);
            setShowReportModal(true);
        } catch (err) {
            setError(toErrorMessage(err, 'Unable to fetch report details'));
        } finally {
            setDetailsLoading(false);
        }
    };

    useEffect(() => {
        if (!loading) {
            loadAreaReports();
        }
    }, [loading]);

    const subtitle = useMemo(() => {
        const [lat, lng] = center;
        return `Centered near ${lat.toFixed(6)}, ${lng.toFixed(6)} | Refreshes every ${REFRESH_INTERVAL_MS / 1000}s | Location: ${locationSource}`;
    }, [center, locationSource]);

    const nearbySubtitle = useMemo(() => {
        if (!clickedPoint) return 'Click anywhere on the map to inspect nearby issues.';
        return `${nearbyIssues.length} nearby issue${nearbyIssues.length === 1 ? '' : 's'} within ${formatDistance(nearbyRadius)} of ${clickedPoint.lat.toFixed(5)}, ${clickedPoint.lng.toFixed(5)}`;
    }, [clickedPoint, nearbyIssues.length, nearbyRadius]);

    return (
        <div className="page-container" id="heatmap-page">
            <div style={{ marginBottom: 18 }}>
                <h2 className="section-title">Complaint Heatmap</h2>
                <p className="section-subtitle" style={{ marginBottom: 4 }}>
                    Real-time MongoDB complaint intensity fetched from backend records.
                </p>
                <p style={{ fontSize: 12, color: 'var(--text-muted)', margin: 0 }}>
                    {subtitle}
                    {lastUpdated ? ` | Updated: ${lastUpdated.toLocaleTimeString()}` : ''}
                </p>
            </div>

            <div style={{ display: 'flex', gap: '10px', marginBottom: '16px', flexWrap: 'wrap' }}>
                <button
                    type="button"
                    className="btn btn-primary-filled"
                    onClick={async () => {
                        const [lat, lng] = await requestUserLocation();
                        const newCenter = [lat, lng];
                        setCenter(newCenter);
                        centerRef.current = newCenter;
                        await fetchHeatmap(lat, lng, true);
                    }}
                    style={{ padding: '8px 16px', fontSize: '13px', display: 'flex', alignItems: 'center', gap: '6px' }}
                >
                    <span style={{ fontSize: '18px' }}>Locate</span>
                </button>
                <button
                    type="button"
                    className="btn btn-ghost"
                    onClick={() => fetchHeatmap(center[0], center[1], true)}
                    style={{ padding: '8px 16px', fontSize: '13px' }}
                >
                    Refresh Heatmap
                </button>
            </div>

            {error && (
                <div style={{ marginBottom: 12, color: '#b91c1c', fontSize: 13, fontWeight: 600 }}>
                    {error}
                </div>
            )}

            <div className="table-glass-container" style={{ marginBottom: 14 }}>
                <div className="table-head">
                    <h3 className="table-title">Nearby Issue Explorer</h3>
                    <div style={{ display: 'flex', gap: 10, alignItems: 'center', flexWrap: 'wrap' }}>
                        <select
                            className="form-input nearby-radius-select"
                            value={nearbyRadius}
                            onChange={(e) => setNearbyRadius(Number(e.target.value))}
                        >
                            <option value={1000}>1 km radius</option>
                            <option value={1500}>1.5 km radius</option>
                            <option value={2000}>2 km radius</option>
                        </select>
                        <button
                            type="button"
                            className="btn btn-ghost"
                            disabled={!clickedPoint || nearbyLoading}
                            onClick={() => clickedPoint && fetchNearbyIssues(clickedPoint.lat, clickedPoint.lng, nearbyRadius)}
                        >
                            {nearbyLoading ? 'Loading Pins...' : 'Refresh Pins'}
                        </button>
                    </div>
                </div>
                <div style={{ padding: 14, fontSize: 13, color: 'var(--text-muted)' }}>
                    {nearbySubtitle}
                </div>
            </div>

            {loading ? (
                <div className="skeleton heatmap-skeleton" />
            ) : (
                <div>
                    <div className="heatmap-shell">
                        <MapComponent center={center} zoom={16} style={{ height: 'min(62vh, 560px)', minHeight: '320px' }}>
                            <MapClickCapture
                                onClick={(latlng) => {
                                    setClickedPoint({ lat: latlng.lat, lng: latlng.lng });
                                }}
                            />

                            <CircleMarker
                                center={center}
                                radius={locationSource === 'live' ? 12 : 9}
                                pathOptions={{
                                    color: locationSource === 'live' ? '#3b82f6' : '#065f46',
                                    fillColor: locationSource === 'live' ? '#60a5fa' : '#10b981',
                                    fillOpacity: 0.8,
                                    weight: 3,
                                    className: locationSource === 'live' ? 'user-location-pulse' : '',
                                }}
                            >
                                <Popup>
                                    <div style={{ textAlign: 'center' }}>
                                        <strong>You are here</strong><br />
                                        <span style={{ fontSize: '11px', color: '#666' }}>
                                            {locationSource === 'live' ? 'Live Geolocation' : 'Default Mumbai Center'}
                                        </span>
                                    </div>
                                </Popup>
                            </CircleMarker>

                            {points.length > 0 && (
                                <HeatmapLayer
                                    points={points}
                                    longitudeExtractor={(m) => m.lng}
                                    latitudeExtractor={(m) => m.lat}
                                    intensityExtractor={(m) => m.intensity}
                                    radius={30}
                                    blur={22}
                                    maxZoom={17}
                                    max={1.0}
                                />
                            )}

                            {clickedPoint && (
                                <Circle
                                    center={[clickedPoint.lat, clickedPoint.lng]}
                                    radius={nearbyRadius}
                                    pathOptions={{
                                        color: '#2563eb',
                                        fillColor: '#60a5fa',
                                        fillOpacity: 0.08,
                                        weight: 2,
                                    }}
                                />
                            )}

                            {nearbyIssues.length > 0 && (
                                <NearbyIssueClusterLayer
                                    issues={nearbyIssues}
                                    onViewDetails={(issue) => {
                                        navigate(`/issues/nearby?lat=${clickedPoint?.lat ?? center[0]}&lng=${clickedPoint?.lng ?? center[1]}&radius=${nearbyRadius}&focus=${issue.id}`);
                                    }}
                                />
                            )}
                        </MapComponent>
                        <MapLegend />
                    </div>

                    <div className="table-glass-container" style={{ marginTop: 14 }}>
                        <div className="dash-section-head">
                            <h3>Reports In This Area</h3>
                        </div>
                        <div style={{ padding: 14 }}>
                            <form
                                onSubmit={(e) => {
                                    e.preventDefault();
                                    loadAreaReports();
                                }}
                                className="area-search-form"
                            >
                                <input
                                    type="text"
                                    className="form-input"
                                    value={areaQuery}
                                    onChange={(e) => setAreaQuery(e.target.value)}
                                    placeholder="Search area/ward"
                                />
                                <select className="form-input" value={areaStatus} onChange={(e) => setAreaStatus(e.target.value)}>
                                    <option value="">All Status</option>
                                    <option value="Open">Open</option>
                                    <option value="In Progress">In Progress</option>
                                    <option value="Resolved">Resolved</option>
                                </select>
                                <button type="submit" className="btn btn-primary-filled" disabled={areaLoading}>
                                    {areaLoading ? 'Loading...' : 'Search'}
                                </button>
                            </form>

                            <div className="area-summary-grid">
                                <div className="glass-panel" style={{ padding: 10 }}>
                                    <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>Total</div>
                                    <div style={{ fontWeight: 700 }}>{areaData.summary.total_reports}</div>
                                </div>
                                <div className="glass-panel" style={{ padding: 10 }}>
                                    <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>Open</div>
                                    <div style={{ fontWeight: 700 }}>{areaData.summary.open_count}</div>
                                </div>
                                <div className="glass-panel" style={{ padding: 10 }}>
                                    <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>In Progress</div>
                                    <div style={{ fontWeight: 700 }}>{areaData.summary.in_progress_count}</div>
                                </div>
                                <div className="glass-panel" style={{ padding: 10 }}>
                                    <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>Resolved</div>
                                    <div style={{ fontWeight: 700 }}>{areaData.summary.resolved_count}</div>
                                </div>
                            </div>

                            <div className="area-reports-split">
                                <div className="area-reports-list">
                                    {areaData.reports.length === 0 && (
                                        <div style={{ fontSize: 13, color: 'var(--text-muted)' }}>No reports in this area.</div>
                                    )}
                                    {areaData.reports.map((r) => (
                                        <button
                                            type="button"
                                            key={r.id}
                                            className="glass-panel"
                                            onClick={() => openReportDetails(r.id)}
                                            style={{
                                                padding: 10,
                                                textAlign: 'left',
                                                border: selectedReport?.id === r.id ? '1px solid rgba(37,99,235,0.5)' : undefined,
                                            }}
                                        >
                                            <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>{r.ward} | {r.status}</div>
                                            <div style={{ fontSize: 13, fontWeight: 700 }}>{r.description?.slice(0, 70) || 'Report'}</div>
                                            <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>
                                                By: {r.reporter?.name || 'Unknown'}
                                            </div>
                                        </button>
                                    ))}
                                </div>

                                <div className="glass-panel" style={{ padding: 12 }}>
                                    <div style={{ fontSize: 13, color: 'var(--text-muted)' }}>
                                        Click any report to open full details in a popup.
                                    </div>
                                    {detailsLoading && (
                                        <div style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 6 }}>
                                            Loading report details...
                                        </div>
                                    )}
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            )}

            <ReportDetailsModal
                report={selectedReport}
                open={showReportModal}
                onClose={() => setShowReportModal(false)}
            />
        </div>
    );
}
