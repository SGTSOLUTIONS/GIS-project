# fix_geojson.py - Updated to convert coordinates
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

file_path = r'C:\begginner django\application\media\corporations\geojson\newjson.geojson'

with open(file_path, 'r') as f:
    data = json.load(f)

for feature in data['features']:
    gis_id = feature['properties'].get('GIS_ID', '')
    sqft = feature['properties'].get('sqft', 0)
    
    # Convert MultiPolygon to Polygon and convert coordinates
    if feature['geometry']['type'] == 'MultiPolygon':
        coords = feature['geometry']['coordinates'][0]
    else:
        coords = feature['geometry']['coordinates']
    
    # Convert coordinates from Web Mercator to WGS84
    converted_coords = convert_coords(coords)
    
    feature['properties'] = {
        'gis_id': f"B-{gis_id.zfill(4)}",
        'building_number': f"B-{gis_id.zfill(4)}",
        'building_name': f"Building {gis_id}",
        'area': float(sqft),
        'building_type': 'residential',
        'floors': 1,
        'owner_name': 'Unknown',
        'address': '',
        'city': 'New Delhi',
        'state': 'Delhi',
        'pincode': '',
    }
    
    feature['geometry'] = {
        'type': 'Polygon',
        'coordinates': converted_coords
    }

if 'crs' in data:
    del data['crs']

output_path = r'C:\begginner django\application\media\corporations\geojson\newjson_converted.geojson'
with open(output_path, 'w') as f:
    json.dump(data, f, indent=2)

print(f"✅ Saved to: {output_path}")