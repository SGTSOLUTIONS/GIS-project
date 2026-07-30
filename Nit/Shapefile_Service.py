import json
import os
import zipfile
import tempfile
import shutil
from io import BytesIO
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from django.db import connection
from django.shortcuts import render
from django.conf import settings
from .models import Data, PolygonFeature, PointFeature, LineFeature, ShapefileImport, ShapefileExport, FeatureEditHistory

class ShapefileService:
    """Service for shapefile import/export without GeoDjango"""
    
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
            
            # Find files
            shp_file = None
            shx_file = None
            dbf_file = None
            prj_file = None
            
            for file in os.listdir(temp_dir):
                if file.endswith('.shp'):
                    shp_file = file
                elif file.endswith('.shx'):
                    shx_file = file
                elif file.endswith('.dbf'):
                    dbf_file = file
                elif file.endswith('.prj'):
                    prj_file = file
            
            if not shp_file:
                raise ValueError("No .shp file found in the zip archive")
            
            # Parse shapefile (simplified - using json representation)
            # In production, use OGR/GDAL or a pure Python shapefile library
            shp_path = os.path.join(temp_dir, shp_file)
            
            # For demo, we'll create sample features
            # In real implementation, use shapefile library to read features
            feature_count = 0
            
            # Determine geometry type from filename or user input
            geom_type = 'polygon'  # Default
            
            # Create features based on geometry type
            if geom_type == 'polygon':
                # Sample polygon creation - replace with actual parsing
                sample_coords = [
                    [[-0.09, 51.505], [-0.08, 51.505], [-0.08, 51.515], [-0.09, 51.515], [-0.09, 51.505]]
                ]
                PolygonFeature.objects.create(
                    data=data_instance,
                    gisid=f"POLY-{feature_count+1}",
                    type='Polygon',
                    coordinates=sample_coords
                )
                feature_count += 1
            elif geom_type == 'point':
                PointFeature.objects.create(
                    data=data_instance,
                    gisid=f"POINT-{feature_count+1}",
                    type='Point',
                    coordinates=[51.505, -0.09]
                )
                feature_count += 1
            elif geom_type == 'line':
                LineFeature.objects.create(
                    data=data_instance,
                    gisid=f"LINE-{feature_count+1}",
                    type='LineString',
                    coordinates=[[-0.09, 51.505], [-0.08, 51.515]],
                    road_name='Sample Road'
                )
                feature_count += 1
            
            # Save import record
            shapefile_import = ShapefileImport.objects.create(
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
                'geom_type': geom_type,
                'import_id': shapefile_import.id
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)
    
    @staticmethod
    def export_shapefile(request,data_instance, geometry_type='polygon'):
        """Export features to shapefile format"""
        temp_dir = tempfile.mkdtemp()
        
        try:
            # Create a simple GeoJSON representation
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
                            'TYPE': feature.type,
                            'DATA_ID': data_instance.id
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
                            'TYPE': feature.type,
                            'DATA_ID': data_instance.id
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
                            'ROAD_NAME': feature.road_name or '',
                            'DATA_ID': data_instance.id
                        }
                    })
            else:
                raise ValueError("Invalid geometry type")
            
            # Create GeoJSON
            geojson = {
                'type': 'FeatureCollection',
                'features': features
            }
            
            # Save as JSON (simplified - in production, convert to shapefile)
            json_path = os.path.join(temp_dir, 'export.geojson')
            with open(json_path, 'w') as f:
                json.dump(geojson, f, indent=2)
            
            # Create zip with GeoJSON
            zip_path = os.path.join(settings.MEDIA_ROOT, f'export_{data_instance.id}_{geometry_type}.zip')
            with zipfile.ZipFile(zip_path, 'w') as zipf:
                zipf.write(json_path, 'export.geojson')
            
            # Save export record
            ShapefileExport.objects.create(
                data=data_instance,
                filename=f'export_{data_instance.id}_{geometry_type}.zip',
                file_path=zip_path,
                geom_type=geometry_type,
                feature_count=len(features),
                exported_by=request.user if hasattr(request, 'user') else None
            )
            
            return zip_path
            
        except Exception as e:
            raise e
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)