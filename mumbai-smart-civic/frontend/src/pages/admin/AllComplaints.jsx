import React, { useEffect, useState } from 'react';
import { SkeletonTable } from '../../components/Skeleton';
import { Link } from 'react-router-dom';
import api from '../../utils/api';
import { useNGO } from '../../context/NGOContext';
import { MdPeople } from 'react-icons/md';

function getSourceBadge(source) {
    const normalized = String(source || '').toLowerCase();
    if (normalized === 'call') {
        return {
            label: 'Call',
            background: 'rgba(37, 99, 235, 0.12)',
            color: 'var(--primary)',
        };
    }
    if (normalized === 'whatsapp') {
        return {
            label: 'WhatsApp',
            background: 'rgba(16, 185, 129, 0.12)',
            color: '#059669',
        };
    }
    return {
        label: 'Web',
        background: 'var(--bg-input)',
        color: 'var(--text-secondary)',
    };
}

export default function AllComplaints() {
    const [complaints, setComplaints] = useState([]);
    const [loading, setLoading] = useState(true);
    const [filter, setFilter] = useState('all');
    const { getRequestsForIssue } = useNGO();

    useEffect(() => {
        (async () => {
            try {
                const res = await api.get('/a/complaints');
                setComplaints(Array.isArray(res.data) ? res.data : []);
            } catch {
                setComplaints([]);
            } finally {
                setLoading(false);
            }
        })();
    }, []);

    const filtered = filter === 'all'
        ? complaints
        : complaints.filter((c) => (c.status || '').toLowerCase() === filter);

    if (loading) {
        return (
            <div className="page-container">
                <div className="skeleton skeleton-text" style={{ height: 32, width: '40%', marginBottom: 32 }} />
                <div className="table-glass-container"><SkeletonTable rows={8} /></div>
            </div>
        );
    }

    return (
        <div className="page-container">
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 32, gap: 16, flexWrap: 'wrap' }}>
                <div>
                    <h2 style={{ fontSize: 24, fontWeight: 700, color: 'var(--text-primary)', marginBottom: 4 }}>
                        All Complaints
                    </h2>
                    <p style={{ fontSize: 13, color: 'var(--text-muted)' }}>
                        Showing {filtered.length} {filter !== 'all' ? filter : 'total'} records
                    </p>
                </div>

                <div style={{ display: 'flex', gap: 8, background: 'var(--bg-glass-strong)', padding: '6px 8px', borderRadius: 20, border: '1px solid var(--glass-border-subtle)', backdropFilter: 'blur(12px)' }}>
                    {['all', 'open', 'in progress', 'resolved'].map((f) => (
                        <button
                            key={f}
                            onClick={() => setFilter(f)}
                            className={`btn ${filter === f ? 'btn-primary-filled' : 'btn-ghost'}`}
                            style={{
                                padding: '6px 16px', borderRadius: 14, fontSize: 12, fontWeight: 700,
                                textTransform: 'capitalize',
                                minWidth: 90,
                                border: 'none',
                                background: filter === f ? 'var(--primary-gradient)' : 'transparent',
                                color: filter === f ? '#fff' : 'var(--text-muted)',
                            }}
                        >
                            {f}
                        </button>
                    ))}
                </div>
            </div>

            <div className="table-glass-container">
                {filtered.length === 0 ? (
                    <div style={{ padding: 60, textAlign: 'center' }}>
                        <h3 style={{ fontSize: 16, fontWeight: 600, color: 'var(--text-secondary)' }}>No results found</h3>
                        <p style={{ fontSize: 13, color: 'var(--text-muted)' }}>Try adjusting your filters</p>
                    </div>
                ) : (
                    <div style={{ overflowX: 'auto' }}>
                        <table className="table-modern">
                            <thead>
                                <tr>
                                    <th>ID</th>
                                    <th>Description</th>
                                    <th>Category</th>
                                    <th>Source</th>
                                    <th>Location</th>
                                    <th>Status</th>
                                    <th>Cluster</th>
                                    <th>Resolution</th>
                                    <th>Submitted</th>
                                    <th>Actions</th>
                                </tr>
                            </thead>
                            <tbody>
                                {filtered.map((c, i) => (
                                    <tr key={c.id || i}>
                                        <td style={{ fontFamily: 'monospace', color: 'var(--text-muted)' }}>
                                            <div style={{ position: 'relative', display: 'inline-block' }}>
                                                #{c.id || 1000 + i}
                                                {getRequestsForIssue(c.id).length > 0 && (
                                                    <Link 
                                                        to="/admin/ngo-requests"
                                                        title={`${getRequestsForIssue(c.id).length} NGO requests`}
                                                        style={{
                                                            position: 'absolute', top: -8, right: -12,
                                                            background: 'var(--primary)', color: 'white',
                                                            fontSize: '9px', padding: '2px 5px', borderRadius: '10px',
                                                            fontWeight: 800, textDecoration: 'none', display: 'flex', alignItems: 'center', gap: '2px'
                                                        }}
                                                    >
                                                        <MdPeople size={10} /> {getRequestsForIssue(c.id).length}
                                                    </Link>
                                                )}
                                            </div>
                                        </td>
                                        <td style={{ fontWeight: 600, color: 'var(--text-primary)' }}>
                                            {c.description?.slice(0, 50) || 'N/A'}
                                            {c.assigned_ngo_name && (
                                                <div style={{ fontSize: '10px', color: '#10b981', fontWeight: 700, textTransform: 'uppercase', marginTop: '2px' }}>
                                                    NGO Assisting: {c.assigned_ngo_name}
                                                    {c.progress_status ? ` | ${c.progress_status}` : ''}
                                                </div>
                                            )}
                                        </td>
                                        <td>
                                            <span className="badge-pill" style={{ background: 'var(--bg-input)', border: '1px solid var(--border-subtle)', color: 'var(--text-secondary)', fontSize: 11 }}>
                                                {c.category || 'General'}
                                            </span>
                                        </td>
                                        <td>
                                            <span className="badge-pill" style={{ background: getSourceBadge(c.source).background, border: '1px solid var(--border-subtle)', color: getSourceBadge(c.source).color, fontSize: 11 }}>
                                                {getSourceBadge(c.source).label}
                                            </span>
                                        </td>
                                        <td style={{ fontSize: 12, color: 'var(--text-muted)' }}>
                                            {Array.isArray(c?.location?.coordinates)
                                                ? `${Number(c.location.coordinates[1]).toFixed(3)}, ${Number(c.location.coordinates[0]).toFixed(3)}`
                                                : '-'}
                                        </td>
                                        <td>
                                            <span className={`badge-pill status-${(c.status || 'open').toLowerCase().replace(/\s+/g, '-')}`}>
                                                {c.status || 'Open'}
                                            </span>
                                        </td>
                                        <td>
                                            {c.cluster_id ? (
                                                <Link 
                                                    to={`/citizen/cluster/${c.cluster_id}`} 
                                                    style={{ 
                                                        fontSize: 11, 
                                                        color: 'var(--primary)', 
                                                        background: 'rgba(59, 130, 246, 0.1)', 
                                                        padding: '4px 8px', 
                                                        borderRadius: 6,
                                                        textDecoration: 'none',
                                                        fontWeight: 600
                                                    }}
                                                >
                                                    {c.cluster_id}
                                                </Link>
                                            ) : (
                                                <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>None</span>
                                            )}
                                        </td>
                                        <td style={{ fontSize: 12, color: 'var(--text-muted)' }}>
                                            {c.fixed_image_url ? (
                                                <a href={c.fixed_image_url} target="_blank" rel="noreferrer" style={{ color: 'var(--primary)', fontWeight: 600 }}>
                                                    Proof Image
                                                </a>
                                            ) : (
                                                'Pending'
                                            )}
                                            {c.resolution_note && (
                                                <div style={{ marginTop: 4, maxWidth: 180 }}>
                                                    {c.resolution_note.slice(0, 45)}{c.resolution_note.length > 45 ? '...' : ''}
                                                </div>
                                            )}
                                        </td>
                                        <td style={{ fontSize: 13, color: 'var(--text-muted)' }}>
                                            {c.created_at ? new Date(c.created_at).toLocaleDateString() : '-'}
                                        </td>
                                        <td>
                                            <button 
                                                disabled={!c.user_id}
                                                onClick={() => {
                                                    if (!c.user_id) return;
                                                    const reason = window.prompt(`Block user ${c.user_id}? Enter reason:`);
                                                    if (reason) {
                                                        api.post(`/moderation/block/${c.user_id}`, { reason })
                                                            .then(() => alert("User blocked successfully"))
                                                            .catch((err) => alert("Failed to block: " + (err.response?.data?.detail || err.message)));
                                                    }
                                                }}
                                                className="btn-glass"
                                                style={{ 
                                                    padding: '4px 8px', 
                                                    fontSize: 11, 
                                                    color: !c.user_id ? 'var(--text-muted)' : '#ef4444', 
                                                    borderColor: !c.user_id ? 'var(--glass-border-subtle)' : 'rgba(239, 68, 68, 0.2)',
                                                    display: 'flex',
                                                    alignItems: 'center',
                                                    gap: 4
                                                }}
                                            >
                                                {!c.user_id ? 'No User' : 'Block'}
                                            </button>
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                )}
            </div>
        </div>
    );
}
