import React, { createContext, useContext, useState, useEffect } from 'react';
import api from '../utils/api';

const NGOContext = createContext();

export const useNGO = () => useContext(NGOContext);

export const NGOProvider = ({ children }) => {
    const [ngoRequests, setNgoRequests] = useState([]);
    const [loading, setLoading] = useState(false);

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
            setNgoRequests(res.data);
        } catch (err) {
            // Don't throw - silently fail so non-NGO pages don't log out
            console.warn("NGO requests fetch skipped or failed:", err?.response?.status);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchRequests();
    }, []);

    const addRequest = async (request) => {
        const res = await api.post('/ngo-requests', {
            issue_id: request.issueId,
            issue_title: request.issueTitle
        });
        setNgoRequests(prev => [...prev, res.data]);
        return res.data;
    };

    const updateRequestStatus = async (requestId, status) => {
        const res = await api.patch(`/ngo-requests/${requestId}`, { status });
        setNgoRequests(prev => prev.map(req => 
            req.id === requestId ? res.data : req
        ));
        return res.data;
    };

    const getRequestsForIssue = (issueId) => {
        return ngoRequests.filter(req => (req.issue_id === issueId || req.issueId === issueId));
    };

    return (
        <NGOContext.Provider value={{ 
            ngoRequests, 
            loading,
            fetchRequests,
            addRequest, 
            updateRequestStatus, 
            getRequestsForIssue 
        }}>
            {children}
        </NGOContext.Provider>
    );
};
