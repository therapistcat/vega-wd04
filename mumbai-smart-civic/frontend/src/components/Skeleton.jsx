import React from 'react';

export function SkeletonBanner() {
    return <div className="skeleton skeleton-banner" />;
}

export function SkeletonStats({ count = 4 }) {
    return (
        <div className="stats-grid">
            {Array.from({ length: count }).map((_, i) => (
                <div key={i} className="skeleton skeleton-stat" />
            ))}
        </div>
    );
}

export function SkeletonTable({ rows = 5 }) {
    return (
        <div style={{ padding: 24 }}>
            {Array.from({ length: rows }).map((_, i) => (
                <div key={i} className="skeleton skeleton-row" style={{ animationDelay: `${i * 0.05}s` }} />
            ))}
        </div>
    );
}

export function SkeletonText({ lines = 3 }) {
    return (
        <div style={{ padding: 24 }}>
            {Array.from({ length: lines }).map((_, i) => (
                <div
                    key={i}
                    className={`skeleton skeleton-text ${i === lines - 1 ? 'short' : ''}`}
                    style={{ animationDelay: `${i * 0.07}s` }}
                />
            ))}
        </div>
    );
}

export function PageLoading() {
    return (
        <div className="page-container">
            <SkeletonBanner />
            <SkeletonStats />
            <div className="glass-card">
                <SkeletonTable />
            </div>
        </div>
    );
}
