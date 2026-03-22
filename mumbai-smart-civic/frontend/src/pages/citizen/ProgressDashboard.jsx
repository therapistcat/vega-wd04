import React, { useEffect, useMemo, useState } from 'react';
import { MdEmojiEvents, MdSearch, MdTimeline } from 'react-icons/md';
import api from '../../utils/api';
import ReportDetailsModal from '../../components/ReportDetailsModal';
import { SkeletonStats } from '../../components/Skeleton';

const REFRESH_INTERVAL_MS = 15000;

function toErrorMessage(err, fallback = 'Unable to load progress data') {
    const detail = err?.response?.data?.detail;
    if (typeof detail === 'string' && detail.trim()) return detail;
    if (Array.isArray(detail) && detail.length > 0) {
        const first = detail[0];
        if (typeof first === 'string') return first;
        if (first && typeof first === 'object' && typeof first.msg === 'string') return first.msg;
    }
    return fallback;
}

export default function ProgressDashboard() {
    const [area, setArea] = useState('');
    const [loading, setLoading] = useState(true);
    const [fetching, setFetching] = useState(false);
    const [error, setError] = useState('');
    const [data, setData] = useState(null);
    const [selectedReport, setSelectedReport] = useState(null);
    const [showModal, setShowModal] = useState(false);

    const load = async (areaValue = area, initial = false, silent = false) => {
        if (initial) setLoading(true);
        else if (!silent) setFetching(true);
        setError('');
        try {
            const res = await api.get('/c/progress/overview', {
                params: {
                    area: areaValue || undefined,
                    limit_recent: 12,
                },
            });
            setData(res.data || null);
        } catch (err) {
            setError(toErrorMessage(err));
            setData(null);
        } finally {
            setLoading(false);
            if (!silent) setFetching(false);
        }
    };

    useEffect(() => {
        load('', true);
    }, []);

    useEffect(() => {
        const timer = setInterval(() => {
            load(area, false, true);
        }, REFRESH_INTERVAL_MS);
        return () => clearInterval(timer);
    }, [area]);

    const progressWidth = useMemo(() => {
        const value = Number(data?.resolution_rate || 0);
        return `${Math.min(100, Math.max(0, value))}%`;
    }, [data]);

    const statusBars = useMemo(() => {
        const source = Array.isArray(data?.status_distribution)
            ? data.status_distribution
            : [
                { label: 'Open', value: Number(data?.open_count || 0) },
                { label: 'In Progress', value: Number(data?.in_progress_count || 0) },
                { label: 'Resolved', value: Number(data?.resolved_count || 0) },
            ];
        const max = Math.max(1, ...source.map((item) => Number(item.value || 0)));
        return source.map((item) => ({
            ...item,
            width: `${Math.max(8, Math.round((Number(item.value || 0) / max) * 100))}%`,
        }));
    }, [data]);

    const trendRows = useMemo(() => {
        const rows = Array.isArray(data?.trend_points) ? data.trend_points : [];
        return rows.slice(-7).map((row) => ({
            label: String(row?.date || '').slice(5),
            open: Number(row?.open || 0),
            inProgress: Number(row?.in_progress || 0),
            resolved: Number(row?.resolved || 0),
            total: Number(row?.total || 0),
        }));
    }, [data]);

    const maxTrend = useMemo(() => Math.max(1, ...trendRows.map((row) => row.total)), [trendRows]);

    const levelProgress = useMemo(() => {
        const points = Number(data?.points || 0);
        const level = Number(data?.level || 1);
        const levelStart = Math.max(0, (level - 1) * 200);
        const levelEnd = Number(data?.next_level_points || level * 200);
        const span = Math.max(1, levelEnd - levelStart);
        const current = Math.max(0, points - levelStart);
        return {
            current,
            span,
            remaining: Math.max(0, levelEnd - points),
            width: `${Math.min(100, Math.round((current / span) * 100))}%`,
        };
    }, [data]);

    if (loading) {
        return (
            <div className="page-container progress-page">
                <SkeletonStats count={5} />
            </div>
        );
    }

    return (
        <div className="page-container progress-page">
            <div className="progress-hero">
                <div>
                    <h2>Progress Dashboard</h2>
                    <p>Track how much progress has been completed for reports in your area.</p>
                </div>
                <form
                    className="progress-search"
                    onSubmit={(e) => {
                        e.preventDefault();
                        load();
                    }}
                >
                    <input
                        className="form-input"
                        value={area}
                        onChange={(e) => setArea(e.target.value)}
                        placeholder="Search area/ward (e.g. M Ward)"
                    />
                    <button type="submit" className="btn btn-primary-filled" disabled={fetching}>
                        <MdSearch /> {fetching ? 'Fetching...' : 'Search'}
                    </button>
                </form>
            </div>

            {error && <div className="progress-error">{error}</div>}

            <div className="progress-card-grid">
                <div className="progress-stat-card warm">
                    <h3>Total Reports</h3>
                    <div>{data?.total_reports ?? 0}</div>
                </div>
                <div className="progress-stat-card green">
                    <h3>Resolved</h3>
                    <div>{data?.resolved_count ?? 0}</div>
                </div>
                <div className="progress-stat-card red">
                    <h3>Open</h3>
                    <div>{data?.open_count ?? 0}</div>
                </div>
                <div className="progress-stat-card amber">
                    <h3>In Progress</h3>
                    <div>{data?.in_progress_count ?? 0}</div>
                </div>
                <div className="progress-stat-card blue">
                    <h3>Your Reports</h3>
                    <div>{data?.my_reports ?? 0}</div>
                </div>
            </div>

            <div className="progress-flex-grid">
                <div className="table-glass-container">
                    <div className="dash-section-head">
                        <h3><MdEmojiEvents style={{ verticalAlign: 'middle', marginRight: 6 }} /> Civic Score</h3>
                    </div>
                    <div style={{ padding: 16 }}>
                        <div className="civic-score-head">
                            <div>
                                <div className="civic-score-points">{Number(data?.points || 0)} pts</div>
                                <div className="civic-score-level">Level {Number(data?.level || 1)}</div>
                            </div>
                            <div className="civic-score-next">{levelProgress.remaining} pts to next level</div>
                        </div>
                        <div className="progress-bar-wrap" style={{ marginTop: 10 }}>
                            <div className="progress-bar-fill" style={{ width: levelProgress.width }} />
                        </div>
                        <div className="badge-cloud">
                            {(data?.badges || []).map((badge) => (
                                <span key={badge} className="civic-badge">{badge}</span>
                            ))}
                        </div>
                    </div>
                </div>

                <div className="table-glass-container">
                    <div className="dash-section-head">
                        <h3>Status Distribution</h3>
                    </div>
                    <div style={{ padding: 16, display: 'grid', gap: 10 }}>
                        {statusBars.map((item) => (
                            <div key={item.label} className="status-bar-row">
                                <div className="status-bar-head">
                                    <span>{item.label}</span>
                                    <strong>{item.value}</strong>
                                </div>
                                <div className="status-bar-track">
                                    <div className={`status-bar-fill ${String(item.label).toLowerCase().replace(/\s+/g, '-')}`} style={{ width: item.width }} />
                                </div>
                            </div>
                        ))}
                    </div>
                </div>
            </div>

            <div className="table-glass-container" style={{ marginTop: 18 }}>
                <div className="dash-section-head">
                    <h3><MdTimeline style={{ verticalAlign: 'middle', marginRight: 6 }} /> Overall Progress</h3>
                </div>
                <div style={{ padding: 16 }}>
                    <div className="progress-bar-wrap">
                        <div className="progress-bar-fill" style={{ width: progressWidth }} />
                    </div>
                    <div className="progress-rate">
                        Resolved Progress: <strong>{Number(data?.resolution_rate || 0).toFixed(2)}%</strong>
                        {' '}| Your Resolution Rate: <strong>{Number(data?.my_resolution_rate || 0).toFixed(2)}%</strong>
                    </div>
                </div>
            </div>

            <div className="table-glass-container" style={{ marginTop: 18 }}>
                <div className="dash-section-head">
                    <h3>7-Day Reporting Trend</h3>
                </div>
                <div className="trend-grid">
                    {trendRows.length === 0 && (
                        <div style={{ fontSize: 14, color: 'var(--text-muted)' }}>No trend data available.</div>
                    )}
                    {trendRows.map((row) => (
                        <div key={row.label} className="trend-col">
                            <div className="trend-bars">
                                <div
                                    className="trend-bar open"
                                    style={{ height: `${Math.max(2, (row.open / maxTrend) * 120)}px` }}
                                    title={`Open: ${row.open}`}
                                />
                                <div
                                    className="trend-bar progress"
                                    style={{ height: `${Math.max(2, (row.inProgress / maxTrend) * 120)}px` }}
                                    title={`In Progress: ${row.inProgress}`}
                                />
                                <div
                                    className="trend-bar resolved"
                                    style={{ height: `${Math.max(2, (row.resolved / maxTrend) * 120)}px` }}
                                    title={`Resolved: ${row.resolved}`}
                                />
                            </div>
                            <div className="trend-total">{row.total}</div>
                            <div className="trend-label">{row.label}</div>
                        </div>
                    ))}
                </div>
            </div>

            <div className="table-glass-container" style={{ marginTop: 18 }}>
                <div className="dash-section-head">
                    <h3>Recent Reports</h3>
                    <span className="feed-count">{(data?.recent_reports || []).length} items</span>
                </div>
                <div style={{ padding: 14, display: 'grid', gap: 10 }}>
                    {(data?.recent_reports || []).length === 0 && (
                        <div style={{ fontSize: 14, color: 'var(--text-muted)' }}>No reports found.</div>
                    )}
                    {(data?.recent_reports || []).map((report) => (
                        <button
                            type="button"
                            key={report.id}
                            className="glass-panel progress-report-row"
                            onClick={() => {
                                setSelectedReport(report);
                                setShowModal(true);
                            }}
                        >
                            <div className="progress-report-row-title">{report.description?.slice(0, 120) || 'Report'}</div>
                            <div className="progress-report-row-meta">
                                <span>{report.ward} | {report.status}</span>
                                <span>By {report.reporter?.name || 'Unknown'}</span>
                                <span>{report.created_at ? new Date(report.created_at).toLocaleString() : '-'}</span>
                            </div>
                        </button>
                    ))}
                </div>
            </div>

            <ReportDetailsModal
                report={selectedReport}
                open={showModal}
                onClose={() => setShowModal(false)}
            />
        </div>
    );
}
