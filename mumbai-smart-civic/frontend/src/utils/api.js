import axios from 'axios';

const API_BASE = import.meta.env.VITE_API_BASE || '/api/v1';

const api = axios.create({
    baseURL: API_BASE,
    headers: {
        'Content-Type': 'application/json',
    },
});

// Attach JWT token on every request
api.interceptors.request.use((config) => {
    const token = localStorage.getItem('token');
    if (token) {
        config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
});

// Handle 401 responses globally
api.interceptors.response.use(
    (res) => res,
    (err) => {
        if (err.response && err.response.status === 401) {
            localStorage.removeItem('token');
            localStorage.removeItem('user');
            window.location.href = '/';
        }
        return Promise.reject(err);
    }
);

export default api;
