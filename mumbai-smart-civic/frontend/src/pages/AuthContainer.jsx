import React, { useEffect, useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import Login from './Login';
import Register from './Register';
import BackgroundSlideshow from '../components/ui/BackgroundSlideshow';
import ThemeToggle from '../components/ui/ThemeToggle';

export default function AuthContainer() {
    const location = useLocation();
    const navigate = useNavigate();
    const [isFlipped, setIsFlipped] = useState(location.pathname === '/register');

    useEffect(() => {
        setIsFlipped(location.pathname === '/register');
    }, [location.pathname]);

    const handleFlip = (path) => {
        navigate(path);
    };

    return (
        <div className="auth-atmosphere-root">
            <div className="floating-toggle-wrapper">
                <ThemeToggle />
            </div>
            {/* Photo slideshow background – sits at z-index 0, pointer-events none */}
            <BackgroundSlideshow />
            
            {/* Dark contrast overlay for readability */}
            <div className="auth-overlay-glass" />
            
            {/* 3D flip wrapper – z-index 10, sits above background */}
            <div className="auth-3d-perspective">
                <div className={`auth-flip-card-inner ${isFlipped ? 'is-flipped' : ''}`}>
                    {/* Front Face - Login */}
                    <div className="auth-flip-face auth-flip-face-front">
                        <Login onSwitch={() => handleFlip('/register')} isFlipped={isFlipped} />
                    </div>

                    {/* Back Face - Register */}
                    <div className="auth-flip-face auth-flip-face-back">
                        <Register onSwitch={() => handleFlip('/')} isFlipped={isFlipped} />
                    </div>
                </div>
            </div>
        </div>
    );
}
