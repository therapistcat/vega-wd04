import React from 'react';
import { MapContainer, TileLayer, useMap } from 'react-leaflet';
import 'leaflet/dist/leaflet.css';

const MUMBAI_CENTER = [19.076, 72.8777];
const GREEN_TILE_URL = 'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png';

function ViewportSync({ center, zoom }) {
    const map = useMap();

    React.useEffect(() => {
        if (!Array.isArray(center) || center.length !== 2) return;
        map.setView(center, zoom, { animate: true });
    }, [map, center, zoom]);

    return null;
}

export default function MapComponent({ children, center = MUMBAI_CENTER, zoom = 12, style }) {
    const containerStyle = {
        width: '100%',
        height: '520px',
        minHeight: '320px',
        position: 'relative',
        borderRadius: '16px',
        overflow: 'hidden',
        border: '1px solid rgba(16, 185, 129, 0.25)',
        boxShadow: '0 16px 38px -20px rgba(5, 150, 105, 0.45)',
        ...style,
    };

    return (
        <div className="map-container" style={containerStyle}>
            <MapContainer
                center={center}
                zoom={zoom}
                scrollWheelZoom
                style={{ width: '100%', height: '100%' }}
            >
                <ViewportSync center={center} zoom={zoom} />
                <TileLayer
                    attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
                    url={GREEN_TILE_URL}
                />
                {children}
            </MapContainer>
        </div>
    );
}
