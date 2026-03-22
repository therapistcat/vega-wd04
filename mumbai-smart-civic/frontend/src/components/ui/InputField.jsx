import React from 'react';

export default function InputField({
    id,
    label,
    hint,
    error,
    as = 'input',
    className = '',
    inputClassName = '',
    children,
    icon: Icon,
    liquid = false,
    size = 'md',
    ...props
}) {
    const fieldClass = [liquid ? 'liquid-field' : 'ui-field', className].filter(Boolean).join(' ');
    const inputClass = ['ui-input', error ? 'ui-input--error' : '', inputClassName]
        .filter(Boolean)
        .join(' ');
    
    const containerClass = [
        liquid ? 'glass-input-liquid' : '',
        liquid && size === 'sm' ? 'glass-input-mini' : ''
    ].filter(Boolean).join(' ');
    const ComponentTag = as === 'textarea' ? 'textarea' : as === 'select' ? 'select' : 'input';

    const renderInput = () => (
        <ComponentTag
            id={id}
            className={liquid ? '' : inputClass}
            aria-invalid={Boolean(error)}
            aria-describedby={(hint || error) ? `${id}-message` : undefined}
            {...props}
        >
            {as === 'select' ? children : null}
        </ComponentTag>
    );

    return (
        <div className={fieldClass}>
            {label && <label htmlFor={id} style={liquid ? { color: 'rgba(255, 255, 255, 0.7)', fontSize: '13px', fontWeight: '500' } : {}}>{label}</label>}
            
            {liquid ? (
                <div className={containerClass}>
                    {Icon && <div className="glass-input-icon"><Icon /></div>}
                    {renderInput()}
                </div>
            ) : (
                renderInput()
            )}

            {(hint || error) && (
                <p id={`${id}-message`} className={error ? 'ui-field__hint ui-field__hint--error' : 'ui-field__hint'}>
                    {error || hint}
                </p>
            )}
        </div>
    );
}
