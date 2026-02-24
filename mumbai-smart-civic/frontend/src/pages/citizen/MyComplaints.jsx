import React, { useEffect, useMemo, useState } from 'react';
import { SkeletonTable } from '../../components/Skeleton';
import CameraCapture from '../../components/CameraCapture';
import api from '../../utils/api';

function toErrorMessage(err, fallback = 'Something went wrong') {
    const detail = err?.response?.data?.detail;
    if (typeof detail === 'string' && detail.trim()) return detail;
    if (Array.isArray(detail) && detail.length > 0) {
        const first = detail[0];
        if (typeof first === 'string') return first;
        if (first && typeof first === 'object' && typeof first.msg === 'string') return first.msg;
        return fallback;
    }
    if (detail && typeof detail === 'object' && typeof detail.msg === 'string') return detail.msg;
    return fallback;
}

export default function MyComplaints() {
    const [complaints, setComplaints] = useState([]);
    const [departments, setDepartments] = useState([]);
    const [loading, setLoading] = useState(true);
    const [showForm, setShowForm] = useState(false);

    const [title, setTitle] = useState('');
    const [description, setDescription] = useState('');
    const [category, setCategory] = useState('garbage');
    const [ward, setWard] = useState('A Ward');
    const [landmark, setLandmark] = useState('');
    const [latitude, setLatitude] = useState('');
    const [longitude, setLongitude] = useState('');
    const [imageFile, setImageFile] = useState(null);
    const [imagePreview, setImagePreview] = useState('');
    const [submitting, setSubmitting] = useState(false);
    const [toast, setToast] = useState(null);
    const [locating, setLocating] = useState(false);
    const [locationHint, setLocationHint] = useState('');

    const fetchComplaints = async () => {
        try {
            const res = await api.get('/c/complaints/me');
            setComplaints(Array.isArray(res.data) ? res.data : []);
        } catch {
            setComplaints([]);
        } finally {
            setLoading(false);
        }
    };

    const fetchDepartments = async () => {
        try {
            const res = await api.get('/c/departments');
            setDepartments(Array.isArray(res.data) ? res.data : []);
        } catch {
            setDepartments([]);
        }
    };

    useEffect(() => {
        fetchComplaints();
        fetchDepartments();
    }, []);

    useEffect(() => () => {
        if (imagePreview) {
            URL.revokeObjectURL(imagePreview);
        }
    }, [imagePreview]);

    const requestLiveLocation = () => {
        if (!navigator.geolocation) {
            setLocationHint('Geolocation is not supported in this browser');
            return;
        }
        setLocating(true);
        setLocationHint('Fetching live location...');
        navigator.geolocation.getCurrentPosition(
            (position) => {
                setLatitude(position.coords.latitude.toFixed(6));
                setLongitude(position.coords.longitude.toFixed(6));
                setLocationHint('Live location fetched from your device');
                setLocating(false);
            },
            () => {
                setLocationHint('Location permission denied. You can still submit with ward + landmark.');
                setLocating(false);
            },
            {
                enableHighAccuracy: true,
                timeout: 10000,
                maximumAge: 0,
            },
        );
    };

    useEffect(() => {
        requestLiveLocation();
    }, []);

    useEffect(() => {
        if (showForm && (!latitude || !longitude)) {
            requestLiveLocation();
        }
    }, [showForm]);

    const routedDepartment = useMemo(() => {
        const row = departments.find((d) => d.category?.toLowerCase() === category.toLowerCase());
        return row?.department || 'General Civic Response';
    }, [category, departments]);

    const handleImageChange = (e) => {
        const file = e.target.files?.[0] || null;
        setImageFile(file);
        if (imagePreview) {
            URL.revokeObjectURL(imagePreview);
        }
        if (file) {
            setImagePreview(URL.createObjectURL(file));
        } else {
            setImagePreview('');
        }
    };

    const handleCameraCapture = (file) => {
        setImageFile(file);
        if (imagePreview) {
            URL.revokeObjectURL(imagePreview);
        }
        if (file) {
            setImagePreview(URL.createObjectURL(file));
        } else {
            setImagePreview('');
        }
    };

    const handleSubmit = async (e) => {
        e.preventDefault();
        const cleanLandmark = landmark.trim();
        const hasLat = latitude.trim() !== '';
        const hasLng = longitude.trim() !== '';

        if (!imageFile) {
            setToast({ type: 'error', message: 'Complaint image is mandatory' });
            setTimeout(() => setToast(null), 3000);
            return;
        }
        if (!cleanLandmark) {
            setToast({ type: 'error', message: 'Nearest landmark is required' });
            setTimeout(() => setToast(null), 3000);
            return;
        }
        if (hasLat !== hasLng) {
            setToast({ type: 'error', message: 'Provide both latitude and longitude, or leave both blank' });
            setTimeout(() => setToast(null), 3000);
            return;
        }

        let parsedLat = null;
        let parsedLng = null;
        if (hasLat && hasLng) {
            parsedLat = parseFloat(latitude);
            parsedLng = parseFloat(longitude);
            if (!Number.isFinite(parsedLat) || !Number.isFinite(parsedLng)) {
                setToast({ type: 'error', message: 'Please enter valid latitude/longitude values' });
                setTimeout(() => setToast(null), 3000);
                return;
            }
        }

        setSubmitting(true);
        try {
            const finalDescription = title ? `${title} - ${description}` : description;
            const formData = new FormData();
            formData.append('description', finalDescription);
            formData.append('category', category);
            formData.append('ward', ward);
            formData.append('landmark', cleanLandmark);
            if (parsedLat !== null && parsedLng !== null) {
                formData.append('lat', String(parsedLat));
                formData.append('lng', String(parsedLng));
            }
            formData.append('image', imageFile);

            await api.post('/c/complaints', formData, {
                headers: { 'Content-Type': 'multipart/form-data' },
            });

            setToast({ type: 'success', message: 'Complaint submitted successfully' });
            setShowForm(false);
            setTitle('');
            setDescription('');
            setCategory('garbage');
            setWard('A Ward');
            setLandmark('');
            setLatitude('');
            setLongitude('');
            if (imagePreview) {
                URL.revokeObjectURL(imagePreview);
            }
            setImageFile(null);
            setImagePreview('');
            requestLiveLocation();
            fetchComplaints();
        } catch (err) {
            setToast({ type: 'error', message: toErrorMessage(err, 'Failed to submit complaint') });
        } finally {
            setSubmitting(false);
            setTimeout(() => setToast(null), 3500);
        }
    };

    if (loading) {
        return (
            <div className="page-container">
                <div className="skeleton skeleton-text full" style={{ height: 30, width: '30%', marginBottom: 24 }} />
                <div className="data-table-wrap"><SkeletonTable rows={6} /></div>
            </div>
        );
    }

    return (
        <div className="page-container" id="my-complaints-page">
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 24, flexWrap: 'wrap', gap: 12 }}>
                <div>
                    <h2 className="section-title" style={{ marginBottom: 0 }}>My Complaints</h2>
                    <p style={{ fontSize: 13, color: 'var(--text-muted)', marginTop: 4 }}>
                        {complaints.length} complaint{complaints.length !== 1 ? 's' : ''} filed
                    </p>
                </div>
                <button
                    className={`btn ${showForm ? 'btn-ghost' : 'btn-primary-filled'}`}
                    id="new-complaint-btn"
                    onClick={() => setShowForm(!showForm)}
                >
                    {showForm ? 'Cancel' : 'New Complaint'}
                </button>
            </div>

            {showForm && (
                <div className="complaint-form" style={{ marginBottom: 24 }}>
                    <form onSubmit={handleSubmit}>
                        <div className="form-group">
                            <label htmlFor="complaint-title">Title</label>
                            <input id="complaint-title" type="text" placeholder="Brief title" value={title} onChange={(e) => setTitle(e.target.value)} required />
                        </div>
                        <div className="form-group">
                            <label htmlFor="complaint-desc">Description</label>
                            <textarea id="complaint-desc" placeholder="Describe the issue" value={description} onChange={(e) => setDescription(e.target.value)} required />
                        </div>

                        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(160px, 1fr))', gap: 16 }}>
                            <div className="form-group">
                                <label htmlFor="complaint-cat">Category</label>
                                <select id="complaint-cat" value={category} onChange={(e) => setCategory(e.target.value)}>
                                    <option value="garbage">Garbage</option>
                                    <option value="road">Road/Pothole</option>
                                    <option value="water">Water Supply</option>
                                    <option value="electricity">Electricity</option>
                                    <option value="sewage">Sewage</option>
                                </select>
                            </div>
                            <div className="form-group">
                                <label htmlFor="complaint-ward">Ward</label>
                                <input id="complaint-ward" type="text" value={ward} onChange={(e) => setWard(e.target.value)} required />
                            </div>
                            <div className="form-group">
                                <label htmlFor="complaint-landmark">Nearest Landmark</label>
                                <input
                                    id="complaint-landmark"
                                    type="text"
                                    placeholder="e.g. Near Andheri Station"
                                    value={landmark}
                                    onChange={(e) => setLandmark(e.target.value)}
                                    required
                                />
                            </div>
                            <div className="form-group">
                                <label htmlFor="complaint-lat">Latitude</label>
                                <input id="complaint-lat" type="number" step="any" placeholder="Optional" value={latitude} onChange={(e) => setLatitude(e.target.value)} />
                            </div>
                            <div className="form-group">
                                <label htmlFor="complaint-lng">Longitude</label>
                                <input id="complaint-lng" type="number" step="any" placeholder="Optional" value={longitude} onChange={(e) => setLongitude(e.target.value)} />
                            </div>
                        </div>

                        <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 12, flexWrap: 'wrap' }}>
                            <button type="button" className="btn btn-ghost" onClick={requestLiveLocation} disabled={locating}>
                                {locating ? 'Fetching Location...' : 'Use Live Location'}
                            </button>
                            <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>
                                {locationHint || 'Coordinates are optional. Landmark is required.'}
                            </div>
                        </div>

                        <div className="form-group">
                            <label htmlFor="complaint-image">Complaint Image (mandatory)</label>
                            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 8, marginBottom: 8 }}>
                                <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>
                                    Capture live photo or upload from your files.
                                </span>
                                <CameraCapture onCapture={handleCameraCapture} />
                            </div>
                            <input
                                id="complaint-image"
                                type="file"
                                accept="image/*"
                                capture="environment"
                                onChange={handleImageChange}
                                required
                            />
                        </div>

                        {imagePreview && (
                            <div style={{ marginBottom: 12 }}>
                                <img
                                    src={imagePreview}
                                    alt="Complaint preview"
                                    style={{ width: 200, height: 130, objectFit: 'cover', borderRadius: 10, border: '1px solid rgba(148,163,184,0.2)' }}
                                />
                            </div>
                        )}

                        <div style={{ marginBottom: 14, fontSize: 13, color: 'var(--text-muted)' }}>
                            Routed department: <strong style={{ color: 'var(--text-primary)' }}>{routedDepartment}</strong>
                        </div>

                        <button type="submit" className="btn btn-success" id="submit-complaint" disabled={submitting}>
                            {submitting ? 'Submitting...' : 'Submit Complaint'}
                        </button>
                    </form>
                </div>
            )}

            {complaints.length === 0 ? (
                <div className="empty-state">
                    <h3>No complaints filed</h3>
                    <p>Click "New Complaint" to report a civic issue in your area</p>
                </div>
            ) : (
                <div style={{ display: 'grid', gap: 14 }}>
                    {complaints.map((c, i) => (
                        <div key={c.id || i} className="glass-panel" style={{ padding: 16 }}>
                            <div className="my-complaint-card-grid">
                                <div>
                                    {c.image_url ? (
                                        <img
                                            src={c.image_url}
                                            alt="Complaint evidence"
                                            onError={(e) => { e.currentTarget.style.display = 'none'; }}
                                            style={{ width: 140, height: 100, objectFit: 'cover', borderRadius: 8 }}
                                        />
                                    ) : (
                                        <div style={{ width: 140, height: 100, borderRadius: 8, background: '#e2e8f0' }} />
                                    )}
                                </div>
                                <div>
                                    <div style={{ fontSize: 14, fontWeight: 700, marginBottom: 6 }}>{c.description?.slice(0, 90) || 'Complaint'}</div>
                                    <div style={{ fontSize: 13, color: 'var(--text-muted)', marginBottom: 6 }}>
                                        Category: {c.category} | Ward: {c.ward}
                                    </div>
                                    <div style={{ fontSize: 13, color: 'var(--text-muted)', marginBottom: 6 }}>
                                        Department: <strong style={{ color: 'var(--text-primary)' }}>{c.department || c.predicted_department || 'N/A'}</strong>
                                    </div>
                                    <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>
                                        Status: {c.status} | Priority: {c.priority_score}
                                    </div>
                                    {c.fixed_image_url && (
                                        <div style={{ marginTop: 10 }}>
                                            <div style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 4 }}>Resolution proof</div>
                                            <img
                                                src={c.fixed_image_url}
                                                alt="Resolution proof"
                                                onError={(e) => { e.currentTarget.style.display = 'none'; }}
                                                style={{ width: 140, height: 100, objectFit: 'cover', borderRadius: 8 }}
                                            />
                                            {c.resolution_note && (
                                                <div style={{ marginTop: 4, fontSize: 12, color: 'var(--text-muted)' }}>
                                                    {c.resolution_note}
                                                </div>
                                            )}
                                        </div>
                                    )}
                                </div>
                            </div>
                        </div>
                    ))}
                </div>
            )}

            {toast && <div className={`toast toast-${toast.type}`} id="toast">{toast.message}</div>}
        </div>
    );
}
