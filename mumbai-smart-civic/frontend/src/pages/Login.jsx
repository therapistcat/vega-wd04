import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { FiMail, FiLock, FiUser } from 'react-icons/fi';
import api from '../utils/api';
import Button from '../components/ui/Button';
import InputField from '../components/ui/InputField';

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

export default function Login({ onSwitch, isFlipped }) {
    const navigate = useNavigate();
    const [email, setEmail] = useState(DEMO_ACCOUNTS.citizen.email);
    const [password, setPassword] = useState(DEMO_ACCOUNTS.citizen.password);
    const [loginAs, setLoginAs] = useState('citizen');
    const [authorityCode, setAuthorityCode] = useState('');
    const [error, setError] = useState('');
    const [loading, setLoading] = useState(false);

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
        <div className="glass-card-liquid" style={{ pointerEvents: isFlipped ? 'none' : 'auto', visibility: isFlipped ? 'hidden' : 'visible' }}>
            <div className="auth-header-liquid auth-header-mini">
                <div className="auth-brand-mark-liquid auth-brand-mark-mini">SC</div>
                <h1>Smart Civic</h1>
                <p>Welcome back</p>
            </div>

            {error && (
                <div className="form-alert form-alert-danger" role="alert" style={{ marginBottom: '12px', borderRadius: '8px', background: 'rgba(239, 68, 68, 0.2)', color: '#feb2b2', padding: '8px 12px', fontSize: '12px', maxHeight: '60px', overflowY: 'auto' }}>
                    {error}
                </div>
            )}

            <form onSubmit={handleSubmit} className="auth-form-liquid" style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                <InputField
                    id="login-as"
                    label="Login As"
                    as="select"
                    value={loginAs}
                    onChange={(e) => setLoginAs(e.target.value)}
                    liquid
                    icon={FiUser}
                    size="sm"
                >
                        <option value="citizen" style={{ background: '#1e293b' }}>Citizen</option>
                        <option value="authority" style={{ background: '#1e293b' }}>Authority</option>
                </InputField>

                <InputField
                    id="email"
                    type="email"
                    label="Email Address"
                    placeholder="your@email.com"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    required
                    liquid
                    icon={FiMail}
                    size="sm"
                />

                <InputField
                    id="password"
                    type="password"
                    label="Password"
                    placeholder="••••••••"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    required
                    liquid
                    icon={FiLock}
                    size="sm"
                />

                {loginAs === 'authority' && (
                    <InputField
                        id="authority-code"
                        type="text"
                        label="Authority Code"
                        placeholder="MUM-XXX-XXXX"
                        value={authorityCode}
                        onChange={(e) => setAuthorityCode(e.target.value)}
                        required
                        liquid
                        size="sm"
                    />
                )}

                <Button 
                    type="submit" 
                    fullWidth 
                    loading={loading}
                    className="btn-liquid-gradient"
                    style={{ padding: '10px', fontSize: '14px' }}
                >
                    {loading ? 'Authenticating...' : 'Login'}
                </Button>
            </form>

            <div style={{ textAlign: 'center', marginTop: '16px', fontSize: '13px', color: 'rgba(255,255,255,0.6)' }}>
                <a href="#forgot" style={{ color: 'rgba(255,255,255,0.8)', textDecoration: 'none' }}>Forgot Password?</a>
            </div>

            <div style={{ display: 'flex', alignItems: 'center', margin: '12px 0', gap: '10px' }}>
                <div style={{ flex: 1, height: '1px', background: 'rgba(255,255,255,0.1)' }}></div>
                <span style={{ fontSize: '10px', color: 'rgba(255,255,255,0.4)', textTransform: 'uppercase', letterSpacing: '0.5px' }}>Quick Fill</span>
                <div style={{ flex: 1, height: '1px', background: 'rgba(255,255,255,0.1)' }}></div>
            </div>

            <div className="auth-quick-fill-row" style={{ display: 'flex', gap: '8px' }}>
                <button
                    type="button"
                    onClick={() => fillDemo('citizen')}
                    style={{ flex: 1, padding: '6px 8px', borderRadius: '8px', background: 'rgba(255,255,255,0.05)', border: '1px solid rgba(255,255,255,0.1)', color: 'white', fontSize: '12px', cursor: 'pointer' }}
                >
                    Citizen
                </button>
                <button
                    type="button"
                    onClick={() => fillDemo('authority')}
                    style={{ flex: 1, padding: '6px 8px', borderRadius: '8px', background: 'rgba(255,255,255,0.05)', border: '1px solid rgba(255,255,255,0.1)', color: 'white', fontSize: '12px', cursor: 'pointer' }}
                >
                    Authority
                </button>
            </div>

            <div className="auth-footer-text" style={{ textAlign: 'center', marginTop: '20px', color: 'rgba(255,255,255,0.7)', fontSize: '13px' }}>
                Don't have an account? <button type="button" onClick={onSwitch} style={{ background: 'none', border: 'none', color: '#818cf8', fontWeight: '600', cursor: 'pointer', padding: 0 }}>Register</button>
            </div>
        </div>
    );
}
