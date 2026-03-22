import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { FiUser, FiMail, FiLock, FiChevronDown, FiBriefcase, FiHash } from 'react-icons/fi';
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
    // Authority fields
    const [authorityRank, setAuthorityRank] = useState('inspector');
    const [authorityCode, setAuthorityCode] = useState('');
    // NGO fields
    const [ngoName, setNgoName] = useState('');
    const [ngoRegistrationId, setNgoRegistrationId] = useState('');
    const [error, setError] = useState('');
    const [loading, setLoading] = useState(false);

    const handleRegister = async (e) => {
        e.preventDefault();
        setError('');
        if (password !== confirmPassword) {
            setError('Passwords do not match');
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
            } else if (registerAs === 'ngo') {
                await api.post('/auth/register', {
                    name,
                    email,
                    password,
                    role: 'ngo',
                    ngo_name: ngoName,
                    ngo_registration_id: ngoRegistrationId,
                });
            } else {
                await api.post('/auth/register', {
                    name,
                    email,
                    password,
                });
            }

            const loginPayload = { email, password, login_as: registerAs };
            if (registerAs === 'authority') {
                loginPayload.authority_code = authorityCode;
            }

            const loginRes = await api.post('/auth/login', loginPayload);
            const { access_token, role, authority_rank, authority_level } = loginRes.data;

            localStorage.setItem('token', access_token);
            localStorage.setItem('user', JSON.stringify({ name, email, role, authority_rank, authority_level }));

            if (role === 'authority' || role === 'admin') {
                navigate('/admin/dashboard', { replace: true });
            } else if (role === 'ngo') {
                navigate('/ngo/dashboard', { replace: true });
            } else {
                navigate('/citizen/dashboard', { replace: true });
            }
        } catch (err) {
            setError(parseErrorMessage(err));
        } finally {
            setLoading(false);
        }
    };

    // Shared input style — fully hardcoded to resist global theme changes
    const inputBoxStyle = {
        display: 'flex',
        alignItems: 'center',
        gap: '10px',
        padding: '0 14px',
        height: '44px',
        background: 'rgba(15, 23, 42, 0.65)',
        border: '1px solid rgba(255,255,255,0.1)',
        borderRadius: '12px',
        marginTop: '4px',
        width: '100%',
        boxSizing: 'border-box',
    };
    const inputStyle = {
        flex: 1,
        background: 'transparent',
        border: 'none',
        outline: 'none',
        color: '#f8fafc',
        fontSize: '13px',
        minWidth: 0,
    };
    const labelStyle = {
        fontSize: '12px',
        fontWeight: '500',
        color: 'rgba(255,255,255,0.65)',
        display: 'block',
        marginBottom: '2px',
    };
    const iconStyle = { color: 'rgba(255,255,255,0.4)', flexShrink: 0, width: 16, height: 16 };

    const Field = ({ id, label, icon: Icon, children, style = {} }) => (
        <div style={{ ...style }}>
            <label htmlFor={id} style={labelStyle}>{label}</label>
            <div style={inputBoxStyle}>
                {Icon && <Icon style={iconStyle} />}
                {children}
            </div>
        </div>
    );

    return (
        <div className="glass-card-liquid" style={{ pointerEvents: isFlipped ? 'auto' : 'none', visibility: isFlipped ? 'visible' : 'hidden' }}>
            <div className="auth-header-liquid auth-header-mini">
                <div className="auth-brand-mark-liquid auth-brand-mark-mini">MC</div>
                <h1>Create Account</h1>
                <p style={{ fontSize: '13px', color: 'rgba(255,255,255,0.65)', marginTop: '4px' }}>Join Mumbai Civic Portal</p>
            </div>

            {error && (
                <div role="alert" style={{ marginBottom: '10px', borderRadius: '8px', background: 'rgba(239,68,68,0.2)', color: '#fca5a5', padding: '8px 12px', fontSize: '12px' }}>
                    {error}
                </div>
            )}

            <form onSubmit={handleRegister} style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                {/* Account Type */}
                <Field id="role" label="Account Type" icon={FiChevronDown}>
                    <select
                        id="role"
                        value={registerAs}
                        onChange={(e) => setRegisterAs(e.target.value)}
                        style={{ ...inputStyle }}
                    >
                        <option value="citizen" style={{ background: '#1e293b' }}>Citizen</option>
                        <option value="authority" style={{ background: '#1e293b' }}>Authority</option>
                        <option value="ngo" style={{ background: '#1e293b' }}>NGO</option>
                    </select>
                </Field>

                {/* Full Name */}
                <Field id="name" label="Full Name" icon={FiUser}>
                    <input id="name" type="text" placeholder="Enter your name" value={name} onChange={(e) => setName(e.target.value)} required style={inputStyle} />
                </Field>

                {/* Email */}
                <Field id="reg-email" label="Email Address" icon={FiMail}>
                    <input id="reg-email" type="email" placeholder="your@mail.com" value={email} onChange={(e) => setEmail(e.target.value)} required style={inputStyle} />
                </Field>

                {/* Password + Confirm — fixed overflow with minWidth: 0 on each col */}
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px' }}>
                    <div style={{ minWidth: 0 }}>
                        <label htmlFor="reg-password" style={labelStyle}>Password</label>
                        <div style={inputBoxStyle}>
                            <FiLock style={iconStyle} />
                            <input id="reg-password" type="password" placeholder="••••••••" value={password} onChange={(e) => setPassword(e.target.value)} required style={inputStyle} />
                        </div>
                    </div>
                    <div style={{ minWidth: 0 }}>
                        <label htmlFor="confirm-password" style={labelStyle}>Confirm</label>
                        <div style={inputBoxStyle}>
                            <FiLock style={iconStyle} />
                            <input id="confirm-password" type="password" placeholder="••••••••" value={confirmPassword} onChange={(e) => setConfirmPassword(e.target.value)} required style={inputStyle} />
                        </div>
                    </div>
                </div>

                {/* Authority-specific fields */}
                {registerAs === 'authority' && (
                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px' }}>
                        <div style={{ minWidth: 0 }}>
                            <label htmlFor="rank" style={labelStyle}>Rank</label>
                            <div style={inputBoxStyle}>
                                <select id="rank" value={authorityRank} onChange={(e) => setAuthorityRank(e.target.value)} style={inputStyle}>
                                    {AUTHORITY_RANK_OPTIONS.map((opt) => (
                                        <option key={opt.value} value={opt.value} style={{ background: '#1e293b' }}>{opt.label}</option>
                                    ))}
                                </select>
                            </div>
                        </div>
                        <div style={{ minWidth: 0 }}>
                            <label htmlFor="reg-authority-code" style={labelStyle}>Auth Code</label>
                            <div style={inputBoxStyle}>
                                <input id="reg-authority-code" type="text" placeholder="MUM-XXX" value={authorityCode} onChange={(e) => setAuthorityCode(e.target.value)} required style={inputStyle} />
                            </div>
                        </div>
                    </div>
                )}

                {/* NGO-specific fields */}
                {registerAs === 'ngo' && (
                    <>
                        <Field id="ngo-name" label="NGO Name" icon={FiBriefcase}>
                            <input id="ngo-name" type="text" placeholder="e.g. Mumbai Care Foundation" value={ngoName} onChange={(e) => setNgoName(e.target.value)} required style={inputStyle} />
                        </Field>
                        <Field id="ngo-reg-id" label="NGO Registration ID" icon={FiHash}>
                            <input id="ngo-reg-id" type="text" placeholder="e.g. MH/NGO/12345" value={ngoRegistrationId} onChange={(e) => setNgoRegistrationId(e.target.value)} required style={inputStyle} />
                        </Field>
                    </>
                )}

                <Button
                    type="submit"
                    fullWidth
                    loading={loading}
                    className="btn-liquid-gradient"
                    style={{ padding: '8px', fontSize: '13px', marginTop: '4px' }}
                >
                    {loading ? 'Creating Account...' : 'Sign Up'}
                </Button>
            </form>

            <div style={{ textAlign: 'center', marginTop: '16px', color: 'rgba(255,255,255,0.65)', fontSize: '13px' }}>
                Already have an account?{' '}
                <button type="button" onClick={onSwitch} style={{ background: 'none', border: 'none', color: '#818cf8', fontWeight: '600', cursor: 'pointer', padding: 0 }}>
                    Login
                </button>
            </div>
        </div>
    );
}
