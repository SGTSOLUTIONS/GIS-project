from django.contrib import admin
from .models import Building, Corporation

@admin.register(Corporation)
class CorporationAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'code', 'created_at']
    search_fields = ['name', 'code']
    readonly_fields = ['created_at', 'updated_at']

@admin.register(Building)
class BuildingAdmin(admin.ModelAdmin):
    list_display = ['id', 'gis_id', 'building_name', 'building_type', 'corporation', 'area', 'created_at']
    list_filter = ['building_type', 'corporation', 'city']
    search_fields = ['gis_id', 'building_name', 'building_number', 'owner_name']
    readonly_fields = ['created_at', 'updated_at']
    
    def get_geometry_display(self, obj):
        if obj.geometry:
            return f"Polygon at ({obj.geometry.centroid.x:.6f}, {obj.geometry.centroid.y:.6f})"
        return "No geometry"
    get_geometry_display.short_description = 'Geometry Location'
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('gis_id', 'building_name', 'building_number')
        }),
        ('Location & Geometry', {
            'fields': ('geometry', 'corporation', 'ward', 'city', 'state', 'pincode')
        }),
        ('Building Details', {
            'fields': ('building_type', 'floors', 'area')
        }),
        ('Owner Information', {
            'fields': ('owner_name', 'owner_contact')
        }),
        ('Metadata', {
            'fields': ('is_active', 'created_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )