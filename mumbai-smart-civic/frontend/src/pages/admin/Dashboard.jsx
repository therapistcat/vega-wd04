import React, { useEffect, useMemo, useState } from 'react';
import {
    MdCheckCircle,
    MdPending,
    MdPeople,
    MdReport,
    MdTrendingUp,
    MdWarningAmber,
} from 'react-icons/md';
import { SkeletonBanner, SkeletonStats, SkeletonTable } from '../../components/Skeleton';
import Button from '../../components/ui/Button';
import api from '../../utils/api';

const BANNER_IMG = 'https://etimg.etb2bimg.com/thumb/msid-64080572%2Cimgsize-1682393%2Cwidth-1200%2Cheight%3D627%2Coverlay-etcio%2Cresizemode-75/internet-of-things/bscdcl-launches-indias-first-integrated-control-and-command-centre-in-madhya-pradesh.jpg';
const ADMIN_REFRESH_MS = 15000;

function toErrorMessage(err, fallback = 'Action failed') {
    const detail = err?.response?.data?.detail;
    if (typeof detail === 'string' && detail.trim()) return detail;
    if (Array.isArray(detail) && detail.length > 0) {
        const first = detail[0];
        if (typeof first === 'string') return first;
        if (first && typeof first === 'object' && typeof first.msg === 'string') return first.msg;
    }
    return fallback;
}

function computePriorityScore(complaint) {
    const created = complaint?.created_at ? new Date(complaint.created_at) : new Date();
    const ageHours = Math.max(0, (Date.now() - created.getTime()) / 36e5);
    const upvotes = Number(complaint?.upvotes_count || 0);
    const priority = Number(complaint?.priority_score || 0);
    const status = String(complaint?.status || '').toLowerCase();

    const freshBonus = Math.max(0, 2 - ageHours / 12);
    const statusBonus = status === 'open' ? 0.8 : (status === 'in progress' ? 0.4 : -0.5);
    const score = (upvotes * 2.5 * Math.pow(0.5, ageHours / 24)) + (priority * 2) + freshBonus + statusBonus;
    return Number(score.toFixed(2));
}

function toStatusClass(status) {
    return String(status || 'pending').toLowerCase().replace(/\s+/g, '-');
}

