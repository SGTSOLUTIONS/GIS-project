# application/urls.py (Main project urls)
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from Nit import views 

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('Nit.urls')),
    path('api/building-search/', views.api_building_search, name='api_building_search'),
]

# Serve static and media files in development
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)