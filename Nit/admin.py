from django.contrib import admin
from .models import Building, Corporation

@admin.register(Corporation)
class CorporationAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'status', 'total_buildings', 'total_area', 'created_at']
    list_filter = ['status', 'created_at']
    search_fields = ['name', 'code', 'description']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'code', 'description', 'status')
        }),
        ('Statistics', {
            'fields': ('total_area', 'total_buildings', 'total_surveys', 'coverage_percentage')
        }),
        ('GIS Data', {
            'fields': ('geometry', 'centroid', 'geojson_file')
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at', 'created_by'),
            'classes': ('collapse',)
        }),
    )


@admin.register(Building)
class BuildingAdmin(admin.ModelAdmin):
    list_display = ['building_number', 'building_name', 'building_type', 'area', 'owner_name', 'city', 'corporation']
    list_filter = ['building_type', 'city', 'corporation']
    search_fields = ['building_number', 'building_name', 'owner_name', 'address', 'city', 'gis_id']
    readonly_fields = ['gis_id']
    
    fieldsets = (
        ('Identification', {
            'fields': ('gis_id', 'building_number', 'building_name')
        }),
        ('Location', {
            'fields': ('address', 'city', 'state', 'pincode')
        }),
        ('GIS Data', {
            'fields': ('geometry',)
        }),
        ('Building Details', {
            'fields': ('building_type', 'area', 'floors', 'year_built')
        }),
        ('Ownership', {
            'fields': ('owner_name', 'owner_contact')
        }),
        ('Corporation', {
            'fields': ('corporation',)
        }),
    )