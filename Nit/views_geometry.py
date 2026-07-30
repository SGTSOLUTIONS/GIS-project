# Nit/views_geometry.py - COMPLETE FIXED VERSION (No Duplicates)
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
    """Corporation dashboard with statistics"""
    corporations = Corporation.objects.all()
    total_corporations = corporations.count()
    total_buildings = Building.objects.count()
    
    corporation_data = []
    for corp in corporations:
        building_count = Building.objects.filter(corporation=corp).count()
        corporation_data.append({
            'id': corp.id,
            'name': corp.name,
            'code': corp.code,
            'description': corp.description,
            'total_buildings': building_count,
            'total_surveys': 0,
            'coverage_percentage': 0,
            'status': corp.status,
            'created_at': corp.created_at,
        })
    
    context = {
        'total_corporations': total_corporations,
        'active_corporations': corporations.filter(status='active').count(),
        'pending_corporations': corporations.filter(status='pending').count(),
        'inactive_corporations': corporations.filter(status='inactive').count(),
        'total_buildings': total_buildings,
        'total_surveys': 0,
        'corporations': corporation_data,
        'corporation': corporations.first(),
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
            'status': corp.status,
            'total_buildings': corp.total_buildings,
            'total_surveys': corp.total_surveys,
            'coverage': corp.coverage_percentage,
            'created_at': corp.created_at.strftime('%Y-%m-%d'),
        })
    return JsonResponse(data, safe=False)


@login_required
def corporation_map(request, corporation_id=None):
    """Corporation map view with buildings - DEBUG VERSION"""
    from .models import Corporation, Building
    import json
    import math
    import logging
    
    # Set up logging
    logger = logging.getLogger(__name__)
    
    corporations = Corporation.objects.all()
    
    if corporation_id:
        selected_corp = get_object_or_404(Corporation, id=corporation_id)
        buildings = Building.objects.filter(corporation=selected_corp)
    else:
        selected_corp = None
        buildings = Building.objects.all()
    
    # DEBUG: Log building count
    logger.info(f"Found {buildings.count()} buildings for corporation {selected_corp.name if selected_corp else 'All'}")
    
    # Function to convert Web Mercator to WGS84
    def web_mercator_to_wgs84(x, y):
        lon = (x / 20037508.34) * 180
        lat = (y / 20037508.34) * 180
        lat = 180 / math.pi * (2 * math.atan(math.exp(lat * math.pi / 180)) - math.pi / 2)
        return [lon, lat]
    
    def convert_coords(coords):
        if isinstance(coords[0], list):
            return [convert_coords(c) for c in coords]
        else:
            return web_mercator_to_wgs84(coords[0], coords[1])
    
    # Build GeoJSON with converted coordinates
    features = []
    for building in buildings:
        if building.geometry:
            try:
                geom_json = json.loads(building.geometry.geojson)
                
                # DEBUG: Log first building
                if len(features) == 0:
                    logger.info(f"First building geometry: {geom_json}")
                    logger.info(f"First building SRID: {building.geometry.srid}")
                
                # Check if coordinates are in Web Mercator (large numbers)
                is_web_mercator = False
                try:
                    test_coord = geom_json['coordinates'][0][0]
                    if len(test_coord) >= 2 and test_coord[0] > 1000000:
                        is_web_mercator = True
                except:
                    pass
                
                # DEBUG: Log if conversion is needed
                if is_web_mercator:
                    logger.info(f"Converting building {building.id} from Web Mercator")
                    if geom_json['type'] == 'Polygon':
                        geom_json['coordinates'] = convert_coords(geom_json['coordinates'])
                    elif geom_json['type'] == 'MultiPolygon':
                        geom_json['coordinates'] = [convert_coords(poly) for poly in geom_json['coordinates']]
                else:
                    logger.info(f"Building {building.id} is already in WGS84")
                
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
                    }
                })
            except Exception as e:
                logger.error(f"Error processing building {building.id}: {e}")
                continue
    
    # DEBUG: Log feature count
    logger.info(f"Created {len(features)} features for map")
    
    buildings_geojson = {
        'type': 'FeatureCollection',
        'features': features
    }
    
    # DEBUG: Log first feature
    if features:
        logger.info(f"First feature: {features[0]}")
    
    context = {
        'selected_corp': selected_corp,
        'building_count': buildings.count(),
        'buildings_geojson': json.dumps(buildings_geojson),
        'geojson_data': '{"type":"FeatureCollection","features":[]}',
        'bounds': None,
    }
    
    return render(request, 'corporation/map.html', context)

# ============================================
# UPLOAD FUNCTION - THE MAIN FIX
# ============================================

