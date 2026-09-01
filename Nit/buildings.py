import json
import logging
from django.core.exceptions import ValidationError
from django.contrib.gis.geos import GEOSGeometry, Polygon, MultiPolygon
import re

logger = logging.getLogger(__name__)

class GeoJSONProcessor:
    """
    Robust GeoJSON processor that handles various GeoJSON formats
    """
    
    @staticmethod
    def validate_and_normalize_geojson(data):
        """
        Validate and normalize GeoJSON data to a standard format
        """
        try:
            # If string, parse JSON
            if isinstance(data, str):
                data = json.loads(data)
            
            # Check for Feature or FeatureCollection
            geojson_type = data.get('type')
            
            if geojson_type == 'FeatureCollection':
                features = data.get('features', [])
                if not features:
                    raise ValidationError("Empty FeatureCollection")
                return {
                    'type': 'FeatureCollection',
                    'features': features
                }
                
            elif geojson_type == 'Feature':
                return data
                
            else:
                # Try to wrap as Feature
                if 'geometry' in data:
                    return {
                        'type': 'Feature',
                        'geometry': data.get('geometry'),
                        'properties': data.get('properties', {})
                    }
                else:
                    raise ValidationError(f"Unsupported GeoJSON type: {geojson_type}")
                    
        except json.JSONDecodeError as e:
            raise ValidationError(f"Invalid JSON: {str(e)}")
    
    @staticmethod
    def extract_building_geometry(feature):
        """
        Extract and validate geometry from a feature
        Handles Polygon, MultiPolygon, and different coordinate systems
        """
        geometry = feature.get('geometry')
        if not geometry:
            return None, "No geometry found"
        
        geom_type = geometry.get('type')
        coordinates = geometry.get('coordinates')
        
        if not coordinates:
            return None, "No coordinates found"
        
        # Validate polygon coordinates
        if geom_type in ['Polygon', 'MultiPolygon']:
            try:
                # Try to create GEOS geometry for validation
                geos_geom = GEOSGeometry(json.dumps(geometry))
                if geos_geom.valid:
                    return geos_geom, None
                else:
                    return None, f"Invalid geometry: {geos_geom.valid_reason}"
            except Exception as e:
                logger.error(f"GEOS validation error: {e}")
                
                # Manual polygon validation
                if geom_type == 'Polygon':
                    if not coordinates or len(coordinates) < 1:
                        return None, "Invalid polygon: no rings"
                    
                    # Check if first ring has at least 4 points (closed polygon)
                    first_ring = coordinates[0]
                    if len(first_ring) < 4:
                        return None, "Invalid polygon: ring has less than 4 points"
                    
                    return geometry, None
                    
        return geometry, None
    
    @staticmethod
    def extract_building_properties(feature):
        """
        Extract building properties from various GeoJSON formats
        """
        properties = feature.get('properties', {})
        
        # Try different common property names
        name = (
            properties.get('building_name') or
            properties.get('name') or
            properties.get('NAME') or
            properties.get('BuildingName') or
            properties.get('BldgName') or
            properties.get('FID') or  # Sometimes use ID as name
            properties.get('id') or
            f"Building {hash(json.dumps(feature)) % 10000}"  # Fallback
        )
        
        # Extract other common properties
        building_type = (
            properties.get('building_type') or
            properties.get('BuildingType') or
            properties.get('type') or
            'Unknown'
        )
        
        height = (
            properties.get('height') or
            properties.get('Height') or
            properties.get('building_height') or
            None
        )
        
        return {
            'name': str(name),
            'type': str(building_type),
            'height': height,
            'properties': properties
        }
    
    @staticmethod
    def get_center_point(geometry):
        """
        Calculate center point from geometry for map centering
        Handles both GEOS geometries and raw GeoJSON
        """
        try:
            # If it's a GEOS geometry
            if hasattr(geometry, 'centroid'):
                centroid = geometry.centroid
                return {
                    'lat': centroid.y,
                    'lng': centroid.x
                }
            
            # If it's raw GeoJSON
            if isinstance(geometry, dict):
                coords = geometry.get('coordinates')
                if not coords:
                    return None
                
                # Handle Polygon
                if geometry.get('type') == 'Polygon':
                    polygon_coords = coords[0]  # First ring
                    return GeoJSONProcessor._calculate_centroid(polygon_coords)
                
                # Handle MultiPolygon
                elif geometry.get('type') == 'MultiPolygon':
                    all_points = []
                    for polygon in coords:
                        all_points.extend(polygon[0])
                    return GeoJSONProcessor._calculate_centroid(all_points)
                
            return None
            
        except Exception as e:
            logger.error(f"Error calculating center: {e}")
            return None
    
    @staticmethod
    def _calculate_centroid(points):
        """
        Calculate centroid from list of points [lng, lat]
        """
        if not points:
            return None
        
        lat_sum = 0
        lng_sum = 0
        count = 0
        
        for point in points:
            if len(point) >= 2:
                lng, lat = point[0], point[1]
                # Validate coordinates
                if -180 <= lng <= 180 and -90 <= lat <= 90:
                    lat_sum += lat
                    lng_sum += lng
                    count += 1
        
        if count > 0:
            return {
                'lat': lat_sum / count,
                'lng': lng_sum / count
            }
        return None

def process_building_geojson(data, building_id=None):
    """
    Main function to process building GeoJSON
    Returns standardized building data
    """
    try:
        # Step 1: Validate and normalize
        normalized = GeoJSONProcessor.validate_and_normalize_geojson(data)
        
        # Step 2: Get features
        features = []
        if normalized.get('type') == 'FeatureCollection':
            features = normalized.get('features', [])
        else:
            features = [normalized]
        
        processed_features = []
        for idx, feature in enumerate(features):
            # Extract geometry
            geometry, error = GeoJSONProcessor.extract_building_geometry(feature)
            if error:
                logger.warning(f"Feature {idx}: {error}")
                continue
            
            # Extract properties
            properties = GeoJSONProcessor.extract_building_properties(feature)
            
            # Calculate center
            center = GeoJSONProcessor.get_center_point(geometry)
            
            processed_features.append({
                'index': idx,
                'geometry': geometry,
                'properties': properties,
                'center': center,
                'raw_feature': feature
            })
        
        if not processed_features:
            return {
                'success': False,
                'error': 'No valid building features found'
            }
        
        return {
            'success': True,
            'features': processed_features,
            'total': len(processed_features)
        }
        
    except Exception as e:
        logger.error(f"Error processing GeoJSON: {e}")
        return {
            'success': False,
            'error': str(e)
        }

def get_building_center(building):
    """
    Get center point from a building object
    """
    try:
        if hasattr(building, 'geometry') and building.geometry:
            return {
                'lat': building.geometry.centroid.y,
                'lng': building.geometry.centroid.x
            }
        
        if hasattr(building, 'geojson_data'):
            return GeoJSONProcessor.get_center_point(building.geojson_data.get('geometry'))
        
        return None
        
    except Exception as e:
        logger.error(f"Error getting building center: {e}")
        return None