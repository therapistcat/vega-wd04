import React, { useEffect, useState } from 'react';
import { SkeletonTable } from '../../components/Skeleton';
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
                                    <th>Location</th>
                                    <th>Status</th>
                                    <th>Resolution</th>
                                    <th>Submitted</th>
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
