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
            <div className="navbar-left">
                <button onClick={onMenuClick} className="mobile-menu-btn navbar-menu-btn" aria-label="Open menu">
                    <MdMenu size={24} />
                </button>
                <h1 className="navbar-title">{title}</h1>
            </div>

            <div className="navbar-right">
                <div className="user-info-desktop navbar-user-copy">
                    <span className="navbar-user-name">{user?.name || 'User'}</span>
                    <span className="navbar-user-role">{roleLabel}</span>
                </div>
                <div className="navbar-avatar">
                    {initials}
                </div>
            </div>
        </header>
    );
}
