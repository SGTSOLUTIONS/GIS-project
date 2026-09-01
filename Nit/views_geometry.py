# Nit/views_geometry.py - COMPLETE FIXED VERSION

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, FileResponse
from django.views.decorators.csrf import csrf_exempt
from django.db import connection
from django.utils import timezone
from django.contrib.gis.geos import GEOSGeometry, MultiPolygon, Polygon, Point
from django.core.files.storage import default_storage
from .models import Corporation, Building
import logging
from django.db.models import Count, Sum, Q
import json
import os
import uuid
import math
from .models import (
    Data, PolygonFeature, PointFeature, LineFeature, 
    FeatureEditHistory, ShapefileImport, Surveyor
)
from .services.shapefile_service import ShapefileService
from .decorators import admin_required, surveyor_required

logger = logging.getLogger(__name__)


# ============================================
# EXISTING GEOMETRY FUNCTIONS
# ============================================

@login_required
@admin_required
def geometry_editor_view(request, data_id):
    """Full geometry editor with map interface"""
    data_instance = get_object_or_404(Data, id=data_id)
    
    polygons = PolygonFeature.objects.filter(data=data_instance)
    points = PointFeature.objects.filter(data=data_instance)
    lines = LineFeature.objects.filter(data=data_instance)
    
    features = {
        'polygons': [
            {
                'gisid': p.gisid,
                'coordinates': p.coordinates,
                'type': p.type,
                'id': p.id
            } for p in polygons
        ],
        'points': [
            {
                'gisid': p.gisid,
                'coordinates': p.coordinates,
                'type': p.type,
                'id': p.id
            } for p in points
        ],
        'lines': [
            {
                'gisid': l.gisid,
                'coordinates': l.coordinates,
                'type': l.type,
                'road_name': l.road_name or '',
                'id': l.id
            } for l in lines
        ]
    }
    
    context = {
        'data': data_instance,
        'features': features,
        'feature_count': polygons.count() + points.count() + lines.count(),
        'polygon_count': polygons.count(),
        'point_count': points.count(),
        'line_count': lines.count(),
        'edit_history': FeatureEditHistory.objects.filter(data=data_instance).order_by('-edited_at')[:20]
    }
    
    return render(request, 'Nit/geometry_editor.html', context)


@login_required
@admin_required
def shapefile_import_view(request):
    """Import shapefile for a data record"""
    data_id = request.GET.get('data_id')
    data_instance = get_object_or_404(Data, id=data_id) if data_id else None
    
    if request.method == 'POST':
        data_id = request.POST.get('data_id')
        data_instance = get_object_or_404(Data, id=data_id)
        
        if 'shapefile' not in request.FILES:
            messages.error(request, 'No shapefile selected')
            return redirect('shapefile_import')
        
        shapefile_zip = request.FILES['shapefile']
        
        result = ShapefileService.import_shapefile(
            data_instance,
            shapefile_zip,
            request.user
        )
        
        if result['success']:
            messages.success(request, 
                f'Shapefile imported successfully! {result["feature_count"]} features imported.')
        else:
            messages.error(request, f'Import failed: {result["error"]}')
        
        return redirect('geometry_editor', data_id=data_instance.id)
    
    context = {
        'data_instances': Data.objects.all().order_by('-created_at'),
        'selected_data': data_instance,
    }
    return render(request, 'Nit/shapefile_import.html', context)


@login_required
@admin_required
def export_shapefile_view(request, data_id):
    """Export data as shapefile"""
    data_instance = get_object_or_404(Data, id=data_id)
    geometry_type = request.GET.get('type', 'polygon')
    
    try:
        zip_path = ShapefileService.export_shapefile(data_instance, geometry_type)
        
        if os.path.exists(zip_path):
            response = FileResponse(open(zip_path, 'rb'))
            response['Content-Type'] = 'application/zip'
            response['Content-Disposition'] = f'attachment; filename="export_{data_instance.ward}_{geometry_type}.zip"'
            
            import atexit
            atexit.register(lambda: os.remove(zip_path) if os.path.exists(zip_path) else None)
            
            return response
        else:
            messages.error(request, 'Export failed - zip file not created')
            return redirect('geometry_editor', data_id=data_id)
            
    except Exception as e:
        messages.error(request, f'Export failed: {str(e)}')
        return redirect('geometry_editor', data_id=data_id)


