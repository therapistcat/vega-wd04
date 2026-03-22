import React, { useRef, useState } from 'react';
import { MdPhotoCamera } from 'react-icons/md';

export default function CameraCapture({ onCapture }) {
    const videoRef = useRef(null);
    const streamRef = useRef(null);
    const [open, setOpen] = useState(false);
    const [error, setError] = useState('');

    const stopCamera = () => {
        if (streamRef.current) {
            streamRef.current.getTracks().forEach((track) => track.stop());
            streamRef.current = null;
        }
    };

    const openCamera = async () => {
        setError('');
        try {
            const stream = await navigator.mediaDevices.getUserMedia({
                video: { facingMode: { ideal: 'environment' } },
                audio: false,
            });
            streamRef.current = stream;
            setOpen(true);
            setTimeout(() => {
                if (videoRef.current) {
                    videoRef.current.srcObject = stream;
                }
            }, 0);
        } catch (err) {
            setError(err?.message || 'Unable to access camera');
        }
    };

    const closeCamera = () => {
        stopCamera();
        setOpen(false);
    };

    const capture = async () => {
        const video = videoRef.current;
        if (!video) return;
        const canvas = document.createElement('canvas');
        canvas.width = video.videoWidth || 1280;
        canvas.height = video.videoHeight || 720;
        const ctx = canvas.getContext('2d');
        ctx.drawImage(video, 0, 0, canvas.width, canvas.height);

        const blob = await new Promise((resolve) => canvas.toBlob(resolve, 'image/jpeg', 0.92));
        if (!blob) {
            setError('Failed to capture image');
            return;
        }
        const file = new File([blob], `camera-${Date.now()}.jpg`, { type: 'image/jpeg' });
        onCapture?.(file);
        closeCamera();
    };

    return (
        <div>
            <button type="button" className="btn btn-secondary-glass" onClick={openCamera}>
                <MdPhotoCamera size={18} />
                Use Camera
            </button>
            {error && <div style={{ marginTop: 6, fontSize: 12, color: '#b91c1c' }}>{error}</div>}

            {open && (
                <div className="report-modal-overlay" onClick={closeCamera}>
                    <div className="report-modal-card" onClick={(e) => e.stopPropagation()}>
                        <div style={{ fontSize: 16, fontWeight: 700, marginBottom: 10 }}>Capture Image</div>
                        <video
                            ref={videoRef}
                            autoPlay
                            playsInline
                            style={{ width: '100%', borderRadius: 12, border: '1px solid rgba(148,163,184,0.25)' }}
                        />
                        <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 10, marginTop: 12 }}>
                            <button type="button" className="btn btn-ghost" onClick={closeCamera}>
                                Cancel
                            </button>
                            <button type="button" className="btn btn-primary-filled" onClick={capture}>
                                Capture
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}
