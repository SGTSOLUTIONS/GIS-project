# Nit/models.py - COMPLETE FIXED VERSION
from django.contrib.gis.db import models  # ✅ GIS models for geometry fields
from django.contrib.auth.models import User
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from django.db.models import Sum
from django.contrib.gis.db import models as gis_models
import json
import uuid


User = get_user_model()


# ============ USER PROFILE ============
class UserProfile(models.Model):
    ROLE_CHOICES = [
        ('admin', 'Admin'),
        ('surveyor', 'Surveyor'),
        ('cbe', 'CBE'),
        ('taxcollector', 'Tax Collector'),
    ]
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='surveyor')
    phone = models.CharField(max_length=15, blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    profile_picture = models.CharField(max_length=500, null=True, blank=True)
    password_reset_token = models.CharField(max_length=255, null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.user.username} - {self.get_role_display()}"


# ============ CBE (Corporation Building Executive) ============
class CBE(models.Model):
    name = models.CharField(max_length=255)
    email = models.EmailField(unique=True)
    password = models.CharField(max_length=255)
    code = models.CharField(max_length=50, null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return self.name
# ============ CORPORATION ============
class Corporation(models.Model):
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('inactive', 'Inactive'),
        ('pending', 'Pending'),
        ('completed', 'Completed'),
    ]
    
    name = models.CharField(max_length=255, unique=True)
    code = models.CharField(max_length=50, unique=True, null=True, blank=True)
    total_area = models.FloatField(default=0)
    total_buildings = models.IntegerField(default=0)
    total_surveys = models.IntegerField(default=0)
    coverage_percentage = models.FloatField(default=0)  # Add this line
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')  # Add this
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    description = models.TextField(blank=True, null=True)
    
    def __str__(self):
        return self.name

# ============ BUILDING ============
class Building(models.Model):
    BUILDING_TYPES = [
        ('RESIDENTIAL', 'Residential'),
        ('COMMERCIAL', 'Commercial'),
        ('INDUSTRIAL', 'Industrial'),
        ('GOVERNMENT', 'Government'),
        ('MIXED_USE', 'Mixed Use'),
        ('OTHER', 'Other'),
    ]
    
    gis_id = models.CharField(max_length=100, unique=True, db_index=True)
    building_name = models.CharField(max_length=255, null=True, blank=True)
    building_number = models.CharField(max_length=50, null=True, blank=True)
    address = models.TextField(blank=True, null=True)
    year_built = models.IntegerField(null=True, blank=True)
    
    # GEOMETRY FIELD - This is the key field for GeoDjango
    geometry = gis_models.GeometryField(srid=4326, null=True, blank=True, geography=True)
    
    area = models.FloatField(null=True, blank=True)
    
    building_type = models.CharField(max_length=50, choices=BUILDING_TYPES, default='OTHER')
    floors = models.IntegerField(null=True, blank=True)
    construction_year = models.IntegerField(null=True, blank=True)
    
    owner_name = models.CharField(max_length=255, null=True, blank=True)
    owner_contact = models.CharField(max_length=20, null=True, blank=True)
    
    corporation = models.ForeignKey(
        'Corporation', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='buildings'
    )
    ward = models.CharField(max_length=50, null=True, blank=True)
    city = models.CharField(max_length=100, default='New Delhi')
    state = models.CharField(max_length=100, default='Delhi')
    pincode = models.CharField(max_length=10, null=True, blank=True, default='')
    
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.gis_id} - {self.building_name or 'Unnamed'}"
class SearchHistory(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    gis_id = models.CharField(max_length=100)
    building = models.ForeignKey(Building, on_delete=models.SET_NULL, null=True, blank=True)
    searched_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-searched_at']
    
    def __str__(self):
        return f"{self.user.username} - {self.gis_id} - {self.searched_at}"
    
    def get_geojson(self):
        if self.geometry:
            return {
                'type': 'Feature',
                'geometry': json.loads(self.geometry.geojson),
                'properties': {
                    'id': self.id,
                    'gis_id': self.gis_id,
                    'building_name': self.building_name,
                    'building_number': self.building_number,
                    'area': self.area,
                    'building_type': self.building_type,
                    'floors': self.floors,
                    'owner_name': self.owner_name,
                    'corporation': self.corporation.name if self.corporation else None,
                    'ward': self.ward,
                    'city': self.city,
                }
            }
        return None


# ============ SURVEYOR ============
class Surveyor(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='surveyor_profile')
    phone = models.CharField(max_length=15, null=True, blank=True)
    address = models.TextField(null=True, blank=True)
    assigned_ward = models.CharField(max_length=50, null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.user.username} - {self.assigned_ward or 'Unassigned'}"


# ============ TAX COLLECTOR ============
class TaxCollector(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='taxcollector_profile')
    employee_id = models.CharField(max_length=50, unique=True)
    phone = models.CharField(max_length=15)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.user.username} - {self.employee_id}"