@csrf_exempt
@login_required
def api_save_geometry(request):
    """API endpoint to save geometry from map editor"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    try:
        data = json.loads(request.body)
        data_id = data.get('data_id')
        gisid = data.get('gisid')
        geometry_type = data.get('type', 'polygon')
        coordinates = data.get('coordinates')
        road_name = data.get('road_name', '')
        notes = data.get('notes', '')
        
        if not all([data_id, gisid, coordinates]):
            return JsonResponse({'error': 'Missing required fields'}, status=400)
        
        data_instance = get_object_or_404(Data, id=data_id)
        old_geometry = None
        
        if geometry_type == 'polygon':
            feature, created = PolygonFeature.objects.update_or_create(
                data=data_instance,
                gisid=gisid,
                defaults={
                    'type': 'Polygon',
                    'coordinates': coordinates
                }
            )
            if not created:
                old_geometry = PolygonFeature.objects.get(data=data_instance, gisid=gisid).coordinates
                
        elif geometry_type == 'point':
            feature, created = PointFeature.objects.update_or_create(
                data=data_instance,
                gisid=gisid,
                defaults={
                    'type': 'Point',
                    'coordinates': coordinates
                }
            )
            if not created:
                old_geometry = PointFeature.objects.get(data=data_instance, gisid=gisid).coordinates
                
        elif geometry_type == 'line':
            feature, created = LineFeature.objects.update_or_create(
                data=data_instance,
                gisid=gisid,
                defaults={
                    'type': 'LineString',
                    'coordinates': coordinates,
                    'road_name': road_name
                }
            )
            if not created:
                old_geometry = LineFeature.objects.get(data=data_instance, gisid=gisid).coordinates
        else:
            return JsonResponse({'error': 'Invalid geometry type'}, status=400)
        
        FeatureEditHistory.objects.create(
            data=data_instance,
            feature_gisid=gisid,
            geometry_type=geometry_type,
            old_geometry=old_geometry,
            new_geometry=coordinates,
            edited_by=request.user,
            notes=notes or 'Geometry updated via editor'
        )
        
        return JsonResponse({
            'success': True,
            'message': 'Geometry saved successfully',
            'gisid': gisid,
            'created': created
        }, status=200)
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
def api_get_geometry(request, data_id, gisid):
    """Get geometry data for a feature"""
    data_instance = get_object_or_404(Data, id=data_id)
    geometry_type = request.GET.get('type', 'polygon')
    
    try:
        if geometry_type == 'polygon':
            feature = get_object_or_404(PolygonFeature, data=data_instance, gisid=gisid)
            return JsonResponse({
                'gisid': feature.gisid,
                'coordinates': feature.coordinates,
                'type': feature.type,
                'data_id': data_id
            }, status=200)
        elif geometry_type == 'point':
            feature = get_object_or_404(PointFeature, data=data_instance, gisid=gisid)
            return JsonResponse({
                'gisid': feature.gisid,
                'coordinates': feature.coordinates,
                'type': feature.type,
                'data_id': data_id
            }, status=200)
        elif geometry_type == 'line':
            feature = get_object_or_404(LineFeature, data=data_instance, gisid=gisid)
            return JsonResponse({
                'gisid': feature.gisid,
                'coordinates': feature.coordinates,
                'type': feature.type,
                'road_name': feature.road_name or '',
                'data_id': data_id
            }, status=200)
        else:
            return JsonResponse({'error': 'Invalid geometry type'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=404)


# ============================================
# API BUILDINGS
# ============================================

@csrf_exempt
@login_required
def api_buildings(request):
    """API endpoint for building CRUD operations"""
    
    if request.method == 'GET':
        buildings = Building.objects.filter(geometry__isnull=False).select_related('corporation')
        features = []
        
        for building in buildings:
            if building.geometry:
                try:
                    if hasattr(building.geometry, 'geojson'):
                        geometry = json.loads(building.geometry.geojson)
                    else:
                        continue
                    
                    feature = {
                        "type": "Feature",
                        "geometry": geometry,
                        "properties": {
                            "id": building.id,
                            "gis_id": building.gis_id,
                            "building_name": building.building_name,
                            "building_number": building.building_number,
                            "area": building.area,
                            "building_type": building.building_type,
                            "floors": building.floors,
                            "owner_name": building.owner_name,
                            "owner_contact": building.owner_contact,
                            "corporation": building.corporation.name if building.corporation else None,
                            "ward": building.ward,
                            "city": building.city,
                        }
                    }
                    features.append(feature)
                except:
                    continue
        
        return JsonResponse({
            "type": "FeatureCollection",
            "features": features
        }, safe=False)
    
    elif request.method == 'POST':
        try:
            data = json.loads(request.body)
            print("📥 Received data:", data)
            
            # Get geometry coordinates
            coords = data.get('geometry_coords')
            if not coords:
                return JsonResponse({'error': 'Geometry coordinates required'}, status=400)
            
            if isinstance(coords, list) and len(coords) > 0:
                if isinstance(coords[0], list) and len(coords[0]) == 2:
                    points = coords
                else:
                    return JsonResponse({'error': 'Invalid coordinate format. Expected [[lng, lat], ...]'}, status=400)
            else:
                return JsonResponse({'error': 'Invalid coordinates'}, status=400)
            
            # ✅ FIX: Convert Web Mercator to WGS84
            def convert_web_mercator_to_wgs84(x, y):
                """Convert Web Mercator (EPSG:3857) to WGS84 (EPSG:4326)"""
                # Check if coordinates are in Web Mercator (large numbers)
                if abs(x) > 1000000:
                    lon = (x / 20037508.34) * 180
                    lat = (y / 20037508.34) * 180
                    lat = 180 / math.pi * (2 * math.atan(math.exp(lat * math.pi / 180)) - math.pi / 2)
                    return [lon, lat]
                else:
                    # Already in WGS84
                    return [x, y]
            
            # Convert all points
            converted_points = []
            for point in points:
                if len(point) >= 2:
                    lng, lat = convert_web_mercator_to_wgs84(point[0], point[1])
                    converted_points.append([lng, lat])
                else:
                    converted_points.append(point)
            
            print(f"📐 Original points: {points}")
            print(f"📐 Converted points: {converted_points}")
            
            # ✅ Validate converted coordinates
            for point in converted_points:
                lng, lat = point[0], point[1]
                if not (-180 <= lng <= 180 and -90 <= lat <= 90):
                    return JsonResponse({
                        'error': f'Invalid coordinate values after conversion: lng={lng}, lat={lat}'
                    }, status=400)
            
            # ✅ Close polygon if not closed
            if converted_points[0] != converted_points[-1]:
                converted_points.append(converted_points[0])
            
            # ✅ Create geometry with correct SRID
            try:
                geojson_polygon = {
                    "type": "Polygon",
                    "coordinates": [converted_points]
                }
                print(f"📐 Creating geometry: {geojson_polygon}")
                
                # ✅ IMPORTANT: Specify SRID=4326 (WGS84)
                geom = GEOSGeometry(json.dumps(geojson_polygon), srid=4326)
                
                if not geom.valid:
                    return JsonResponse({'error': f'Invalid geometry: {geom.valid_reason}'}, status=400)
                    
            except Exception as e:
                print(f"❌ Geometry error: {e}")
                return JsonResponse({'error': f'Invalid geometry: {str(e)}'}, status=400)
            
            # Get corporation
            corporation_id = data.get('corporation')
            corporation = None
            if corporation_id:
                try:
                    corporation = Corporation.objects.get(id=corporation_id)
                except Corporation.DoesNotExist:
                    pass
            
            # Generate GIS ID
            gis_id = data.get('gis_id')
            if not gis_id:
                gis_id = f"B-{uuid.uuid4().hex[:8].upper()}"
            
            # ✅ Create building with converted geometry
            building = Building.objects.create(
                gis_id=gis_id,
                building_name=data.get('building_name', 'Unnamed Building'),
                building_number=data.get('building_number', gis_id),
                geometry=geom,
                area=data.get('area', 0),
                building_type=data.get('building_type', 'RESIDENTIAL'),
                floors=data.get('floors', 0),
                owner_name=data.get('owner_name', 'Unknown'),
                owner_contact=data.get('owner_contact', ''),
                corporation=corporation,
                ward=data.get('ward', ''),
                city=data.get('city', 'New Delhi'),
                state=data.get('state', 'Delhi'),
                pincode=data.get('pincode', ''),
                created_by=request.user if request.user.is_authenticated else None,
            )
            
            print(f"✅ Building created: ID={building.id}, GIS_ID={building.gis_id}")
            print(f"📍 Geometry: {geom}")
            
            # Get center coordinates for response
            geom_coords = None
            if building.geometry:
                try:
                    geom_json = json.loads(building.geometry.geojson)
                    if geom_json.get('type') == 'Polygon':
                        coords_array = geom_json.get('coordinates', [[]])[0]
                        if coords_array and len(coords_array) > 0:
                            lats = [c[1] for c in coords_array]
                            lngs = [c[0] for c in coords_array]
                            center_lat = sum(lats) / len(lats)
                            center_lng = sum(lngs) / len(lngs)
                            geom_coords = [center_lng, center_lat]
                except Exception as e:
                    print(f"Error getting geometry center: {e}")
            
            return JsonResponse({
                'status': 'success',
                'id': building.id,
                'gis_id': building.gis_id,
                'building_name': building.building_name,
                'building_number': building.building_number,
                'geometry': geom_coords,
                'message': 'Building created successfully'
            }, status=201)
            
        except Exception as e:
            print(f"❌ Error in POST: {e}")
            import traceback
            traceback.print_exc()
            return JsonResponse({'error': str(e)}, status=400)
    
    return JsonResponse({'error': 'Method not allowed'}, status=405)
@csrf_exempt
@login_required
def api_building_detail(request, building_id):
    """API endpoint for single building CRUD operations"""
    
    try:
        building = Building.objects.get(id=building_id)
    except Building.DoesNotExist:
        return JsonResponse({'error': 'Building not found'}, status=404)
    
    if request.method == 'GET':
        data = {
            'id': building.id,
            'gis_id': building.gis_id,
            'building_name': building.building_name,
            'building_number': building.building_number,
            'area': building.area,
            'building_type': building.building_type,
            'floors': building.floors,
            'owner_name': building.owner_name,
            'owner_contact': building.owner_contact,
            'corporation': building.corporation.id if building.corporation else None,
            'ward': building.ward,
            'city': building.city,
        }
        
        if building.geometry:
            if hasattr(building.geometry, 'geojson'):
                data['geometry'] = json.loads(building.geometry.geojson)
        
        return JsonResponse(data)
    
    elif request.method == 'PUT':
        try:
            data = json.loads(request.body)
            
            building.gis_id = data.get('gis_id', building.gis_id)
            building.building_name = data.get('building_name', building.building_name)
            building.building_number = data.get('building_number', building.building_number)
            building.building_type = data.get('building_type', building.building_type)
            building.floors = data.get('floors', building.floors)
            building.area = data.get('area', building.area)
            building.owner_name = data.get('owner_name', building.owner_name)
            building.owner_contact = data.get('owner_contact', building.owner_contact)
            building.ward = data.get('ward', building.ward)
            building.city = data.get('city', building.city)
            
            corporation_id = data.get('corporation')
            if corporation_id:
                try:
                    building.corporation = Corporation.objects.get(id=corporation_id)
                except Corporation.DoesNotExist:
                    pass
            else:
                building.corporation = None
            
            coords = data.get('geometry_coords')
            if coords:
                points = [(c[0], c[1]) for c in coords]
                if points[0] != points[-1]:
                    points.append(points[0])
                
                geojson_polygon = {
                    "type": "Polygon",
                    "coordinates": [points]
                }
                building.geometry = GEOSGeometry(json.dumps(geojson_polygon))
            
            building.save()
            
            return JsonResponse({
                'status': 'success',
                'id': building.id,
                'message': 'Building updated successfully'
            }, status=200)
            
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)
    
    elif request.method == 'DELETE':
        try:
            building.delete()
            return JsonResponse({
                'status': 'success',
                'message': 'Building deleted successfully'
            }, status=200)
        except Exception as e:
            return JsonResponse({
                'status': 'error',
                'error': str(e)
            }, status=400)
    
    return JsonResponse({'error': 'Method not allowed'}, status=405)


@login_required
@admin_required
def api_get_all_features(request, data_id):
    """Get all features for a data record"""
    data_instance = get_object_or_404(Data, id=data_id)
    
    polygons = PolygonFeature.objects.filter(data=data_instance)
    points = PointFeature.objects.filter(data=data_instance)
    lines = LineFeature.objects.filter(data=data_instance)
    
    return JsonResponse({
        'polygons': [
            {
                'gisid': p.gisid,
                'coordinates': p.coordinates,
                'type': p.type,
                'id': p.id
            } for p in polygons
        ],
        'points': [
            {
                'gisid': p.gisid,
                'coordinates': p.coordinates,
                'type': p.type,
                'id': p.id
            } for p in points
        ],
        'lines': [
            {
                'gisid': l.gisid,
                'coordinates': l.coordinates,
                'type': l.type,
                'road_name': l.road_name or '',
                'id': l.id
            } for l in lines
        ]
    }, status=200)


@csrf_exempt
def api_building_search(request):
    """
    Simple API endpoint to search a single building by GIS ID
    Returns: List with one building object or empty list
    URL: /api/building-search/?gis_id=B-MS8ULZ5P
    """
    if request.method != 'GET':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    gis_id = request.GET.get('gis_id', '').strip()
    
    if not gis_id:
        return JsonResponse([], safe=False)
    
    try:
        building = Building.objects.select_related('corporation').filter(
            gis_id__iexact=gis_id
        ).first()
        
        if building:
            data = {
                'id': building.id,
                'gis_id': building.gis_id,
                'building_name': building.building_name or 'Unnamed',
                'building_number': building.building_number,
                'address': building.address,
                'building_type': building.get_building_type_display() if building.building_type else 'Other',
                'floors': building.floors or 0,
                'area': float(building.area) if building.area else 0,
                'ward': building.ward or 'N/A',
                'city': building.city or 'New Delhi',
                'state': building.state or 'Delhi',
                'pincode': building.pincode or 'N/A',
                'owner_name': building.owner_name or 'Unknown',
                'owner_contact': building.owner_contact or 'N/A',
                'corporation': building.corporation.name if building.corporation else None,
                'is_active': building.is_active,
                'created_at': building.created_at.strftime('%d/%m/%Y %H:%M') if building.created_at else None,
                'updated_at': building.updated_at.strftime('%d/%m/%Y %H:%M') if building.updated_at else None,
            }
            
            if building.geometry:
                try:
                    if hasattr(building.geometry, 'geojson'):
                        geom_json = json.loads(building.geometry.geojson)
                        if geom_json.get('type') == 'Point':
                            coords = geom_json.get('coordinates', [])
                            if coords:
                                data['geometry'] = {
                                    'type': 'Point',
                                    'coordinates': coords
                                }
                        elif geom_json.get('type') == 'Polygon':
                            coords = geom_json.get('coordinates', [[]])[0]
                            if coords and len(coords) > 0:
                                lats = [c[1] for c in coords]
                                lngs = [c[0] for c in coords]
                                center_lat = sum(lats) / len(lats)
                                center_lng = sum(lngs) / len(lngs)
                                data['geometry'] = {
                                    'type': 'Point',
                                    'coordinates': [center_lng, center_lat]
                                }
                except:
                    pass
            
            return JsonResponse([data], safe=False)
        else:
            return JsonResponse([], safe=False)
            
    except Exception as e:
        print(f"Search error: {e}")
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@admin_required
def api_delete_feature(request, data_id, gisid):
    """Delete a feature"""
    if request.method != 'DELETE':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    data_instance = get_object_or_404(Data, id=data_id)
    geometry_type = request.GET.get('type', 'polygon')
    
    try:
        if geometry_type == 'polygon':
            feature = get_object_or_404(PolygonFeature, data=data_instance, gisid=gisid)
        elif geometry_type == 'point':
            feature = get_object_or_404(PointFeature, data=data_instance, gisid=gisid)
        elif geometry_type == 'line':
            feature = get_object_or_404(LineFeature, data=data_instance, gisid=gisid)
        else:
            return JsonResponse({'error': 'Invalid geometry type'}, status=400)
        
        FeatureEditHistory.objects.create(
            data=data_instance,
            feature_gisid=gisid,
            geometry_type=geometry_type,
            old_geometry=feature.coordinates,
            new_geometry=None,
            edited_by=request.user,
            notes='Feature deleted'
        )
        
        feature.delete()
        
        return JsonResponse({
            'success': True,
            'message': 'Feature deleted successfully'
        }, status=200)
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=404)


@login_required
@admin_required
def api_edit_history(request, data_id):
    """Get edit history for a data record"""
    data_instance = get_object_or_404(Data, id=data_id)
    history = FeatureEditHistory.objects.filter(data=data_instance).order_by('-edited_at')[:50]
    
    return JsonResponse({
        'history': [
            {
                'gisid': h.feature_gisid,
                'type': h.geometry_type,
                'edited_by': h.edited_by.username if h.edited_by else 'Unknown',
                'edited_at': h.edited_at.strftime('%Y-%m-%d %H:%M:%S'),
                'notes': h.notes
            } for h in history
        ]
    }, status=200)


# ============================================
# CORPORATION FUNCTIONS
# ============================================

@login_required
def corporation_dashboard(request):
    """Corporation dashboard view"""
    try:
        corporations = Corporation.objects.all().annotate(
            building_count=Count('buildings'),
            total_building_area=Sum('buildings__area')
        )
        
        total_corporations = corporations.count()
        total_buildings = Building.objects.count()
        total_area = Building.objects.aggregate(Sum('area'))['area__sum'] or 0
        active_corporations = corporations.filter(status='active').count()
        pending_corporations = corporations.filter(status='pending').count()
        
        corporation_data = []
        for corp in corporations:
            buildings = Building.objects.filter(corporation=corp)
            corporation_data.append({
                'id': corp.id,
                'name': corp.name,
                'code': corp.code or '',
                'total_area': corp.total_area or 0,
                'building_count': buildings.count(),
                'buildings': buildings[:5],
                'created_at': corp.created_at,
                'status': getattr(corp, 'status', 'active'),
                'total_surveys': getattr(corp, 'total_surveys', 0),
                'coverage_percentage': getattr(corp, 'coverage_percentage', 0),
            })
        
        context = {
            'corporations': corporation_data,
            'total_corporations': total_corporations,
            'active_corporations': active_corporations,
            'pending_corporations': pending_corporations,
            'total_buildings': total_buildings,
            'total_area': total_area,
            'total_surveys': 0,
            'page_title': 'Corporation Dashboard',
        }
        
        return render(request, 'corporation/dashboard.html', context)
        
    except Exception as e:
        logger.error(f"Error in corporation_dashboard: {str(e)}")
        context = {
            'corporations': [],
            'total_corporations': 0,
            'active_corporations': 0,
            'pending_corporations': 0,
            'total_buildings': 0,
            'total_area': 0,
            'total_surveys': 0,
            'page_title': 'Corporation Dashboard',
            'error': str(e),
        }
        return render(request, 'corporation/dashboard.html', context)


@login_required
def corporation_list(request):
    """API endpoint for corporation list"""
    corporations = Corporation.objects.all()
    data = []
    for corp in corporations:
        data.append({
            'id': corp.id,
            'name': corp.name,
            'code': corp.code,
            'status': getattr(corp, 'status', 'active'),
            'total_buildings': corp.buildings.count(),
            'total_surveys': getattr(corp, 'total_surveys', 0),
            'coverage': getattr(corp, 'coverage_percentage', 0),
            'created_at': corp.created_at.strftime('%Y-%m-%d') if corp.created_at else '',
        })
    return JsonResponse(data, safe=False)


@login_required
def corporation_map(request, corporation_id=None):
    """Corporation map view with buildings"""
    from .models import Corporation, Building
    import json
    import math
    import logging
    
    logger = logging.getLogger(__name__)
    
    corporations = Corporation.objects.all()
    total_buildings = Building.objects.count()
    
    # Get map position from URL parameters
    map_lat = request.GET.get('lat')
    map_lng = request.GET.get('lng')
    map_zoom = request.GET.get('zoom', 12)
    
    if corporation_id:
        selected_corp = get_object_or_404(Corporation, id=corporation_id)
        buildings = Building.objects.filter(corporation=selected_corp)
    else:
        selected_corp = None
        buildings = Building.objects.all()
    
    # Build GeoJSON with converted coordinates
    def web_mercator_to_wgs84(x, y):
        lon = (x / 20037508.34) * 180
        lat = (y / 20037508.34) * 180
        lat = 180 / math.pi * (2 * math.atan(math.exp(lat * math.pi / 180)) - math.pi / 2)
        return [lon, lat]
    
    def convert_coords(coords):
        if isinstance(coords[0], list):
            return [convert_coords(c) for c in coords]
        else:
            if len(coords) >= 2:
                if abs(coords[0]) > 1000000 or abs(coords[1]) > 1000000:
                    return web_mercator_to_wgs84(coords[0], coords[1])
                return coords
            return coords
    
    features = []
    for building in buildings:
        if building.geometry:
            try:
                geom_json = json.loads(building.geometry.geojson)
                
                # Check if coordinates are in Web Mercator
                is_web_mercator = False
                try:
                    test_coord = geom_json['coordinates'][0][0]
                    if len(test_coord) >= 2 and abs(test_coord[0]) > 1000000:
                        is_web_mercator = True
                except:
                    pass
                
                if is_web_mercator:
                    if geom_json['type'] == 'Polygon':
                        geom_json['coordinates'] = convert_coords(geom_json['coordinates'])
                    elif geom_json['type'] == 'MultiPolygon':
                        geom_json['coordinates'] = [convert_coords(poly) for poly in geom_json['coordinates']]
                
                features.append({
                    'type': 'Feature',
                    'geometry': geom_json,
                    'properties': {
                        'id': building.id,
                        'gis_id': building.gis_id,
                        'building_number': building.building_number,
                        'building_name': building.building_name,
                        'area': float(building.area) if building.area else 0,
                        'building_type': building.building_type,
                        'floors': building.floors,
                        'owner_name': building.owner_name,
                        'address': building.address,
                        'city': building.city,
                        'state': building.state,
                        'pincode': building.pincode,
                        'owner_contact': building.owner_contact,
                        'year_built': building.year_built,
                        'corporation': building.corporation.name if building.corporation else 'Unknown',
                        'corporation_id': building.corporation.id if building.corporation else None,
                    }
                })
            except Exception as e:
                logger.error(f"Error processing building {building.id}: {e}")
                continue
    
    buildings_geojson = {
        'type': 'FeatureCollection',
        'features': features
    }
    
    # Get corporation stats
    corporation_stats = []
    for corp in corporations:
        corp_buildings = corp.buildings.all()
        corporation_stats.append({
            'id': corp.id,
            'name': corp.name,
            'count': corp_buildings.count(),
        })
    
    context = {
        'selected_corp': selected_corp,
        'building_count': buildings.count(),
        'total_buildings': total_buildings,
        'corporation_stats': corporation_stats,
        'corporation_id': corporation_id,
        'buildings_geojson': json.dumps(buildings_geojson),
        'geojson_data': '{"type":"FeatureCollection","features":[]}',
        'bounds': None,
        'map_lat': float(map_lat) if map_lat and map_lat != 'None' else 28.6139,
        'map_lng': float(map_lng) if map_lng and map_lng != 'None' else 77.2090,
        'map_zoom': float(map_zoom) if map_zoom else 12,
    }
    
    return render(request, 'corporation/map.html', context)

# ============================================
# CORPORATION GEOJSON FUNCTIONS
# ============================================
@login_required
def corporation_geojson(request, corporation_id):
    """Get GeoJSON data for a corporation - Convert to 4326 for viewing"""
    import math
    
    corporation = get_object_or_404(Corporation, id=corporation_id)
    buildings = Building.objects.filter(corporation=corporation, geometry__isnull=False)
    
    def web_mercator_to_wgs84(x, y):
        lon = (x / 20037508.34) * 180
        lat = (y / 20037508.34) * 180
        lat = 180 / math.pi * (2 * math.atan(math.exp(lat * math.pi / 180)) - math.pi / 2)
        return [lon, lat]
    
    def convert_coords_to_4326(coords):
        if not coords:
            return coords
        if isinstance(coords[0], list):
            return [convert_coords_to_4326(c) for c in coords]
        else:
            if len(coords) >= 2:
                if abs(coords[0]) > 1000000 or abs(coords[1]) > 1000000:
                    return web_mercator_to_wgs84(coords[0], coords[1])
                return coords
            return coords
    
    features = []
    for building in buildings:
        if building.geometry:
            try:
                geom_json = json.loads(building.geometry.geojson)
                
                if geom_json['type'] == 'Polygon':
                    geom_json['coordinates'] = convert_coords_to_4326(geom_json['coordinates'])
                elif geom_json['type'] == 'MultiPolygon':
                    geom_json['coordinates'] = [convert_coords_to_4326(poly) for poly in geom_json['coordinates']]
                
                features.append({
                    'type': 'Feature',
                    'geometry': geom_json,
                    'properties': {
                        'id': building.id,
                        'gis_id': building.gis_id,
                        'building_number': building.building_number,
                        'building_name': building.building_name,
                        'area': float(building.area) if building.area else 0,
                        'building_type': building.building_type,
                        'floors': building.floors,
                        'owner_name': building.owner_name,
                        'address': building.address,
                        'city': building.city,
                        'state': building.state,
                        'pincode': building.pincode,
                        'corporation': corporation.name,
                    }
                })
            except Exception as e:
                print(f"Error processing building {building.id}: {e}")
                continue
    
    geojson = {
        'type': 'FeatureCollection',
        'name': corporation.name,
        'total_features': len(features),
        'features': features
    }
    
    return JsonResponse(geojson, safe=False)
@login_required
def download_corporation_geojson(request, corporation_id):
    """Download corporation buildings as GeoJSON file"""
    corporation = get_object_or_404(Corporation, id=corporation_id)
    buildings = Building.objects.filter(corporation=corporation, geometry__isnull=False)
    
    features = []
    for building in buildings:
        if building.geometry:
            try:
                geom_json = json.loads(building.geometry.geojson)
                features.append({
                    'type': 'Feature',
                    'geometry': geom_json,
                    'properties': {
                        'id': building.id,
                        'gis_id': building.gis_id,
                        'building_number': building.building_number,
                        'building_name': building.building_name,
                        'area': float(building.area) if building.area else 0,
                        'building_type': building.building_type,
                        'floors': building.floors,
                        'owner_name': building.owner_name,
                        'address': building.address,
                        'city': building.city,
                        'state': building.state,
                        'pincode': building.pincode,
                        'corporation': corporation.name,
                    }
                })
            except Exception as e:
                print(f"Error processing building {building.id}: {e}")
                continue
    
    geojson = {
        'type': 'FeatureCollection',
        'name': f'{corporation.code}_{corporation.name}',
        'features': features
    }
    
    response = JsonResponse(geojson, safe=False)
    response['Content-Disposition'] = f'attachment; filename="{corporation.code}_{corporation.name}_buildings.geojson"'
    return response


# ============================================
# UPLOAD CORPORATION GEOJSON - FIXED
# ============================================

@login_required
@csrf_exempt
def upload_corporation_geojson(request):
    """Upload GeoJSON - Fix coordinate structure and close polygons"""
    
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    try:
        name = request.POST.get('name')
        code = request.POST.get('code')
        description = request.POST.get('description', '')
        geojson_file = request.FILES.get('geojson_file') or request.FILES.get('geojson')
        
        if not name:
            return JsonResponse({'error': 'Corporation name is required'}, status=400)
        
        if not geojson_file:
            return JsonResponse({'error': 'GeoJSON file is required'}, status=400)
        
        if not code:
            code = name.upper()[:10]
            base_code = code
            counter = 1
            while Corporation.objects.filter(code=code).exists():
                code = f"{base_code}{counter}"
                counter += 1
        
        # Read file content
        content = geojson_file.read().decode('utf-8')
        data = json.loads(content)
        features = data.get('features', [])
        
        if not features:
            return JsonResponse({'error': 'No features found in GeoJSON file'}, status=400)
        
        # Create corporation
        corporation = Corporation.objects.create(
            name=name,
            code=code,
            description=description,
            status='active'
        )
        
        created_count = 0
        error_count = 0
        error_messages = []
        existing_ids = set(Building.objects.values_list('gis_id', flat=True))
        
        for i, feature in enumerate(features):
            try:
                properties = feature.get('properties', {})
                geometry = feature.get('geometry')
                
                if not geometry:
                    error_count += 1
                    error_messages.append(f"Feature {i}: No geometry found")
                    continue
                
                # Get coordinates
                if geometry.get('type') == 'MultiPolygon':
                    coords = geometry['coordinates'][0]
                else:
                    coords = geometry['coordinates']
                
                # Flatten coordinates
                while coords and isinstance(coords[0], list) and isinstance(coords[0][0], list):
                    coords = coords[0]
                
                # Close polygon
                if coords and coords[0] != coords[-1]:
                    coords.append(coords[0])
                
                # Generate GIS ID
                gis_id = properties.get('gis_id') or properties.get('GIS_ID') or properties.get('id')
                
                if not gis_id or str(gis_id).strip() == '':
                    gis_id = f"B-{uuid.uuid4().hex[:8].upper()}"
                else:
                    gis_id = str(gis_id).strip()
                    original_gis_id = gis_id
                    counter_dup = 1
                    while gis_id in existing_ids:
                        gis_id = f"{original_gis_id}-{counter_dup}"
                        counter_dup += 1
                
                existing_ids.add(gis_id)
                
                building_name = properties.get('building_name') or properties.get('name') or f"Building {gis_id}"
                building_number = properties.get('building_number') or properties.get('number') or gis_id
                
                area = properties.get('area') or properties.get('sqft') or 0
                try:
                    area = float(area)
                except:
                    area = 0
                
                building_type = properties.get('building_type') or properties.get('type') or 'residential'
                
                floors = properties.get('floors') or 1
                try:
                    floors = int(floors)
                except:
                    floors = 1
                
                owner_name = properties.get('owner_name') or properties.get('owner') or 'Unknown'
                address = properties.get('address') or properties.get('Address') or ''
                
                # Create geometry
                geom_dict = {
                    'type': 'Polygon',
                    'coordinates': [coords]
                }
                geom = GEOSGeometry(json.dumps(geom_dict), srid=4326)
                
                # ✅ FIXED: Remove duplicate building_number
                Building.objects.create(
                    corporation=corporation,
                    gis_id=gis_id,
                    building_number=str(building_number),  # Only once!
                    building_name=str(building_name),
                    address=str(address),
                    city=properties.get('city', 'New Delhi'),
                    state=properties.get('state', 'Delhi'),
                    pincode=properties.get('pincode', ''),
                    geometry=geom,
                    building_type=str(building_type).lower() if building_type else 'residential',
                    area=area,
                    floors=floors,
                    year_built=properties.get('year_built'),
                    owner_name=str(owner_name),
                    owner_contact=properties.get('owner_contact', ''),
                )
                created_count += 1
                
            except Exception as e:
                error_count += 1
                error_messages.append(f"Feature {i}: {str(e)}")
                print(f"Error creating building: {e}")
                continue
        
        if created_count == 0:
            corporation.delete()
            error_detail = "\n".join(error_messages[:5])
            return JsonResponse({
                'error': f'No buildings could be created. Errors: {error_detail}'
            }, status=400)
        
        corporation.total_buildings = created_count
        corporation.save()
        
        return JsonResponse({
            'success': True,
            'message': f'Corporation "{name}" created with {created_count} buildings!',
            'corporation_id': corporation.id,
            'buildings_created': created_count,
            'errors': error_count
        }, status=200)
        
    except Exception as e:
        print(f"Upload error: {str(e)}")
        import traceback
        traceback.print_exc()
        return JsonResponse({'error': str(e)}, status=500)

# ============================================
# BUILDINGS GEOJSON API
# ============================================

# views_geometry.py

@login_required
def buildings_geojson(request, corporation_id=None):
    """API endpoint - Return geometry converted to Web Mercator (3857) for OpenLayers"""
    import json
    import math
    
    def wgs84_to_web_mercator(lng, lat):
        """Convert WGS84 (EPSG:4326) to Web Mercator (EPSG:3857)"""
        x = lng * 20037508.34 / 180
        y = math.log(math.tan((90 + lat) * math.pi / 360)) / (math.pi / 180)
        y = y * 20037508.34 / 180
        return [x, y]
    
    def convert_coords_to_3857(coords):
        """Recursively convert coordinates from 4326 to 3857"""
        if isinstance(coords[0], list):
            return [convert_coords_to_3857(c) for c in coords]
        else:
            if len(coords) >= 2:
                return wgs84_to_web_mercator(coords[0], coords[1])
            return coords
    
    if corporation_id:
        buildings = Building.objects.filter(corporation_id=corporation_id, geometry__isnull=False)
    else:
        buildings = Building.objects.filter(geometry__isnull=False)
    
    features = []
    for building in buildings:
        if building.geometry:
            try:
                # ✅ Data is stored in 4326
                geom_json = json.loads(building.geometry.geojson)
                
                # ✅ Convert to 3857 for OpenLayers display
                if geom_json['type'] == 'Polygon':
                    geom_json['coordinates'] = convert_coords_to_3857(geom_json['coordinates'])
                elif geom_json['type'] == 'MultiPolygon':
                    geom_json['coordinates'] = [convert_coords_to_3857(poly) for poly in geom_json['coordinates']]
                
                feature = {
                    'type': 'Feature',
                    'geometry': geom_json,
                    'properties': {
                        'id': building.id,
                        'gis_id': building.gis_id,
                        'building_number': building.building_number,
                        'building_name': building.building_name,
                        'area': float(building.area) if building.area else 0,
                        'owner_name': building.owner_name,
                        'address': building.address,
                        'city': building.city,
                        'building_type': building.building_type,
                        'floors': building.floors,
                        'year_built': building.year_built,
                        'owner_contact': building.owner_contact,
                        'state': building.state,
                        'pincode': building.pincode,
                        'corporation': building.corporation.name if building.corporation else None,
                        'corporation_id': building.corporation.id if building.corporation else None,
                    }
                }
                features.append(feature)
            except Exception as e:
                print(f"Error processing building {building.id}: {e}")
                continue
    
    geojson = {
        'type': 'FeatureCollection',
        'features': features
    }
    
    return JsonResponse(geojson)

@login_required
def get_corporation_buildings_geojson(request, corporation_id):
    """API to get buildings GeoJSON for a corporation - Convert to 4326 for Leaflet"""
    import math
    
    corporation = get_object_or_404(Corporation, id=corporation_id)
    buildings = Building.objects.filter(corporation=corporation, geometry__isnull=False)
    
    def web_mercator_to_wgs84(x, y):
        """Convert Web Mercator (EPSG:3857) to WGS84 (EPSG:4326)"""
        lon = (x / 20037508.34) * 180
        lat = (y / 20037508.34) * 180
        lat = 180 / math.pi * (2 * math.atan(math.exp(lat * math.pi / 180)) - math.pi / 2)
        return [lon, lat]
    
    def convert_coords_to_4326(coords):
        """Recursively convert coordinates from 3857 to 4326"""
        if not coords:
            return coords
        
        if isinstance(coords[0], list):
            return [convert_coords_to_4326(c) for c in coords]
        else:
            if len(coords) >= 2:
                # Check if coordinates are in Web Mercator (large numbers)
                if abs(coords[0]) > 1000000 or abs(coords[1]) > 1000000:
                    return web_mercator_to_wgs84(coords[0], coords[1])
                else:
                    # Already in WGS84
                    return [coords[0], coords[1]]
            return coords
    
    features = []
    for building in buildings:
        if building.geometry:
            try:
                geom_json = json.loads(building.geometry.geojson)
                
                # ✅ Convert from 3857 to 4326 for Leaflet
                if geom_json['type'] == 'Polygon':
                    geom_json['coordinates'] = convert_coords_to_4326(geom_json['coordinates'])
                elif geom_json['type'] == 'MultiPolygon':
                    geom_json['coordinates'] = [convert_coords_to_4326(poly) for poly in geom_json['coordinates']]
                
                # Get center point for the building
                center = None
                try:
                    if building.geometry:
                        center_point = building.geometry.centroid
                        # Convert center if needed
                        if abs(center_point.x) > 1000000 or abs(center_point.y) > 1000000:
                            lng, lat = web_mercator_to_wgs84(center_point.x, center_point.y)
                        else:
                            lng, lat = center_point.x, center_point.y
                        center = {'lng': lng, 'lat': lat}
                except:
                    pass
                
                features.append({
                    'type': 'Feature',
                    'geometry': geom_json,
                    'properties': {
                        'id': building.id,
                        'gis_id': building.gis_id,
                        'building_number': building.building_number,
                        'building_name': building.building_name,
                        'area': float(building.area) if building.area else 0,
                        'building_type': building.building_type,
                        'floors': building.floors,
                        'owner_name': building.owner_name,
                        'address': building.address,
                        'city': building.city,
                        'state': building.state,
                        'pincode': building.pincode,
                        'corporation': corporation.name,
                        'center_lat': center['lat'] if center else None,
                        'center_lng': center['lng'] if center else None,
                    }
                })
            except Exception as e:
                print(f"Error processing building {building.id}: {e}")
                continue
    
    return JsonResponse({
        'type': 'FeatureCollection',
        'features': features
    })

# ============================================
# DEBUG FUNCTIONS
# ============================================

@login_required
def debug_buildings(request, corporation_id=None):
    """Debug view to check building data"""
    if corporation_id:
        buildings = Building.objects.filter(corporation_id=corporation_id)
    else:
        buildings = Building.objects.all()
    
    data = {
        'total': buildings.count(),
        'buildings': []
    }
    
    for building in buildings[:10]:
        data['buildings'].append({
            'id': building.id,
            'gis_id': building.gis_id,
            'building_number': building.building_number,
            'has_geometry': building.geometry is not None,
            'geometry_type': building.geometry.geom_type if building.geometry else None,
            'geometry_srid': building.geometry.srid if building.geometry else None,
        })
    
    first_building = buildings.filter(geometry__isnull=False).first()
    if first_building and first_building.geometry:
        try:
            geom_json = json.loads(first_building.geometry.geojson)
            data['first_geometry'] = geom_json
        except:
            data['first_geometry'] = 'Error parsing geometry'
    
    return JsonResponse(data)


@login_required
def debug_buildings_json(request, corporation_id=None):
    """Debug view to see building coordinates"""
    if corporation_id:
        buildings = Building.objects.filter(corporation_id=corporation_id)[:5]
    else:
        buildings = Building.objects.all()[:5]
    
    data = []
    for building in buildings:
        if building.geometry:
            geom_json = json.loads(building.geometry.geojson)
            data.append({
                'id': building.id,
                'gis_id': building.gis_id,
                'geometry_type': geom_json['type'],
                'first_coords': geom_json['coordinates'][0][:3] if geom_json['type'] == 'Polygon' else None,
            })
    
    return JsonResponse({'buildings': data, 'count': len(data)})


# ============================================
# CORPORATION CRUD OPERATIONS
# ============================================

@login_required
def delete_corporation(request, corporation_id):
    """Delete a corporation"""
    if request.method != 'DELETE':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    try:
        corporation = get_object_or_404(Corporation, id=corporation_id)
        Building.objects.filter(corporation=corporation).delete()
        corporation.delete()
        return JsonResponse({'success': True, 'message': 'Corporation deleted successfully'})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
def corporation_details(request, corporation_id):
    """Get corporation details"""
    try:
        corp = get_object_or_404(Corporation, id=corporation_id)
        data = {
            'id': corp.id,
            'name': corp.name,
            'code': corp.code,
            'description': corp.description,
            'status': corp.status,
            'total_buildings': corp.total_buildings,
            'total_surveys': corp.total_surveys,
            'coverage_percentage': corp.coverage_percentage,
            'total_area': corp.total_area,
            'created_at': corp.created_at.strftime('%Y-%m-%d %H:%M'),
            'updated_at': corp.updated_at.strftime('%Y-%m-%d %H:%M'),
        }
        return JsonResponse(data)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


def test_buildings(request):
    """Simple test view to check buildings"""
    buildings = Building.objects.all()[:5]
    data = []
    for b in buildings:
        if b.geometry:
            data.append({
                'id': b.id,
                'gis_id': b.gis_id,
                'geometry': json.loads(b.geometry.geojson),
                'srid': b.geometry.srid
            })
    
    return JsonResponse({'buildings': data, 'total': Building.objects.count()})


@login_required
def update_corporation(request, corporation_id):
    """Update corporation details"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    try:
        corp = get_object_or_404(Corporation, id=corporation_id)
        data = json.loads(request.body)
        
        if 'name' in data:
            corp.name = data['name']
        if 'description' in data:
            corp.description = data['description']
        if 'status' in data:
            corp.status = data['status']
        
        corp.save()
        
        return JsonResponse({
            'success': True,
            'message': 'Corporation updated successfully'
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)