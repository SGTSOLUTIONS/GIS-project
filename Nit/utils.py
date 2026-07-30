# utils.py
import json
import math
from decimal import Decimal
from django.db import connection
from django.db.models import Q
# import pandas as pd  # ❌ Removed from top - only imported when needed
from io import BytesIO
import zipfile
import os
from django.conf import settings


def calculate_polygon_area(coordinates):
    """
    Calculate area of a polygon in square feet
    Similar to Laravel calculatePolygonAreaInSquareFeet
    """
    if not coordinates or not isinstance(coordinates, list) or len(coordinates) == 0:
        return 0
    
    # Handle different coordinate structures
    if isinstance(coordinates[0], list) and len(coordinates[0]) > 0:
        if isinstance(coordinates[0][0], list):
            if len(coordinates[0][0]) == 2:
                points = coordinates[0]
            else:
                points = coordinates[0][0]
        else:
            points = coordinates[0]
    else:
        points = coordinates
    
    num_points = len(points)
    if num_points < 3:
        return 0
    
    area = 0
    for i in range(num_points):
        try:
            x = float(points[i][0])
            y = float(points[i][1])
            next_i = (i + 1) % num_points
            x_next = float(points[next_i][0])
            y_next = float(points[next_i][1])
            area += (x * y_next) - (y * x_next)
        except (ValueError, IndexError, TypeError):
            continue
    
    area = abs(area) / 2
    # Convert to square feet (1 square meter = 10.7639 sq ft)
    return area * 10.7639


def calculate_midpoint(coordinates):
    """
    Calculate midpoint of polygon coordinates
    Similar to Laravel calculateDataMidpoint
    """
    if not coordinates or not isinstance(coordinates, list) or len(coordinates) == 0:
        return [0, 0]
    
    # Handle nested coordinates
    if isinstance(coordinates[0], list) and len(coordinates[0]) > 0:
        if isinstance(coordinates[0][0], list):
            points = coordinates[0]
        else:
            points = coordinates
    else:
        points = coordinates
    
    total_points = len(points)
    if total_points == 0:
        return [0, 0]
    
    mid_lat = sum(p[0] for p in points) / total_points
    mid_lng = sum(p[1] for p in points) / total_points
    
    return [mid_lat, mid_lng]


