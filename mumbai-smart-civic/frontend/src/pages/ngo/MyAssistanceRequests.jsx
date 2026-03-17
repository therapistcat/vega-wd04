import React from 'react';
import { useNGO } from '../../context/NGOContext';

export default function MyAssistanceRequests() {
    const { ngoRequests } = useNGO();
    const user = JSON.parse(localStorage.getItem('user') || '{}');
    const myRequests = ngoRequests.filter(req => (req.ngo_name || req.ngoName) === user.name);

    return (
        <div className="page-container">
            <h2 style={{ fontSize: 24, fontWeight: 700, color: 'var(--text-primary)', marginBottom: 24 }}>
                My Assistance Requests
            </h2>

            <div className="table-glass-container">
                {myRequests.length === 0 ? (
                    <div style={{ padding: '60px', textAlign: 'center' }}>
                        <p style={{ color: 'var(--text-muted)' }}>No requests submitted yet.</p>
                    </div>
                ) : (
                    <table className="table-modern">
                        <thead>
                            <tr>
                                <th>Issue Reference</th>
                                <th>Request Date</th>
                                <th>Status</th>
                            </tr>
                        </thead>
                        <tbody>
                            {myRequests.map((req) => (
                                <tr key={req.id}>
                                    <td style={{ fontWeight: 600, color: 'var(--text-primary)' }}>{(req.issue_title || req.issueTitle)?.slice(0, 80)}</td>
                                    <td style={{ color: 'var(--text-muted)', fontSize: '13px' }}>
                                        {new Date(req.created_at || req.timestamp).toLocaleDateString()}
                                    </td>
                                    <td>
                                        <span className={`badge-pill status-${req.status}`}>
                                            {req.status.charAt(0).toUpperCase() + req.status.slice(1)}
                                        </span>
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                )}
            </div>
        </div>
    );
}
