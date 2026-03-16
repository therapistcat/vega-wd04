import React, { useEffect, useMemo, useState } from 'react';
import {
    MdArrowUpward,
    MdCall,
    MdCheckCircle,
    MdMyLocation,
    MdPending,
    MdPhotoCamera,
    MdReport,
    MdSearch,
    MdTrendingUp,
} from 'react-icons/md';
import { SkeletonBanner, SkeletonStats } from '../../components/Skeleton';
import CameraCapture from '../../components/CameraCapture';
import ReportDetailsModal from '../../components/ReportDetailsModal';
import Button from '../../components/ui/Button';
import api from '../../utils/api';

const BANNER_IMG = 'https://images.unsplash.com/photo-1524661135-423995f22d0b?q=80&w=2500&auto=format&fit=crop';
const HOTLINE_NUMBER = '+16018043496';

const CATEGORY_OPTIONS = [
    { value: 'garbage', label: 'Garbage' },
    { value: 'road', label: 'Road/Pothole' },
    { value: 'water', label: 'Water Supply' },
    { value: 'electricity', label: 'Electricity' },
    { value: 'sewage', label: 'Sewage' },
];
const DETECTION_VERIFY_THRESHOLD = 0.5;
const DASHBOARD_REFRESH_MS = 15000;

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

