# Nit/utils/geometry_utils.py
import json
from django.db import connection
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
import zipfile
import tempfile
import os
import shutil

class GeometryHelper:
    """Helper class for working with dynamic geometry tables"""
    
    @staticmethod
    def get_features(data_instance, geom_type='polygon'):
        """Get features from dynamic table"""
        table_name = getattr(data_instance, geom_type, None)
        if not table_name:
            return []
        
        with connection.cursor() as cursor:
            cursor.execute(f"SELECT gisid, coordinates, type FROM `{table_name}`")
            rows = cursor.fetchall()
            
        features = []
        for row in rows:
            try:
                features.append({
                    'gisid': row[0],
                    'coordinates': json.loads(row[1]) if row[1] else [],
                    'type': row[2] if len(row) > 2 else geom_type
                })
            except:
                continue
        return features
    
    @staticmethod
    def save_feature(data_instance, gisid, coordinates, geom_type='polygon', road_name=''):
        """Save or update a feature in dynamic table"""
        table_name = getattr(data_instance, geom_type, None)
        if not table_name:
            raise ValueError(f"Table not found for {geom_type}")
        
        with connection.cursor() as cursor:
            # Check if feature exists
            cursor.execute(f"SELECT id FROM `{table_name}` WHERE gisid = %s", [gisid])
            exists = cursor.fetchone()
            
            if exists:
                # Update existing
                if geom_type == 'line':
                    cursor.execute(f"""
                        UPDATE `{table_name}` 
                        SET coordinates = %s, road_name = %s, updated_at = NOW()
                        WHERE gisid = %s
                    """, [json.dumps(coordinates), road_name, gisid])
                else:
                    cursor.execute(f"""
                        UPDATE `{table_name}` 
                        SET coordinates = %s, updated_at = NOW()
                        WHERE gisid = %s
                    """, [json.dumps(coordinates), gisid])
            else:
                # Insert new
                if geom_type == 'line':
                    cursor.execute(f"""
                        INSERT INTO `{table_name}` 
                        (gisid, coordinates, type, road_name, created_at, updated_at)
                        VALUES (%s, %s, %s, %s, NOW(), NOW())
                    """, [gisid, json.dumps(coordinates), geom_type, road_name])
                else:
                    cursor.execute(f"""
                        INSERT INTO `{table_name}` 
                        (gisid, coordinates, type, created_at, updated_at)
                        VALUES (%s, %s, %s, %s, NOW(), NOW())
                    """, [gisid, json.dumps(coordinates), geom_type])
        
        return {'success': True, 'gisid': gisid}
    
    @staticmethod
    def delete_feature(data_instance, gisid, geom_type='polygon'):
        """Delete a feature from dynamic table"""
        table_name = getattr(data_instance, geom_type, None)
        if not table_name:
            raise ValueError(f"Table not found for {geom_type}")
        
        with connection.cursor() as cursor:
            cursor.execute(f"DELETE FROM `{table_name}` WHERE gisid = %s", [gisid])
        
        return {'success': True}
    
    @staticmethod
    def export_to_geojson(data_instance, geom_type='polygon'):
        """Export features to GeoJSON"""
        features = GeometryHelper.get_features(data_instance, geom_type)
        
        geojson = {
            'type': 'FeatureCollection',
            'features': []
        }
        
        for feature in features:
            if geom_type == 'polygon':
                geometry = {
                    'type': 'Polygon',
                    'coordinates': feature['coordinates']
                }
            elif geom_type == 'point':
                geometry = {
                    'type': 'Point',
                    'coordinates': feature['coordinates']
                }
            elif geom_type == 'line':
                geometry = {
                    'type': 'LineString',
                    'coordinates': feature['coordinates']
                }
            else:
                continue
            
            geojson['features'].append({
                'type': 'Feature',
                'geometry': geometry,
                'properties': {
                    'gisid': feature['gisid'],
                    'type': feature['type']
                }
            })
        
        return geojson
    
    @staticmethod
    def import_geojson(data_instance, geojson_data, geom_type='polygon'):
        """Import features from GeoJSON"""
        features = geojson_data.get('features', [])
        count = 0
        
        for feature in features:
            geometry = feature.get('geometry', {})
            properties = feature.get('properties', {})
            gisid = properties.get('gisid', f"GIS-{count+1}")
            coordinates = geometry.get('coordinates', [])
            
            if coordinates:
                GeometryHelper.save_feature(
                    data_instance, 
                    gisid, 
                    coordinates, 
                    geom_type
                )
                count += 1
        
        return {'success': True, 'imported': count}