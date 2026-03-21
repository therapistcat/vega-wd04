import React, { useEffect, useMemo } from 'react';
import { Link } from 'react-router-dom';
import { MdReport, MdVolunteerActivism, MdCheckCircle, MdPending } from 'react-icons/md';
import { useNGO } from '../../context/NGOContext';

export default function NGODashboard() {
    const { ngoRequests, assignedIssues, fetchRequests, fetchAssignedIssues } = useNGO();
    const user = JSON.parse(localStorage.getItem('user') || '{}');

    useEffect(() => {
        fetchRequests();
        fetchAssignedIssues();
    }, []);

    const stats = useMemo(() => {
        const myRequests = ngoRequests.filter(req => (req.ngo_name || req.ngoName) === user.name);
        return {
            total: myRequests.length,
            pending: myRequests.filter(r => r.status === 'pending').length,
            approved: myRequests.filter(r => r.status === 'approved').length,
            rejected: myRequests.filter(r => r.status === 'rejected').length,
        };
    }, [ngoRequests, user.name]);

    return (
        <div className="page-container">
            <div className="banner-hero" style={{ height: '180px' }}>
                <img src="https://images.unsplash.com/photo-1488521787991-ed7bbaae773c?ixlib=rb-4.0.3&auto=format&fit=crop&w=1200&q=80" alt="NGO Dashboard" />
                <div className="banner-content">
                    <h2>NGO Partner Dashboard</h2>
                    <p>Welcome, {user.name}. Track your assistance requests and impact.</p>
                </div>
            </div>

            <div className="dashboard-grid" style={{ marginTop: '24px' }}>
                <div className="card-stat-glass">
                    <div className="card-header-flex">
                        <div className="card-icon-box stat-icon-info"><MdReport /></div>
                    </div>
                    <div className="card-value-large">{stats.total}</div>
                    <div className="card-label-sub">My Requests</div>
                </div>

                <div className="card-stat-glass">
                    <div className="card-header-flex">
                        <div className="card-icon-box stat-icon-warning"><MdPending /></div>
                    </div>
                    <div className="card-value-large">{stats.pending}</div>
                    <div className="card-label-sub">Pending Approval</div>
                </div>

                <div className="card-stat-glass">
                    <div className="card-header-flex">
                        <div className="card-icon-box stat-icon-success"><MdCheckCircle /></div>
                    </div>
                    <div className="card-value-large">{stats.approved}</div>
                    <div className="card-label-sub">Approved Tasks</div>
                </div>

                <div className="card-stat-glass">
                    <div className="card-header-flex">
                        <div className="card-icon-box stat-icon-purple"><MdVolunteerActivism /></div>
                    </div>
                    <div className="card-value-large">{assignedIssues.length}</div>
                    <div className="card-label-sub">Active Assistance</div>
                </div>
            </div>

            <div className="table-glass-container" style={{ marginTop: '24px' }}>
                <div className="table-head">
                    <h3 className="table-title">Recent Activity</h3>
                </div>
                <div style={{ padding: '20px', textAlign: 'center', color: 'var(--text-muted)' }}>
                    {stats.total === 0 ? "You haven't made any requests yet." : "View 'My Requests' for detailed status tracking."}
                </div>
            </div>

            <div className="table-glass-container" style={{ marginTop: '24px' }}>
                <div className="table-head">
                    <h3 className="table-title">My Assigned Issues</h3>
                    <Link to="/ngo/assigned-issues" className="btn btn-ghost" style={{ textDecoration: 'none' }}>
                        Open Workspace
                    </Link>
                </div>
                <div style={{ padding: '20px', display: 'grid', gap: 12 }}>
                    {assignedIssues.length === 0 && (
                        <div style={{ color: 'var(--text-muted)', textAlign: 'center' }}>
                            No issues are assigned yet. Approved NGO work will appear here once an authority assigns a complaint to your team.
                        </div>
                    )}
                    {assignedIssues.slice(0, 3).map((issue) => (
                        <div key={issue.id} className="glass-panel" style={{ padding: 14, display: 'flex', justifyContent: 'space-between', gap: 12, flexWrap: 'wrap' }}>
                            <div>
                                <div style={{ color: 'var(--text-primary)', fontWeight: 700 }}>{issue.description?.slice(0, 100)}</div>
                                <div style={{ marginTop: 6, color: 'var(--text-muted)', fontSize: 13 }}>
                                    {issue.landmark || issue.ward || 'Unknown location'} | {issue.category || 'General'}
                                </div>
                            </div>
                            <span className={`badge-pill status-${String(issue.progress_status || 'pending').toLowerCase().replace(/\s+/g, '-')}`}>
                                {issue.progress_status || 'Pending'}
                            </span>
                        </div>
                    ))}
                </div>
            </div>
        </div>
    );
}
