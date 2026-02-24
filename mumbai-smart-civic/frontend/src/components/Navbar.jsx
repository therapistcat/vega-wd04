import React from 'react';
import { useLocation } from 'react-router-dom';
import { MdMenu } from 'react-icons/md';

const pageTitles = {
    '/citizen/dashboard': 'Dashboard',
    '/citizen/progress-dashboard': 'Progress Dashboard',
    '/citizen/my-complaints': 'My Complaints',
    '/citizen/heatmap': 'Heatmap',
    '/citizen/blockchain-ledger': 'Chain Ledger',
    '/citizen/notifications': 'Notifications',
    '/admin/dashboard': 'Dashboard',
    '/admin/all-complaints': 'All Complaints',
    '/admin/resolve': 'Resolve Complaints',
    '/admin/analytics': 'Analytics',
};

export default function Navbar({ onMenuClick }) {
    const location = useLocation();
    const title = pageTitles[location.pathname] || 'Smart Civic';

    let user = null;
    try { user = JSON.parse(localStorage.getItem('user')); } catch { }

    const initials = user?.name
        ? user.name.split(' ').map((w) => w[0]).join('').toUpperCase().slice(0, 2)
        : 'U';
    const roleLabel = user?.role === 'authority' ? 'authority' : (user?.role || 'citizen');

    return (
        <header className="navbar-glass">
            <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
                <button onClick={onMenuClick} style={{ padding: 8, display: 'flex', color: 'var(--text-secondary)' }} className="mobile-menu-btn">
                    <MdMenu size={24} />
                </button>
                <h1 className="navbar-title">{title}</h1>
            </div>

            <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                <div style={{ textAlign: 'right', flexDirection: 'column' }} className="user-info-desktop">
                    <span style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-primary)' }}>{user?.name || 'User'}</span>
                    <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>{roleLabel}</span>
                </div>
                <div style={{
                    width: 36, height: 36, borderRadius: '50%',
                    background: 'rgba(37, 99, 235, 0.1)', color: 'var(--primary)',
                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                    fontWeight: 700, fontSize: 13, border: '1px solid rgba(37, 99, 235, 0.2)'
                }}>
                    {initials}
                </div>
            </div>
        </header>
    );
}
