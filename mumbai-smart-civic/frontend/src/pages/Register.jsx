import React, { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import api from '../utils/api';
import Button from '../components/ui/Button';
import InputField from '../components/ui/InputField';
import Card from '../components/ui/Card';

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

            <Card glass className="login-card-glass auth-card-wide">
                <div className="login-header">
                    <div className="auth-brand-mark">MC</div>
                    <h1>Join Mumbai Civic Portal</h1>
                    <p>Create your citizen or authority account</p>
                </div>

                {error && (
                    <div className="form-alert form-alert-danger" role="alert" aria-live="assertive">
                        {error}
                    </div>
                )}

                <form onSubmit={handleRegister} className="auth-form">
                    <InputField
                        id="register-as"
                        label="Register As"
                        as="select"
                        value={registerAs}
                        onChange={(e) => setRegisterAs(e.target.value)}
                    >
                            <option value="citizen">Citizen</option>
                            <option value="authority">Authority</option>
                    </InputField>

                    <InputField
                        id="name"
                        type="text"
                        label="Full Name"
                        value={name}
                        onChange={(e) => setName(e.target.value)}
                        required
                    />

                    <InputField
                        id="email"
                        type="email"
                        label="Email Address"
                        value={email}
                        onChange={(e) => setEmail(e.target.value)}
                        required
                    />

                    <div className="auth-two-col">
                        <InputField
                            id="password"
                            type="password"
                            label="Password"
                            value={password}
                            onChange={(e) => setPassword(e.target.value)}
                            required
                            minLength={8}
                        />
                        <InputField
                            id="confirm-password"
                            type="password"
                            label="Confirm Password"
                            value={confirmPassword}
                            onChange={(e) => setConfirmPassword(e.target.value)}
                            required
                            minLength={8}
                        />
                    </div>

                    {registerAs === 'authority' && (
                        <div className="auth-two-col">
                            <InputField
                                id="authority-rank"
                                label="Authority Rank"
                                as="select"
                                value={authorityRank}
                                onChange={(e) => setAuthorityRank(e.target.value)}
                            >
                                    {AUTHORITY_RANK_OPTIONS.map((opt) => (
                                        <option key={opt.value} value={opt.value}>{opt.label}</option>
                                    ))}
                            </InputField>
                            <InputField
                                id="authority-code"
                                type="text"
                                label="Authority Code"
                                value={authorityCode}
                                onChange={(e) => setAuthorityCode(e.target.value)}
                                required
                            />
                        </div>
                    )}

                    <Button type="submit" fullWidth loading={loading}>
                        {loading ? 'Creating Account...' : 'Register'}
                    </Button>
                </form>

                <div className="auth-footer-text">
                    Already have an account? <Link to="/" className="auth-link">Login here</Link>
                </div>
            </Card>
        </div>
    );
}
