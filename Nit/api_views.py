import time
import json
import logging
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Sum, Count
from django.contrib.gis.geos import GEOSGeometry
from .models import Building, Corporation

logger = logging.getLogger(__name__)

@csrf_exempt
def buildings_api(request):
    """API endpoint for buildings - GET all, POST new"""
    
    if request.method == 'GET':
        # Get all buildings as GeoJSON
        buildings = Building.objects.all().select_related('corporation')
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
                except Exception as e:
                    logger.error(f"Error: {e}")
                    continue
        
        return JsonResponse({
            "type": "FeatureCollection",
            "features": features
        }, safe=False)
    
    elif request.method == 'POST':
        try:
            data = json.loads(request.body)
            
            # Get coordinates
            coords = data.get('geometry_coords')
            if not coords:
                return JsonResponse({'error': 'Geometry coordinates required'}, status=400)
            
            # Create polygon
            points = [(c[0], c[1]) for c in coords]
            if points[0] != points[-1]:
                points.append(points[0])
            
            polygon = GEOSGeometry({
                "type": "Polygon",
                "coordinates": [points]
            }, srid=4326)
            
            # Get corporation
            corporation_id = data.get('corporation')
            corporation = None
            if corporation_id:
                try:
                    corporation = Corporation.objects.get(id=corporation_id)
                except Corporation.DoesNotExist:
                    pass
            
            # Calculate area
            area = polygon.area * 10890  # Approximate conversion
            
            # Create building
            building = Building.objects.create(
                gis_id=data.get('gis_id', f"B{int(time.time())}"),
                building_name=data.get('building_name', ''),
                building_number=data.get('building_number', ''),
                geometry=polygon,
                area=data.get('area', area),
                building_type=data.get('building_type', 'OTHER'),
                floors=data.get('floors', 0),
                owner_name=data.get('owner_name', ''),
                owner_contact=data.get('owner_contact', ''),
                corporation=corporation,
                ward=data.get('ward', ''),
                city=data.get('city', 'New Delhi'),
            )
            
            return JsonResponse({
                'status': 'success',
                'id': building.id,
                'message': 'Building created successfully'
            }, status=201)
            
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)
    
    return JsonResponse({'error': 'Method not allowed'}, status=405)


@csrf_exempt
def building_detail_api(request, building_id):
    """API endpoint for single building - GET, PUT, DELETE"""
    
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
        
        if building.geometry and hasattr(building.geometry, 'geojson'):
            data['geometry'] = json.loads(building.geometry.geojson)
        
        return JsonResponse(data)
    
    elif request.method == 'PUT':
        try:
            data = json.loads(request.body)
            
            # Update fields
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
            
            # Update corporation
            corporation_id = data.get('corporation')
            if corporation_id:
                try:
                    building.corporation = Corporation.objects.get(id=corporation_id)
                except Corporation.DoesNotExist:
                    pass
            else:
                building.corporation = None
            
            # Update geometry
            coords = data.get('geometry_coords')
            if coords:
                points = [(c[0], c[1]) for c in coords]
                if points[0] != points[-1]:
                    points.append(points[0])
                
                polygon = GEOSGeometry({
                    "type": "Polygon",
                    "coordinates": [points]
                }, srid=4326)
                building.geometry = polygon
                building.area = polygon.area * 10890
            
            building.save()
            
            return JsonResponse({
                'status': 'success',
                'message': 'Building updated successfully'
            })
            
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)
    
    elif request.method == 'DELETE':
        try:
            building.delete()
            return JsonResponse({
                'status': 'success',
                'message': 'Building deleted successfully'
            })
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)
    
    return JsonResponse({'error': 'Method not allowed'}, status=405)


@csrf_exempt
def map_stats_api(request):
    """Get map statistics"""
    try:
        total_buildings = Building.objects.count()
        total_area = Building.objects.aggregate(Sum('area'))['area__sum'] or 0
        
        corporation_stats = []
        for corp in Corporation.objects.all():
            corp_buildings = corp.buildings.all()
            corporation_stats.append({
                'id': corp.id,
                'name': corp.name,
                'building_count': corp_buildings.count(),
                'total_area': corp_buildings.aggregate(Sum('area'))['area__sum'] or 0
            })
        
        return JsonResponse({
            'total_buildings': total_buildings,
            'total_area': total_area,
            'corporations': corporation_stats
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)