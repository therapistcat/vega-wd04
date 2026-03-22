import React from 'react';

export default function MapLegend() {
    return (
        <div className="map-legend">
            <h4>Heat Intensity</h4>
            <div className="legend-row">
                <span className="dot high" />
                <span>High</span>
            </div>
            <div className="legend-row">
                <span className="dot medium" />
                <span>Medium</span>
            </div>
            <div className="legend-row">
                <span className="dot low" />
                <span>Low</span>
            </div>
        </div>
    );
}
