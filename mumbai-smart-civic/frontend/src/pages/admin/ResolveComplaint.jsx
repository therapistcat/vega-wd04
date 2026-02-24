import React, { useEffect, useMemo, useRef, useState } from 'react';
import api from '../../utils/api';

function toErrorMessage(err, fallback = 'Action failed') {
    const detail = err?.response?.data?.detail;
    if (typeof detail === 'string' && detail.trim()) return detail;
    if (Array.isArray(detail) && detail.length > 0) {
        const first = detail[0];
        if (typeof first === 'string') return first;
        if (first && typeof first === 'object' && typeof first.msg === 'string') return first.msg;
    }
    if (detail && typeof detail === 'object' && typeof detail.msg === 'string') return detail.msg;
    return fallback;
}

const defaultFormState = {
    status: 'In Progress',
    resolution_note: '',
    fixed_image: null,
    imagePreview: '',
};

function resolveFormState(map, id, status) {
    const current = map[id];
    if (current) return current;
    const seed = { ...defaultFormState };
    if (status === 'Open') seed.status = 'In Progress';
    return seed;
}

export default function ResolveComplaint() {
    const [complaints, setComplaints] = useState([]);
    const [loading, setLoading] = useState(true);
    const [toast, setToast] = useState(null);
    const [formsById, setFormsById] = useState({});
    const [submittingId, setSubmittingId] = useState('');
    const formsRef = useRef(formsById);

    const pendingComplaints = useMemo(
        () => complaints.filter((c) => c.status !== 'Resolved'),
        [complaints],
    );

    const fetchComplaints = async () => {
        try {
            const res = await api.get('/a/complaints');
            const data = Array.isArray(res.data) ? res.data : [];
            setComplaints(data);
        } catch {
            setComplaints([]);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        formsRef.current = formsById;
    }, [formsById]);

    useEffect(() => {
        fetchComplaints();
        return () => {
            Object.values(formsRef.current).forEach((row) => {
                if (row?.imagePreview) URL.revokeObjectURL(row.imagePreview);
            });
        };
    }, []);

    const updateForm = (id, patch) => {
        setFormsById((prev) => ({
            ...prev,
            [id]: {
                ...resolveFormState(prev, id),
                ...patch,
            },
        }));
    };

    const handleFileChange = (id, file) => {
        const current = resolveFormState(formsById, id);
        if (current.imagePreview) URL.revokeObjectURL(current.imagePreview);
        updateForm(id, {
            fixed_image: file || null,
            imagePreview: file ? URL.createObjectURL(file) : '',
        });
    };

    const submitStatusUpdate = async (complaintId, currentStatus) => {
        const state = resolveFormState(formsById, complaintId, currentStatus);
        if (state.status === 'Resolved' && !state.fixed_image) {
            setToast({ type: 'error', message: 'Resolved complaints require fixed-work image proof' });
            setTimeout(() => setToast(null), 3000);
            return;
        }

        const formData = new FormData();
        formData.append('status', state.status);
        if (state.resolution_note?.trim()) {
            formData.append('resolution_note', state.resolution_note.trim());
        }
        if (state.fixed_image) {
            formData.append('fixed_image', state.fixed_image);
        }

        setSubmittingId(complaintId);
        try {
            const res = await api.post(`/a/complaints/${complaintId}/status-with-proof`, formData, {
                headers: { 'Content-Type': 'multipart/form-data' },
            });

            const updated = res.data;
            setComplaints((prev) => prev.map((row) => (row.id === complaintId ? { ...row, ...updated } : row)));

            if (state.imagePreview) URL.revokeObjectURL(state.imagePreview);
            setFormsById((prev) => {
                const next = { ...prev };
                delete next[complaintId];
                return next;
            });

            setToast({ type: 'success', message: `Complaint updated to ${state.status}` });
        } catch (err) {
            setToast({ type: 'error', message: toErrorMessage(err) });
        } finally {
            setSubmittingId('');
            setTimeout(() => setToast(null), 3000);
        }
    };

    if (loading) {
        return (
            <div className="page-container">
                <h2 style={{ fontSize: 24, fontWeight: 700, marginBottom: 20 }}>Resolve Complaints</h2>
                <div className="skeleton" style={{ height: 140, borderRadius: 16 }} />
            </div>
        );
    }

    return (
        <div className="page-container">
            <h2 style={{ fontSize: 24, fontWeight: 700, color: 'var(--text-primary)', marginBottom: 8 }}>
                Resolve Complaints With Proof
            </h2>
            <p style={{ fontSize: 13, color: 'var(--text-muted)', marginBottom: 24 }}>
                Pending complaints: {pendingComplaints.length} | Resolved complaints: {complaints.length - pendingComplaints.length}
            </p>

            {pendingComplaints.length === 0 ? (
                <div className="glass-panel" style={{ padding: 40, textAlign: 'center' }}>
                    <h3 style={{ fontSize: 18, fontWeight: 700, color: 'var(--text-primary)' }}>No pending complaints</h3>
                </div>
            ) : (
                <div style={{ display: 'grid', gap: 16 }}>
                    {pendingComplaints.map((c) => {
                        const form = resolveFormState(formsById, c.id, c.status);
                        return (
                            <div key={c.id} className="glass-panel resolve-card">
                                <div style={{ marginBottom: 8, color: 'var(--text-muted)', fontSize: 12 }}>
                                    #{c.id}
                                </div>
                                <h3 style={{ marginBottom: 8 }}>{c.description?.slice(0, 120) || 'Complaint'}</h3>
                                <p style={{ marginBottom: 12, color: 'var(--text-muted)' }}>
                                    {c.category} | {c.ward} | Current status: <strong>{c.status}</strong>
                                </p>

                                {c.image_url && (
                                    <div className="resolve-image-row">
                                        <img src={c.image_url} alt="Complaint evidence" />
                                        <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>Citizen evidence image</div>
                                    </div>
                                )}

                                <div className="resolve-form-grid">
                                    <div className="form-group" style={{ marginBottom: 0 }}>
                                        <label>Status</label>
                                        <select
                                            value={form.status}
                                            onChange={(e) => updateForm(c.id, { status: e.target.value })}
                                        >
                                            <option value="In Progress">In Progress</option>
                                            <option value="Resolved">Resolved</option>
                                            <option value="Open">Open</option>
                                        </select>
                                    </div>

                                    <div className="form-group" style={{ marginBottom: 0 }}>
                                        <label>Resolution Note</label>
                                        <textarea
                                            value={form.resolution_note}
                                            onChange={(e) => updateForm(c.id, { resolution_note: e.target.value })}
                                            placeholder="Formal action note for audit trail"
                                        />
                                    </div>

                                    <div className="form-group" style={{ marginBottom: 0 }}>
                                        <label>Fixed-work Image Proof {form.status === 'Resolved' ? '(required)' : '(optional)'}</label>
                                        <input
                                            type="file"
                                            accept="image/*"
                                            capture="environment"
                                            onChange={(e) => handleFileChange(c.id, e.target.files?.[0] || null)}
                                        />
                                    </div>

                                    {form.imagePreview && (
                                        <div className="resolve-preview-wrap">
                                            <img src={form.imagePreview} alt="Resolution preview" />
                                        </div>
                                    )}
                                </div>

                                <div style={{ display: 'flex', gap: 10, marginTop: 14 }}>
                                    <button
                                        onClick={() => submitStatusUpdate(c.id, c.status)}
                                        className="btn-gradient"
                                        style={{ width: 'auto', padding: '10px 18px' }}
                                        disabled={submittingId === c.id}
                                    >
                                        {submittingId === c.id ? 'Saving...' : `Update to ${form.status}`}
                                    </button>
                                </div>
                            </div>
                        );
                    })}
                </div>
            )}

            {toast && (
                <div style={{
                    position: 'fixed', bottom: 24, right: 24, padding: '10px 18px',
                    borderRadius: 12, color: '#fff',
                    background: toast.type === 'success' ? 'rgba(16, 185, 129, 0.9)' : 'rgba(239, 68, 68, 0.9)',
                }}>
                    {toast.message}
                </div>
            )}
        </div>
    );
}
