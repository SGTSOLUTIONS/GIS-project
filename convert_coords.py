import os
import django
import json
import math

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'application.settings')
django.setup()

from Nit.models import Building, Corporation
from django.contrib.gis.geos import GEOSGeometry

def web_mercator_to_wgs84(x, y):
    """Convert Web Mercator to WGS84"""
    lon = (x / 20037508.34) * 180
    lat = (y / 20037508.34) * 180
    lat = 180 / math.pi * (2 * math.atan(math.exp(lat * math.pi / 180)) - math.pi / 2)
    return [lon, lat]

def convert_coords(coords):
    """Recursively convert coordinates"""
    if isinstance(coords[0], list):
        return [convert_coords(c) for c in coords]
    else:
        return web_mercator_to_wgs84(coords[0], coords[1])

print("Converting building coordinates...")

updated = 0
errors = 0

for building in Building.objects.filter(geometry__isnull=False):
    try:
        # Get current geometry as GeoJSON
        geom_json = json.loads(building.geometry.geojson)
        
        # Convert coordinates
        if geom_json['type'] == 'Polygon':
            geom_json['coordinates'] = convert_coords(geom_json['coordinates'])
        elif geom_json['type'] == 'MultiPolygon':
            geom_json['coordinates'] = [convert_coords(poly) for poly in geom_json['coordinates']]
        
        # Convert to WKT and create new geometry
        # Use WKT to avoid transform issues
        from django.contrib.gis.geos import GEOSGeometry
        new_geom = GEOSGeometry(json.dumps(geom_json))
        new_geom.srid = 4326
        
        # Save
        building.geometry = new_geom
        building.save()
        updated += 1
        
        if updated % 100 == 0:
            print(f"✅ Updated {updated} buildings...")
            
    except Exception as e:
        errors += 1
        if errors <= 10:  # Only show first 10 errors
            print(f"❌ Error updating {building.id}: {e}")

print(f"\n✅ Done! Updated {updated} buildings, {errors} errors.")

# Verify first building
first = Building.objects.filter(geometry__isnull=False).first()
if first:
    import json
    geom_json = json.loads(first.geometry.geojson)
    print(f"\nFirst building coordinates (should be around 77, 28):")
    print(f"First coordinate: {geom_json['coordinates'][0][0][:3]}...")