# ============ WARD ============
class Ward(models.Model):
    name = models.CharField(max_length=255)
    ward_number = models.CharField(max_length=50, unique=True)
    area_ha = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    population = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return self.name


# ============ DATA ============
class Data(models.Model):
    corporation = models.ForeignKey(Corporation, on_delete=models.CASCADE, related_name='datasets')
    corporation_name = models.CharField(max_length=200)
    ward = models.CharField(max_length=50)
    zone = models.CharField(max_length=50)
    image = models.CharField(max_length=500, blank=True, null=True)
    
    polygon = models.CharField(max_length=255, blank=True, null=True)
    line = models.CharField(max_length=255, blank=True, null=True)
    point = models.CharField(max_length=255, blank=True, null=True)
    mis = models.CharField(max_length=255, blank=True, null=True)
    qc = models.CharField(max_length=255, blank=True, null=True)
    pointdata = models.CharField(max_length=255, blank=True, null=True)
    polygondata = models.CharField(max_length=255, blank=True, null=True)
    
    extend_left = models.BooleanField(default=False)
    extend_right = models.BooleanField(default=False)
    extend_top = models.BooleanField(default=False)
    extend_bottom = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.corporation_name} - Zone {self.zone} - Ward {self.ward}"


# ============ ASSESSMENT ============
class Assessment(models.Model):
    ASSESSMENT_STATUS = [
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('verified', 'Verified'),
        ('rejected', 'Rejected'),
    ]
    
    PROPERTY_TYPES = [
        ('residential', 'Residential'),
        ('commercial', 'Commercial'),
        ('industrial', 'Industrial'),
        ('agricultural', 'Agricultural'),
        ('mixed', 'Mixed Use'),
    ]
    
    gis_id = models.CharField(max_length=50, unique=True)
    surveyor = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='assessments')
    ward = models.ForeignKey(Ward, on_delete=models.SET_NULL, null=True)
    data = models.ForeignKey(Data, on_delete=models.SET_NULL, null=True)
    
    owner_name = models.CharField(max_length=200)
    present_owner_name = models.CharField(max_length=200, blank=True)
    owner_contact = models.CharField(max_length=15, blank=True)
    address = models.TextField()
    property_type = models.CharField(max_length=50, choices=PROPERTY_TYPES, default='residential')
    
    latitude = models.DecimalField(max_digits=10, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=10, decimal_places=6, null=True, blank=True)
    area_sq_m = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    plot_area = models.CharField(max_length=50, blank=True, null=True)
    water_tax = models.CharField(max_length=50, blank=True, null=True)
    halfyeartax = models.CharField(max_length=50, blank=True, null=True)
    balance = models.CharField(max_length=50, blank=True, null=True)
    
    building_type = models.CharField(max_length=50, blank=True)
    floor_count = models.IntegerField(default=1)
    number_floor = models.CharField(max_length=50, blank=True, null=True)
    construction_type = models.CharField(max_length=50, blank=True)
    construction_year = models.IntegerField(null=True, blank=True)
    condition = models.CharField(max_length=50, blank=True, choices=[
        ('excellent', 'Excellent'),
        ('good', 'Good'),
        ('average', 'Average'),
        ('poor', 'Poor'),
        ('dilapidated', 'Dilapidated'),
    ])
    
    old_assessment = models.CharField(max_length=50, blank=True, null=True)
    old_door_no = models.CharField(max_length=50, blank=True, null=True)
    new_door_no = models.CharField(max_length=50, blank=True, null=True)
    new_address = models.CharField(max_length=255, blank=True, null=True)
    phone = models.CharField(max_length=20, blank=True, null=True)
    
    bill_usage = models.CharField(max_length=50, blank=True, null=True)
    building_usage = models.CharField(max_length=50, blank=True, null=True)
    
    tax_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    tax_paid = models.BooleanField(default=False)
    tax_paid_date = models.DateField(null=True, blank=True)
    
    status = models.CharField(max_length=20, choices=ASSESSMENT_STATUS, default='pending')
    remarks = models.TextField(blank=True)
    qc_area = models.CharField(max_length=50, blank=True, null=True)
    qc_usage = models.CharField(max_length=50, blank=True, null=True)
    qc_name = models.CharField(max_length=100, blank=True, null=True)
    qc_remarks = models.TextField(blank=True, null=True)
    otsarea = models.CharField(max_length=50, blank=True, null=True)
    
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='created_assessments')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    verified_at = models.DateTimeField(null=True, blank=True)
    verified_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='verified_assessments')
    
    def __str__(self):
        return f"{self.gis_id} - {self.owner_name}"


