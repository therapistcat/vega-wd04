import React from 'react';
import { useNGO } from '../../context/NGOContext';
import Button from '../../components/ui/Button';
import { MdCheck, MdClose, MdVisibility } from 'react-icons/md';

export default function AdminNGORequests() {
    const { ngoRequests, updateRequestStatus } = useNGO();

    return (
        <div className="page-container">
            <h2 style={{ fontSize: 24, fontWeight: 700, color: 'var(--text-primary)', marginBottom: 24 }}>
                NGO Assistance Requests
            </h2>

            <div className="grid-responsive" style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(350px, 1fr))', gap: '20px' }}>
                {ngoRequests.length === 0 ? (
                    <div className="table-glass-container" style={{ gridColumn: '1 / -1', padding: '60px', textAlign: 'center' }}>
                        <p style={{ color: 'var(--text-muted)' }}>No incoming requests from NGOs.</p>
                    </div>
                ) : (
                    ngoRequests.map((req) => (
                        <div key={req.id} className="glass-card" style={{ padding: '20px', border: '1px solid var(--glass-border-subtle)' }}>
                            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '16px' }}>
                                <div>
                                    <h4 style={{ color: 'var(--primary)', fontWeight: 700, fontSize: '14px', textTransform: 'uppercase' }}>{req.ngo_name || req.ngoName}</h4>
                                    <p style={{ color: 'var(--text-primary)', fontWeight: 600, marginTop: '4px' }}>{(req.issue_title || req.issueTitle)?.slice(0, 50)}...</p>
                                </div>
                                <span className={`badge-pill status-${req.status}`}>{req.status}</span>
                            </div>

                            <div style={{ display: 'flex', gap: '8px', marginTop: 'auto' }}>
                                {req.status === 'pending' && (
                                    <>
                                        <Button 
                                            size="sm" 
                                            className="btn-success" 
                                            style={{ background: '#10b981', color: 'white', border: 'none' }}
                                            onClick={() => updateRequestStatus(req.id, 'approved')}
                                        >
                                            <MdCheck style={{ marginRight: '4px' }} /> Approve
                                        </Button>
                                        <Button 
                                            size="sm" 
                                            variant="danger" 
                                            onClick={() => updateRequestStatus(req.id, 'rejected')}
                                        >
                                            <MdClose style={{ marginRight: '4px' }} /> Reject
                                        </Button>
                                    </>
                                )}
                                <Button size="sm" variant="ghost">
                                    <MdVisibility style={{ marginRight: '4px' }} /> View Issue
                                </Button>
                            </div>
                        </div>
                    ))
                )}
            </div>
        </div>
    );
}
