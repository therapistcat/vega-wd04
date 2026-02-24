import { useEffect, useMemo } from 'react';
import { useMap } from 'react-leaflet';
import L from 'leaflet';
import 'leaflet.heat';

/**
 * Custom HeatmapLayer component using leaflet.heat
 *
 * Props:
 *   points       – array of objects
 *   latitudeExtractor  – fn(point) => lat
 *   longitudeExtractor – fn(point) => lng
 *   intensityExtractor – fn(point) => intensity
 *   fitBoundsOnLoad    – boolean
 *   fitBoundsOnUpdate  – boolean
 *   radius, blur, maxZoom, max – leaflet.heat options
 */
export default function HeatmapLayer({
    points = [],
    latitudeExtractor = (p) => p.lat,
    longitudeExtractor = (p) => p.lng,
    intensityExtractor = (p) => p.intensity,
    fitBoundsOnLoad = false,
    fitBoundsOnUpdate = false,
    radius = 25,
    blur = 15,
    maxZoom = 18,
    max = 1.0,
}) {
    const map = useMap();
    const heatData = useMemo(() => {
        if (!Array.isArray(points) || points.length === 0) return [];
        return points
            .map((p) => {
                const rawLat = Number(latitudeExtractor(p));
                const rawLng = Number(longitudeExtractor(p));
                const rawIntensity = Number(intensityExtractor(p));

                if (!Number.isFinite(rawLat) || !Number.isFinite(rawLng)) return null;
                if (rawLat < -90 || rawLat > 90 || rawLng < -180 || rawLng > 180) return null;

                // Leaflet heat is stable with bounded positive intensity values.
                const intensity = Number.isFinite(rawIntensity)
                    ? Math.min(1, Math.max(0.05, rawIntensity))
                    : 0.5;
                return [rawLat, rawLng, intensity];
            })
            .filter(Boolean);
    }, [points, latitudeExtractor, longitudeExtractor, intensityExtractor]);

    useEffect(() => {
        if (!heatData.length) return undefined;

        let heatLayer = null;

        try {
            if (!map.getSize || map.getSize().x <= 0 || map.getSize().y <= 0) {
                map.invalidateSize(false);
            }

            heatLayer = L.heatLayer(heatData, {
                radius,
                blur,
                maxZoom,
                max,
                gradient: {
                    0.0: '#22c55e',
                    0.4: '#84cc16',
                    0.6: '#facc15',
                    0.8: '#f97316',
                    1.0: '#dc2626',
                },
            });

            heatLayer.addTo(map);

            if ((fitBoundsOnLoad || fitBoundsOnUpdate) && heatData.length > 0) {
                const bounds = L.latLngBounds(heatData.map(([lat, lng]) => [lat, lng]));
                if (bounds.isValid()) {
                    map.fitBounds(bounds, { padding: [40, 40] });
                }
            }
        } catch (error) {
            console.error('Failed to render heatmap layer safely:', error);
        }

        return () => {
            if (heatLayer && map.hasLayer(heatLayer)) {
                map.removeLayer(heatLayer);
            }
        };
    }, [heatData, radius, blur, maxZoom, max, map, fitBoundsOnLoad, fitBoundsOnUpdate]);

    return null;
}
