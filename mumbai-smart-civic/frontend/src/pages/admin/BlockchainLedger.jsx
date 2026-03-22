import React, { useEffect, useMemo, useState } from 'react';
import { MdDone, MdRefresh, MdShield, MdWarningAmber } from 'react-icons/md';
import api from '../../utils/api';

function toErrorMessage(err, fallback = 'Unable to load blockchain audit ledger') {
    const detail = err?.response?.data?.detail;
    if (typeof detail === 'string' && detail.trim()) return detail;
    if (Array.isArray(detail) && detail.length > 0) {
        const first = detail[0];
        if (typeof first === 'string') return first;
        if (first && typeof first === 'object' && typeof first.msg === 'string') return first.msg;
    }
    return fallback;
}

function shortHash(hashValue) {
    const text = String(hashValue || '');
    if (!text) return '-';
    if (text.length <= 24) return text;
    return `${text.slice(0, 14)}...${text.slice(-8)}`;
}

function formatDate(value) {
    if (!value) return '-';
    try {
        return new Date(value).toLocaleString();
    } catch {
        return String(value);
    }
}

export default function AdminBlockchainLedger() {
    const [items, setItems] = useState([]);
    const [verification, setVerification] = useState({ valid: true, checked_blocks: 0, failure_index: null });
    const [issueFilter, setIssueFilter] = useState('');
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState('');

    const loadLedger = async (showLoader = false) => {
        if (showLoader) setLoading(true);
        try {
            const [ledgerRes, verifyRes] = await Promise.all([
                api.get('/blockchain/ledger', { params: { limit: 500 } }),
                api.get('/blockchain/verify'),
            ]);
            const payload = ledgerRes.data || {};
            setItems(Array.isArray(payload.items) ? payload.items : []);
            setVerification(verifyRes.data || payload.verification || { valid: true, checked_blocks: 0, failure_index: null });
            setError('');
        } catch (err) {
            setItems([]);
            setError(toErrorMessage(err));
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        loadLedger(true);
    }, []);

    const filteredItems = useMemo(() => {
        const normalizedFilter = issueFilter.trim().toLowerCase();
        if (!normalizedFilter) return items;
        return items.filter((block) => String(block?.data?.issue_id || '').toLowerCase().includes(normalizedFilter));
    }, [items, issueFilter]);

    if (loading) {
        return (
            <div className="page-container">
                <div className="skeleton" style={{ height: 120, borderRadius: 18, marginBottom: 16 }} />
                <div className="skeleton" style={{ height: 360, borderRadius: 18 }} />
            </div>
        );
    }

    return (
        <div className="page-container blockchain-page">
            <div className="table-glass-container" style={{ marginBottom: 16 }}>
                <div className="table-head">
                    <h3 className="table-title"><MdShield style={{ verticalAlign: 'middle', marginRight: 6 }} /> Blockchain Transparency Ledger</h3>
                    <button type="button" className="btn btn-ghost" onClick={() => loadLedger(false)}>
                        <MdRefresh style={{ marginRight: 6 }} /> Refresh
                    </button>
                </div>
                <div style={{ padding: 16 }}>
                    <div className="chain-stats-grid">
                        <div className="card-stat-glass chain-stat">
                            <div className="chain-stat-label">Audit Blocks</div>
                            <div className="chain-stat-value">{items.length}</div>
                        </div>
                        <div className="card-stat-glass chain-stat">
                            <div className="chain-stat-label">Verification</div>
                            <div className="chain-stat-value" style={{ color: verification.valid ? 'var(--success)' : 'var(--danger)' }}>
                                {verification.valid ? 'Verified' : 'Invalid'}
                            </div>
                        </div>
                        <div className="card-stat-glass chain-stat">
                            <div className="chain-stat-label">Failure Index</div>
                            <div className="chain-stat-value">{verification.failure_index ?? '-'}</div>
                        </div>
                    </div>
                    <div style={{ marginTop: 14, display: 'flex', gap: 10, flexWrap: 'wrap', alignItems: 'center' }}>
                        <input
                            type="text"
                            className="form-input"
                            placeholder="Filter by issue id"
                            value={issueFilter}
                            onChange={(e) => setIssueFilter(e.target.value)}
                            style={{ maxWidth: 300 }}
                        />
                        <span className={`badge-pill ${verification.valid ? 'impact-priority-low' : 'impact-priority-high'}`}>
                            {verification.valid ? <MdDone style={{ marginRight: 4 }} /> : <MdWarningAmber style={{ marginRight: 4 }} />}
                            {verification.valid ? 'Verified Chain' : 'Tampering Detected'}
                        </span>
                    </div>
                    {!verification.valid && (
                        <div className="progress-error" style={{ marginTop: 12 }}>
                            Chain verification failed at block index {verification.failure_index ?? 'unknown'}.
                        </div>
                    )}
                    {error && <div className="progress-error" style={{ marginTop: 12 }}>{error}</div>}
                </div>
            </div>

            <div className="table-glass-container">
                <div className="table-head">
                    <h3 className="table-title">Audit Timeline</h3>
                    <span className="feed-count">{filteredItems.length} blocks</span>
                </div>
                <div className="chain-list">
                    {filteredItems.length === 0 && (
                        <div className="glass-panel" style={{ padding: 16 }}>
                            No audit ledger entries found for this filter.
                        </div>
                    )}
                    {filteredItems.map((block, index) => (
                        <article key={block.id || `${block.index}-${index}`} className="glass-panel chain-block-card">
                            {index < filteredItems.length - 1 && <div className="chain-link-line" />}
                            <div className="chain-block-top">
                                <span className="chain-block-index">#{block.index}</span>
                                <span className={`badge-pill ${verification.valid ? 'impact-priority-low' : 'impact-priority-high'}`}>
                                    {block.data?.action_type || 'AUDIT_EVENT'}
                                </span>
                            </div>

                            <div className="chain-row">
                                <div className="chain-row-label">Issue ID</div>
                                <div className="chain-row-value">{block.data?.issue_id || '-'}</div>
                            </div>
                            <div className="chain-row">
                                <div className="chain-row-label">Performed By</div>
                                <div className="chain-row-value">
                                    {block.data?.performed_by?.name || 'Unknown'} ({block.data?.performed_by?.role || 'system'})
                                </div>
                            </div>
                            <div className="chain-row">
                                <div className="chain-row-label">Timestamp</div>
                                <div className="chain-row-value">{formatDate(block.timestamp)}</div>
                            </div>
                            <div className="chain-row">
                                <div className="chain-row-label">Hash</div>
                                <div className="chain-row-value chain-hash">{shortHash(block.hash)}</div>
                            </div>
                            <div className="chain-row">
                                <div className="chain-row-label">Previous Hash</div>
                                <div className="chain-row-value chain-hash">{shortHash(block.previous_hash)}</div>
                            </div>
                            <div className="chain-row">
                                <div className="chain-row-label">Metadata</div>
                                <div className="chain-row-value">
                                    <pre style={{ margin: 0, whiteSpace: 'pre-wrap', fontSize: 12, color: 'var(--text-secondary)' }}>
                                        {JSON.stringify(block.data?.metadata || {}, null, 2)}
                                    </pre>
                                </div>
                            </div>
                        </article>
                    ))}
                </div>
            </div>
        </div>
    );
}
