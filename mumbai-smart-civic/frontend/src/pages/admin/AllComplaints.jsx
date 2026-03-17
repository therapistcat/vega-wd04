import React, { useEffect, useState } from 'react';
import { SkeletonTable } from '../../components/Skeleton';
import { Link } from 'react-router-dom';
import api from '../../utils/api';

export default function AllComplaints() {
    const [complaints, setComplaints] = useState([]);
    const [loading, setLoading] = useState(true);
    const [filter, setFilter] = useState('all');

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

                <div style={{ display: 'flex', gap: 8, background: 'rgba(255,255,255,0.8)', padding: 6, borderRadius: 16, border: '1px solid rgba(148, 163, 184, 0.2)', backdropFilter: 'blur(8px)' }}>
                    {['all', 'open', 'in progress', 'resolved'].map((f) => (
                        <button
                            key={f}
                            onClick={() => setFilter(f)}
                            style={{
                                padding: '8px 16px', borderRadius: 10, fontSize: 13, fontWeight: 600,
                                textTransform: 'capitalize', color: filter === f ? 'var(--primary)' : 'var(--text-muted)',
                                background: filter === f ? 'rgba(37, 99, 235, 0.15)' : 'transparent',
                                transition: 'all 0.2s', border: filter === f ? '1px solid rgba(37, 99, 235, 0.2)' : '1px solid transparent'
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
                                        <td style={{ fontFamily: 'monospace', color: 'var(--text-muted)' }}>#{c.id || 1000 + i}</td>
                                        <td style={{ fontWeight: 600, color: 'var(--text-primary)' }}>{c.description?.slice(0, 50) || 'N/A'}</td>
                                        <td>
                                            <span className="badge-pill" style={{ background: 'var(--bg-input)', border: '1px solid var(--border-subtle)', color: 'var(--text-secondary)', fontSize: 11 }}>
                                                {c.category || 'General'}
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
                                                onClick={() => {
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
                                                    color: '#ef4444', 
                                                    borderColor: 'rgba(239, 68, 68, 0.2)',
                                                    display: 'flex',
                                                    alignItems: 'center',
                                                    gap: 4
                                                }}
                                            >
                                                Block
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
