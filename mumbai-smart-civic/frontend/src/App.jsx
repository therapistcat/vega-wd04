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
import EmergencyAssistant from './pages/citizen/EmergencyAssistant';
import ClusterPage from './pages/citizen/ClusterPage';
import NearbyIssuesPage from './pages/shared/NearbyIssues';

// Admin pages
import AdminDashboard from './pages/admin/Dashboard';
import AllComplaints from './pages/admin/AllComplaints';
import ResolveComplaint from './pages/admin/ResolveComplaint';
import Analytics from './pages/admin/Analytics';
import AdminBlockchainLedger from './pages/admin/BlockchainLedger';
import NGORequests from './pages/admin/NGORequests';
import TrafficPrediction from './pages/admin/TrafficPrediction';
import BlockedUsers from './pages/admin/BlockedUsers';

// NGO pages
import NGODashboard from './pages/ngo/Dashboard';
import AvailableIssues from './pages/ngo/AvailableIssues';
import MyRequests from './pages/ngo/MyAssistanceRequests';
import AssignedIssues from './pages/ngo/AssignedIssues';

// Context
import { NGOProvider } from './context/NGOContext';

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

function getLayoutRole() {
    const user = getUser();
    if (isAuthorityRole(user?.role)) return 'authority';
    if (user?.role === 'ngo') return 'ngo';
    return 'citizen';
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
    if (allowedRole === 'ngo' && user.role !== 'ngo') {
        return <Navigate to="/citizen/dashboard" replace />;
    }
    return children;
}

function AuthenticatedRoute({ children }) {
    const token = localStorage.getItem('token');
    const user = getUser();
    if (!token || !user) return <Navigate to="/" replace />;
    return children;
}

export default function App() {
    return (
        <NGOProvider>
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
                        <Route path="emergency-assistant" element={<EmergencyAssistant />} />
                        <Route path="cluster/:clusterId" element={<ClusterPage />} />
                    </Route>

                    {/* NGO routes */}
                    <Route
                        path="/ngo/*"
                        element={
                            <ProtectedRoute allowedRole="ngo">
                                <AppLayout role="ngo" />
                            </ProtectedRoute>
                        }
                    >
                        <Route path="dashboard" element={<NGODashboard />} />
                        <Route path="available-issues" element={<AvailableIssues />} />
                        <Route path="my-requests" element={<MyRequests />} />
                        <Route path="assigned-issues" element={<AssignedIssues />} />
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
                        <Route path="blockchain-ledger" element={<AdminBlockchainLedger />} />
                        <Route path="ngo-requests" element={<NGORequests />} />
                        <Route path="traffic-prediction" element={<TrafficPrediction />} />
                        <Route path="blocked" element={<BlockedUsers />} />
                    </Route>

                    <Route
                        path="/issues/*"
                        element={
                            <AuthenticatedRoute>
                                <AppLayout role={getLayoutRole()} />
                            </AuthenticatedRoute>
                        }
                    >
                        <Route path="nearby" element={<NearbyIssuesPage />} />
                    </Route>


                    {/* Fallback */}
                    <Route path="*" element={<Navigate to="/" replace />} />
                </Routes>
            </BrowserRouter>
        </NGOProvider>
    );
}