# ============ ASSESSMENT DATA ============
class AssessmentData(models.Model):
    gis_id = models.CharField(max_length=100, unique=True)
    building = models.ForeignKey(Building, on_delete=models.CASCADE, related_name='assessments', null=True, blank=True)
    assessed_value = models.FloatField(default=0)
    tax_amount = models.FloatField(default=0)
    assessment_year = models.IntegerField(null=True, blank=True)
    status = models.CharField(max_length=50, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.gis_id} - {self.assessment_year}"


# ============ ATTENDANCE ============
class Attendance(models.Model):
    surveyor = models.ForeignKey(User, on_delete=models.CASCADE, related_name='attendances')
    date = models.DateField(default=timezone.now)
    check_in_time = models.DateTimeField(null=True, blank=True)
    check_out_time = models.DateTimeField(null=True, blank=True)
    check_in_lat = models.DecimalField(max_digits=10, decimal_places=6, null=True, blank=True)
    check_in_lng = models.DecimalField(max_digits=10, decimal_places=6, null=True, blank=True)
    check_out_lat = models.DecimalField(max_digits=10, decimal_places=6, null=True, blank=True)
    check_out_lng = models.DecimalField(max_digits=10, decimal_places=6, null=True, blank=True)
    inlocation = models.JSONField(null=True, blank=True)
    outlocation = models.JSONField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=[
        ('present', 'Present'),
        ('absent', 'Absent'),
        ('half_day', 'Half Day'),
        ('leave', 'Leave'),
    ], default='present')
    ward = models.CharField(max_length=50, blank=True, null=True)
    remarks = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['surveyor', 'date']
    
    def __str__(self):
        return f"{self.surveyor.username} - {self.date}"


# ============ BUILDING DATA ============
class BuildingData(models.Model):
    data = models.ForeignKey(Data, on_delete=models.CASCADE, related_name='buildings')
    gisid = models.CharField(max_length=50)
    number_bill = models.CharField(max_length=50, blank=True, null=True)
    number_shop = models.CharField(max_length=50, blank=True, null=True)
    number_floor = models.CharField(max_length=50, blank=True, null=True)
    new_address = models.CharField(max_length=255, blank=True, null=True)
    liftroom = models.CharField(max_length=50, blank=True, null=True)
    headroom = models.CharField(max_length=50, blank=True, null=True)
    overhead_tank = models.CharField(max_length=50, blank=True, null=True)
    percentage = models.CharField(max_length=50, blank=True, null=True)
    building_name = models.CharField(max_length=200, blank=True, null=True)
    building_usage = models.CharField(max_length=50, blank=True, null=True)
    construction_type = models.CharField(max_length=50, blank=True, null=True)
    road_name = models.CharField(max_length=200, blank=True, null=True)
    ugd = models.CharField(max_length=50, blank=True, null=True)
    rainwater_harvesting = models.CharField(max_length=50, blank=True, null=True)
    parking = models.CharField(max_length=50, blank=True, null=True)
    ramp = models.CharField(max_length=50, blank=True, null=True)
    hoarding = models.CharField(max_length=50, blank=True, null=True)
    cctv = models.CharField(max_length=50, blank=True, null=True)
    cell_tower = models.CharField(max_length=50, blank=True, null=True)
    solar_panel = models.CharField(max_length=50, blank=True, null=True)
    basement = models.CharField(max_length=50, blank=True, null=True)
    water_connection = models.CharField(max_length=50, blank=True, null=True)
    phone = models.CharField(max_length=20, blank=True, null=True)
    building_type = models.CharField(max_length=50, blank=True, null=True)
    image = models.CharField(max_length=500, blank=True, null=True)
    sqfeet = models.CharField(max_length=50, blank=True, null=True)
    merge = models.CharField(max_length=50, blank=True, null=True)
    split = models.CharField(max_length=50, blank=True, null=True)
    worker_name = models.CharField(max_length=100, blank=True, null=True)
    remarks = models.TextField(blank=True, null=True)
    corporationremarks = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['data', 'gisid']
    
    def __str__(self):
        return f"{self.data.corporation_name} - {self.gisid}"


