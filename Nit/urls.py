# Nit/urls.py - CLEAN VERSION (remove duplicates)
from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from . import views
from . import views_geometry
from .views_geometry import upload_corporation_geojson

urlpatterns = [

    # ============================================
    # ADMIN LOGIN
    # ============================================
    path('admin/login/', views.admin_login_view, name='admin_login'),
    path('admin/logout/', views.admin_logout_view, name='admin_logout'),

    # ============================================
    # AUTHENTICATION (Using custom views)
    # ============================================
    path('', views.login_view, name='login'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('register/', views.register_view, name='register'),

    # ============================================
    # FORGET PASSWORD
    # ============================================
    path('forget-password/', views.forget_password, name='forget_password'),
    path('forget-email/', views.forget_email, name='forget_email'),
    path('password/reset/<str:token>/', views.reset_password_form, name='reset_password_form'),
    path('password/reset/', views.reset_password, name='reset_password'),
    
    # ============================================
    # HOME & COMMON PAGES
    # ============================================
    path('home/', views.home_view, name='home'),
    path('about/', views.about_view, name='about'),
    path('wards/', views.wards_view, name='wards'),
    path('profile/', views.profile_view, name='profile'),
    
    # ============================================
    # PROPERTY PAGES
    # ============================================
    path('property/', views.property_view, name='property'),
    path('residential/', views.residential_view, name='residential'),
    path('commercial/', views.commercial_view, name='commercial'),
    path('industrial/', views.industrial_view, name='industrial'),
    path('gis/', views.gis_view, name='gis'),
    path('reports/', views.reports_view, name='reports'),
    
    # ============================================
    # MAP VIEWS - KEEP ONLY THESE
    # ============================================
    path('map/', views.map_view, name='map_view'),
    path('map/corporation/<int:corporation_id>/', views.map_view, name='corporation_map'),
    path('buildings-geojson/corporation/<int:corporation_id>/', views.buildings_geojson, name='corporation_buildings_geojson'),
    path('buildings-geojson/', views.buildings_geojson, name='buildings_geojson'),
    
    # ============================================
    # DASHBOARD REDIRECT
    # ============================================
    path('dashboard/', views.dashboard_redirect, name='dashboard'),

    # ============================================
    # ADMIN ROUTES
    # ============================================
    path('admin-dashboard/', views.admin_dashboard, name='admin_dashboard'),
    
    # SURVEYOR MANAGEMENT
    path('admin-surveyors/', views.surveyors_list, name='admin_surveyors'),
    path('admin-surveyors/create/', views.store_surveyor, name='admin_store_surveyor'),
    path('admin-surveyors/edit/<int:id>/', views.surveyor_update, name='admin_surveyor_update'),
    path('admin-surveyors/delete/<int:id>/', views.surveyor_destroy, name='admin_surveyor_destroy'),
    
    # Admin Reports & Export
    path('admin-reports/', views.admin_reports, name='admin_reports'),
    path('admin-export/', views.admin_export, name='admin_export'),
    
    # CBE Management
    path('admin-cbe/', views.cbe_list, name='admin_cbe'),
    path('admin-cbe/store/', views.cbe_store, name='admin_cbe_store'),
    path('admin-cbe/update/', views.cbe_update, name='admin_cbe_update'),
    path('admin-cbe/delete/<int:id>/', views.cbe_destroy, name='admin_cbe_destroy'),
    
    # Data Store
    path('admin/data-store/', views.data_store, name='admin_data_store'),
    
    # Export Functions
    path('admin/export/usage-variation/<int:data_id>/', views.usage_variation_export, name='admin_usage_variation'),
    path('admin/export/area-variation/<int:data_id>/', views.area_variation_export, name='admin_area_variation'),
    path('admin/export/usage-area-variation/<int:data_id>/', views.usage_and_area_variation_export, name='admin_usage_area_variation'),
    path('admin/export/polygon/<int:data_id>/', views.polygon_download, name='admin_polygon_download'),
    path('admin/export/point/<int:data_id>/', views.point_download, name='admin_point_download'),
    path('admin/export/road/<int:data_id>/', views.road_download, name='admin_road_download'),
    path('admin/export/streetwise/<int:data_id>/', views.download_streetwise, name='admin_streetwise'),
    path('admin/export/missing-bill/<int:data_id>/', views.download_missing_bill, name='admin_missing_bill'),
    path('admin/export/surveyors-count/<int:data_id>/', views.surveyors_count_export, name='admin_surveyors_count'),
    path('admin/export/point-data/<int:data_id>/', views.download_point_data, name='admin_point_data'),
    path('admin/export/building-data/<int:data_id>/', views.download_building_data, name='admin_building_data'),
    
    # Search & Update
    path('admin/search-gisid/', views.search_gisid, name='admin_search_gisid'),
    path('admin/search-building-gisid/', views.search_building_gisid, name='admin_search_building_gisid'),
    path('admin/update-building-data/', views.update_building_data, name='admin_update_building_data'),
    path('admin/delete-building-data/', views.delete_building_data, name='admin_delete_building_data'),
    path('admin/update-assessment/', views.update_assessment_data, name='admin_update_assessment'),
    path('admin/delete-assessment/', views.delete_assessment_data, name='admin_delete_assessment'),
    path('admin/replace-gisid/', views.replace_gisid, name='admin_replace_gisid'),
    path('admin/bulk-import/', views.bulk_import_assessment, name='bulk_import'),
    
    # ============================================
    # ADMIN GIS ROUTES
    # ============================================
    path('admin/gis-features/', views.admin_gis_features, name='admin_gis_features'),
    path('admin/get-gis-data/', views.admin_get_gis_data, name='admin_get_gis_data'),
    
    # ============================================
    # SURVEYOR GIS DRAWING ROUTES
    # ============================================
    path('surveyor/add-polygon/', views.add_polygon_feature, name='add_polygon'),
    path('surveyor/add-line/', views.add_line_feature, name='add_line'),
    path('surveyor/merge-polygon/', views.merge_polygon, name='merge_polygon'),
    path('surveyor/delete-polygon/', views.delete_polygon_feature, name='delete_polygon'),
    path('surveyor/update-roadname/', views.update_road_name, name='update_road_name'),
    path('surveyor/split-polygon/', views.split_polygon, name='split_polygon'),
    path('surveyor/get-gis-features/', views.get_gis_features, name='get_gis_features'),
    
    # ============================================
    # SURVEYOR ROUTES
    # ============================================
    path('surveyor-dashboard/', views.surveyor_dashboard, name='surveyor_dashboard'),
    path('surveyor-find-gisid/', views.find_gisid, name='surveyor_find_gisid'),
    path('surveyor-upload-assessment/', views.upload_assessment_data, name='surveyor_upload_assessment'),
    path('surveyor-attendance-in/', views.attendance_in, name='surveyor_attendance_in'),
    path('surveyor-attendance-out/', views.attendance_out, name='surveyor_attendance_out'),
    
    # ============================================
    # CBE & TAX COLLECTOR
    # ============================================
    path('cbe-dashboard/', views.cbe_dashboard, name='cbe_dashboard'),
    path('taxcollector-dashboard/', views.taxcollector_dashboard, name='taxcollector_dashboard'),
    
    # ============================================
    # API ROUTES
    # ============================================
    path('api/surveys/', views.api_surveys, name='api_surveys'),
    path('api/wards/', views.api_wards, name='api_wards'),
    path('api/property/<str:gis_id>/', views.api_property_detail, name='api_property_detail'),
    
    # ============================================
    # SEARCH
    # ============================================
    path('advanced-search/', views.advanced_search, name='advanced_search'),

    # ============================================
    # GEOMETRY EDITOR ROUTES
    # ============================================
    path('geometry-editor/<int:data_id>/', views_geometry.geometry_editor_view, name='geometry_editor'),
    path('geometry-import/', views_geometry.shapefile_import_view, name='shapefile_import'),
    path('geometry-export/<int:data_id>/', views_geometry.export_shapefile_view, name='export_shapefile'),
    
    # Geometry API Routes
    path('api/geometry/save/', views_geometry.api_save_geometry, name='api_save_geometry'),
    path('api/geometry/<int:data_id>/<str:gisid>/', views_geometry.api_get_geometry, name='api_get_geometry'),
    path('api/geometry/all/<int:data_id>/', views_geometry.api_get_all_features, name='api_get_all_features'),
    path('api/geometry/delete/<int:data_id>/<str:gisid>/', views_geometry.api_delete_feature, name='api_delete_feature'),
    path('api/geometry/history/<int:data_id>/', views_geometry.api_edit_history, name='api_edit_history'),

    # ============================================
    # CORPORATION ROUTES
    # ============================================
    path('corporation/dashboard/', views_geometry.corporation_dashboard, name='corporation_dashboard'),
    path('corporation/list/', views_geometry.corporation_list, name='corporation_list'),
    path('corporation/map/', views_geometry.corporation_map, name='corporation_map'),
    path('corporation/map/<int:corporation_id>/', views_geometry.corporation_map, name='corporation_map_detail'),
    path('corporation/upload/', views_geometry.upload_corporation_geojson, name='upload_corporation'),
    path('corporation/delete/<int:corporation_id>/', views_geometry.delete_corporation, name='delete_corporation'),
    path('corporation/details/<int:corporation_id>/', views_geometry.corporation_details, name='corporation_details'),
    path('corporation/update/<int:corporation_id>/', views_geometry.update_corporation, name='update_corporation'),
    path('corporation/map/<int:corporation_id>/', views_geometry.corporation_map, name='corporation_map_detail'),
    path('corporation/<int:corporation_id>/upload-geojson/', upload_corporation_geojson, name='upload_corporation_geojson'),
    path('api/corporation/<int:corporation_id>/buildings-geojson/', views_geometry.get_corporation_buildings_geojson, name='api_corporation_buildings_geojson'),
    path('debug/buildings/', views_geometry.debug_buildings, name='debug_buildings'),
    path('debug/map/', views.map_view, name='debug_map'),
    path('debug/buildings/<int:corporation_id>/', views_geometry.debug_buildings, name='debug_buildings_corp'),
    path('debug/buildings-json/', views_geometry.debug_buildings_json, name='debug_buildings_json'),
    path('debug/buildings-json/<int:corporation_id>/', views_geometry.debug_buildings_json, name='debug_buildings_json_corp'),
    path('test-buildings/', views_geometry.test_buildings, name='test_buildings'),
]

# ============================================
# SERVE STATIC & MEDIA FILES IN DEVELOPMENT
# ============================================
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)