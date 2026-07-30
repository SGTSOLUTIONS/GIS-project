// static/js/gis_functions.js

// Get CSRF Token
function getCsrfToken() {
    return document.querySelector('[name=csrfmiddlewaretoken]')?.value || 
           document.querySelector('input[name="csrfmiddlewaretoken"]')?.value;
}

// Add Polygon
function addPolygon(coordinates) {
    $.ajax({
        url: '/surveyor/add-polygon/',
        method: 'POST',
        data: {
            coordinates: JSON.stringify(coordinates),
            csrfmiddlewaretoken: getCsrfToken()
        },
        success: function(response) {
            if (response.success) {
                console.log('✅ Polygon added! GIS ID:', response.gisid);
                loadFeatures();
                showNotification('Polygon added successfully!');
            }
        },
        error: function(xhr) {
            console.error('❌ Error:', xhr.responseJSON?.error || 'Unknown error');
            showNotification('Error: ' + (xhr.responseJSON?.error || 'Unknown error'), 'error');
        }
    });
}

// Merge Polygons
function mergePolygons(firstGisid, secondGisid) {
    if (!firstGisid || !secondGisid) {
        showNotification('Please select two polygons to merge', 'error');
        return;
    }
    
    $.ajax({
        url: '/surveyor/merge-polygon/',
        method: 'POST',
        data: {
            firstmerge: firstGisid,
            secondmerge: secondGisid,
            csrfmiddlewaretoken: getCsrfToken()
        },
        success: function(response) {
            if (response.success) {
                console.log('✅ Polygons merged!');
                loadFeatures();
                showNotification('Polygons merged successfully!');
            }
        },
        error: function(xhr) {
            console.error('❌ Error:', xhr.responseJSON?.error);
            showNotification('Error: ' + (xhr.responseJSON?.error || 'Unknown error'), 'error');
        }
    });
}

// Delete Polygon
function deletePolygon(gisid) {
    if (!gisid) {
        showNotification('Please select a polygon to delete', 'error');
        return;
    }
    
    if (!confirm('Are you sure you want to delete this polygon?')) return;
    
    $.ajax({
        url: '/surveyor/delete-polygon/',
        method: 'POST',
        data: {
            gisid: gisid,
            csrfmiddlewaretoken: getCsrfToken()
        },
        success: function(response) {
            if (response.success) {
                console.log('✅ Polygon deleted!');
                loadFeatures();
                showNotification('Polygon deleted successfully!');
            }
        },
        error: function(xhr) {
            console.error('❌ Error:', xhr.responseJSON?.error);
            if (xhr.responseJSON?.name) {
                showNotification('This area is being worked on by: ' + xhr.responseJSON.name, 'error');
            } else {
                showNotification('Error: ' + (xhr.responseJSON?.error || 'Unknown error'), 'error');
            }
        }
    });
}

// Update Road Name
function updateRoadName(lineGisid, roadName) {
    if (!lineGisid || !roadName) {
        showNotification('Please provide GIS ID and road name', 'error');
        return;
    }
    
    $.ajax({
        url: '/surveyor/update-roadname/',
        method: 'POST',
        data: {
            linegisid: lineGisid,
            roadname: roadName,
            csrfmiddlewaretoken: getCsrfToken()
        },
        success: function(response) {
            if (response.success) {
                console.log('✅ Road name updated!');
                showNotification('Road name updated successfully!');
                loadFeatures();
            }
        },
        error: function(xhr) {
            console.error('❌ Error:', xhr.responseJSON?.error);
            showNotification('Error: ' + (xhr.responseJSON?.error || 'Unknown error'), 'error');
        }
    });
}

// Load GIS Features
function loadFeatures() {
    $.ajax({
        url: '/surveyor/get-gis-features/',
        method: 'GET',
        success: function(data) {
            console.log('📊 Loaded GIS data:', data);
            renderFeatures(data);
        },
        error: function(xhr) {
            console.error('❌ Error loading features:', xhr.responseJSON?.error);
        }
    });
}

// Render Features on Map (Example with Leaflet)
function renderFeatures(data) {
    // This function assumes you have a global 'map' variable
    // Clear existing layers
    if (window.gisLayers) {
        window.gisLayers.forEach(layer => {
            if (map.hasLayer(layer)) {
                map.removeLayer(layer);
            }
        });
    }
    window.gisLayers = [];
    
    // Render Polygons
    if (data.polygons && data.polygons.length > 0) {
        data.polygons.forEach(polygon => {
            try {
                const coords = JSON.parse(polygon.coordinates);
                const latlngs = coords[0].map(c => [c[1], c[0]]);
                
                const layer = L.polygon(latlngs, {
                    color: '#3498db',
                    weight: 2,
                    fillColor: '#3498db',
                    fillOpacity: 0.3
                }).bindPopup(`
                    <strong>GIS ID:</strong> ${polygon.gisid}<br>
                    <strong>Type:</strong> ${polygon.type}
                `);
                
                layer.addTo(map);
                window.gisLayers.push(layer);
            } catch (e) {
                console.error('Error rendering polygon:', e);
            }
        });
    }
    
    // Render Points
    if (data.points && data.points.length > 0) {
        data.points.forEach(point => {
            try {
                const coords = JSON.parse(point.coordinates);
                const marker = L.marker([coords[1], coords[0]])
                    .bindPopup(`
                        <strong>GIS ID:</strong> ${point.gisid}<br>
                        <strong>Type:</strong> ${point.type}
                    `);
                
                marker.addTo(map);
                window.gisLayers.push(marker);
            } catch (e) {
                console.error('Error rendering point:', e);
            }
        });
    }
    
    // Render Lines
    if (data.lines && data.lines.length > 0) {
        data.lines.forEach(line => {
            try {
                const coords = JSON.parse(line.coordinates);
                const latlngs = coords.map(c => [c[1], c[0]]);
                
                const layer = L.polyline(latlngs, {
                    color: '#e67e22',
                    weight: 3
                }).bindPopup(`
                    <strong>GIS ID:</strong> ${line.gisid}<br>
                    <strong>Type:</strong> ${line.type}<br>
                    <strong>Road:</strong> ${line.road_name || 'N/A'}
                `);
                
                layer.addTo(map);
                window.gisLayers.push(layer);
            } catch (e) {
                console.error('Error rendering line:', e);
            }
        });
    }
    
    // Fit map to all features
    if (window.gisLayers.length > 0) {
        const group = L.featureGroup(window.gisLayers);
        map.fitBounds(group.getBounds().pad(0.1));
    }
}

// Notification Function
function showNotification(message, type = 'success') {
    const colors = {
        success: '#27ae60',
        error: '#e74c3c',
        warning: '#f39c12',
        info: '#3498db'
    };
    
    const toast = document.createElement('div');
    toast.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        padding: 16px 24px;
        background: ${colors[type] || colors.success};
        color: white;
        border-radius: 12px;
        font-weight: 500;
        box-shadow: 0 8px 30px rgba(0,0,0,0.15);
        z-index: 9999;
        animation: slideIn 0.3s ease;
        max-width: 400px;
    `;
    toast.textContent = message;
    document.body.appendChild(toast);
    
    setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transition = 'opacity 0.3s ease';
        setTimeout(() => toast.remove(), 300);
    }, 4000);
}

// Add CSS animation
const style = document.createElement('style');
style.textContent = `
    @keyframes slideIn {
        from { transform: translateX(100px); opacity: 0; }
        to { transform: translateX(0); opacity: 1; }
    }
`;
document.head.appendChild(style);