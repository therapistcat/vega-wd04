import React, { createContext, useContext, useState, useEffect } from 'react';
import api from '../utils/api';

const NGOContext = createContext();

export const useNGO = () => useContext(NGOContext);

export const NGOProvider = ({ children }) => {
    const [ngoRequests, setNgoRequests] = useState([]);
    const [assignedIssues, setAssignedIssues] = useState([]);
    const [loading, setLoading] = useState(false);
    const [assignedLoading, setAssignedLoading] = useState(false);

    const getUser = () => {
        try { return JSON.parse(localStorage.getItem('user')); } catch { return null; }
    };

    const fetchRequests = async () => {
        const user = getUser();
        if (!user || (user.role !== 'ngo' && user.role !== 'authority' && user.role !== 'admin')) return;
        setLoading(true);
        try {
            const endpoint = (user.role === 'authority' || user.role === 'admin') 
                ? '/ngo-requests' 
                : '/ngo-requests/me';
            const res = await api.get(endpoint);
            setNgoRequests(Array.isArray(res.data) ? res.data : []);
        } catch (err) {
            // Don't throw - silently fail so non-NGO pages don't log out
            console.warn("NGO requests fetch skipped or failed:", err?.response?.status);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchRequests();
        fetchAssignedIssues();
    }, []);

    const fetchAssignedIssues = async () => {
        const user = getUser();
        if (!user || user.role !== 'ngo') {
            setAssignedIssues([]);
            return;
        }
        const token = localStorage.getItem('token');
        setAssignedLoading(true);
        try {
            const res = await api.get('/ngo/assigned-issues', {
                headers: token ? { Authorization: `Bearer ${token}` } : undefined
            });
            setAssignedIssues(Array.isArray(res.data) ? res.data : []);
        } catch (err) {
            console.warn("Assigned issues fetch failed:", err?.response?.status);
            setAssignedIssues([]);
        } finally {
            setAssignedLoading(false);
        }
    };

    const addRequest = async (issueId, issueTitle = '') => {
        const token = localStorage.getItem('token');
        console.log("Sending request", issueId);
        const res = await api.post('/ngo-requests', {
            issue_id: issueId
        }, {
            headers: token ? { Authorization: `Bearer ${token}` } : undefined
        });
        setNgoRequests(prev => [...prev, res.data]);
        return res.data;
    };

    const updateRequestStatus = async (requestId, status) => {
        const token = localStorage.getItem('token');
        const res = await api.patch(`/ngo-requests/${requestId}`, { status }, {
            headers: token ? { Authorization: `Bearer ${token}` } : undefined
        });
        setNgoRequests(prev => prev.map(req => 
            req.id === requestId ? res.data : req
        ));
        return res.data;
    };

    const updateIssueProgress = async (issueId, payload) => {
        const token = localStorage.getItem('token');
        const formData = new FormData();
        formData.append('status', payload.status);
        formData.append('message', payload.message);
        (payload.images || []).forEach((image) => {
            formData.append('images', image);
        });

        const res = await api.patch(`/ngo/issues/${issueId}/progress`, formData, {
            headers: {
                ...(token ? { Authorization: `Bearer ${token}` } : {}),
                'Content-Type': 'multipart/form-data',
            },
        });

        setAssignedIssues((prev) => prev.map((issue) => (
            issue.id === issueId ? res.data : issue
        )));
        return res.data;
    };

    const getIssueUpdates = async (issueId) => {
        const token = localStorage.getItem('token');
        const res = await api.get(`/ngo/issues/${issueId}/updates`, {
            headers: token ? { Authorization: `Bearer ${token}` } : undefined
        });
        return Array.isArray(res.data) ? res.data : [];
    };

    const getRequestsForIssue = (issueId) => {
        return ngoRequests.filter(req => (req.issue_id === issueId || req.issueId === issueId));
    };

    return (
        <NGOContext.Provider value={{ 
            ngoRequests, 
            assignedIssues,
            loading,
            assignedLoading,
            fetchRequests,
            fetchAssignedIssues,
            addRequest, 
            updateRequestStatus, 
            updateIssueProgress,
            getIssueUpdates,
            getRequestsForIssue
        }}>
            {children}
        </NGOContext.Provider>
    );
};
