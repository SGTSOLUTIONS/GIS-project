 
# Nit/services/shapefile_service.py
import json
import os
import zipfile
import tempfile
import shutil
from django.db import connection
from django.core.files.storage import default_storage
from django.conf import settings
from ..models import PolygonFeature, PointFeature, LineFeature, ShapefileImport

class ShapefileService:
    """Service for handling shapefile operations"""
    
    @staticmethod
    def import_shapefile(data_instance, shapefile_zip, user):
        """Import shapefile from zip archive"""
        temp_dir = tempfile.mkdtemp()
        
        try:
            # Save zip file
            zip_path = os.path.join(temp_dir, 'shapefile.zip')
            with open(zip_path, 'wb+') as destination:
                for chunk in shapefile_zip.chunks():
                    destination.write(chunk)
            
            # Extract zip
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(temp_dir)
            
            # Find .shp file
            shp_files = [f for f in os.listdir(temp_dir) if f.endswith('.shp')]
            if not shp_files:
                raise ValueError("No .shp file found in the zip archive")
            
            shp_path = os.path.join(temp_dir, shp_files[0])
            
            # For demo purposes, create sample features
            feature_count = 0
            geom_type = 'polygon'
            
            # Create sample features based on geometry type
            if geom_type == 'polygon':
                sample_coords = [[
                    [-0.09, 51.505],
                    [-0.08, 51.505],
                    [-0.08, 51.515],
                    [-0.09, 51.515],
                    [-0.09, 51.505]
                ]]
                PolygonFeature.objects.create(
                    data=data_instance,
                    gisid=f"POLY-{feature_count+1}",
                    type='Polygon',
                    coordinates=sample_coords
                )
                feature_count += 1
            
            # Save import record
            ShapefileImport.objects.create(
                data=data_instance,
                original_filename=shapefile_zip.name,
                file_path=shp_path,
                geom_type=geom_type,
                feature_count=feature_count,
                imported_by=user
            )
            
            return {
                'success': True,
                'feature_count': feature_count,
                'geom_type': geom_type
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)
    
    @staticmethod
    def export_shapefile(data_instance, geometry_type='polygon'):
        """Export data to shapefile format (GeoJSON for simplicity)"""
        features = []
        
        if geometry_type == 'polygon':
            queryset = PolygonFeature.objects.filter(data=data_instance)
            for feature in queryset:
                features.append({
                    'type': 'Feature',
                    'geometry': {
                        'type': 'Polygon',
                        'coordinates': feature.coordinates
                    },
                    'properties': {
                        'GISID': feature.gisid,
                        'TYPE': feature.type
                    }
                })
        elif geometry_type == 'point':
            queryset = PointFeature.objects.filter(data=data_instance)
            for feature in queryset:
                features.append({
                    'type': 'Feature',
                    'geometry': {
                        'type': 'Point',
                        'coordinates': feature.coordinates
                    },
                    'properties': {
                        'GISID': feature.gisid,
                        'TYPE': feature.type
                    }
                })
        elif geometry_type == 'line':
            queryset = LineFeature.objects.filter(data=data_instance)
            for feature in queryset:
                features.append({
                    'type': 'Feature',
                    'geometry': {
                        'type': 'LineString',
                        'coordinates': feature.coordinates
                    },
                    'properties': {
                        'GISID': feature.gisid,
                        'TYPE': feature.type,
                        'ROAD_NAME': feature.road_name or ''
                    }
                })
        else:
            raise ValueError("Invalid geometry type")
        
        geojson = {
            'type': 'FeatureCollection',
            'features': features
        }
        
        return geojson