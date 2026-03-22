import React from 'react';

const VARIANT_CLASS = {
    primary: 'ui-btn--primary',
    secondary: 'ui-btn--secondary',
    ghost: 'ui-btn--ghost',
    success: 'ui-btn--success',
    danger: 'ui-btn--danger',
};

const SIZE_CLASS = {
    sm: 'ui-btn--sm',
    md: 'ui-btn--md',
    lg: 'ui-btn--lg',
};

export default function Button({
    children,
    variant = 'primary',
    size = 'md',
    fullWidth = false,
    loading = false,
    className = '',
    disabled = false,
    ...props
}) {
    const classes = [
        'ui-btn',
        VARIANT_CLASS[variant] || VARIANT_CLASS.primary,
        SIZE_CLASS[size] || SIZE_CLASS.md,
        fullWidth ? 'ui-btn--full' : '',
        className,
    ]
        .filter(Boolean)
        .join(' ');

    return (
        <button className={classes} disabled={disabled || loading} {...props}>
            <span className={loading ? 'ui-btn__label ui-btn__label--loading' : 'ui-btn__label'}>
                {children}
            </span>
        </button>
    );
}
