import React, { useEffect, useMemo, useState } from 'react';
import { MdCheckCircle, MdPending, MdPhotoCamera, MdTimeline } from 'react-icons/md';
import { SkeletonTable } from '../../components/Skeleton';
import Button from '../../components/ui/Button';
import { useNGO } from '../../context/NGOContext';


function formatTimestamp(value) {
    if (!value) return '-';
    try {
        return new Date(value).toLocaleString();
    } catch {
        return '-';
    }
}

function statusClass(status) {
    return `status-${String(status || 'pending').toLowerCase().replace(/\s+/g, '-')}`;
}

export default function AssignedIssues() {
    const {
        assignedIssues,
        assignedLoading,
        updateIssueProgress,
        getIssueUpdates,
        fetchAssignedIssues,
    } = useNGO();
    const [selectedIssue, setSelectedIssue] = useState(null);
    const [selectedUpdates, setSelectedUpdates] = useState([]);
    const [statusValue, setStatusValue] = useState('In Progress');
    const [message, setMessage] = useState('');
    const [imageFiles, setImageFiles] = useState([]);
    const [submitting, setSubmitting] = useState(false);
    const [toast, setToast] = useState(null);

    const stats = useMemo(() => ({
        total: assignedIssues.length,
        pending: assignedIssues.filter((issue) => issue.progress_status === 'Pending').length,
        inProgress: assignedIssues.filter((issue) => issue.progress_status === 'In Progress').length,
        resolved: assignedIssues.filter((issue) => issue.progress_status === 'Resolved').length,
    }), [assignedIssues]);

    useEffect(() => {
        fetchAssignedIssues();
    }, []);

    const openProgressModal = async (issue) => {
        setSelectedIssue(issue);
        setStatusValue(issue?.progress_status === 'Resolved' ? 'Resolved' : 'In Progress');
        setMessage('');
        setImageFiles([]);
        try {
            const updates = await getIssueUpdates(issue.id);
            setSelectedUpdates(updates);
        } catch {
            setSelectedUpdates(Array.isArray(issue?.progress_updates) ? issue.progress_updates : []);
        }
    };

    const closeModal = () => {
        setSelectedIssue(null);
        setSelectedUpdates([]);
        setStatusValue('In Progress');
        setMessage('');
        setImageFiles([]);
        setSubmitting(false);
    };

    const handleSubmit = async (e) => {
        e.preventDefault();
        if (!selectedIssue) return;

        setSubmitting(true);
        try {
            await updateIssueProgress(selectedIssue.id, {
                status: statusValue,
                message,
                images: imageFiles,
            });
            await fetchAssignedIssues();
            const updates = await getIssueUpdates(selectedIssue.id);
            setSelectedUpdates(updates);
            setToast({ type: 'success', message: 'Progress updated successfully' });
            setTimeout(() => setToast(null), 3000);
            closeModal();
        } catch (err) {
            const detail = err?.response?.data?.detail || 'Failed to update issue progress';
            setToast({ type: 'error', message: detail });
            setTimeout(() => setToast(null), 3000);
            setSubmitting(false);
        }
    };

    if (assignedLoading) {
        return <div className="page-container"><SkeletonTable rows={8} /></div>;
    }

    return (
        <div className="page-container">
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 16, flexWrap: 'wrap', marginBottom: 24 }}>
                <div>
                    <h2 style={{ fontSize: 24, fontWeight: 700, color: 'var(--text-primary)' }}>My Assigned Issues</h2>
                    <p style={{ color: 'var(--text-muted)', fontSize: 13, marginTop: 4 }}>
                        Only issues approved and assigned to your NGO appear here.
                    </p>
                </div>
                <Button type="button" variant="ghost" onClick={fetchAssignedIssues}>Refresh</Button>
            </div>

            <div className="dashboard-grid" style={{ marginBottom: 24 }}>
                <div className="card-stat-glass">
                    <div className="card-value-large">{stats.total}</div>
                    <div className="card-label-sub">Assigned</div>
                </div>
                <div className="card-stat-glass">
                    <div className="card-value-large">{stats.pending}</div>
                    <div className="card-label-sub">Pending</div>
                </div>
                <div className="card-stat-glass">
                    <div className="card-value-large">{stats.inProgress}</div>
                    <div className="card-label-sub">In Progress</div>
                </div>
                <div className="card-stat-glass">
                    <div className="card-value-large">{stats.resolved}</div>
                    <div className="card-label-sub">Resolved</div>
                </div>
            </div>

            {assignedIssues.length === 0 ? (
                <div className="table-glass-container" style={{ padding: 48, textAlign: 'center' }}>
                    <h3 style={{ color: 'var(--text-primary)', marginBottom: 8 }}>No assigned issues yet</h3>
                    <p style={{ color: 'var(--text-muted)' }}>Approved NGO work will appear here once an authority assigns an issue to your organization.</p>
                </div>
            ) : (
                <div style={{ display: 'grid', gap: 16 }}>
                    {assignedIssues.map((issue) => {
                        const updates = Array.isArray(issue.progress_updates) ? issue.progress_updates : [];
                        return (
                            <div key={issue.id} className="table-glass-container" style={{ padding: 18 }}>
                                <div style={{ display: 'flex', justifyContent: 'space-between', gap: 16, flexWrap: 'wrap', marginBottom: 12 }}>
                                    <div style={{ flex: '1 1 340px' }}>
                                        <div style={{ fontSize: 17, fontWeight: 700, color: 'var(--text-primary)', marginBottom: 8 }}>
                                            {issue.description}
                                        </div>
                                        <div style={{ fontSize: 13, color: 'var(--text-muted)', display: 'flex', gap: 12, flexWrap: 'wrap' }}>
                                            <span>Location: {issue.landmark || issue.ward || 'N/A'}</span>
                                            <span>Category: {issue.category || 'General'}</span>
                                            <span>Department: {issue.department || issue.predicted_department || 'N/A'}</span>
                                        </div>
                                    </div>
                                    <div style={{ display: 'grid', gap: 10, justifyItems: 'end' }}>
                                        <span className={`badge-pill ${statusClass(issue.progress_status)}`}>
                                            {issue.progress_status || 'Pending'}
                                        </span>
                                        <Button type="button" size="sm" onClick={() => openProgressModal(issue)}>
                                            Update Progress
                                        </Button>
                                    </div>
                                </div>

                                <div style={{ borderTop: '1px solid var(--glass-border-subtle)', paddingTop: 14 }}>
                                    <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 12, color: 'var(--text-primary)', fontWeight: 700 }}>
                                        <MdTimeline /> Progress Timeline
                                    </div>

                                    {updates.length === 0 ? (
                                        <div style={{ color: 'var(--text-muted)', fontSize: 13 }}>No updates added yet.</div>
                                    ) : (
                                        <div style={{ display: 'grid', gap: 12 }}>
                                            {updates.map((update, index) => (
                                                <div key={`${issue.id}-${index}`} className="glass-panel" style={{ padding: 12 }}>
                                                    <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12, flexWrap: 'wrap', marginBottom: 6 }}>
                                                        <div style={{ display: 'flex', alignItems: 'center', gap: 8, color: 'var(--text-primary)', fontWeight: 600 }}>
                                                            {update.status === 'Resolved' ? <MdCheckCircle /> : <MdPending />}
                                                            <span>{update.message}</span>
                                                        </div>
                                                        <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>
                                                            {formatTimestamp(update.timestamp)}
                                                        </div>
                                                    </div>
                                                    <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>
                                                        Status: {update.status || issue.progress_status || 'Pending'}
                                                    </div>
                                                    {Array.isArray(update.images) && update.images.length > 0 && (
                                                        <div style={{ marginTop: 10, display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(90px, 1fr))', gap: 8 }}>
                                                            {update.images.map((image, imageIndex) => (
                                                                <a key={`${issue.id}-${index}-${imageIndex}`} href={image} target="_blank" rel="noreferrer" style={{ textDecoration: 'none' }}>
                                                                    <div style={{ marginBottom: 4, fontSize: 11, color: 'var(--text-muted)', display: 'flex', alignItems: 'center', gap: 4 }}>
                                                                        <MdPhotoCamera /> Image attached
                                                                    </div>
                                                                    <img src={image} alt="NGO progress update" style={{ width: '100%', height: 88, objectFit: 'cover', borderRadius: 8 }} />
                                                                </a>
                                                            ))}
                                                        </div>
                                                    )}
                                                </div>
                                            ))}
                                        </div>
                                    )}
                                </div>
                            </div>
                        );
                    })}
                </div>
            )}

            {selectedIssue && (
                <div className="modal-overlay" style={{ position: 'fixed', inset: 0, background: 'rgba(15, 23, 42, 0.72)', display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 20, zIndex: 1000 }}>
                    <div className="glass-card" style={{ width: 'min(720px, 100%)', padding: 24 }}>
                        <h3 style={{ fontSize: 20, fontWeight: 700, color: 'var(--text-primary)', marginBottom: 8 }}>Update Progress</h3>
                        <p style={{ fontSize: 13, color: 'var(--text-muted)', marginBottom: 18 }}>
                            {selectedIssue.description}
                        </p>

                        <form onSubmit={handleSubmit} style={{ display: 'grid', gap: 14 }}>
                            <div className="form-group">
                                <label htmlFor="ngo-progress-status">Status</label>
                                <select id="ngo-progress-status" value={statusValue} onChange={(e) => setStatusValue(e.target.value)}>
                                    <option value="In Progress">In Progress</option>
                                    <option value="Resolved">Resolved</option>
                                </select>
                            </div>

                            <div className="form-group">
                                <label htmlFor="ngo-progress-message">Update Message</label>
                                <textarea
                                    id="ngo-progress-message"
                                    value={message}
                                    onChange={(e) => setMessage(e.target.value)}
                                    placeholder="Describe what work has started or what was completed"
                                    required
                                />
                            </div>

                            <div className="form-group">
                                <label htmlFor="ngo-progress-images">Images (optional)</label>
                                <input
                                    id="ngo-progress-images"
                                    type="file"
                                    accept="image/*"
                                    multiple
                                    onChange={(e) => setImageFiles(Array.from(e.target.files || []))}
                                />
                            </div>

                            {selectedUpdates.length > 0 && (
                                <div className="glass-panel" style={{ padding: 12 }}>
                                    <div style={{ fontWeight: 700, color: 'var(--text-primary)', marginBottom: 10 }}>Recent Updates</div>
                                    <div style={{ display: 'grid', gap: 8 }}>
                                        {selectedUpdates.slice().reverse().slice(0, 3).map((update, index) => (
                                            <div key={`${selectedIssue.id}-recent-${index}`} style={{ fontSize: 13, color: 'var(--text-secondary)' }}>
                                                [{update.status === 'Resolved' ? 'Resolved' : 'In Progress'}] {update.message} - {formatTimestamp(update.timestamp)}
                                            </div>
                                        ))}
                                    </div>
                                </div>
                            )}

                            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 10 }}>
                                <Button type="button" variant="ghost" onClick={closeModal}>Cancel</Button>
                                <Button type="submit" disabled={submitting}>
                                    {submitting ? 'Saving...' : 'Save Update'}
                                </Button>
                            </div>
                        </form>
                    </div>
                </div>
            )}

            {toast && <div className={`toast toast-${toast.type}`}>{toast.message}</div>}
        </div>
    );
}
