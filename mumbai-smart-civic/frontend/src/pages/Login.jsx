import React, { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import api from '../utils/api';

const IMAGES = [
    'https://images.unsplash.com/photo-1570168007204-dfb528c6958f?q=90&w=2535&auto=format&fit=crop',
    'https://images.unsplash.com/photo-1567157577867-05ccb1388e66?q=90&w=2670&auto=format&fit=crop',
    'https://images.unsplash.com/photo-1566552881560-0be862a7c445?q=90&w=2535&auto=format&fit=crop',
    'https://commons.wikimedia.org/wiki/Special:FilePath/Mumbai%20Bandra-Worli%20Sea%20Link.jpg',
];

const DEMO_ACCOUNTS = {
    citizen: {
        email: 'citizen@example.com',
        password: 'Citizen@12345',
    },
    authority: {
        email: 'authority@example.com',
        password: 'Authority@12345',
        authorityCode: 'MUM-COM-4404',
    },
};

export default function Login() {
    const navigate = useNavigate();
    const [email, setEmail] = useState(DEMO_ACCOUNTS.citizen.email);
    const [password, setPassword] = useState(DEMO_ACCOUNTS.citizen.password);
    const [loginAs, setLoginAs] = useState('citizen');
    const [authorityCode, setAuthorityCode] = useState('');
    const [error, setError] = useState('');
    const [loading, setLoading] = useState(false);
    const [currentImage, setCurrentImage] = useState(0);

    useEffect(() => {
        const timer = setInterval(() => {
            setCurrentImage((prev) => (prev + 1) % IMAGES.length);
        }, 6000);
        return () => clearInterval(timer);
    }, []);

    const fillDemo = (mode) => {
        if (mode === 'authority') {
            setLoginAs('authority');
            setEmail(DEMO_ACCOUNTS.authority.email);
            setPassword(DEMO_ACCOUNTS.authority.password);
            setAuthorityCode(DEMO_ACCOUNTS.authority.authorityCode);
            return;
        }
        setLoginAs('citizen');
        setEmail(DEMO_ACCOUNTS.citizen.email);
        setPassword(DEMO_ACCOUNTS.citizen.password);
        setAuthorityCode('');
    };

    const handleSubmit = async (e) => {
        e.preventDefault();
        setError('');
        setLoading(true);

        try {
            const payload = {
                email,
                password,
                login_as: loginAs,
            };
            if (loginAs === 'authority') {
                payload.authority_code = authorityCode;
            }

            const res = await api.post('/auth/login', payload);
            const {
                access_token,
                role,
                authority_rank,
                authority_level,
            } = res.data;

            const user = {
                email,
                name: email.split('@')[0],
                role,
                authority_rank,
                authority_level,
            };

            localStorage.setItem('token', access_token);
            localStorage.setItem('user', JSON.stringify(user));

            if (role === 'authority' || role === 'admin') {
                navigate('/admin/dashboard', { replace: true });
            } else {
                navigate('/citizen/dashboard', { replace: true });
            }
        } catch (err) {
            setError(err.response?.data?.detail || 'Login failed');
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="login-page">
            <div className="login-carousel">
                {IMAGES.map((img, index) => (
                    <div
                        key={index}
                        className={`carousel-slide ${index === currentImage ? 'active' : ''}`}
                        style={{ backgroundImage: `url(${img})` }}
                    />
                ))}
                <div className="carousel-overlay" />
            </div>

            <div className="login-card-glass">
                <div className="login-header">
                    <div style={{
                        width: 72, height: 72, background: 'linear-gradient(135deg, #ea580c, #f59e0b)',
                        borderRadius: '20px', color: '#fff', fontSize: '28px', fontWeight: '800',
                        display: 'flex', alignItems: 'center', justifyContent: 'center', margin: '0 auto 24px',
                        boxShadow: '0 15px 35px -5px rgba(234,88,12,0.4)'
                    }}>
                        SC
                    </div>
                    <h1>Smart Civic</h1>
                    <p>Mumbai Civic Portal</p>
                </div>

                {error && (
                    <div style={{
                        background: 'var(--danger-bg)', color: '#DC2626', padding: '12px',
                        borderRadius: '12px', marginBottom: '20px', fontSize: '13px', fontWeight: '600',
                        border: '1px solid rgba(220,38,38,0.2)', textAlign: 'center'
                    }}>
                        {error}
                    </div>
                )}

                <form onSubmit={handleSubmit}>
                    <div className="form-input-group">
                        <label htmlFor="login-as">Login As</label>
                        <select
                            id="login-as"
                            className="form-input"
                            value={loginAs}
                            onChange={(e) => setLoginAs(e.target.value)}
                        >
                            <option value="citizen">Citizen</option>
                            <option value="authority">Authority</option>
                        </select>
                    </div>

                    <div className="form-input-group">
                        <label htmlFor="email">Email Address</label>
                        <input
                            id="email"
                            type="email"
                            className="form-input"
                            value={email}
                            onChange={(e) => setEmail(e.target.value)}
                            required
                        />
                    </div>

                    <div className="form-input-group">
                        <label htmlFor="password">Password</label>
                        <input
                            id="password"
                            type="password"
                            className="form-input"
                            value={password}
                            onChange={(e) => setPassword(e.target.value)}
                            required
                        />
                    </div>

                    {loginAs === 'authority' && (
                        <div className="form-input-group">
                            <label htmlFor="authority-code">Authority Code</label>
                            <input
                                id="authority-code"
                                type="text"
                                className="form-input"
                                value={authorityCode}
                                onChange={(e) => setAuthorityCode(e.target.value)}
                                required
                            />
                        </div>
                    )}

                    <button type="submit" className="btn-gradient" disabled={loading}>
                        {loading ? 'Authenticating...' : 'Login'}
                    </button>
                </form>

                <div style={{ marginTop: 20, fontSize: 12, color: 'var(--text-muted)', textAlign: 'center' }}>
                    Authority rank is validated by authority code during login.
                </div>

                <div style={{ marginTop: 24, paddingTop: 18, borderTop: '1px solid rgba(148,163,184,0.15)' }}>
                    <p style={{ fontSize: 12, color: 'var(--text-muted)', textAlign: 'center', marginBottom: 12 }}>
                        QUICK FILL
                    </p>
                    <div style={{ display: 'flex', gap: 12 }}>
                        <button
                            type="button"
                            onClick={() => fillDemo('citizen')}
                            style={{
                                flex: 1, padding: '10px', borderRadius: '12px', border: '1px solid var(--border-default)',
                                background: '#fff', fontSize: '13px', fontWeight: '600', color: 'var(--text-secondary)',
                                transition: 'all 0.2s'
                            }}
                        >
                            Citizen
                        </button>
                        <button
                            type="button"
                            onClick={() => fillDemo('authority')}
                            style={{
                                flex: 1, padding: '10px', borderRadius: '12px', border: '1px solid var(--border-default)',
                                background: '#fff', fontSize: '13px', fontWeight: '600', color: 'var(--text-secondary)',
                                transition: 'all 0.2s'
                            }}
                        >
                            Authority
                        </button>
                    </div>
                </div>

                <div style={{ marginTop: 16, textAlign: 'center', fontSize: 13, color: 'var(--text-muted)' }}>
                    New user? <Link to="/register" style={{ color: 'var(--primary)', fontWeight: 700 }}>Create account</Link>
                </div>
            </div>
        </div>
    );
}
