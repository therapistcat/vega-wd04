import { useEffect } from 'react';
import { useMap } from 'react-leaflet';
import L from 'leaflet';
import 'leaflet.markercluster';
import 'leaflet.markercluster/dist/MarkerCluster.css';
import 'leaflet.markercluster/dist/MarkerCluster.Default.css';

function sanitizeIssues(issues) {
    if (!Array.isArray(issues)) return [];
    return issues.filter((item) => (
        item
        && Number.isFinite(Number(item.latitude))
        && Number.isFinite(Number(item.longitude))
    ));
}

function statusClass(issue) {
    const status = String(issue?.display_status || issue?.progress_status || issue?.status || 'Pending').toLowerCase();
    if (status.includes('resolved')) return 'resolved';
    if (status.includes('progress')) return 'in-progress';
    return 'pending';
}

function markerIcon(issue) {
    return L.divIcon({
        className: 'nearby-issue-marker-wrapper',
        html: `<span class="nearby-issue-marker nearby-issue-marker-${statusClass(issue)}"></span>`,
        iconSize: [20, 20],
        iconAnchor: [10, 10],
        popupAnchor: [0, -12],
    });
}

function clusterIcon(cluster) {
    const count = cluster.getChildCount();
    return L.divIcon({
        className: 'nearby-cluster-wrapper',
        html: `<div class="nearby-cluster-marker"><span>${count}</span></div>`,
        iconSize: [42, 42],
        iconAnchor: [21, 21],
    });
}

export default function NearbyIssueClusterLayer({ issues, onViewDetails }) {
    const map = useMap();

    useEffect(() => {
        const safeIssues = sanitizeIssues(issues);
        const clusterGroup = L.markerClusterGroup({
            showCoverageOnHover: false,
            spiderfyOnMaxZoom: true,
            disableClusteringAtZoom: 17,
            maxClusterRadius: 52,
            iconCreateFunction: clusterIcon,
        });

        safeIssues.forEach((issue) => {
            const marker = L.marker(
                [Number(issue.latitude), Number(issue.longitude)],
                { icon: markerIcon(issue), title: issue.description || 'Nearby issue' },
            );

            const popupNode = document.createElement('div');
            popupNode.className = 'nearby-popup-card';
            popupNode.innerHTML = `
                <div class="nearby-popup-title">${issue.description || 'Issue'}</div>
                <div class="nearby-popup-meta">
                    <span class="nearby-popup-badge nearby-popup-badge-${statusClass(issue)}">
                        ${issue.display_status || issue.progress_status || issue.status || 'Pending'}
                    </span>
                    <span>${Math.round(Number(issue.distance_m || 0))}m away</span>
                </div>
                <div class="nearby-popup-ngo">
                    NGO: ${issue.assigned_ngo_name || 'Not assigned'}
                </div>
            `;

            const button = document.createElement('button');
            button.type = 'button';
            button.className = 'btn btn-primary-filled nearby-popup-button';
            button.textContent = 'View Details';
            button.addEventListener('click', () => onViewDetails?.(issue));
            popupNode.appendChild(button);

            marker.bindPopup(popupNode, { maxWidth: 280 });
            clusterGroup.addLayer(marker);
        });

        map.addLayer(clusterGroup);
        return () => {
            map.removeLayer(clusterGroup);
        };
    }, [issues, map, onViewDetails]);

    return null;
}
