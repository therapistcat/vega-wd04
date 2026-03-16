import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';

import AuthContainer from './pages/AuthContainer';

// Citizen pages
import CitizenDashboard from './pages/citizen/Dashboard';
import ProgressDashboard from './pages/citizen/ProgressDashboard';
import MyComplaints from './pages/citizen/MyComplaints';
import Heatmap from './pages/citizen/Heatmap';
import Notifications from './pages/citizen/Notifications';
import BlockchainLedger from './pages/citizen/BlockchainLedger';

// Admin pages
import AdminDashboard from './pages/admin/Dashboard';
import AllComplaints from './pages/admin/AllComplaints';
import ResolveComplaint from './pages/admin/ResolveComplaint';
import Analytics from './pages/admin/Analytics';

// Layout
import AppLayout from './components/AppLayout';

/* ---- helpers ---- */
function getUser() {
    try {
        return JSON.parse(localStorage.getItem('user'));
    } catch {
        return null;
    }
}

function isAuthorityRole(role) {
    return role === 'authority' || role === 'admin';
}

function ProtectedRoute({ children, allowedRole }) {
    const token = localStorage.getItem('token');
    const user = getUser();
    if (!token || !user) return <Navigate to="/" replace />;

    if (allowedRole === 'authority' && !isAuthorityRole(user.role)) {
        return <Navigate to="/citizen/dashboard" replace />;
    }
    if (allowedRole === 'citizen' && user.role !== 'citizen') {
        return <Navigate to="/admin/dashboard" replace />;
    }
    return children;
}

export default function App() {
    return (
        <BrowserRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
            <Routes>
                {/* Public - 3D Flipping Auth Container handles both */}
                <Route path="/" element={<AuthContainer />} />
                <Route path="/register" element={<AuthContainer />} />

                {/* Citizen routes */}
                <Route
                    path="/citizen/*"
                    element={
                        <ProtectedRoute allowedRole="citizen">
                            <AppLayout role="citizen" />
                        </ProtectedRoute>
                    }
                >
                    <Route path="dashboard" element={<CitizenDashboard />} />
                    <Route path="progress-dashboard" element={<ProgressDashboard />} />
                    <Route path="my-complaints" element={<MyComplaints />} />
                    <Route path="heatmap" element={<Heatmap />} />
                    <Route path="notifications" element={<Notifications />} />
                    <Route path="blockchain-ledger" element={<BlockchainLedger />} />
                </Route>

                {/* Admin routes */}
                <Route
                    path="/admin/*"
                    element={
                        <ProtectedRoute allowedRole="authority">
                            <AppLayout role="authority" />
                        </ProtectedRoute>
                    }
                >
                    <Route path="dashboard" element={<AdminDashboard />} />
                    <Route path="all-complaints" element={<AllComplaints />} />
                    <Route path="resolve" element={<ResolveComplaint />} />
                    <Route path="analytics" element={<Analytics />} />
                </Route>

                {/* Fallback */}
                <Route path="*" element={<Navigate to="/" replace />} />
            </Routes>
        </BrowserRouter>
    );
}