def create_dynamic_tables(data_instance):
    """
    Create dynamic tables for GIS data
    Similar to Laravel table creation
    """
    table_prefix = f"{data_instance.corporation_name}_{data_instance.zone}_{data_instance.ward}_"
    
    # Table schemas
    tables = {
        'polygons': """
            CREATE TABLE IF NOT EXISTS `{prefix}polygons` (
                id INT AUTO_INCREMENT PRIMARY KEY,
                gisid VARCHAR(255),
                type VARCHAR(50),
                coordinates JSON,
                created_at DATETIME,
                updated_at DATETIME
            )
        """,
        'points': """
            CREATE TABLE IF NOT EXISTS `{prefix}points` (
                id INT AUTO_INCREMENT PRIMARY KEY,
                gisid VARCHAR(255),
                type VARCHAR(50),
                coordinates JSON,
                created_at DATETIME,
                updated_at DATETIME
            )
        """,
        'lines': """
            CREATE TABLE IF NOT EXISTS `{prefix}lines` (
                id INT AUTO_INCREMENT PRIMARY KEY,
                gisid VARCHAR(255),
                type VARCHAR(50),
                coordinates JSON,
                created_at DATETIME,
                updated_at DATETIME
            )
        """,
        'mis': """
            CREATE TABLE IF NOT EXISTS `{prefix}mis` (
                id INT AUTO_INCREMENT PRIMARY KEY,
                assessment VARCHAR(255),
                old_assessment VARCHAR(255),
                number_floor VARCHAR(255),
                new_address VARCHAR(255),
                building_usage VARCHAR(255),
                construction_type VARCHAR(255),
                road_name VARCHAR(255),
                phone VARCHAR(255),
                building_type VARCHAR(255),
                ward VARCHAR(255),
                owner_name VARCHAR(255),
                old_door_no VARCHAR(255),
                new_door_no VARCHAR(255),
                plot_area VARCHAR(255),
                watertax VARCHAR(255),
                halfyeartax VARCHAR(255),
                balance VARCHAR(255),
                created_at DATETIME,
                updated_at DATETIME
            )
        """,
        'pointdata': """
            CREATE TABLE IF NOT EXISTS `{prefix}pointdata` (
                id INT AUTO_INCREMENT PRIMARY KEY,
                data_id VARCHAR(255),
                point_gisid VARCHAR(255),
                worker_name VARCHAR(255),
                assessment VARCHAR(255),
                old_assessment VARCHAR(255),
                owner_name VARCHAR(255),
                present_owner_name VARCHAR(255),
                eb VARCHAR(255),
                floor VARCHAR(255),
                bill_usage VARCHAR(255),
                aadhar_no VARCHAR(255),
                ration_no VARCHAR(255),
                phone_number VARCHAR(255),
                shop_floor VARCHAR(255),
                shop_name VARCHAR(255),
                shop_owner_name VARCHAR(255),
                old_door_no VARCHAR(255),
                new_door_no VARCHAR(255),
                shop_category VARCHAR(255),
                shop_mobile VARCHAR(255),
                license VARCHAR(255),
                professional_tax VARCHAR(255),
                gst VARCHAR(255),
                number_of_employee VARCHAR(255),
                trade_income VARCHAR(255),
                establishment_remarks TEXT,
                remarks TEXT,
                plot_area VARCHAR(255),
                water_tax VARCHAR(255),
                halfyeartax VARCHAR(255),
                balance VARCHAR(255),
                building_data_id VARCHAR(255),
                qc_area VARCHAR(255),
                qc_usage VARCHAR(255),
                qc_name VARCHAR(255),
                qc_remarks TEXT,
                otsarea VARCHAR(255),
                created_at DATETIME,
                updated_at DATETIME
            )
        """,
        'buildingdata': """
            CREATE TABLE IF NOT EXISTS `{prefix}buildingdata` (
                id INT AUTO_INCREMENT PRIMARY KEY,
                data_id VARCHAR(255),
                gisid VARCHAR(255),
                number_bill VARCHAR(255),
                number_shop VARCHAR(255),
                number_floor VARCHAR(255),
                new_address VARCHAR(255),
                liftroom VARCHAR(255),
                headroom VARCHAR(255),
                overhead_tank VARCHAR(255),
                percentage VARCHAR(255),
                building_name VARCHAR(255),
                building_usage VARCHAR(255),
                construction_type VARCHAR(255),
                road_name VARCHAR(255),
                ugd VARCHAR(255),
                rainwater_harvesting VARCHAR(255),
                parking VARCHAR(255),
                ramp VARCHAR(255),
                hoarding VARCHAR(255),
                cctv VARCHAR(255),
                cell_tower VARCHAR(255),
                solar_panel VARCHAR(255),
                basement VARCHAR(255),
                water_connection VARCHAR(255),
                phone VARCHAR(255),
                building_type VARCHAR(255),
                image VARCHAR(255),
                sqfeet VARCHAR(255),
                merge VARCHAR(255),
                split VARCHAR(255),
                worker_name VARCHAR(255),
                remarks TEXT,
                corporationremarks TEXT,
                created_at DATETIME,
                updated_at DATETIME
            )
        """,
        'qc': """
            CREATE TABLE IF NOT EXISTS `{prefix}qc` (
                id INT AUTO_INCREMENT PRIMARY KEY,
                gisid VARCHAR(255),
                floor VARCHAR(255),
                length VARCHAR(255),
                breth VARCHAR(255),
                qcarea VARCHAR(255),
                qcusage VARCHAR(255),
                otsarea VARCHAR(255),
                qcremarks TEXT,
                qcname VARCHAR(255),
                created_at DATETIME,
                updated_at DATETIME
            )
        """,
    }
    
    with connection.cursor() as cursor:
        for table_name, schema in tables.items():
            full_table_name = f"{table_prefix}{table_name}"
            sql = schema.format(prefix=table_prefix)
            cursor.execute(sql)
    
    # Update Data model with table names
    data_instance.polygon = f"{table_prefix}polygons"
    data_instance.point = f"{table_prefix}points"
    data_instance.line = f"{table_prefix}lines"
    data_instance.mis = f"{table_prefix}mis"
    data_instance.pointdata = f"{table_prefix}pointdata"
    data_instance.polygondata = f"{table_prefix}buildingdata"
    data_instance.qc = f"{table_prefix}qc"
    data_instance.save()
    
    return data_instance


def usage_variations(data_instance):
    """
    Get usage variations
    Similar to Laravel usageVariations
    """
    from .models import PointData, BuildingData
    
    # Get all point data with building data
    point_datas = PointData.objects.filter(data=data_instance).select_related()
    building_datas = BuildingData.objects.filter(data=data_instance)
    
    # Build mapping
    building_map = {bd.gisid: bd for bd in building_datas}
    
    results = []
    for pd in point_datas:
        building_usage = None
        if pd.point_gisid in building_map:
            building_data = building_map[pd.point_gisid]
            building_usage = building_data.building_usage
        
        if building_usage and pd.bill_usage:
            bu = building_usage.upper()
            bill = pd.bill_usage.upper()
            
            # Check for variations
            if (bu == 'RESIDENTIAL' and bill in ['COMMERCIAL', 'MIXED']) or \
               (bu == 'COMMERCIAL' and bill == 'MIXED'):
                results.append({
                    'point_gisid': pd.point_gisid,
                    'road_name': building_map.get(pd.point_gisid, None).road_name if pd.point_gisid in building_map else None,
                    'assessment': pd.assessment,
                    'old_assessment': pd.old_assessment,
                    'building_usage': building_usage,
                    'bill_usage': pd.bill_usage,
                    'owner_name': pd.owner_name,
                    'floor': pd.floor,
                    'phone_number': pd.phone_number,
                    'plot_area': pd.plot_area,
                    'halfyeartax': pd.halfyeartax,
                    'balance': pd.balance,
                })
    
    return results