export default function CitizenDashboard() {
    const [myComplaints, setMyComplaints] = useState([]);
    const [feedComplaints, setFeedComplaints] = useState([]);
    const [departments, setDepartments] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState('');
    const [showComposer, setShowComposer] = useState(false);

    const [title, setTitle] = useState('');
    const [description, setDescription] = useState('');
    const [category, setCategory] = useState('garbage');
    const [ward, setWard] = useState('A Ward');
    const [landmark, setLandmark] = useState('');
    const [latitude, setLatitude] = useState('');
    const [longitude, setLongitude] = useState('');
    const [imageFile, setImageFile] = useState(null);
    const [imagePreview, setImagePreview] = useState('');
    const [detectingImage, setDetectingImage] = useState(false);
    const [imageDetections, setImageDetections] = useState([]);
    const [locating, setLocating] = useState(false);
    const [locationHint, setLocationHint] = useState('');
    const [submitting, setSubmitting] = useState(false);
    const [votingIds, setVotingIds] = useState([]);
    const [toast, setToast] = useState(null);
    const [areaQuery, setAreaQuery] = useState('');
    const [areaStatus, setAreaStatus] = useState('');
    const [areaData, setAreaData] = useState({
        summary: { total_reports: 0, open_count: 0, in_progress_count: 0, resolved_count: 0 },
        reports: [],
    });
    const [areaLoading, setAreaLoading] = useState(false);
    const [detailsLoading, setDetailsLoading] = useState(false);
    const [selectedReport, setSelectedReport] = useState(null);
    const [showReportModal, setShowReportModal] = useState(false);
    const [dailyPriority, setDailyPriority] = useState({
        date: '',
        has_data: false,
        message: 'No reports detected today.',
        score: null,
        top_report: null,
    });

    let user = null;
    try { user = JSON.parse(localStorage.getItem('user')); } catch { }

    const fetchDashboardData = async () => {
        setError('');
        try {
            const [mineRes, feedRes, deptRes, priorityRes] = await Promise.all([
                api.get('/c/complaints/me'),
                api.get('/c/complaints/feed'),
                api.get('/c/departments'),
                api.get('/c/reports/priority-today'),
            ]);
            setMyComplaints(Array.isArray(mineRes.data) ? mineRes.data : []);
            setFeedComplaints(Array.isArray(feedRes.data) ? feedRes.data : []);
            setDepartments(Array.isArray(deptRes.data) ? deptRes.data : []);
            setDailyPriority(priorityRes?.data || {
                date: '',
                has_data: false,
                message: 'No reports detected today.',
                score: null,
                top_report: null,
            });
        } catch (err) {
            setError(toErrorMessage(err, 'Unable to load dashboard data'));
            setMyComplaints([]);
            setFeedComplaints([]);
            setDepartments([]);
            setDailyPriority({
                date: '',
                has_data: false,
                message: 'No reports detected today.',
                score: null,
                top_report: null,
            });
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchDashboardData();
    }, []);

    useEffect(() => {
        const timer = setInterval(() => {
            fetchDashboardData();
        }, DASHBOARD_REFRESH_MS);
        return () => clearInterval(timer);
    }, []);

    const loadAreaReports = async (query = areaQuery) => {
        setAreaLoading(true);
        try {
            const res = await api.get('/c/reports/by-area', {
                params: {
                    area: query || undefined,
                    status: areaStatus || undefined,
                    limit: 120,
                },
            });
            const payload = res.data || {};
            setAreaData({
                summary: payload.summary || { total_reports: 0, open_count: 0, in_progress_count: 0, resolved_count: 0 },
                reports: Array.isArray(payload.reports) ? payload.reports : [],
            });
            setSelectedReport(null);
        } catch (err) {
            setToast({ type: 'error', message: toErrorMessage(err, 'Failed to fetch area reports') });
            setTimeout(() => setToast(null), 3000);
            setAreaData({
                summary: { total_reports: 0, open_count: 0, in_progress_count: 0, resolved_count: 0 },
                reports: [],
            });
            setSelectedReport(null);
        } finally {
            setAreaLoading(false);
        }
    };

    const openReportDetails = async (reportId) => {
        setDetailsLoading(true);
        try {
            const res = await api.get(`/c/reports/${reportId}`);
            setSelectedReport(res.data || null);
            setShowReportModal(true);
        } catch (err) {
            setToast({ type: 'error', message: toErrorMessage(err, 'Failed to fetch report details') });
            setTimeout(() => setToast(null), 3000);
        } finally {
            setDetailsLoading(false);
        }
    };

    useEffect(() => {
        loadAreaReports('');
    }, []);

    useEffect(() => {
        requestLiveLocation();
    }, []);

    const routedDepartment = useMemo(() => {
        const row = departments.find((d) => d.category?.toLowerCase() === category.toLowerCase());
        return row?.department || 'General Civic Response';
    }, [category, departments]);

    const stats = useMemo(() => {
        const total = myComplaints.length;
        const resolved = myComplaints.filter((c) => c.status === 'Resolved').length;
        const pending = myComplaints.filter((c) => c.status === 'Open').length;
        const inProgress = myComplaints.filter((c) => c.status === 'In Progress').length;
        return { total, resolved, pending, inProgress };
    }, [myComplaints]);

    const departmentSummary = useMemo(() => {
        const counts = {};
        myComplaints.forEach((c) => {
            const dept = c.department || c.predicted_department || 'General Civic Response';
            counts[dept] = (counts[dept] || 0) + 1;
        });
        return Object.entries(counts)
            .map(([department, count]) => ({ department, count }))
            .sort((a, b) => b.count - a.count);
    }, [myComplaints]);

    const detectionSummary = useMemo(() => {
        if (!imageDetections.length) {
            return {
                predictedClass: null,
                confidence: 0,
                verified: false,
                aligned: false,
                statusLabel: 'No issue detected',
            };
        }
        const top = [...imageDetections].sort(
            (a, b) => Number(b?.confidence || 0) - Number(a?.confidence || 0),
        )[0];

        const predictedClass = String(top?.class || '').toLowerCase();
        const confidence = Number(top?.confidence || 0);
        const verified = confidence >= DETECTION_VERIFY_THRESHOLD && ['garbage', 'pothole'].includes(predictedClass);
        const selectedCategory = String(category || '').toLowerCase();
        const categoryAlias = selectedCategory === 'road' ? 'pothole' : selectedCategory;
        const aligned = verified && categoryAlias === predictedClass;
        const statusLabel = verified ? 'Verified by AI' : 'Needs manual review';
        return {
            predictedClass,
            confidence,
            verified,
            aligned,
            statusLabel,
        };
    }, [imageDetections, category]);

    const requestLiveLocation = () => {
        if (!navigator.geolocation) {
            setLocationHint('Geolocation is not supported in this browser');
            return;
        }

        setLocating(true);
        setLocationHint('Fetching your live location...');

        navigator.geolocation.getCurrentPosition(
            (position) => {
                setLatitude(position.coords.latitude.toFixed(6));
                setLongitude(position.coords.longitude.toFixed(6));
                setLocationHint('Live location captured from your device');
                setLocating(false);
            },
            () => {
                setLocationHint('Location access denied. You can still submit with ward + landmark.');
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
        if (showComposer && (!latitude || !longitude)) {
            requestLiveLocation();
        }
    }, [showComposer]);

    const handleImageChange = (e) => {
        const file = e.target.files?.[0] || null;
        setImageFile(file);
        setImageDetections([]);
        if (imagePreview) {
            URL.revokeObjectURL(imagePreview);
        }
        if (file) {
            setImagePreview(URL.createObjectURL(file));
            runImageDetection(file);
        } else {
            setImagePreview('');
        }
    };

    const handleCameraCapture = (file) => {
        setImageFile(file);
        setImageDetections([]);
        if (imagePreview) {
            URL.revokeObjectURL(imagePreview);
        }
        if (file) {
            setImagePreview(URL.createObjectURL(file));
            runImageDetection(file);
        } else {
            setImagePreview('');
        }
    };

    const runImageDetection = async (file) => {
        if (!file) return;
        setDetectingImage(true);
        try {
            const formData = new FormData();
            formData.append('image', file);
            const res = await api.post('/detect', formData, {
                headers: { 'Content-Type': 'multipart/form-data' },
            });
            const detections = Array.isArray(res?.data?.detections) ? res.data.detections : [];
            setImageDetections(detections);
        } catch {
            setImageDetections([]);
        } finally {
            setDetectingImage(false);
        }
    };

    const resetComposer = () => {
        setTitle('');
        setDescription('');
        setCategory('garbage');
        setWard('A Ward');
        setLandmark('');
        setLatitude('');
        setLongitude('');
        setImageFile(null);
        if (imagePreview) {
            URL.revokeObjectURL(imagePreview);
        }
        setImagePreview('');
        setImageDetections([]);
        setLocationHint('');
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
                setToast({ type: 'error', message: 'Invalid latitude/longitude values' });
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
            setShowComposer(false);
            resetComposer();
            await fetchDashboardData();
            await loadAreaReports();
        } catch (err) {
            setToast({ type: 'error', message: toErrorMessage(err, 'Failed to submit complaint') });
        } finally {
            setSubmitting(false);
            setTimeout(() => setToast(null), 3500);
        }
    };

    const handleUpvote = async (complaintId) => {
        const item = feedComplaints.find((c) => c.id === complaintId);
        if (!item || votingIds.includes(complaintId)) return;

        const optimistic = {
            ...item,
            has_upvoted: !item.has_upvoted,
            upvotes_count: item.has_upvoted
                ? Math.max((item.upvotes_count || 0) - 1, 0)
                : (item.upvotes_count || 0) + 1,
        };

        setVotingIds((prev) => [...prev, complaintId]);
        setFeedComplaints((prev) => prev.map((c) => (c.id === complaintId ? optimistic : c)));
        setMyComplaints((prev) => prev.map((c) => (c.id === complaintId ? optimistic : c)));

        try {
            const res = await api.post(`/c/complaints/${complaintId}/upvote`);
            const updated = res.data;
            setFeedComplaints((prev) => prev.map((c) => (c.id === complaintId ? { ...c, ...updated } : c)));
            setMyComplaints((prev) => prev.map((c) => (c.id === complaintId ? { ...c, ...updated } : c)));
            await fetchDashboardData();
        } catch {
            setFeedComplaints((prev) => prev.map((c) => (c.id === complaintId ? item : c)));
            setMyComplaints((prev) => prev.map((c) => (c.id === complaintId ? item : c)));
            setToast({ type: 'error', message: 'Unable to upvote right now' });
            setTimeout(() => setToast(null), 2500);
        } finally {
            setVotingIds((prev) => prev.filter((id) => id !== complaintId));
        }
    };

    if (loading) {
        return (
            <div className="page-container">
                <SkeletonBanner />
                <SkeletonStats />
            </div>
        );
    }

    return (
        <div className="page-container">
            <div className="banner-hero">
                <img src={BANNER_IMG} alt="Mumbai cityscape" loading="lazy" />
                <div className="banner-content">
                    <h2>Welcome, {user?.name || 'Citizen'}</h2>
                    <p>Report live issues, route them to departments, and boost important complaints with upvotes.</p>
                </div>
            </div>

            <div className="hotline-strip">
                <div>
                    <div className="hotline-label">24x7 Civic Hotline</div>
                    <a className="hotline-number" href={`tel:${HOTLINE_NUMBER}`}>{HOTLINE_NUMBER}</a>
                    <div className="hotline-note">
                        Call this number, explain the problem, and the support team can register your complaint.
                    </div>
                </div>
                <a className="btn hotline-call-btn" href={`tel:${HOTLINE_NUMBER}`}>
                    <MdCall /> Call Hotline
                </a>
            </div>

            {error && <div className="dashboard-error">{error}</div>}

            <div className="dashboard-grid">
                <div className="card-stat-glass">
                    <div className="card-header-flex">
                        <div className="card-icon-box stat-icon-info">
                            <MdReport />
                        </div>
                    </div>
                    <div className="card-value-large">{stats.total}</div>
                    <div className="card-label-sub">Your Complaints</div>
                </div>
                <div className="card-stat-glass">
                    <div className="card-header-flex">
                        <div className="card-icon-box stat-icon-success">
                            <MdCheckCircle />
                        </div>
                    </div>
                    <div className="card-value-large">{stats.resolved}</div>
                    <div className="card-label-sub">Resolved</div>
                </div>
                <div className="card-stat-glass">
                    <div className="card-header-flex">
                        <div className="card-icon-box stat-icon-warning">
                            <MdPending />
                        </div>
                    </div>
                    <div className="card-value-large">{stats.pending}</div>
                    <div className="card-label-sub">Open</div>
                </div>
                <div className="card-stat-glass">
                    <div className="card-header-flex">
                        <div className="card-icon-box stat-icon-trend">
                            <MdTrendingUp />
                        </div>
                    </div>
                    <div className="card-value-large">{stats.inProgress}</div>
                    <div className="card-label-sub">In Progress</div>
                </div>
            </div>

            <div className="dashboard-shell">
                <div className="dashboard-left">
                    <div className="table-glass-container dashboard-panel-gap">
                        <div className="dash-section-head">
                            <h3>Quick Complaint</h3>
                            <Button
                                type="button"
                                variant={showComposer ? 'ghost' : 'primary'}
                                size="sm"
                                onClick={() => {
                                    const next = !showComposer;
                                    setShowComposer(next);
                                    if (!next) resetComposer();
                                }}
                            >
                                {showComposer ? 'Close' : 'Report Issue'}
                            </Button>
                        </div>

                        {showComposer && (
                            <div className="dash-composer-wrap">
                                <form onSubmit={handleSubmit}>
                                    <div className="composer-grid">
                                        <div className="form-group">
                                            <label htmlFor="dash-title">Title</label>
                                            <input
                                                id="dash-title"
                                                type="text"
                                                value={title}
                                                onChange={(e) => setTitle(e.target.value)}
                                                placeholder="Brief issue title"
                                                required
                                            />
                                        </div>
                                        <div className="form-group">
                                            <label htmlFor="dash-category">Category</label>
                                            <select id="dash-category" value={category} onChange={(e) => setCategory(e.target.value)}>
                                                {CATEGORY_OPTIONS.map((opt) => (
                                                    <option key={opt.value} value={opt.value}>{opt.label}</option>
                                                ))}
                                            </select>
                                        </div>
                                    </div>

                                    <div className="form-group">
                                        <label htmlFor="dash-desc">Description</label>
                                        <textarea
                                            id="dash-desc"
                                            value={description}
                                            onChange={(e) => setDescription(e.target.value)}
                                            placeholder="Explain what happened and where exactly."
                                            required
                                        />
                                    </div>

                                    <div className="composer-grid">
                                        <div className="form-group">
                                            <label htmlFor="dash-ward">Ward</label>
                                            <input id="dash-ward" type="text" value={ward} onChange={(e) => setWard(e.target.value)} required />
                                        </div>
                                        <div className="form-group">
                                            <label htmlFor="dash-landmark">Nearest Landmark</label>
                                            <input
                                                id="dash-landmark"
                                                type="text"
                                                value={landmark}
                                                onChange={(e) => setLandmark(e.target.value)}
                                                placeholder="e.g. Near Andheri Station"
                                                required
                                            />
                                        </div>
                                        <div className="form-group">
                                            <label htmlFor="dash-lat">Latitude</label>
                                            <input
                                                id="dash-lat"
                                                type="number"
                                                step="any"
                                                value={latitude}
                                                onChange={(e) => setLatitude(e.target.value)}
                                                placeholder="Optional"
                                            />
                                        </div>
                                        <div className="form-group">
                                            <label htmlFor="dash-lng">Longitude</label>
                                            <input
                                                id="dash-lng"
                                                type="number"
                                                step="any"
                                                value={longitude}
                                                onChange={(e) => setLongitude(e.target.value)}
                                                placeholder="Optional"
                                            />
                                        </div>
                                    </div>

                                    <div className="composer-actions">
                                        <Button
                                            type="button"
                                            variant="ghost"
                                            size="sm"
                                            disabled={locating}
                                            onClick={requestLiveLocation}
                                        >
                                            <MdMyLocation /> {locating ? 'Locating...' : 'Use Live Location'}
                                        </Button>
                                        <div className="location-hint">{locationHint || 'Coordinates are optional. Landmark is required.'}</div>
                                    </div>

                                    <div className="form-group">
                                        <label htmlFor="dash-image">Image Evidence (mandatory)</label>
                                        <div className="composer-upload-row">
                                            <span className="composer-upload-hint">
                                                Upload from files or capture live from camera.
                                            </span>
                                            <CameraCapture onCapture={handleCameraCapture} />
                                        </div>
                                        <input
                                            id="dash-image"
                                            type="file"
                                            accept="image/*"
                                            capture="environment"
                                            onChange={handleImageChange}
                                            required
                                        />
                                    </div>

                                    {imagePreview && (
                                        <div className="image-preview-wrap">
                                            <img src={imagePreview} alt="Preview" />
                                        </div>
                                    )}
                                    {(detectingImage || imageFile) && (
                                        <div className="ai-detect-panel">
                                            <div className="ai-detect-label">AI Verification</div>
                                            {detectingImage && (
                                                <div className="ai-detect-loading">Analyzing image...</div>
                                            )}
                                            {!detectingImage && imageDetections.length === 0 && (
                                                <div className="ai-detect-empty">No clear garbage/pothole found in this image.</div>
                                            )}
                                            {!detectingImage && imageDetections.length > 0 && (
                                                <>
                                                    <div className="ai-detect-status-row">
                                                        <span className={`ai-detect-status ${detectionSummary.verified ? 'ok' : 'review'}`}>
                                                            {detectionSummary.statusLabel}
                                                        </span>
                                                    </div>
                                                    <div className="ai-detect-summary ai-detect-summary-compact">
                                                        <div className="ai-detect-summary-row">
                                                            <span className="ai-detect-summary-key">Prediction</span>
                                                            <span className="ai-detect-summary-value">
                                                                {detectionSummary.predictedClass || '-'}
                                                            </span>
                                                        </div>
                                                        <div className="ai-detect-summary-row">
                                                            <span className="ai-detect-summary-key">Confidence</span>
                                                            <span className="ai-detect-summary-value">
                                                                {Math.round(detectionSummary.confidence * 100)}%
                                                            </span>
                                                        </div>
                                                    </div>
                                                    {!detectionSummary.aligned && (
                                                        <div className="ai-detect-warning">
                                                            Selected category may not match the detected issue.
                                                        </div>
                                                    )}
                                                </>
                                            )}
                                        </div>
                                    )}

                                    <div className="composer-bottom">
                                        <div className="route-chip">
                                            Routed to: <strong>{routedDepartment}</strong>
                                        </div>
                                        <Button type="submit" variant="success" size="sm" disabled={submitting}>
                                            <MdPhotoCamera /> {submitting ? 'Submitting...' : 'Submit Complaint'}
                                        </Button>
                                    </div>
                                </form>
                            </div>
                        )}
                    </div>

                    <div className="table-glass-container">
                        <div className="dash-section-head">
                            <h3>Community Complaint Feed</h3>
                            <span className="feed-count">{feedComplaints.length} posts</span>
                        </div>
                        <div className="reddit-feed">
                            {feedComplaints.length === 0 && (
                                <div className="feed-empty">No complaints yet. Be the first to report.</div>
                            )}
                            {feedComplaints.map((c) => (
                                <article key={c.id} className="reddit-card">
                                    <div className="vote-rail">
                                        <button
                                            type="button"
                                            className={`vote-btn ${c.has_upvoted ? 'active' : ''}`}
                                            onClick={() => handleUpvote(c.id)}
                                            disabled={votingIds.includes(c.id)}
                                        >
                                            <MdArrowUpward />
                                        </button>
                                        <span>{c.upvotes_count || 0}</span>
                                    </div>

                                    <div className="feed-main">
                                        <div className="feed-meta">
                                            <span>{c.category} | {c.ward}</span>
                                            <span>{c.created_at ? new Date(c.created_at).toLocaleString() : '-'}</span>
                                        </div>
                                        <h4>{c.description?.slice(0, 160) || 'Complaint'}</h4>
                                        <div className="feed-tags">
                                            <span className="tag">Status: {c.status}</span>
                                            <span className="tag">Department: {c.department || c.predicted_department || 'N/A'}</span>
                                            <span className="tag">Priority: {c.priority_score}</span>
                                        </div>
                                        {c.image_url && (
                                            <div className="feed-image-wrap">
                                                <img
                                                    src={c.image_url}
                                                    alt="Complaint evidence"
                                                    onError={(e) => { e.currentTarget.style.display = 'none'; }}
                                                />
                                            </div>
                                        )}
                                    </div>
                                </article>
                            ))}
                        </div>
                    </div>
                </div>

                <div className="dashboard-right">
                    <div className="table-glass-container" style={{ marginBottom: 14 }}>
                        <div className="dash-section-head">
                            <h3>Most Important Fix Today</h3>
                            <span className="feed-count">{dailyPriority?.date || '-'}</span>
                        </div>
                        <div style={{ padding: 14, display: 'grid', gap: 10 }}>
                            {!dailyPriority?.has_data && (
                                <div className="area-empty-state">
                                    {dailyPriority?.message || 'No reports detected today.'}
                                </div>
                            )}
                            {dailyPriority?.has_data && dailyPriority?.top_report && (
                                <button
                                    type="button"
                                    className="glass-panel area-report-item"
                                    onClick={() => openReportDetails(dailyPriority.top_report.id)}
                                >
                                    <div className="area-report-meta">
                                        {dailyPriority.top_report.ward} | {dailyPriority.top_report.status}
                                    </div>
                                    <div className="area-report-title">
                                        {dailyPriority.top_report.description?.slice(0, 90) || 'Report'}
                                    </div>
                                    <div className="area-report-reporter">
                                        Upvotes: {dailyPriority.top_report.upvotes_count || 0}
                                        {' '}| Score: {dailyPriority.score ?? '-'}
                                    </div>
                                </button>
                            )}
                            <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>
                                Updated live from database every {Math.round(DASHBOARD_REFRESH_MS / 1000)}s.
                            </div>
                        </div>
                    </div>

                    <div className="table-glass-container dashboard-panel-tight-gap">
                        <div className="dash-section-head">
                            <h3>Area Report Search</h3>
                        </div>
                        <div className="area-panel-body">
                            <form
                                onSubmit={(e) => {
                                    e.preventDefault();
                                    loadAreaReports();
                                }}
                                className="area-search-form"
                            >
                                <input
                                    type="text"
                                    placeholder="Search ward/area (e.g. M Ward)"
                                    value={areaQuery}
                                    onChange={(e) => setAreaQuery(e.target.value)}
                                    className="form-input"
                                />
                                <select
                                    value={areaStatus}
                                    onChange={(e) => setAreaStatus(e.target.value)}
                                    className="form-input"
                                >
                                    <option value="">All Status</option>
                                    <option value="Open">Open</option>
                                    <option value="In Progress">In Progress</option>
                                    <option value="Resolved">Resolved</option>
                                </select>
                                <Button type="submit" size="sm" disabled={areaLoading} className="search-icon-btn">
                                    {areaLoading ? <div className="spinner-tiny" /> : <MdSearch size={22} />}
                                </Button>
                            </form>

                            <div className="area-summary-grid">
                                <div className="glass-panel area-summary-card">
                                    <div className="area-summary-label">Total</div>
                                    <div className="area-summary-value">{areaData.summary.total_reports}</div>
                                </div>
                                <div className="glass-panel area-summary-card">
                                    <div className="area-summary-label">Open</div>
                                    <div className="area-summary-value">{areaData.summary.open_count}</div>
                                </div>
                                <div className="glass-panel area-summary-card">
                                    <div className="area-summary-label">In Progress</div>
                                    <div className="area-summary-value">{areaData.summary.in_progress_count}</div>
                                </div>
                                <div className="glass-panel area-summary-card">
                                    <div className="area-summary-label">Resolved</div>
                                    <div className="area-summary-value">{areaData.summary.resolved_count}</div>
                                </div>
                            </div>

                            <div className="area-reports-list">
                                {areaData.reports.length === 0 && (
                                    <div className="area-empty-state">No reports found for this area.</div>
                                )}
                                {areaData.reports.map((r) => (
                                    <button
                                        key={r.id}
                                        type="button"
                                        className={`glass-panel area-report-item ${selectedReport?.id === r.id ? 'active' : ''}`}
                                        onClick={() => openReportDetails(r.id)}
                                    >
                                        <div className="area-report-meta">{r.ward} | {r.status}</div>
                                        <div className="area-report-title">{r.description?.slice(0, 75) || 'Report'}</div>
                                        <div className="area-report-reporter">
                                            By: {r.reporter?.name || 'Unknown'} ({r.reporter?.email || 'N/A'})
                                        </div>
                                    </button>
                                ))}
                            </div>

                            <div className="glass-panel area-help-card">
                                <div className="area-help-text">
                                    Click any report above to open full details in a popup.
                                </div>
                                {detailsLoading && (
                                    <div className="area-help-loading">
                                        Loading report details...
                                    </div>
                                )}
                            </div>
                        </div>
                    </div>

                    <div className="table-glass-container">
                        <div className="dash-section-head">
                            <h3>Department Routing</h3>
                        </div>
                        <div className="department-routing-wrap">
                            {departmentSummary.length === 0 && (
                                <div className="area-empty-state">No complaints filed yet.</div>
                            )}
                            {departmentSummary.map((row) => (
                                <div key={row.department} className="glass-panel department-card">
                                    <div className="department-card-label">Department</div>
                                    <div className="department-card-name">{row.department}</div>
                                    <div className="department-card-count">
                                        Complaints filed: {row.count}
                                    </div>
                                </div>
                            ))}
                        </div>
                    </div>
                </div>
            </div>

            <ReportDetailsModal
                report={selectedReport}
                open={showReportModal}
                onClose={() => setShowReportModal(false)}
            />

            {toast && <div className={`toast toast-${toast.type}`}>{toast.message}</div>}
        </div>
    );
}