# ============ POINT DATA ============
class PointData(models.Model):
    data = models.ForeignKey(Data, on_delete=models.CASCADE, related_name='pointdata_set')
    point_data_id = models.CharField(max_length=50, blank=True, null=True)
    point_gisid = models.CharField(max_length=50)
    worker_name = models.CharField(max_length=100, blank=True, null=True)
    assessment = models.CharField(max_length=50, blank=True, null=True)
    old_assessment = models.CharField(max_length=50, blank=True, null=True)
    owner_name = models.CharField(max_length=200, blank=True, null=True)
    present_owner_name = models.CharField(max_length=200, blank=True, null=True)
    eb = models.CharField(max_length=50, blank=True, null=True)
    floor = models.CharField(max_length=50, blank=True, null=True)
    bill_usage = models.CharField(max_length=50, blank=True, null=True)
    aadhar_no = models.CharField(max_length=20, blank=True, null=True)
    ration_no = models.CharField(max_length=50, blank=True, null=True)
    phone_number = models.CharField(max_length=20, blank=True, null=True)
    shop_floor = models.CharField(max_length=50, blank=True, null=True)
    shop_name = models.CharField(max_length=200, blank=True, null=True)
    shop_owner_name = models.CharField(max_length=200, blank=True, null=True)
    old_door_no = models.CharField(max_length=50, blank=True, null=True)
    new_door_no = models.CharField(max_length=50, blank=True, null=True)
    shop_category = models.CharField(max_length=100, blank=True, null=True)
    shop_mobile = models.CharField(max_length=20, blank=True, null=True)
    license = models.CharField(max_length=50, blank=True, null=True)
    professional_tax = models.CharField(max_length=50, blank=True, null=True)
    gst = models.CharField(max_length=50, blank=True, null=True)
    number_of_employee = models.CharField(max_length=50, blank=True, null=True)
    trade_income = models.CharField(max_length=50, blank=True, null=True)
    establishment_remarks = models.TextField(blank=True, null=True)
    remarks = models.TextField(blank=True, null=True)
    plot_area = models.CharField(max_length=50, blank=True, null=True)
    water_tax = models.CharField(max_length=50, blank=True, null=True)
    halfyeartax = models.CharField(max_length=50, blank=True, null=True)
    balance = models.CharField(max_length=50, blank=True, null=True)
    building_data_id = models.CharField(max_length=50, blank=True, null=True)
    qc_area = models.CharField(max_length=50, blank=True, null=True)
    qc_usage = models.CharField(max_length=50, blank=True, null=True)
    qc_name = models.CharField(max_length=100, blank=True, null=True)
    qc_remarks = models.TextField(blank=True, null=True)
    otsarea = models.CharField(max_length=50, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.data.corporation_name} - {self.assessment}"


# ============ GIS FEATURES ============
class PolygonFeature(models.Model):
    data = models.ForeignKey(Data, on_delete=models.CASCADE, related_name='polygons')
    gisid = models.CharField(max_length=50)
    type = models.CharField(max_length=50, default='Polygon')
    coordinates = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['data', 'gisid']
    
    def __str__(self):
        return f"{self.data.corporation_name} - {self.gisid}"


class PointFeature(models.Model):
    data = models.ForeignKey(Data, on_delete=models.CASCADE, related_name='points')
    gisid = models.CharField(max_length=50)
    type = models.CharField(max_length=50, default='Point')
    coordinates = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['data', 'gisid']
    
    def __str__(self):
        return f"{self.data.corporation_name} - {self.gisid}"


