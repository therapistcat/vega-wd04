import React from 'react';

function getStatusClass(status) {
    const s = String(status || '').toLowerCase();
    if (s.includes('resolv')) return 'status-chip resolved';
    if (s.includes('progress')) return 'status-chip progress';
    return 'status-chip open';
}

export default function ReportDetailsModal({ report, open, onClose }) {
    if (!open || !report) return null;

    const coords = report?.location?.coordinates || [];
    const lng = Number(coords[0]);
    const lat = Number(coords[1]);

    return (
        <div
            className="report-modal-overlay"
            onClick={onClose}
            role="dialog"
            aria-modal="true"
            aria-label={`Report ${report.id}`}
        >
            <div className="report-modal-card" onClick={(e) => e.stopPropagation()}>
                <div className="report-modal-head">
                    <div>
                        <span className="report-modal-category">{report.category}</span>
                        <h3>{report.description || 'Report Details'}</h3>
                        <div className="report-modal-id">Report ID: {report.id}</div>
                    </div>
                    <div className="report-modal-badges">
                        <span className={getStatusClass(report.status)}>{report.status || 'Unknown'}</span>
                        <span className="report-ward-chip">{report.ward || 'N/A'}</span>
                    </div>
                </div>

                <div className="report-modal-image-grid">
                    <div>
                        <div className="report-modal-image-label">Complaint Evidence</div>
                        {report.image_url ? (
                            <img
                                className="report-modal-image"
                                src={report.image_url}
                                alt="Report evidence"
                                onError={(e) => { e.currentTarget.style.display = 'none'; }}
                            />
                        ) : (
                            <div className="report-modal-empty-image">No image evidence</div>
                        )}
                    </div>
                    {(report.fixed_image_url || report.status === 'Resolved') && (
                        <div>
                            <div className="report-modal-image-label">Resolution Proof</div>
                            {report.fixed_image_url ? (
                                <img
                                    className="report-modal-image"
                                    src={report.fixed_image_url}
                                    alt="Resolution proof"
                                    onError={(e) => { e.currentTarget.style.display = 'none'; }}
                                />
                            ) : (
                                <div className="report-modal-empty-image">No resolution image uploaded yet</div>
                            )}
                        </div>
                    )}
                </div>

                <div className="report-modal-grid">
                    <div><strong>Department:</strong> {report.department || report.predicted_department || 'N/A'}</div>
                    <div><strong>Priority:</strong> {report.priority_score ?? '-'}</div>
                    <div><strong>Upvotes:</strong> {report.upvotes_count ?? 0}</div>
                    <div>
                        <strong>Coordinates:</strong>{' '}
                        {Number.isFinite(lat) && Number.isFinite(lng) ? `${lat.toFixed(6)}, ${lng.toFixed(6)}` : 'N/A'}
                    </div>
                    <div><strong>Created:</strong> {report.created_at ? new Date(report.created_at).toLocaleString() : '-'}</div>
                    <div><strong>Updated:</strong> {report.updated_at ? new Date(report.updated_at).toLocaleString() : '-'}</div>
                    <div><strong>Resolved At:</strong> {report.resolved_at ? new Date(report.resolved_at).toLocaleString() : '-'}</div>
                    <div><strong>Resolved By:</strong> {report.resolved_by?.name || '-'}</div>
                    {report.source === 'call' && (
                        <div style={{ gridColumn: '1 / -1', marginTop: 10, background: 'rgba(59, 130, 246, 0.1)', padding: 12, borderRadius: 8 }}>
                            <div style={{ color: 'var(--primary)', fontWeight: 'bold', marginBottom: 6 }}>📞 Voice Call Metadata</div>
                            <div style={{ fontSize: 13, display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
                                <div><strong>Caller:</strong> {report.call_metadata?.phone_number || 'Unknown'}</div>
                                <div><strong>Call ID:</strong> {report.call_metadata?.call_id || 'N/A'}</div>
                                {report.call_metadata?.duration && <div><strong>Duration:</strong> {report.call_metadata?.duration}s</div>}
                            </div>
                            <div style={{ marginTop: 10 }}>
                                <strong>Transcript:</strong>
                                <p style={{ fontSize: 13, background: 'rgba(255,255,255,0.05)', padding: 8, borderRadius: 4, marginTop: 4, whiteSpace: 'pre-wrap' }}>
                                    {report.call_metadata?.transcript || 'No transcript available'}
                                </p>
                            </div>
                        </div>
                    )}
                </div>

                {report.resolution_note && (
                    <div className="report-modal-reporter">
                        <strong>Resolution Note:</strong> {report.resolution_note}
                    </div>
                )}

                <div className="report-modal-reporter">
                    <strong>Reported By:</strong>{' '}
                    {report.reporter?.name || 'Unknown'} ({report.reporter?.email || 'N/A'}) [{report.reporter?.role || 'citizen'}]
                </div>

                <div className="report-modal-actions">
                    <button type="button" className="btn btn-primary-filled" onClick={onClose}>
                        Close
                    </button>
                </div>
            </div>
        </div>
    );
}
