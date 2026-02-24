import React, { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import api from '../utils/api';

const CAROUSEL_IMAGES = [
    'https://images.unsplash.com/photo-1570168007204-dfb528c6958f?q=90&w=2535&auto=format&fit=crop',
    'https://images.unsplash.com/photo-1567157577867-05ccb1388e66?q=90&w=2670&auto=format&fit=crop',
    'https://images.unsplash.com/photo-1566552881560-0be862a7c445?q=90&w=2535&auto=format&fit=crop',
    'https://commons.wikimedia.org/wiki/Special:FilePath/Mumbai%20Bandra-Worli%20Sea%20Link.jpg',
];

const AUTHORITY_RANK_OPTIONS = [
    { value: 'inspector', label: 'Inspector' },
    { value: 'ward_officer', label: 'Ward Officer' },
    { value: 'deputy_commissioner', label: 'Deputy Commissioner' },
    { value: 'commissioner', label: 'Commissioner' },
];

function parseErrorMessage(err, fallback = 'Registration failed') {
    const detail = err?.response?.data?.detail;
    if (typeof detail === 'string' && detail.trim()) return detail;
    if (Array.isArray(detail) && detail.length > 0) {
        const first = detail[0];
        if (typeof first === 'string') return first;
        if (first && typeof first === 'object' && typeof first.msg === 'string') return first.msg;
    }
    if (detail && typeof detail === 'object' && typeof detail.msg === 'string') return detail.msg;
    return fallback;
}

export default function Register() {
    const navigate = useNavigate();
    const [registerAs, setRegisterAs] = useState('citizen');
    const [name, setName] = useState('');
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [confirmPassword, setConfirmPassword] = useState('');
    const [authorityRank, setAuthorityRank] = useState('inspector');
    const [authorityCode, setAuthorityCode] = useState('');
    const [error, setError] = useState('');
    const [loading, setLoading] = useState(false);
    const [currentImage, setCurrentImage] = useState(0);

    useEffect(() => {
        const timer = setInterval(() => {
            setCurrentImage((prev) => (prev + 1) % CAROUSEL_IMAGES.length);
        }, 6000);
        return () => clearInterval(timer);
    }, []);

    const handleRegister = async (e) => {
        e.preventDefault();
        setError('');
        if (password !== confirmPassword) {
            setError('Password and confirm password do not match');
            return;
        }

        setLoading(true);
        try {
            if (registerAs === 'authority') {
                await api.post('/auth/register/authority', {
                    name,
                    email,
                    password,
                    authority_rank: authorityRank,
                    authority_code: authorityCode,
                });
            } else {
                await api.post('/auth/register', {
                    name,
                    email,
                    password,
                });
            }

            const loginPayload = {
                email,
                password,
                login_as: registerAs,
            };
            if (registerAs === 'authority') {
                loginPayload.authority_code = authorityCode;
            }

            const loginRes = await api.post('/auth/login', loginPayload);
            const { access_token, role, authority_rank, authority_level } = loginRes.data;

            localStorage.setItem('token', access_token);
            localStorage.setItem('user', JSON.stringify({
                name,
                email,
                role,
                authority_rank,
                authority_level,
            }));

            if (role === 'authority' || role === 'admin') {
                navigate('/admin/dashboard', { replace: true });
            } else {
                navigate('/citizen/dashboard', { replace: true });
            }
        } catch (err) {
            setError(parseErrorMessage(err));
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="login-page">
            <div className="login-carousel">
                {CAROUSEL_IMAGES.map((img, index) => (
                    <div
                        key={index}
                        className={`carousel-slide ${index === currentImage ? 'active' : ''}`}
                        style={{ backgroundImage: `url(${img})` }}
                    />
                ))}
                <div className="carousel-overlay" />
            </div>

            <div className="login-card-glass auth-card-wide">
                <div className="login-header">
                    <div style={{
                        width: 72, height: 72, background: 'linear-gradient(135deg, #ea580c, #f59e0b)',
                        borderRadius: '20px', color: '#fff', fontSize: '28px', fontWeight: '800',
                        display: 'flex', alignItems: 'center', justifyContent: 'center', margin: '0 auto 24px',
                        boxShadow: '0 15px 35px -5px rgba(234,88,12,0.4)',
                    }}>
                        MC
                    </div>
                    <h1>Join Mumbai Civic Portal</h1>
                    <p>Create your citizen or authority account</p>
                </div>

                {error && (
                    <div style={{
                        background: 'var(--danger-bg)', color: '#DC2626', padding: '12px',
                        borderRadius: '12px', marginBottom: '20px', fontSize: '13px', fontWeight: '600',
                        border: '1px solid rgba(220,38,38,0.2)', textAlign: 'center',
                    }}>
                        {error}
                    </div>
                )}

                <form onSubmit={handleRegister}>
                    <div className="form-input-group">
                        <label htmlFor="register-as">Register As</label>
                        <select
                            id="register-as"
                            className="form-input"
                            value={registerAs}
                            onChange={(e) => setRegisterAs(e.target.value)}
                        >
                            <option value="citizen">Citizen</option>
                            <option value="authority">Authority</option>
                        </select>
                    </div>

                    <div className="form-input-group">
                        <label htmlFor="name">Full Name</label>
                        <input
                            id="name"
                            type="text"
                            className="form-input"
                            value={name}
                            onChange={(e) => setName(e.target.value)}
                            required
                        />
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

                    <div className="auth-two-col">
                        <div className="form-input-group">
                            <label htmlFor="password">Password</label>
                            <input
                                id="password"
                                type="password"
                                className="form-input"
                                value={password}
                                onChange={(e) => setPassword(e.target.value)}
                                required
                                minLength={8}
                            />
                        </div>
                        <div className="form-input-group">
                            <label htmlFor="confirm-password">Confirm Password</label>
                            <input
                                id="confirm-password"
                                type="password"
                                className="form-input"
                                value={confirmPassword}
                                onChange={(e) => setConfirmPassword(e.target.value)}
                                required
                                minLength={8}
                            />
                        </div>
                    </div>

                    {registerAs === 'authority' && (
                        <div className="auth-two-col">
                            <div className="form-input-group">
                                <label htmlFor="authority-rank">Authority Rank</label>
                                <select
                                    id="authority-rank"
                                    className="form-input"
                                    value={authorityRank}
                                    onChange={(e) => setAuthorityRank(e.target.value)}
                                >
                                    {AUTHORITY_RANK_OPTIONS.map((opt) => (
                                        <option key={opt.value} value={opt.value}>{opt.label}</option>
                                    ))}
                                </select>
                            </div>
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
                        </div>
                    )}

                    <button type="submit" className="btn-gradient" disabled={loading}>
                        {loading ? 'Creating Account...' : 'Register'}
                    </button>
                </form>

                <div style={{ marginTop: 16, textAlign: 'center', fontSize: 13, color: 'var(--text-muted)' }}>
                    Already have an account? <Link to="/" style={{ color: 'var(--primary)', fontWeight: 700 }}>Login here</Link>
                </div>
            </div>
        </div>
    );
}
