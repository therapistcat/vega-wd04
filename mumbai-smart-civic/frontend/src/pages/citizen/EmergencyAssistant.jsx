import React, { useState, useRef, useEffect, useCallback } from 'react';
import axios from 'axios';

// ------- Disaster Icon Map -------
const DISASTER_ICONS = {
    earthquake: '🌍',
    fire: '🔥',
    flood: '🌊',
    medical: '🏥',
    accident: '🚗',
    generic: '⚠️',
};

const URGENCY_CONFIG = {
    critical: { label: 'CRITICAL', cls: 'urgency-critical' },
    high:     { label: 'HIGH',     cls: 'urgency-high' },
    medium:   { label: 'MEDIUM',  cls: 'urgency-medium' },
    low:      { label: 'LOW',      cls: 'urgency-low' },
};

const ACTION_ICONS = {
    drop_cover_hold:        '🛡️',
    avoid_lift:             '🚫',
    stay_away_windows:      '⚠️',
    evacuate_after_shaking: '🚶',
    move_to_open_ground:    '🌿',
    stay_low:               '⬇️',
    cover_mouth:            '😷',
    use_stairs:             '🪜',
    call_fire_brigade:      '🚒',
    do_not_open_hot_doors:  '🔥',
    move_to_high_ground:    '⛰️',
    avoid_floodwater:       '🌊',
    call_emergency:         '📞',
    do_not_walk_flood:      '🚫',
    switch_off_electricity: '⚡',
    call_ambulance:         '🚑',
    do_not_move_victim:     '🛑',
    apply_pressure:         '🩹',
    cpr_if_needed:          '❤️',
    keep_conscious:         '👁️',
    manage_traffic:         '✋',
    keep_victim_warm:       '🧥',
    stay_calm:              '🧘',
    follow_authorities:     '👮',
    evacuate_if_told:       '🚪',
};

