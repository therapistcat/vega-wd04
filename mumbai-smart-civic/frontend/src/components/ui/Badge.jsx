import React from 'react';

const Badge = ({ children, color = 'var(--text-light)', borderColor = 'rgba(255,255,255,0.1)', style = {}, className = '' }) => {
    return (
        <div 
            className={`glass-badge ${className}`} 
            style={{ 
                borderColor: borderColor,
                color: color,
                display: 'inline-flex',
                alignItems: 'center',
                padding: '6px 14px',
                borderRadius: '20px',
                fontSize: '0.85rem',
                fontWeight: 600,
                background: 'rgba(255, 255, 255, 0.05)',
                backdropFilter: 'blur(4px)',
                border: '1px solid',
                ...style 
            }}
        >
            {children}
        </div>
    );
};

export default Badge;
