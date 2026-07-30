import json
import os
from django.core.management.base import BaseCommand
from django.contrib.gis.geos import GEOSGeometry, MultiPolygon
from django.contrib.auth import get_user_model
from Nit.models import Building

User = get_user_model()

class Command(BaseCommand):
    help = 'Import building data from GeoJSON file'

    def add_arguments(self, parser):
        parser.add_argument(
            '--file',
            type=str,
            required=True,
            help='Path to the GeoJSON file'
        )
        parser.add_argument(
            '--user',
            type=str,
            default=None,
            help='Username to set as creator'
        )

    def handle(self, *args, **options):
        file_path = options['file']
        username = options['user']
        
        # Get user if provided
        user = None
        if username:
            try:
                user = User.objects.get(username=username)
            except User.DoesNotExist:
                self.stdout.write(self.style.WARNING(f"User '{username}' not found. Proceeding without creator."))
        
        # Check if file exists
        if not os.path.exists(file_path):
            self.stdout.write(self.style.ERROR(f"File not found: {file_path}"))
            return
        
        # Load and parse GeoJSON
        try:
            with open(file_path, 'r') as f:
                data = json.load(f)
        except json.JSONDecodeError:
            self.stdout.write(self.style.ERROR("Invalid JSON file"))
            return
        
        # Count features
        features = data.get('features', [])
        total = len(features)
        self.stdout.write(f"Found {total} building features")
        
        created_count = 0
        updated_count = 0
        error_count = 0
        
        for i, feature in enumerate(features, 1):
            try:
                properties = feature.get('properties', {})
                geometry = feature.get('geometry')
                
                if not geometry:
                    self.stdout.write(self.style.WARNING(f"Feature {i}: No geometry found"))
                    error_count += 1
                    continue
                
                # Get GIS_ID
                gis_id = properties.get('GIS_ID')
                if not gis_id:
                    self.stdout.write(self.style.WARNING(f"Feature {i}: No GIS_ID found"))
                    error_count += 1
                    continue
                
                # Get sqft
                sqft = properties.get('sqft', 0)
                
                # Convert geometry to GEOS
                try:
                    geom = GEOSGeometry(json.dumps(geometry), srid=3857)
                    # Ensure it's a MultiPolygon
                    if geom.geom_type != 'MultiPolygon':
                        geom = MultiPolygon(geom)
                except Exception as e:
                    self.stdout.write(self.style.WARNING(f"Feature {i}: Invalid geometry - {str(e)}"))
                    error_count += 1
                    continue
                
                # Create or update building
                building, created = Building.objects.update_or_create(
                    gis_id=gis_id,
                    defaults={
                        'geometry': geom,
                        'sqft': sqft,
                        'created_by': user,
                    }
                )
                
                if created:
                    created_count += 1
                else:
                    updated_count += 1
                
                # Progress indicator
                if i % 100 == 0:
                    self.stdout.write(f"Processed {i}/{total} features...")
                    
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Feature {i}: Error - {str(e)}"))
                error_count += 1
        
        # Summary
        self.stdout.write("\n" + "="*50)
        self.stdout.write(self.style.SUCCESS(f"Import complete!"))
        self.stdout.write(f"  ✅ Created: {created_count}")
        self.stdout.write(f"  🔄 Updated: {updated_count}")
        self.stdout.write(f"  ❌ Errors: {error_count}")
        self.stdout.write(f"  📊 Total: {created_count + updated_count + error_count}")