export default function EmergencyAssistant() {
    const [input, setInput] = useState('');
    const [loading, setLoading] = useState(false);
    const [result, setResult] = useState(null);
    const [error, setError] = useState(null);
    const [listening, setListening] = useState(false);
    const [dots, setDots] = useState('');
    const recognitionRef = useRef(null);
    const resultsRef = useRef(null);

    // Animated dots for loading
    useEffect(() => {
        if (!loading) return;
        const id = setInterval(() => setDots(d => d.length >= 3 ? '' : d + '.'), 500);
        return () => clearInterval(id);
    }, [loading]);

    // Scroll to results when they appear
    useEffect(() => {
        if (result && resultsRef.current) {
            resultsRef.current.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }
    }, [result]);

    // ---- Voice Input ----
    const startListening = useCallback(() => {
        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        if (!SpeechRecognition) {
            setError('Voice input is not supported in this browser. Please use Chrome.');
            return;
        }
        const recognition = new SpeechRecognition();
        recognition.lang = 'en-IN';
        recognition.interimResults = true;
        recognition.continuous = false;
        recognition.onstart = () => setListening(true);
        recognition.onend = () => setListening(false);
        recognition.onresult = (e) => {
            const transcript = Array.from(e.results)
                .map(r => r[0].transcript)
                .join('');
            setInput(transcript);
        };
        recognition.onerror = () => {
            setListening(false);
            setError('Voice recognition error. Please try again.');
        };
        recognitionRef.current = recognition;
        recognition.start();
    }, []);

    const stopListening = useCallback(() => {
        recognitionRef.current?.stop();
        setListening(false);
    }, []);

    // ---- Submit ----
    const handleSubmit = async (e) => {
        e?.preventDefault();
        if (!input.trim()) return;
        setLoading(true);
        setError(null);
        setResult(null);
        try {
            const { data } = await axios.post(
                'http://localhost:8000/api/emergency-visual',
                { user_input: input.trim() },
                { timeout: 30000 }
            );
            setResult(data);
        } catch (err) {
            const msg = err?.response?.data?.detail || 'Failed to process emergency. Please try again.';
            setError(msg);
        } finally {
            setLoading(false);
        }
    };

    const handleDownload = () => {
        if (!result?.pdf_url) return;
        const link = document.createElement('a');
        link.href = `http://localhost:8000${result.pdf_url}`;
        link.download = `emergency-guide-${result.disaster_type}.pdf`;
        link.target = '_blank';
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
    };

    const urgencyConf = URGENCY_CONFIG[result?.urgency_level] || URGENCY_CONFIG.high;

    return (
        <div className="emergency-page">
            {/* ---- Hero Header ---- */}
            <div className="emergency-hero">
                <div className="emergency-hero-glow" />
                <div className="emergency-hero-content">
                    <div className="emergency-hero-icon">🆘</div>
                    <div>
                        <h1 className="emergency-hero-title">AI Emergency Visual Assistant</h1>
                        <p className="emergency-hero-sub">
                            Describe any emergency situation in your own words — we'll instantly generate
                            a visual safety guide anyone can follow.
                        </p>
                    </div>
                </div>
                <div className="emergency-stats-row">
                    <div className="emergency-stat"><span>🌍</span> Earthquake</div>
                    <div className="emergency-stat"><span>🔥</span> Fire</div>
                    <div className="emergency-stat"><span>🌊</span> Flood</div>
                    <div className="emergency-stat"><span>🏥</span> Medical</div>
                    <div className="emergency-stat"><span>🚗</span> Accident</div>
                </div>
            </div>

            {/* ---- Input Card ---- */}
            <div className="emergency-input-card glass-panel">
                <h2 className="emergency-section-title">
                    <span className="emergency-section-icon">🗣️</span>
                    Describe Your Emergency
                </h2>
                <p className="emergency-section-hint">
                    Type or speak freely — e.g. <em>"earthquake on 5th floor of school"</em> or <em>"fire in kitchen"</em>
                </p>

                <form onSubmit={handleSubmit} className="emergency-form">
                    <div className={`emergency-textarea-wrap ${listening ? 'listening' : ''}`}>
                        <textarea
                            className="emergency-textarea"
                            placeholder="Describe your emergency situation here..."
                            value={input}
                            onChange={e => setInput(e.target.value)}
                            rows={4}
                            maxLength={1000}
                            disabled={loading}
                        />
                        <div className="emergency-textarea-bottom">
                            <span className="emergency-char-count">{input.length}/1000</span>
                            <button
                                type="button"
                                className={`emergency-mic-btn ${listening ? 'active' : ''}`}
                                onClick={listening ? stopListening : startListening}
                                disabled={loading}
                                title={listening ? 'Stop listening' : 'Start voice input'}
                            >
                                {listening ? (
                                    <>🔴 <span>Listening{dots}</span></>
                                ) : (
                                    <>🎙️ <span>Voice Input</span></>
                                )}
                            </button>
                        </div>
                    </div>

                    <button
                        type="submit"
                        className="emergency-submit-btn"
                        disabled={loading || !input.trim()}
                    >
                        {loading ? (
                            <span className="emergency-btn-loading">
                                <span className="emergency-spinner" /> Analyzing Emergency{dots}
                            </span>
                        ) : (
                            <span>🔍 Analyze Emergency &amp; Generate Guide</span>
                        )}
                    </button>
                </form>

                {error && (
                    <div className="emergency-error-banner">
                        <span>⚠️</span>
                        <span>{error}</span>
                    </div>
                )}
            </div>

            {/* ---- Loading Pulse ---- */}
            {loading && (
                <div className="emergency-loading-card glass-panel">
                    <div className="emergency-pulse-ring" />
                    <div className="emergency-loading-text">
                        <h3>AI is analyzing your situation{dots}</h3>
                        <p>Gemini 2.5 Flash is extracting emergency context and generating your visual guide.</p>
                    </div>
                </div>
            )}

            {/* ---- Results ---- */}
            {result && !loading && (
                <div ref={resultsRef} className="emergency-results">
                    {/* Context Summary */}
                    <div className="emergency-context-bar glass-panel">
                        <div className="emergency-disaster-badge">
                            <span className="emergency-disaster-icon">
                                {DISASTER_ICONS[result.disaster_type] || '⚠️'}
                            </span>
                            <div>
                                <div className="emergency-disaster-title">{result.disaster_title}</div>
                                {result.location_context && (
                                    <div className="emergency-location">📍 {result.location_context}</div>
                                )}
                            </div>
                        </div>

                        <div className="emergency-context-meta">
                            <span className={`emergency-urgency-badge ${urgencyConf.cls}`}>
                                {urgencyConf.label} ALERT
                            </span>
                            {result.floor_level && (
                                <span className="emergency-floor-badge">Floor {result.floor_level}</span>
                            )}
                            {result.cached && (
                                <span className="emergency-cached-badge">⚡ Cached</span>
                            )}
                        </div>
                    </div>

                    {/* Action Steps Grid */}
                    <div className="emergency-steps-section">
                        <h2 className="emergency-section-title">
                            <span className="emergency-section-icon">📋</span>
                            Follow These {result.actions?.length} Safety Steps
                        </h2>
                        <div className="emergency-steps-grid">
                            {result.actions?.map((action, idx) => (
                                <div key={action} className="emergency-step-card glass-hover">
                                    <div className="emergency-step-number">{idx + 1}</div>
                                    <div className="emergency-step-icon">
                                        {ACTION_ICONS[action] || '⚠️'}
                                    </div>
                                    <div className="emergency-step-label">
                                        {result.action_labels?.[action] || action.replace(/_/g, ' ')}
                                    </div>
                                </div>
                            ))}
                        </div>
                    </div>

                    {/* Download PDF CTA */}
                    <div className="emergency-download-section glass-panel">
                        <div className="emergency-download-info">
                            <div className="emergency-download-icon">📄</div>
                            <div>
                                <h3>Visual Safety Guide Ready</h3>
                                <p>
                                    Download a PDF designed for anyone — including those who cannot read.
                                    Large icons, color-coded steps, minimal text.
                                </p>
                            </div>
                        </div>
                        <button className="emergency-download-btn" onClick={handleDownload}>
                            ⬇️ Download Visual PDF Guide
                        </button>
                    </div>

                    {/* Emergency Contacts */}
                    <div className="emergency-contacts glass-panel">
                        <h3 className="emergency-contacts-title">📞 Emergency Contacts</h3>
                        <div className="emergency-contacts-grid">
                            <a href="tel:112" className="emergency-contact-chip">🆘 112 — Helpline</a>
                            <a href="tel:101" className="emergency-contact-chip">🚒 101 — Fire</a>
                            <a href="tel:108" className="emergency-contact-chip">🚑 108 — Ambulance</a>
                            <a href="tel:100" className="emergency-contact-chip">👮 100 — Police</a>
                        </div>
                    </div>

                    {/* Re-analyze */}
                    <button
                        className="emergency-retry-btn"
                        onClick={() => { setResult(null); setInput(''); }}
                    >
                        ↩ Analyze Another Emergency
                    </button>
                </div>
            )}
        </div>
    );
}
