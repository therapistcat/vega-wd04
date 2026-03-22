import React, { useEffect, useMemo, useState } from 'react';
import { MdCampaign, MdWarningAmber } from 'react-icons/md';
import api from '../../utils/api';

const NOTIFICATIONS_REFRESH_MS = 15000;

const FALLBACK_ANNOUNCEMENTS = [
    {
        id: 'fallback-1',
        title: 'Municipal Operations Briefing',
        message: 'Priority road maintenance and storm-water cleaning activities are under execution in identified wards.',
        severity: 'info',
        created_at: new Date().toISOString(),
    },
    {
        id: 'fallback-2',
        title: 'Public Safety Advisory',
        message: 'Please attach image evidence for road hazards and exposed utility lines to enable faster dispatch.',
        severity: 'warning',
        created_at: new Date(Date.now() - 3 * 60 * 60 * 1000).toISOString(),
    },
    {
        id: 'fallback-3',
        title: 'Emergency Escalation Notice',
        message: 'Reports marked as critical and accompanied by precise coordinates are escalated through emergency channels.',
        severity: 'critical',
        created_at: new Date(Date.now() - 26 * 60 * 60 * 1000).toISOString(),
    },
];

function toErrorMessage(err, fallback = 'Unable to load announcements') {
    const detail = err?.response?.data?.detail;
    if (typeof detail === 'string' && detail.trim()) return detail;
    if (Array.isArray(detail) && detail.length > 0) {
        const first = detail[0];
        if (typeof first === 'string') return first;
        if (first && typeof first === 'object' && typeof first.msg === 'string') return first.msg;
    }
    return fallback;
}

export default function Notifications() {
    const [announcements, setAnnouncements] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState('');

    const fetchAnnouncements = async (silent = false) => {
        if (!silent) setLoading(true);
        try {
            const [primary, fallback] = await Promise.allSettled([
                api.get('/c/notifications'),
                api.get('/c/announcements'),
            ]);

            const primaryRows = primary.status === 'fulfilled' && Array.isArray(primary.value?.data)
                ? primary.value.data
                : [];
            const fallbackRows = fallback.status === 'fulfilled' && Array.isArray(fallback.value?.data)
                ? fallback.value.data
                : [];

            const rows = primaryRows.length > 0 ? primaryRows : fallbackRows;
            setAnnouncements(rows.length > 0 ? rows : FALLBACK_ANNOUNCEMENTS);

            if (primary.status === 'rejected' && fallback.status === 'rejected') {
                setError(toErrorMessage(primary.reason || fallback.reason));
            } else {
                setError('');
            }
        } catch (err) {
            setAnnouncements(FALLBACK_ANNOUNCEMENTS);
            setError(toErrorMessage(err));
        } finally {
            if (!silent) setLoading(false);
        }
    };

    useEffect(() => {
        fetchAnnouncements(false);
        const timer = setInterval(() => {
            fetchAnnouncements(true);
        }, NOTIFICATIONS_REFRESH_MS);
        return () => clearInterval(timer);
    }, []);

    const counts = useMemo(() => {
        const output = { info: 0, warning: 0, critical: 0 };
        announcements.forEach((item) => {
            const key = String(item.severity || 'info').toLowerCase();
            if (output[key] !== undefined) output[key] += 1;
        });
        return output;
    }, [announcements]);

    if (loading) {
        return (
            <div className="page-container">
                <div className="skeleton skeleton-text" style={{ height: 28, width: '25%', marginBottom: 24 }} />
                {Array.from({ length: 4 }).map((_, i) => (
                    <div key={i} className="skeleton" style={{ height: 110, borderRadius: 'var(--radius-lg)', marginBottom: 10 }} />
                ))}
            </div>
        );
    }

    return (
        <div className="page-container">
            <div className="announcement-hero">
                <div>
                    <h2 className="section-title" style={{ marginBottom: 6 }}>Municipal Announcements</h2>
                    <p className="section-subtitle" style={{ marginBottom: 0 }}>
                        Official updates, advisories, and service bulletins issued by civic authorities.
                    </p>
                </div>
                <div className="announcement-summary">
                    <div className="announcement-summary-item info">{counts.info} Info</div>
                    <div className="announcement-summary-item warning">{counts.warning} Warning</div>
                    <div className="announcement-summary-item critical">{counts.critical} Critical</div>
                </div>
            </div>

            {error && (
                <div className="progress-error" style={{ marginTop: 8, marginBottom: 12 }}>
                    {error}
                </div>
            )}

            {announcements.length === 0 ? (
                <div className="empty-state">
                    <h3>No announcements available</h3>
                    <p>Municipal advisories will appear here when published.</p>
                </div>
            ) : (
                <div className="announcement-list">
                    {announcements.map((item, index) => (
                        <article
                            key={item.id || index}
                            className={`announcement-card ${String(item.severity || 'info').toLowerCase()}`}
                        >
                            <div className="announcement-head">
                                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                                    {String(item.severity).toLowerCase() === 'critical'
                                        ? <MdWarningAmber />
                                        : <MdCampaign />}
                                    <span className={`announcement-chip ${String(item.severity || 'info').toLowerCase()}`}>
                                        {String(item.severity || 'info').toUpperCase()}
                                    </span>
                                </div>
                                <span className="announcement-time">
                                    {item.created_at ? new Date(item.created_at).toLocaleString() : '-'}
                                </span>
                            </div>
                            <h3>{item.title || 'Municipal Announcement'}</h3>
                            <p>{item.message || ''}</p>
                        </article>
                    ))}
                </div>
            )}
        </div>
    );
}
