import React from 'react';

export default function Card({ children, className = '', glass = false, as = 'section', ...props }) {
    const ComponentTag = as;
    const classes = ['ui-card', glass ? 'ui-card--glass' : '', className].filter(Boolean).join(' ');

    return (
        <ComponentTag className={classes} {...props}>
            {children}
        </ComponentTag>
    );
}