def area_variations(data_instance):
    """
    Get area variations
    Similar to Laravel areaVariations
    """
    from .models import PointData, BuildingData, PolygonFeature
    
    polygons = PolygonFeature.objects.filter(data=data_instance)
    polygon_map = {p.gisid: p for p in polygons}
    
    building_datas = BuildingData.objects.filter(data=data_instance)
    building_map = {bd.gisid: bd for bd in building_datas}
    
    point_datas = PointData.objects.filter(data=data_instance)
    
    results = []
    for pd in point_datas:
        if pd.point_gisid not in polygon_map:
            continue
        
        polygon = polygon_map[pd.point_gisid]
        building_data = building_map.get(pd.point_gisid)
        
        if not building_data:
            continue
        
        try:
            coordinates = json.loads(polygon.coordinates)
            area = calculate_polygon_area(coordinates)
            
            number_floor = float(building_data.number_floor) if building_data.number_floor else 0
            basement = float(building_data.basement) if building_data.basement else 0
            percentage = float(building_data.percentage) / 100 if building_data.percentage else 0
            
            total_drone_area = area * (number_floor + basement + percentage)
            plot_area = float(pd.plot_area) if pd.plot_area else 0
            
            area_variation = total_drone_area - plot_area
            
            if area_variation > 150:
                if area_variation > 350:
                    if building_data.building_type not in ['Flat', 'apartment', 'Flat-Multistoried']:
                        results.append({
                            'point_gisid': pd.point_gisid,
                            'coordinates': coordinates,
                            'road_name': building_data.road_name,
                            'building_type': building_data.building_type,
                            'assessment': pd.assessment,
                            'bill_usage': pd.bill_usage,
                            'dronearea': area,
                            'totaldronearea': total_drone_area,
                            'plotcount': plot_area,
                            'areavariation': area_variation,
                            'zone': data_instance.zone,
                            'ward': data_instance.ward,
                        })
                elif pd.bill_usage and pd.bill_usage.lower() == 'commercial':
                    results.append({
                        'point_gisid': pd.point_gisid,
                        'coordinates': coordinates,
                        'road_name': building_data.road_name,
                        'building_type': building_data.building_type,
                        'assessment': pd.assessment,
                        'bill_usage': pd.bill_usage,
                        'dronearea': area,
                        'totaldronearea': total_drone_area,
                        'plotcount': plot_area,
                        'areavariation': area_variation,
                        'zone': data_instance.zone,
                        'ward': data_instance.ward,
                    })
        except (ValueError, TypeError, json.JSONDecodeError):
            continue
    
    return results


def create_zip_archive(source_dir, destination):
    """
    Create zip archive from directory
    Similar to Laravel createZipArchive
    """
    import zipfile
    import os    
    if not os.path.exists(source_dir):
        raise Exception(f"Source directory does not exist: {source_dir}")
    
    with zipfile.ZipFile(destination, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(source_dir):
            for file in files:
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, source_dir)
                zipf.write(file_path, arcname)
    
    return True


def import_mis_excel(file_path, table_name):
    """
    Import MIS Excel file
    Similar to Laravel MisImport
    """
    import pandas as pd  # ✅ Import pandas only when this function is called
    from django.db import connection
    
    try:
        df = pd.read_excel(file_path)
    except Exception as e:
        raise Exception(f"Error reading Excel file: {str(e)}")
    
    # Map Excel columns to database columns
    column_mapping = {
        'assessment': 'assessment',
        'old_assessment': 'old_assessment',
        'number_floor': 'number_floor',
        'new_address': 'new_address',
        'building_usage': 'building_usage',
        'construction_type': 'construction_type',
        'road_name': 'road_name',
        'phone': 'phone',
        'building_type': 'building_type',
        'ward': 'ward',
        'owner_name': 'owner_name',
        'old_door_no': 'old_door_no',
        'new_door_no': 'new_door_no',
        'plot_area': 'plot_area',
        'watertax': 'watertax',
        'halfyeartax': 'halfyeartax',
        'balance': 'balance',
    }
    
    with connection.cursor() as cursor:
        for _, row in df.iterrows():
            columns = []
            values = []
            for excel_col, db_col in column_mapping.items():
                if excel_col in row and pd.notna(row[excel_col]):
                    columns.append(f"`{db_col}`")
                    values.append(str(row[excel_col]))
            
            if columns:
                columns.append('created_at')
                columns.append('updated_at')
                values.append('NOW()')
                values.append('NOW()')
                
                sql = f"INSERT INTO `{table_name}` ({', '.join(columns)}) VALUES ({', '.join(['%s'] * len(values))})"
                cursor.execute(sql, values)
    
    return True


# ✅ Optional: Add a function to check if pandas is available
def is_pandas_available():
    """Check if pandas is installed and working"""
    try:
        import pandas as pd
        return True
    except ImportError:
        return False