class LineFeature(models.Model):
    data = models.ForeignKey(Data, on_delete=models.CASCADE, related_name='lines')
    gisid = models.CharField(max_length=50)
    type = models.CharField(max_length=50, default='LineString')
    coordinates = models.JSONField()
    road_name = models.CharField(max_length=200, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['data', 'gisid']
    
    def __str__(self):
        return f"{self.data.corporation_name} - {self.gisid}"


# ============ QC DATA ============
class QCData(models.Model):
    data = models.ForeignKey(Data, on_delete=models.CASCADE, related_name='qc_data')
    gisid = models.CharField(max_length=50, blank=True, null=True)
    floor = models.CharField(max_length=50, blank=True, null=True)
    length = models.CharField(max_length=50, blank=True, null=True)
    breth = models.CharField(max_length=50, blank=True, null=True)
    qcarea = models.CharField(max_length=50, blank=True, null=True)
    qcusage = models.CharField(max_length=50, blank=True, null=True)
    otsarea = models.CharField(max_length=50, blank=True, null=True)
    qcremarks = models.TextField(blank=True, null=True)
    qcname = models.CharField(max_length=100, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.data.corporation_name} - {self.gisid}"


# ============ ACTIVITY LOG ============
class ActivityLog(models.Model):
    ACTION_CHOICES = [
        ('CREATE', 'Create'),
        ('UPDATE', 'Update'),
        ('DELETE', 'Delete'),
        ('VIEW', 'View'),
        ('LOGIN', 'Login'),
        ('LOGOUT', 'Logout'),
        ('EXPORT', 'Export'),
        ('IMPORT', 'Import'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='activities')
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    model_name = models.CharField(max_length=100)
    object_id = models.CharField(max_length=50, blank=True, null=True)
    details = models.JSONField(default=dict, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True, null=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-timestamp']
        verbose_name_plural = 'Activity Logs'
    
    def __str__(self):
        return f"{self.user.username} - {self.action} - {self.model_name}"


# ============ PASSWORD RESET TOKEN ============
class PasswordResetToken(models.Model):
    email = models.EmailField()
    token = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.email} - {self.token}"


# ============ ROAD ============
class Road(models.Model):
    name = models.CharField(max_length=200)
    road_type = models.CharField(max_length=50, choices=[
        ('national_highway', 'National Highway'),
        ('state_highway', 'State Highway'),
        ('district_road', 'District Road'),
        ('village_road', 'Village Road'),
        ('street', 'Street'),
    ], default='street')
    start_lat = models.DecimalField(max_digits=10, decimal_places=6, null=True, blank=True)
    start_lng = models.DecimalField(max_digits=10, decimal_places=6, null=True, blank=True)
    end_lat = models.DecimalField(max_digits=10, decimal_places=6, null=True, blank=True)
    end_lng = models.DecimalField(max_digits=10, decimal_places=6, null=True, blank=True)
    length_m = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    ward = models.ForeignKey(Ward, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return self.name


# ============ GIS FILE UPLOAD ============
class GISFileUpload(models.Model):
    FILE_TYPES = [
        ('shapefile', 'Shapefile'),
        ('geojson', 'GeoJSON'),
        ('kml', 'KML'),
        ('csv', 'CSV'),
        ('gpx', 'GPX'),
        ('excel', 'Excel'),
    ]
    
    data = models.ForeignKey(Data, on_delete=models.CASCADE, related_name='gis_uploads', null=True, blank=True)
    file_name = models.CharField(max_length=255, default='', blank=True)
    file_type = models.CharField(max_length=20, choices=FILE_TYPES, default='geojson')
    file_path = models.CharField(max_length=500, default='', blank=True)
    geom_type = models.CharField(max_length=50, blank=True, null=True)
    feature_count = models.IntegerField(default=0)
    uploaded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)
    
    def __str__(self):
        return f"{self.file_name} - {self.file_type}"


# ============ FEATURE EDIT HISTORY ============
class FeatureEditHistory(models.Model):
    data = models.ForeignKey(Data, on_delete=models.CASCADE, related_name='edit_history')
    feature_gisid = models.CharField(max_length=50)
    geometry_type = models.CharField(max_length=20, choices=[
        ('polygon', 'Polygon'),
        ('point', 'Point'),
        ('line', 'Line'),
    ])
    old_geometry = models.JSONField(null=True, blank=True)
    new_geometry = models.JSONField()
    edited_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    edited_at = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True, null=True)
    
    def __str__(self):
        return f"Edit {self.feature_gisid} - {self.edited_at.strftime('%Y-%m-%d %H:%M')}"


# ============ SHAPEFILE IMPORT ============
class ShapefileImport(models.Model):
    data = models.ForeignKey(Data, on_delete=models.CASCADE, related_name='shapefile_imports')
    original_filename = models.CharField(max_length=255)
    file_path = models.CharField(max_length=500)
    geom_type = models.CharField(max_length=50)
    feature_count = models.IntegerField(default=0)
    srs_wkt = models.TextField(null=True, blank=True)
    imported_at = models.DateTimeField(auto_now_add=True)
    imported_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    is_active = models.BooleanField(default=True)
    
    def __str__(self):
        return f"{self.original_filename} - {self.feature_count} features"


# ============ SHAPEFILE EXPORT ============
class ShapefileExport(models.Model):
    data = models.ForeignKey(Data, on_delete=models.CASCADE, related_name='shapefile_exports')
    filename = models.CharField(max_length=255)
    file_path = models.CharField(max_length=500)
    geom_type = models.CharField(max_length=50)
    feature_count = models.IntegerField(default=0)
    exported_at = models.DateTimeField(auto_now_add=True)
    exported_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    
    def __str__(self):
        return f"Export {self.filename} - {self.exported_at}"