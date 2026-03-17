import React from 'react';
import { NavLink, useNavigate } from 'react-router-dom';
import {
    MdDashboard,
    MdInsights,
    MdReport,
    MdMap,
    MdNotifications,
    MdLogout,
    MdAnalytics,
    MdList,
    MdCheckCircle,
    MdLink,
    MdOutlineEmergencyShare,
    MdVolunteerActivism,
    MdAssignment,
    MdBlock,
} from 'react-icons/md';

const citizenLinks = [
    { to: '/citizen/dashboard', label: 'Dashboard', icon: <MdDashboard /> },
    { to: '/citizen/progress-dashboard', label: 'Progress', icon: <MdInsights /> },
    { to: '/citizen/my-complaints', label: 'My Complaints', icon: <MdReport /> },
    { to: '/citizen/heatmap', label: 'Heatmap', icon: <MdMap /> },
    { to: '/citizen/blockchain-ledger', label: 'Chain Ledger', icon: <MdLink /> },
    { to: '/citizen/notifications', label: 'Notifications', icon: <MdNotifications /> },
    { to: '/citizen/emergency-assistant', label: 'Emergency Help', icon: <MdOutlineEmergencyShare /> },
];

const ngoLinks = [
    { to: '/ngo/dashboard', label: 'Dashboard', icon: <MdDashboard /> },
    { to: '/ngo/available-issues', label: 'Available Issues', icon: <MdList /> },
    { to: '/ngo/my-requests', label: 'My Requests', icon: <MdAssignment /> },
];

const authorityLinks = [
    { to: '/admin/dashboard', label: 'Dashboard', icon: <MdDashboard /> },
    { to: '/admin/all-complaints', label: 'All Complaints', icon: <MdList /> },
    { to: '/admin/ngo-requests', label: 'NGO Requests', icon: <MdVolunteerActivism /> },
    { to: '/admin/resolve', label: 'Resolve', icon: <MdCheckCircle /> },
    { to: '/admin/analytics', label: 'Analytics', icon: <MdAnalytics /> },
    { to: '/admin/traffic-prediction', label: 'Traffic AI', icon: <MdInsights /> },
    { to: '/admin/blocked', label: 'Blocked Users', icon: <MdBlock /> },
];

export default function Sidebar({ role, open, onClose }) {
    const navigate = useNavigate();
    const isAuthority = role === 'authority' || role === 'admin';
    const isNGO = role === 'ngo';
    
    let links = citizenLinks;
    if (isAuthority) links = authorityLinks;
    else if (isNGO) links = ngoLinks;

    let roleLabel = 'Citizen Portal';
    if (isAuthority) roleLabel = 'Authority Portal';
    else if (isNGO) roleLabel = 'NGO Portal';

    const handleLogout = () => {
        localStorage.removeItem('token');
        localStorage.removeItem('user');
        navigate('/', { replace: true });
    };

    const handleNav = () => {
        if (onClose) onClose();
    };

    return (
        <aside className={`sidebar-glass ${open ? 'open' : ''}`}>
            <div className="sidebar-header">
                <div className="sidebar-brand-row">
                    <div className="sidebar-brand-mark">SC</div>
                    <div className="brand-text">
                        <h2>Smart Civic</h2>
                        <span>{roleLabel}</span>
                    </div>
                </div>
            </div>

            <nav className="sidebar-nav">
                {links.map((link) => (
                    <NavLink
                        key={link.to}
                        to={link.to}
                        className={({ isActive }) => `nav-link-glass ${isActive ? 'active' : ''}`}
                        onClick={handleNav}
                    >
                        {link.icon}
                        <span>{link.label}</span>
                    </NavLink>
                ))}
            </nav>

            <div className="sidebar-footer">
                <button
                    onClick={handleLogout}
                    className="nav-link-glass nav-link-danger"
                >
                    <MdLogout />
                    <span>Logout</span>
                </button>
            </div>
        </aside>
    );
}