@login_required
@csrf_exempt
def upload_corporation_geojson(request):
    """Upload GeoJSON - Fix coordinate structure and close polygons"""
    import json
    import uuid
    import math
    from django.contrib.gis.geos import GEOSGeometry
    
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
        
        # Function to convert Web Mercator to WGS84
        def web_mercator_to_wgs84(x, y):
            lon = (x / 20037508.34) * 180
            lat = (y / 20037508.34) * 180
            lat = 180 / math.pi * (2 * math.atan(math.exp(lat * math.pi / 180)) - math.pi / 2)
            return [lon, lat]
        
        def convert_coords(coords):
            if isinstance(coords[0], list):
                return [convert_coords(c) for c in coords]
            else:
                return web_mercator_to_wgs84(coords[0], coords[1])
        
        def flatten_and_close_polygon(coords):
            """Extract the actual coordinate list and close it"""
            # Handle different nesting levels
            # The coordinates might be like:
            # - [[[x1,y1], [x2,y2], ...]]  (MultiPolygon/Polygon with extra nesting)
            # - [[x1,y1], [x2,y2], ...]     (Polygon)
            # - [x1,y1]                     (Single coordinate)
            
            # Get the actual points
            points = coords
            while points and isinstance(points[0], list) and len(points[0]) == 2 and not isinstance(points[0][0], list):
                # Already in correct format [[x1,y1], [x2,y2]]
                break
            while points and isinstance(points[0], list) and isinstance(points[0][0], list):
                # Too nested, go one level deeper
                points = points[0]
            
            # If it's still nested, keep going
            while points and isinstance(points[0], list) and isinstance(points[0][0], list):
                points = points[0]
            
            # Now points should be [[x1,y1], [x2,y2], ...]
            # Make sure each point is a list of 2 numbers
            clean_points = []
            for p in points:
                if isinstance(p, list) and len(p) >= 2:
                    clean_points.append([float(p[0]), float(p[1])])
                else:
                    clean_points.append([float(p), float(p[0])] if len(str(p).split()) > 1 else [0, 0])
            
            # Close the polygon if needed
            if clean_points and clean_points[0] != clean_points[-1]:
                clean_points.append(clean_points[0][:])
            
            return clean_points
        
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
                
                # Flatten and close the polygon
                clean_points = flatten_and_close_polygon(coords)
                
                if len(clean_points) < 3:
                    error_count += 1
                    error_messages.append(f"Feature {i}: Not enough points")
                    continue
                
                # Check if coordinates are in Web Mercator and convert
                is_web_mercator = False
                try:
                    if len(clean_points) > 0 and len(clean_points[0]) >= 2:
                        if clean_points[0][0] > 1000000:
                            is_web_mercator = True
                except:
                    pass
                
                if is_web_mercator:
                    converted_coords = convert_coords(clean_points)
                else:
                    converted_coords = clean_points
                
                # Create proper GeoJSON structure
                geom_dict = {
                    'type': 'Polygon',
                    'coordinates': [converted_coords]
                }
                
                # Generate unique GIS ID
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
                geom_json_str = json.dumps(geom_dict)
                geom = GEOSGeometry(geom_json_str, srid=4326)
                
                Building.objects.create(
                    corporation=corporation,
                    gis_id=gis_id,
                    building_number=properties.get('building_number') or properties.get('number') or gis_id,
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
        return JsonResponse({'error': str(e)}, status=500)
    

# ============================================
# BUILDINGS GEOJSON API - FOR MAP DISPLAY
# ============================================

@login_required
def buildings_geojson(request, corporation_id=None):
    """API endpoint - Return geometry converted to WGS84 for map"""
    import json
    import math
    
    def web_mercator_to_wgs84(x, y):
        lon = (x / 20037508.34) * 180
        lat = (y / 20037508.34) * 180
        lat = 180 / math.pi * (2 * math.atan(math.exp(lat * math.pi / 180)) - math.pi / 2)
        return [lon, lat]
    
    def convert_coords(coords):
        if isinstance(coords[0], list):
            return [convert_coords(c) for c in coords]
        else:
            return web_mercator_to_wgs84(coords[0], coords[1])
    
    if corporation_id:
        buildings = Building.objects.filter(corporation_id=corporation_id, geometry__isnull=False)
    else:
        buildings = Building.objects.filter(geometry__isnull=False)
    
    features = []
    for building in buildings:
        if building.geometry:
            try:
                geom_json = json.loads(building.geometry.geojson)
                
                # Check if coordinates are in Web Mercator
                is_web_mercator = False
                try:
                    test_coord = geom_json['coordinates'][0][0]
                    if len(test_coord) >= 2 and test_coord[0] > 1000000:
                        is_web_mercator = True
                except:
                    pass
                
                # Convert if in Web Mercator
                if is_web_mercator:
                    if geom_json['type'] == 'Polygon':
                        geom_json['coordinates'] = convert_coords(geom_json['coordinates'])
                    elif geom_json['type'] == 'MultiPolygon':
                        geom_json['coordinates'] = [convert_coords(poly) for poly in geom_json['coordinates']]
                
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

# ============================================
# API - GET CORPORATION BUILDINGS GEOJSON
# ============================================

@login_required
def get_corporation_buildings_geojson(request, corporation_id):
    """API to get buildings GeoJSON for a corporation"""
    import json
    from .models import Corporation, Building
    
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
                    }
                })
            except Exception as e:
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
    import json
    from django.http import JsonResponse
    
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
    from django.http import JsonResponse
    import json
    
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
    from django.http import JsonResponse
    from .models import Building
    import json
    
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