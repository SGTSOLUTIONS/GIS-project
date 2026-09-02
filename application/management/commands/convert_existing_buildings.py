from django.core.management.base import BaseCommand
from application.models import Building  # Make sure this path is correct

class Command(BaseCommand):
    help = 'Convert building geometries to WGS84 (EPSG:4326) for map display'

    def handle(self, *args, **options):
        count = 0
        for building in Building.objects.all():
            if building.geometry:
                try:
                    # Step 1: Tell Django the current numbers are in Web Mercator (meters)
                    building.geometry.srid = 3857
                    
                    # Step 2: Transform them to WGS84 (degrees) so the map can read them
                    building.geometry.transform(4326)
                    
                    # Step 3: Save it
                    building.save()
                    count += 1
                    self.stdout.write(self.style.SUCCESS(f'Fixed building {building.id}: {building.geometry.coords}'))
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f'Error on building {building.id}: {e}'))

        self.stdout.write(self.style.SUCCESS(f'Done. Converted {count} buildings for the map.'))