export default function AdminDashboard() {
    const [complaints, setComplaints] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState('');
    const [updatingIds, setUpdatingIds] = useState([]);
    const [toast, setToast] = useState(null);

    const fetchComplaints = async (silent = false) => {
        if (!silent) setLoading(true);
        try {
            const complaintsRes = await api.get('/a/complaints');
            const allComplaints = Array.isArray(complaintsRes.data)
                ? complaintsRes.data
                : complaintsRes.data.complaints || [];
            setComplaints(allComplaints);
            setError('');
        } catch (err) {
            setError(toErrorMessage(err, 'Unable to load authority dashboard'));
            if (!silent) setComplaints([]);
        } finally {
            if (!silent) setLoading(false);
        }
    };

    useEffect(() => {
        fetchComplaints(false);
        const timer = setInterval(() => fetchComplaints(true), ADMIN_REFRESH_MS);
        return () => clearInterval(timer);
    }, []);

    const stats = useMemo(() => {
        const total = complaints.length;
        const resolved = complaints.filter((c) => c.status === 'Resolved').length;
        const pending = complaints.filter((c) => c.status !== 'Resolved').length;
        const citizens = new Set(complaints.map((c) => c.user_id)).size;
        return { total, resolved, pending, citizens };
    }, [complaints]);

    const rankedComplaints = useMemo(() => {
        return [...complaints]
            .map((c) => ({ ...c, dashboard_score: computePriorityScore(c) }))
            .sort((a, b) => {
                if (b.dashboard_score !== a.dashboard_score) return b.dashboard_score - a.dashboard_score;
                return new Date(b.updated_at || b.created_at || 0).getTime() - new Date(a.updated_at || a.created_at || 0).getTime();
            });
    }, [complaints]);

    const recent = useMemo(() => rankedComplaints.slice(0, 5), [rankedComplaints]);
    const actionable = useMemo(() => rankedComplaints.filter((c) => c.status !== 'Resolved').slice(0, 8), [rankedComplaints]);

    const topToday = useMemo(() => {
        const now = new Date();
        const start = new Date(now.getFullYear(), now.getMonth(), now.getDate());
        return rankedComplaints.find((c) => {
            const created = c?.created_at ? new Date(c.created_at) : null;
            return created && created >= start;
        }) || null;
    }, [rankedComplaints]);

    const updateStatus = async (complaintId, status) => {
        if (updatingIds.includes(complaintId)) return;
        setUpdatingIds((prev) => [...prev, complaintId]);
        try {
            const res = await api.patch(`/a/complaints/${complaintId}/status`, { status });
            const updated = res?.data || {};
            setComplaints((prev) => prev.map((row) => (row.id === complaintId ? { ...row, ...updated } : row)));
            setToast({ type: 'success', message: `Complaint moved to ${status}` });
            fetchComplaints(true);
        } catch (err) {
            setToast({ type: 'error', message: toErrorMessage(err) });
        } finally {
            setUpdatingIds((prev) => prev.filter((id) => id !== complaintId));
            setTimeout(() => setToast(null), 2500);
        }
    };

    if (loading) {
        return (
            <div className="page-container">
                <SkeletonBanner />
                <SkeletonStats />
                <div className="table-glass-container"><SkeletonTable /></div>
            </div>
        );
    }

    return (
        <div className="page-container">
            <div className="banner-hero">
                <img src={BANNER_IMG} alt="Command Centre" loading="lazy" />
                <div className="banner-content">
                    <h2>Authority Command Centre</h2>
                    <div className="admin-hero-chips">
                        <span className="badge-pill admin-hero-chip">Live Queue</span>
                        <span className="badge-pill admin-hero-chip">Refresh: {ADMIN_REFRESH_MS / 1000}s</span>
                    </div>
                </div>
            </div>

            {error && <div className="progress-error" style={{ marginTop: 10 }}>{error}</div>}

            <div className="dashboard-grid">
                <div className="card-stat-glass">
                    <div className="card-header-flex">
                        <div className="card-icon-box stat-icon-info"><MdReport /></div>
                    </div>
                    <div className="card-value-large">{stats.total}</div>
                    <div className="card-label-sub">Total Complaints</div>
                </div>

                <div className="card-stat-glass">
                    <div className="card-header-flex">
                        <div className="card-icon-box stat-icon-success"><MdCheckCircle /></div>
                    </div>
                    <div className="card-value-large">{stats.resolved}</div>
                    <div className="card-label-sub">Resolved Cases</div>
                </div>

                <div className="card-stat-glass">
                    <div className="card-header-flex">
                        <div className="card-icon-box stat-icon-warning"><MdPending /></div>
                    </div>
                    <div className="card-value-large">{stats.pending}</div>
                    <div className="card-label-sub">Pending Action</div>
                </div>

                <div className="card-stat-glass">
                    <div className="card-header-flex">
                        <div className="card-icon-box stat-icon-purple"><MdPeople /></div>
                    </div>
                    <div className="card-value-large">{stats.citizens}</div>
                    <div className="card-label-sub">Registered Citizens</div>
                </div>
            </div>

            <div className="table-glass-container" style={{ marginBottom: 16 }}>
                <div className="table-head">
                    <h3 className="table-title"><MdWarningAmber style={{ verticalAlign: 'middle', marginRight: 6 }} />Top Priority Today</h3>
                </div>
                <div style={{ padding: 14 }}>
                    {!topToday && <div className="dashboard-empty"><p>No reports detected today.</p></div>}
                    {topToday && (
                        <div className="glass-panel" style={{ padding: 12 }}>
                            <div className="area-report-meta">{topToday.ward} | {topToday.status}</div>
                            <div className="area-report-title">{topToday.description?.slice(0, 120) || 'Complaint'}</div>
                            <div style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 6 }}>
                                Upvotes: {topToday.upvotes_count || 0} | Priority: {topToday.priority_score || 0} | Score: {topToday.dashboard_score}
                            </div>
                        </div>
                    )}
                </div>
            </div>

            <div className="table-glass-container" style={{ marginBottom: 16 }}>
                <div className="table-head">
                    <h3 className="table-title">Priority Action Queue</h3>
                    <Button size="sm" variant="secondary" onClick={() => fetchComplaints(true)}>Refresh</Button>
                </div>

                {actionable.length === 0 ? (
                    <div className="dashboard-empty">
                        <h3>No pending issues</h3>
                        <p>All visible complaints are resolved.</p>
                    </div>
                ) : (
                    <div className="table-scroll">
                        <table className="table-modern">
                            <thead>
                                <tr>
                                    <th>Issue</th>
                                    <th>Upvotes</th>
                                    <th>Priority</th>
                                    <th>Score</th>
                                    <th>Status</th>
                                    <th>Quick Action</th>
                                </tr>
                            </thead>
                            <tbody>
                                {actionable.map((c) => (
                                    <tr key={c.id}>
                                        <td className="cell-title">{c.description?.slice(0, 80) || 'Complaint'}</td>
                                        <td>{c.upvotes_count || 0}</td>
                                        <td>{c.priority_score || 0}</td>
                                        <td>{c.dashboard_score}</td>
                                        <td>
                                            <span className={`badge-pill status-${toStatusClass(c.status)}`}>
                                                {c.status || 'Pending'}
                                            </span>
                                        </td>
                                        <td>
                                            <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
                                                <Button
                                                    size="sm"
                                                    variant="ghost"
                                                    disabled={c.status === 'Open' || updatingIds.includes(c.id)}
                                                    onClick={() => updateStatus(c.id, 'Open')}
                                                >
                                                    Open
                                                </Button>
                                                <Button
                                                    size="sm"
                                                    variant="secondary"
                                                    disabled={c.status === 'In Progress' || updatingIds.includes(c.id)}
                                                    onClick={() => updateStatus(c.id, 'In Progress')}
                                                >
                                                    In Progress
                                                </Button>
                                                <Button
                                                    size="sm"
                                                    variant="success"
                                                    disabled={c.status === 'Resolved' || updatingIds.includes(c.id)}
                                                    onClick={() => updateStatus(c.id, 'Resolved')}
                                                >
                                                    Resolve
                                                </Button>
                                            </div>
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                )}
            </div>

            <div className="table-glass-container">
                <div className="table-head">
                    <h3 className="table-title">Recent Activity</h3>
                </div>
                {recent.length === 0 ? (
                    <div className="dashboard-empty">
                        <h3>No recent data</h3>
                        <p>Incoming complaints will appear here automatically.</p>
                    </div>
                ) : (
                    <div className="table-scroll">
                        <table className="table-modern">
                            <thead>
                                <tr>
                                    <th>Reference ID</th>
                                    <th>Title</th>
                                    <th>Category</th>
                                    <th>Status</th>
                                    <th>Date</th>
                                </tr>
                            </thead>
                            <tbody>
                                {recent.map((c, i) => (
                                    <tr key={c.id || i}>
                                        <td className="cell-mono">#{c.id || 1000 + i}</td>
                                        <td className="cell-title">{c.description?.slice(0, 45) || 'Complaint'}</td>
                                        <td><span className="cell-category">{c.category || 'General'}</span></td>
                                        <td>
                                            <span className={`badge-pill status-${toStatusClass(c.status)}`}>
                                                {c.status || 'Pending'}
                                            </span>
                                        </td>
                                        <td className="cell-date">
                                            {c.created_at ? new Date(c.created_at).toLocaleDateString(undefined, { month: 'short', day: 'numeric' }) : '--'}
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                )}
            </div>

            {toast && (
                <div style={{
                    position: 'fixed', right: 20, bottom: 20, zIndex: 40,
                    padding: '10px 14px', borderRadius: 10,
                    color: '#fff',
                    background: toast.type === 'success' ? 'rgba(16,185,129,0.95)' : 'rgba(239,68,68,0.95)',
                }}>
                    {toast.message}
                </div>
            )}
        </div>
    );
}
