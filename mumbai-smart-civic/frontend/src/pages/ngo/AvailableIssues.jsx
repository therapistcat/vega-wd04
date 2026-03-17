import React, { useEffect, useState } from 'react';
import { SkeletonTable } from '../../components/Skeleton';
import api from '../../utils/api';
import Button from '../../components/ui/Button';
import { useNGO } from '../../context/NGOContext';

export default function AvailableIssues() {
    const { addRequest, ngoRequests } = useNGO();
    const [complaints, setComplaints] = useState([]);
    const [loading, setLoading] = useState(true);
    const [showModal, setShowModal] = useState(null);
    const [toast, setToast] = useState(null);
    const user = JSON.parse(localStorage.getItem('user') || '{}');

    const fetchComplaints = async () => {
        setLoading(true);
        try {
            const res = await api.get('/ngo-requests/available-issues');
            setComplaints(res.data);
        } catch (err) {
            console.error("Failed to fetch available issues:", err);
            setComplaints([]);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchComplaints();
    }, []);

    const handleRequest = async (issue) => {
        try {
            await addRequest({
                issueId: issue.id,
                issueTitle: issue.description,
                ngoName: user.name,
                ngoEmail: user.email
            });
            setShowModal(null);
            setToast("Request sent to Admin for approval");
            setTimeout(() => setToast(null), 3000);
        } catch (err) {
            setToast("Failed to send request");
            setTimeout(() => setToast(null), 3000);
        }
    };

    const isAlreadyRequested = (issueId) => {
        return ngoRequests.some(req => (req.issue_id === issueId || req.issueId === issueId));
    };

    if (loading) return <div className="page-container"><SkeletonTable rows={10} /></div>;

    return (
        <div className="page-container">
            <h2 style={{ fontSize: 24, fontWeight: 700, color: 'var(--text-primary)', marginBottom: 24 }}>
                Available Issues for Assistance
            </h2>

            <div className="table-glass-container">
                <table className="table-modern">
                    <thead>
                        <tr>
                            <th>ID</th>
                            <th>Description</th>
                            <th>Category</th>
                            <th>Status</th>
                            <th>Action</th>
                        </tr>
                    </thead>
                    <tbody>
                        {complaints.map((c, i) => (
                            <tr key={c.id || i}>
                                <td style={{ fontFamily: 'monospace', color: 'var(--text-muted)' }}>#{c.id || 1000 + i}</td>
                                <td style={{ color: 'var(--text-primary)', fontWeight: 500 }}>{c.description?.slice(0, 60)}</td>
                                <td><span className="badge-pill">{c.category || 'General'}</span></td>
                                <td>
                                    <span className={`badge-pill status-${(c.status || 'open').toLowerCase().replace(/\s+/g, '-')}`}>
                                        {c.status || 'Open'}
                                    </span>
                                </td>
                                <td>
                                    {isAlreadyRequested(c.id) ? (
                                        <span style={{ fontSize: '12px', color: 'var(--text-muted)', fontWeight: 600 }}>Requested</span>
                                    ) : (
                                        <Button size="sm" onClick={() => setShowModal(c)}>Request to Assist</Button>
                                    )}
                                </td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>

            {showModal && (
                <div className="modal-overlay" style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.7)', backdropFilter: 'blur(4px)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 100 }}>
                    <div className="glass-card" style={{ maxWidth: '400px', width: '90%', padding: '24px', textAlign: 'center' }}>
                        <h3 style={{ fontSize: '18px', fontWeight: 600, marginBottom: '12px' }}>Confirm Request</h3>
                        <p style={{ fontSize: '14px', color: 'var(--text-muted)', marginBottom: '24px' }}>
                            Are you sure you want to request to assist with this issue: <strong>{showModal.description?.slice(0, 40)}...</strong>?
                        </p>
                        <div style={{ display: 'flex', gap: '12px', justifyContent: 'center' }}>
                            <Button variant="ghost" onClick={() => setShowModal(null)}>Cancel</Button>
                            <Button onClick={() => handleRequest(showModal)}>Confirm</Button>
                        </div>
                    </div>
                </div>
            )}

            {toast && (
                <div style={{ position: 'fixed', bottom: '24px', right: '24px', background: 'var(--primary-gradient)', color: 'white', padding: '12px 20px', borderRadius: '12px', boxShadow: '0 8px 32px rgba(0,0,0,0.3)', zIndex: 1000 }}>
                    {toast}
                </div>
            )}
        </div>
    );
}
