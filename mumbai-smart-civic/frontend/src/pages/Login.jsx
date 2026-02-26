import React, { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import api from '../utils/api';
import Button from '../components/ui/Button';
import InputField from '../components/ui/InputField';
import Card from '../components/ui/Card';

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

            <Card glass className="login-card-glass">
                <div className="login-header">
                    <div className="auth-brand-mark">SC</div>
                    <h1>Smart Civic</h1>
                    <p>Mumbai Civic Portal</p>
                </div>

                {error && (
                    <div className="form-alert form-alert-danger" role="alert" aria-live="assertive">
                        {error}
                    </div>
                )}

                <form onSubmit={handleSubmit} className="auth-form">
                    <InputField
                        id="login-as"
                        label="Login As"
                        as="select"
                        value={loginAs}
                        onChange={(e) => setLoginAs(e.target.value)}
                    >
                            <option value="citizen">Citizen</option>
                            <option value="authority">Authority</option>
                    </InputField>

                    <InputField
                        id="email"
                        type="email"
                        label="Email Address"
                        value={email}
                        onChange={(e) => setEmail(e.target.value)}
                        required
                    />

                    <InputField
                        id="password"
                        type="password"
                        label="Password"
                        value={password}
                        onChange={(e) => setPassword(e.target.value)}
                        required
                    />

                    {loginAs === 'authority' && (
                        <InputField
                            id="authority-code"
                            type="text"
                            label="Authority Code"
                            value={authorityCode}
                            onChange={(e) => setAuthorityCode(e.target.value)}
                            required
                        />
                    )}

                    <Button type="submit" fullWidth loading={loading}>
                        {loading ? 'Authenticating...' : 'Login'}
                    </Button>
                </form>

                <div className="auth-help-text">
                    Authority rank is validated by authority code during login.
                </div>

                <div className="auth-quick-fill">
                    <p className="auth-quick-fill-label">
                        QUICK FILL
                    </p>
                    <div className="auth-quick-fill-row">
                        <Button
                            type="button"
                            variant="secondary"
                            onClick={() => fillDemo('citizen')}
                            fullWidth
                        >
                            Citizen
                        </Button>
                        <Button
                            type="button"
                            variant="secondary"
                            onClick={() => fillDemo('authority')}
                            fullWidth
                        >
                            Authority
                        </Button>
                    </div>
                </div>

                <div className="auth-footer-text">
                    New user? <Link to="/register" className="auth-link">Create account</Link>
                </div>
            </Card>
        </div>
    );
}
