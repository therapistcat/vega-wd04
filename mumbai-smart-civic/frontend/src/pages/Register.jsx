import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { FiUser, FiMail, FiLock, FiChevronDown } from 'react-icons/fi';
import api from '../utils/api';
import Button from '../components/ui/Button';
import InputField from '../components/ui/InputField';

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

export default function Register({ onSwitch, isFlipped }) {
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
        <div className="glass-card-liquid" style={{ pointerEvents: isFlipped ? 'auto' : 'none', visibility: isFlipped ? 'visible' : 'hidden' }}>
            <div className="auth-header-liquid auth-header-mini">
                <div className="auth-brand-mark-liquid auth-brand-mark-mini">MC</div>
                <h1>Create Account</h1>
                <p style={{ fontSize: '13px' }}>Join Mumbai Civic Portal</p>
            </div>

            {error && (
                <div className="form-alert form-alert-danger" role="alert" style={{ marginBottom: '12px', borderRadius: '8px', background: 'rgba(239, 68, 68, 0.2)', color: '#feb2b2', padding: '8px 12px', fontSize: '12px', maxHeight: '60px', overflowY: 'auto' }}>
                    {error}
                </div>
            )}

            <form onSubmit={handleRegister} className="auth-form-liquid" style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                <InputField
                    id="register-as"
                    label="Register As"
                    as="select"
                    value={registerAs}
                    onChange={(e) => setRegisterAs(e.target.value)}
                    liquid
                    icon={FiChevronDown}
                    size="sm"
                >
                        <option value="citizen" style={{ background: '#1e293b' }}>Citizen</option>
                        <option value="authority" style={{ background: '#1e293b' }}>Authority</option>
                </InputField>

                <InputField
                    id="name"
                    type="text"
                    label="Full Name"
                    placeholder="John Doe"
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    required
                    liquid
                    icon={FiUser}
                    size="sm"
                />

                <InputField
                    id="email"
                    type="email"
                    label="Email Address"
                    placeholder="john@example.com"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    required
                    liquid
                    icon={FiMail}
                    size="sm"
                />

                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }} className="auth-row-liquid">
                    <InputField
                        id="password"
                        type="password"
                        label="Password"
                        placeholder="••••••••"
                        value={password}
                        onChange={(e) => setPassword(e.target.value)}
                        required
                        minLength={8}
                        liquid
                        icon={FiLock}
                        size="sm"
                    />
                    <InputField
                        id="confirm-password"
                        type="password"
                        label="Confirm Password"
                        placeholder="••••••••"
                        value={confirmPassword}
                        onChange={(e) => setConfirmPassword(e.target.value)}
                        required
                        minLength={8}
                        liquid
                        icon={FiLock}
                        size="sm"
                    />
                </div>

                {registerAs === 'authority' && (
                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }} className="auth-row-liquid">
                        <InputField
                            id="authority-rank"
                            label="Rank"
                            as="select"
                            value={authorityRank}
                            onChange={(e) => setAuthorityRank(e.target.value)}
                            liquid
                            size="sm"
                        >
                                {AUTHORITY_RANK_OPTIONS.map((opt) => (
                                    <option key={opt.value} value={opt.value} style={{ background: '#1e293b' }}>{opt.label}</option>
                                ))}
                        </InputField>
                        <InputField
                            id="authority-code"
                            type="text"
                            label="Code"
                            placeholder="MUM-XXX-XXXX"
                            value={authorityCode}
                            onChange={(e) => setAuthorityCode(e.target.value)}
                            required
                            liquid
                            size="sm"
                        />
                    </div>
                )}

                <Button 
                    type="submit" 
                    fullWidth 
                    loading={loading}
                    className="btn-liquid-gradient"
                    style={{ marginTop: '5px', padding: '10px', fontSize: '14px' }}
                >
                    {loading ? 'Creating Account...' : 'Register'}
                </Button>
            </form>

            <div className="auth-footer-text" style={{ textAlign: 'center', marginTop: '20px', color: 'rgba(255,255,255,0.7)', fontSize: '13px' }}>
                Already have an account? <button type="button" onClick={onSwitch} style={{ background: 'none', border: 'none', color: '#818cf8', fontWeight: '600', cursor: 'pointer', padding: 0 }}>Login</button>
            </div>
        </div>
    );
}
