import React, { useEffect, useMemo, useState } from 'react';
import { MdDone, MdLink, MdShield, MdWarningAmber } from 'react-icons/md';
import api from '../../utils/api';

function toErrorMessage(err, fallback = 'Something went wrong') {
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
    if (text.length <= 20) return text;
    return `${text.slice(0, 12)}...${text.slice(-6)}`;
}

function formatDate(value) {
    if (!value) return '-';
    try {
        return new Date(value).toLocaleString();
    } catch {
        return String(value);
    }
}

function statusClass(statusValue) {
    const normalized = String(statusValue || '').toLowerCase();
    if (normalized === 'resolved') return 'resolved';
    if (normalized.includes('progress')) return 'in-progress';
    return 'open';
}

export default function BlockchainLedger() {
    const [items, setItems] = useState([]);
    const [stats, setStats] = useState({
        total_blocks: 0,
        chain_length: 0,
        last_block_hash: '',
        difficulty: 2,
    });
    const [loading, setLoading] = useState(true);
    const [anchoring, setAnchoring] = useState(false);
    const [verifying, setVerifying] = useState({});
    const [verifyResults, setVerifyResults] = useState({});
    const [error, setError] = useState('');
    const [toast, setToast] = useState(null);

    const loadChain = async (showLoading = false) => {
        if (showLoading) setLoading(true);
        setError('');
        try {
            const res = await api.get('/blockchain/chain', { params: { limit: 300 } });
            const payload = res.data || {};
            setItems(Array.isArray(payload.items) ? payload.items : []);
            setStats(payload.stats || {
                total_blocks: 0,
                chain_length: 0,
                last_block_hash: '',
                difficulty: 2,
            });
        } catch (err) {
            setError(toErrorMessage(err, 'Unable to load blockchain ledger'));
            setItems([]);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        loadChain(true);
    }, []);

    const anchorAll = async () => {
        setAnchoring(true);
        try {
            const res = await api.post('/blockchain/anchor-all');
            const data = res.data || {};
            setToast({
                type: 'success',
                message: `Anchored ${data.anchored_new || 0} new complaints. Already anchored: ${data.already_anchored || 0}.`,
            });
            await loadChain(false);
        } catch (err) {
            setToast({ type: 'error', message: toErrorMessage(err, 'Failed to anchor complaints') });
        } finally {
            setAnchoring(false);
            setTimeout(() => setToast(null), 3500);
        }
    };

    const verifyComplaint = async (complaintId) => {
        if (!complaintId) return;
        setVerifying((prev) => ({ ...prev, [complaintId]: true }));
        try {
            const res = await api.get(`/blockchain/verify/${complaintId}`);
            setVerifyResults((prev) => ({ ...prev, [complaintId]: res.data || {} }));
        } catch (err) {
            setVerifyResults((prev) => ({
                ...prev,
                [complaintId]: { valid: false, anchored: false, reason: toErrorMessage(err, 'Verification failed') },
            }));
        } finally {
            setVerifying((prev) => ({ ...prev, [complaintId]: false }));
        }
    };

    const complaintBlocks = useMemo(
        () => items.filter((block) => !block.is_genesis),
        [items],
    );

    if (loading) {
        return (
            <div className="page-container blockchain-page">
                <div className="skeleton" style={{ height: 120, borderRadius: 18, marginBottom: 16 }} />
                <div className="skeleton" style={{ height: 300, borderRadius: 18 }} />
            </div>
        );
    }

    return (
        <div className="page-container blockchain-page">
            <div className="table-glass-container" style={{ marginBottom: 16 }}>
                <div className="dash-section-head">
                    <h3><MdShield style={{ verticalAlign: 'middle', marginRight: 6 }} /> Blockchain Complaint Ledger</h3>
                    <button
                        type="button"
                        className="btn btn-primary-filled"
                        onClick={anchorAll}
                        disabled={anchoring}
                    >
                        <MdLink /> {anchoring ? 'Anchoring...' : 'Anchor My Complaints'}
                    </button>
                </div>
                <div style={{ padding: 16 }}>
                    <div className="chain-stats-grid">
                        <div className="card-stat-glass chain-stat">
                            <div className="chain-stat-label">Total Blocks</div>
                            <div className="chain-stat-value">{Number(stats.total_blocks || 0)}</div>
                        </div>
                        <div className="card-stat-glass chain-stat">
                            <div className="chain-stat-label">Chain Length</div>
                            <div className="chain-stat-value">{Number(stats.chain_length || 0)}</div>
                        </div>
                        <div className="card-stat-glass chain-stat">
                            <div className="chain-stat-label">Last Block Hash</div>
                            <div className="chain-stat-value chain-hash-big">{shortHash(stats.last_block_hash)}</div>
                        </div>
                    </div>
                    {error && <div className="progress-error" style={{ marginTop: 12 }}>{error}</div>}
                </div>
            </div>

            <div className="table-glass-container">
                <div className="dash-section-head">
                    <h3>Anchored Complaint Blocks</h3>
                    <span className="feed-count">{complaintBlocks.length} blocks</span>
                </div>

                <div className="chain-list">
                    {complaintBlocks.length === 0 && (
                        <div className="glass-panel" style={{ padding: 16 }}>
                            No complaint blocks yet. Click "Anchor My Complaints" to create your ledger records.
                        </div>
                    )}

                    {complaintBlocks.map((block, index) => {
                        const complaintId = block.complaint_id;
                        const snapshot = block.complaint_snapshot || {};
                        const verify = complaintId ? verifyResults[complaintId] : null;
                        const verifyState = complaintId ? verifying[complaintId] : false;
                        const status = snapshot.status || 'Open';

                        return (
                            <article key={block.id || `${block.index}-${index}`} className="glass-panel chain-block-card">
                                {index < complaintBlocks.length - 1 && <div className="chain-link-line" />}

                                <div className="chain-block-top">
                                    <span className="chain-block-index">#{block.index}</span>
                                    <span className={`chain-status ${statusClass(status)}`}>{status}</span>
                                </div>

                                <div className="chain-row">
                                    <div className="chain-row-label">TX Hash</div>
                                    <div className="chain-row-value chain-hash">{shortHash(block.block_hash)}</div>
                                </div>

                                <div className="chain-row">
                                    <div className="chain-row-label">Complaint</div>
                                    <div className="chain-row-value">
                                        {snapshot.description ? String(snapshot.description).slice(0, 140) : 'No description available'}
                                    </div>
                                </div>

                                <div className="chain-row">
                                    <div className="chain-row-label">Timestamp</div>
                                    <div className="chain-row-value">{formatDate(block.mined_at || snapshot.created_at)}</div>
                                </div>

                                <div className="chain-row chain-row-last">
                                    <button
                                        type="button"
                                        className="btn btn-success"
                                        disabled={!complaintId || verifyState}
                                        onClick={() => verifyComplaint(complaintId)}
                                    >
                                        {verifyState ? 'Verifying...' : 'Verify'}
                                    </button>

                                    {verify && (
                                        <span className={`chain-verify ${verify.valid ? 'ok' : 'bad'}`}>
                                            {verify.valid ? <MdDone /> : <MdWarningAmber />}
                                            {verify.valid ? 'Verified' : 'Tampered/Invalid'}
                                        </span>
                                    )}
                                </div>
                            </article>
                        );
                    })}
                </div>
            </div>

            {toast && <div className={`toast toast-${toast.type}`}>{toast.message}</div>}
        </div>
    );
}
