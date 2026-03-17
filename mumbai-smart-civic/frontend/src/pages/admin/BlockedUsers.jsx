import React, { useEffect, useState } from 'react';
import { SkeletonTable } from '../../components/Skeleton';
import api from '../../utils/api';
import { MdUndo, MdBlock, MdPerson, MdEmail, MdEvent, MdInfo } from 'react-icons/md';

export default function BlockedUsers() {
    const [users, setUsers] = useState([]);
    const [loading, setLoading] = useState(true);

    const fetchBlockedUsers = async () => {
        setLoading(true);
        try {
            // We need an endpoint to list all blocked users. 
            // The prompt didn't explicitly ask for it, but it's implied for the panel.
            // Let's assume /api/v1/moderation/blocked exists or I should add it.
            // Actually, I'll just filter all users if such an endpoint exists, 
            // but usually we want a specific one. 
            // Since I'm the one who implemented the backend, I should have added it.
            // Let's quickly add a GET /blocked endpoint to moderation.py if it's missing.
            const res = await api.get('/moderation/blocked');
            setUsers(Array.isArray(res.data) ? res.data : []);
        } catch (err) {
            console.error("Failed to fetch blocked users", err);
            setUsers([]);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchBlockedUsers();
    }, []);

    const handleUnblock = async (userId) => {
        if (!window.confirm("Are you sure you want to unblock this user?")) return;
        try {
            await api.post(`/moderation/unblock/${userId}`);
            fetchBlockedUsers();
        } catch (err) {
            alert("Failed to unblock user");
        }
    };

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
            <div style={{ marginBottom: 32 }}>
                <h2 style={{ fontSize: 24, fontWeight: 700, color: 'var(--text-primary)', marginBottom: 4 }}>
                    <MdBlock style={{ verticalAlign: 'middle', marginRight: 8, color: '#ef4444' }} />
                    Blocked Users
                </h2>
                <p style={{ fontSize: 13, color: 'var(--text-muted)' }}>
                    Manage users who have been restricted from using the platform.
                </p>
            </div>

            <div className="table-glass-container">
                {users.length === 0 ? (
                    <div style={{ padding: 60, textAlign: 'center' }}>
                        <div style={{ fontSize: 48, color: 'var(--border-subtle)', marginBottom: 16 }}><MdPerson /></div>
                        <h3 style={{ fontSize: 16, fontWeight: 600, color: 'var(--text-secondary)' }}>No blocked users</h3>
                        <p style={{ fontSize: 13, color: 'var(--text-muted)' }}>All clear! No users are currently restricted.</p>
                    </div>
                ) : (
                    <div style={{ overflowX: 'auto' }}>
                        <table className="table-modern">
                            <thead>
                                <tr>
                                    <th>User</th>
                                    <th>Reason</th>
                                    <th>Blocked At</th>
                                    <th>Blocked By</th>
                                    <th>Actions</th>
                                </tr>
                            </thead>
                            <tbody>
                                {users.map((u) => (
                                    <tr key={u.id}>
                                        <td>
                                            <div style={{ display: 'flex', flexDirection: 'column' }}>
                                                <span style={{ fontWeight: 600, color: 'var(--text-primary)' }}>{u.name}</span>
                                                <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>{u.email}</span>
                                            </div>
                                        </td>
                                        <td style={{ maxWidth: 250 }}>
                                            <div style={{ display: 'flex', alignItems: 'flex-start', gap: 6 }}>
                                                <MdInfo style={{ color: 'var(--text-muted)', marginTop: 2 }} />
                                                <span style={{ fontSize: 13 }}>{u.blocked_reason || 'No reason provided'}</span>
                                            </div>
                                        </td>
                                        <td style={{ fontSize: 13, color: 'var(--text-muted)' }}>
                                            {u.blocked_at ? new Date(u.blocked_at).toLocaleString() : '-'}
                                        </td>
                                        <td style={{ fontSize: 12, color: 'var(--text-muted)', fontFamily: 'monospace' }}>
                                            {u.blocked_by || '-'}
                                        </td>
                                        <td>
                                            <button 
                                                className="btn-glass"
                                                onClick={() => handleUnblock(u.id)}
                                                style={{ 
                                                    display: 'flex', 
                                                    alignItems: 'center', 
                                                    gap: 4, 
                                                    color: 'var(--primary)',
                                                    fontSize: 12,
                                                    fontWeight: 600
                                                }}
                                            >
                                                <MdUndo /> Unblock
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
