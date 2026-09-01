from rest_framework import serializers
from .models import Building, Corporation
from django.contrib.gis.geos import GEOSGeometry
import json

class BuildingSerializer(serializers.ModelSerializer):
    geometry_json = serializers.SerializerMethodField()
    corporation_name = serializers.SerializerMethodField()
    
    class Meta:
        model = Building
        fields = [
            'id', 'gis_id', 'building_name', 'building_number', 
            'geometry', 'geometry_json', 'area',
            'building_type', 'floors',
            'owner_name', 'owner_contact',
            'corporation', 'corporation_name', 'ward', 'city',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_geometry_json(self, obj):
        if obj.geometry:
            try:
                return json.loads(obj.geometry.geojson)
            except:
                return None
        return None
    
    def get_corporation_name(self, obj):
        if obj.corporation:
            return obj.corporation.name
        return None

class BuildingCreateSerializer(serializers.ModelSerializer):
    geometry_coords = serializers.ListField(write_only=True, required=False)
    
    class Meta:
        model = Building
        fields = [
            'gis_id', 'building_name', 'building_number',
            'geometry_coords', 'area',
            'building_type', 'floors',
            'owner_name', 'owner_contact',
            'corporation', 'ward', 'city'
        ]
    
    def create(self, validated_data):
        coords = validated_data.pop('geometry_coords', None)
        if coords and len(coords) >= 3:
            try:
                # Create polygon from coordinates
                points = [(c[0], c[1]) for c in coords]
                if points[0] != points[-1]:
                    points.append(points[0])  # Close polygon
                polygon = GEOSGeometry({
                    "type": "Polygon",
                    "coordinates": [points]
                }, srid=4326)
                validated_data['geometry'] = polygon
                
                # Calculate area if not provided
                if not validated_data.get('area'):
                    validated_data['area'] = polygon.area * 10890
            except Exception as e:
                raise serializers.ValidationError(f"Invalid geometry: {str(e)}")
        
        return super().create(validated_data)
    
    def update(self, instance, validated_data):
        coords = validated_data.pop('geometry_coords', None)
        if coords and len(coords) >= 3:
            try:
                points = [(c[0], c[1]) for c in coords]
                if points[0] != points[-1]:
                    points.append(points[0])
                polygon = GEOSGeometry({
                    "type": "Polygon",
                    "coordinates": [points]
                }, srid=4326)
                instance.geometry = polygon
                
                if not validated_data.get('area'):
                    instance.area = polygon.area * 10890
            except Exception as e:
                raise serializers.ValidationError(f"Invalid geometry: {str(e)}")
        
        return super().update(instance, validated_data)