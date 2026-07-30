import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'application.settings')
django.setup()
from django.db import connection
print("Starting database reset...")
with connection.cursor() as cursor:
    try:
        cursor.execute("SET FOREIGN_KEY_CHECKS = 0")
        cursor.execute("SHOW TABLES")
        tables = cursor.fetchall()
        if not tables:
            print("No tables found.")
        else:
            for table in tables:
                try:
                    cursor.execute(f"DROP TABLE IF EXISTS {table[0]}")
                    print(f"Dropped {table[0]}")
                except Exception as e:
                    print(f"Error dropping {table[0]}: {e}")
        cursor.execute("SET FOREIGN_KEY_CHECKS = 1")
        print("All tables dropped successfully!")
    except Exception as e:
        print(f"Error: {e}")
print("Database reset complete!")