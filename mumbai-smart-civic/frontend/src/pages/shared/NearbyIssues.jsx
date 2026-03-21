import React, { useEffect, useMemo, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import ReportDetailsModal from '../../components/ReportDetailsModal';
import api from '../../utils/api';

function toErrorMessage(err, fallback = 'Unable to load nearby issues') {
    const detail = err?.response?.data?.detail;
    if (typeof detail === 'string' && detail.trim()) return detail;
    if (Array.isArray(detail) && detail.length > 0) {
        const first = detail[0];
        if (typeof first === 'string') return first;
        if (first && typeof first === 'object' && typeof first.msg === 'string') return first.msg;
    }
    return fallback;
}

function formatDistance(distance) {
    const meters = Number(distance || 0);
    if (meters >= 1000) return `${(meters / 1000).toFixed(2)} km`;
    return `${Math.round(meters)} m`;
}

function getDisplayStatus(issue) {
    return issue?.display_status || issue?.progress_status || issue?.status || 'Pending';
}

function statusClass(issue) {
    return String(getDisplayStatus(issue)).toLowerCase().replace(/\s+/g, '-');
}

export default function NearbyIssuesPage() {
    const navigate = useNavigate();
    const [searchParams] = useSearchParams();
    const [issues, setIssues] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState('');
    const [sortBy, setSortBy] = useState('distance');
    const [selectedIssue, setSelectedIssue] = useState(null);
    const [selectedReport, setSelectedReport] = useState(null);
    const [detailsLoading, setDetailsLoading] = useState(false);

    const lat = Number(searchParams.get('lat'));
    const lng = Number(searchParams.get('lng'));
    const radius = Number(searchParams.get('radius') || 2000);
    const focusIssueId = searchParams.get('focus');

    useEffect(() => {
        if (!Number.isFinite(lat) || !Number.isFinite(lng)) {
            setError('Missing or invalid map coordinates');
            setLoading(false);
            setIssues([]);
            return;
        }

        const fetchNearbyIssues = async () => {
            setLoading(true);
            try {
                const res = await api.get('/issues/nearby', {
                    params: { lat, lng, radius },
                });
                const rows = Array.isArray(res.data) ? res.data : [];
                setIssues(rows);
                setSelectedIssue(rows.find((item) => item.id === focusIssueId) || rows[0] || null);
                setError('');
            } catch (err) {
                setIssues([]);
                setSelectedIssue(null);
                setError(toErrorMessage(err));
            } finally {
                setLoading(false);
            }
        };

        fetchNearbyIssues();
    }, [focusIssueId, lat, lng, radius]);

    const sortedIssues = useMemo(() => {
        const rows = [...issues];
        rows.sort((a, b) => {
            if (sortBy === 'priority') {
                if (Number(b.priority_score || 0) !== Number(a.priority_score || 0)) {
                    return Number(b.priority_score || 0) - Number(a.priority_score || 0);
                }
                return Number(a.distance_m || 0) - Number(b.distance_m || 0);
            }
            return Number(a.distance_m || 0) - Number(b.distance_m || 0);
        });
        return rows;
    }, [issues, sortBy]);

    const openIssueDetails = async (issueId) => {
        setDetailsLoading(true);
        try {
            const res = await api.get(`/c/reports/${issueId}`);
            setSelectedReport(res.data || null);
        } catch (err) {
            setError(toErrorMessage(err, 'Unable to load issue details'));
        } finally {
            setDetailsLoading(false);
        }
    };

    return (
        <div className="page-container">
            <div className="table-glass-container nearby-dashboard-hero">
                <div>
                    <h2 className="section-title" style={{ marginBottom: 8 }}>Nearby Issues Dashboard</h2>
                    <p className="section-subtitle" style={{ marginBottom: 6 }}>
                        Issues discovered near the point you selected on the map.
                    </p>
                    <div className="nearby-dashboard-meta">
                        <span>Center: {Number.isFinite(lat) ? lat.toFixed(6) : '-'}, {Number.isFinite(lng) ? lng.toFixed(6) : '-'}</span>
                        <span>Radius: {formatDistance(radius)}</span>
                        <span>Results: {issues.length}</span>
                    </div>
                </div>
                <div style={{ display: 'flex', gap: 10, alignItems: 'center', flexWrap: 'wrap' }}>
                    <select value={sortBy} onChange={(e) => setSortBy(e.target.value)} className="form-input nearby-sort-select">
                        <option value="distance">Sort by Distance</option>
                        <option value="priority">Sort by Priority</option>
                    </select>
                    <button
                        type="button"
                        className="btn btn-ghost"
                        onClick={() => navigate(`/citizen/heatmap?lat=${lat}&lng=${lng}&radius=${radius}`)}
                    >
                        Back to Heatmap
                    </button>
                </div>
            </div>

            {error && (
                <div className="progress-error" style={{ marginTop: 12 }}>
                    {error}
                </div>
            )}

            <div className="nearby-dashboard-grid">
                <div className="table-glass-container">
                    <div className="table-head">
                        <h3 className="table-title">Nearby Complaint List</h3>
                    </div>
                    <div className="nearby-issue-list">
                        {loading && <div className="dashboard-empty"><p>Loading nearby issues...</p></div>}
                        {!loading && sortedIssues.length === 0 && <div className="dashboard-empty"><p>No issues found in this radius.</p></div>}
                        {!loading && sortedIssues.map((issue) => (
                            <button
                                type="button"
                                key={issue.id}
                                className={`glass-panel nearby-issue-row ${selectedIssue?.id === issue.id ? 'active' : ''}`}
                                onClick={() => setSelectedIssue(issue)}
                            >
                                <div className="nearby-issue-row-head">
                                    <span className={`badge-pill status-${statusClass(issue)}`}>{getDisplayStatus(issue)}</span>
                                    <span className="nearby-distance-chip">{formatDistance(issue.distance_m)}</span>
                                </div>
                                <div className="nearby-issue-title">{issue.description}</div>
                                <div className="nearby-issue-sub">
                                    {issue.ward || 'Unknown ward'} | Priority {Number(issue.priority_score || 0).toFixed(1)}
                                </div>
                                <div className="nearby-issue-sub">
                                    NGO: {issue.assigned_ngo_name || 'Not assigned'}
                                </div>
                            </button>
                        ))}
                    </div>
                </div>

                <div className="table-glass-container">
                    <div className="table-head">
                        <h3 className="table-title">Selected Issue</h3>
                    </div>
                    <div className="nearby-details-panel">
                        {!selectedIssue && !loading && (
                            <div className="dashboard-empty">
                                <p>Select any issue to inspect its details.</p>
                            </div>
                        )}
                        {selectedIssue && (
                            <>
                                <div className="nearby-detail-title">{selectedIssue.description}</div>
                                <div className="nearby-detail-grid">
                                    <div><strong>Status:</strong> {getDisplayStatus(selectedIssue)}</div>
                                    <div><strong>Distance:</strong> {formatDistance(selectedIssue.distance_m)}</div>
                                    <div><strong>Priority:</strong> {Number(selectedIssue.priority_score || 0).toFixed(1)}</div>
                                    <div><strong>NGO:</strong> {selectedIssue.assigned_ngo_name || 'Not assigned'}</div>
                                    <div><strong>Ward:</strong> {selectedIssue.ward || 'N/A'}</div>
                                    <div><strong>Category:</strong> {selectedIssue.category || 'General'}</div>
                                </div>
                                <div className="nearby-detail-actions">
                                    <button
                                        type="button"
                                        className="btn btn-primary-filled"
                                        disabled={detailsLoading}
                                        onClick={() => openIssueDetails(selectedIssue.id)}
                                    >
                                        {detailsLoading ? 'Loading...' : 'Open Issue Detail'}
                                    </button>
                                    <button
                                        type="button"
                                        className="btn btn-ghost"
                                        onClick={() => navigate(`/citizen/heatmap?lat=${lat}&lng=${lng}&radius=${radius}`)}
                                    >
                                        Recenter Map
                                    </button>
                                </div>
                            </>
                        )}
                    </div>
                </div>
            </div>

            <ReportDetailsModal
                report={selectedReport}
                open={Boolean(selectedReport)}
                onClose={() => setSelectedReport(null)}
            />
        </div>
    );
}
