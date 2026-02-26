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
    ...props
}) {
    const fieldClass = ['ui-field', className].filter(Boolean).join(' ');
    const inputClass = ['ui-input', error ? 'ui-input--error' : '', inputClassName]
        .filter(Boolean)
        .join(' ');
    const messageId = `${id}-message`;
    const ComponentTag = as === 'textarea' ? 'textarea' : as === 'select' ? 'select' : 'input';

    return (
        <div className={fieldClass}>
            {label && <label htmlFor={id}>{label}</label>}
            <ComponentTag
                id={id}
                className={inputClass}
                aria-invalid={Boolean(error)}
                aria-describedby={hint || error ? messageId : undefined}
                {...props}
            >
                {as === 'select' ? children : null}
            </ComponentTag>
            {(hint || error) && (
                <p id={messageId} className={error ? 'ui-field__hint ui-field__hint--error' : 'ui-field__hint'}>
                    {error || hint}
                </p>
            )}
        </div>
    );
}
