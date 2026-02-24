import React, { useState, useCallback } from 'react';
import { Outlet } from 'react-router-dom';
import Sidebar from './Sidebar';
import Navbar from './Navbar';

export default function AppLayout({ role }) {
    const [sidebarOpen, setSidebarOpen] = useState(false);

    const toggleSidebar = useCallback(() => setSidebarOpen((o) => !o), []);
    const closeSidebar = useCallback(() => setSidebarOpen(false), []);

    return (
        <div className="app-layout">
            <Sidebar role={role} open={sidebarOpen} onClose={closeSidebar} />
            {sidebarOpen && <div className="sidebar-overlay" onClick={closeSidebar} />}
            <div className="main-content">
                <Navbar onMenuClick={toggleSidebar} />
                <Outlet />
            </div>
        </div>
    );
}
