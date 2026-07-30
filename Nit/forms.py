# forms.py
from django import forms
from .models import Assessment, BuildingData, PointData, PolygonFeature, Surveyor


class AssessmentForm(forms.ModelForm):
    class Meta:
        model = Assessment
        fields = [
            'gis_id', 'owner_name', 'present_owner_name', 'owner_contact',
            'address', 'property_type', 'latitude', 'longitude', 'area_sq_m',
            'plot_area', 'water_tax', 'halfyeartax', 'balance',
            'building_type', 'floor_count', 'number_floor', 'construction_type',
            'construction_year', 'condition', 'old_assessment', 'old_door_no',
            'new_door_no', 'new_address', 'phone', 'bill_usage', 'building_usage',
            'tax_amount', 'tax_paid', 'tax_paid_date', 'status', 'remarks',
            'qc_area', 'qc_usage', 'qc_name', 'qc_remarks', 'otsarea'
        ]
        widgets = {
            'address': forms.Textarea(attrs={'rows': 3}),
            'remarks': forms.Textarea(attrs={'rows': 3}),
            'qc_remarks': forms.Textarea(attrs={'rows': 3}),
        }


class BuildingDataForm(forms.ModelForm):
    class Meta:
        model = BuildingData
        fields = [
            'gisid', 'number_bill', 'number_shop', 'number_floor', 'new_address',
            'liftroom', 'headroom', 'overhead_tank', 'percentage', 'building_name',
            'building_usage', 'construction_type', 'road_name', 'ugd',
            'rainwater_harvesting', 'parking', 'ramp', 'hoarding', 'cctv',
            'cell_tower', 'solar_panel', 'basement', 'water_connection',
            'phone', 'building_type', 'image', 'sqfeet', 'merge', 'split',
            'worker_name', 'remarks', 'corporationremarks'
        ]
        widgets = {
            'remarks': forms.Textarea(attrs={'rows': 3}),
            'corporationremarks': forms.Textarea(attrs={'rows': 3}),
        }


class PointDataForm(forms.ModelForm):
    class Meta:
        model = PointData
        fields = [
            'point_gisid', 'worker_name', 'assessment', 'old_assessment',
            'owner_name', 'present_owner_name', 'eb', 'floor', 'bill_usage',
            'aadhar_no', 'ration_no', 'phone_number', 'shop_floor', 'shop_name',
            'shop_owner_name', 'old_door_no', 'new_door_no', 'shop_category',
            'shop_mobile', 'license', 'professional_tax', 'gst',
            'number_of_employee', 'trade_income', 'establishment_remarks',
            'remarks', 'plot_area', 'water_tax', 'halfyeartax', 'balance',
            'building_data_id', 'qc_area', 'qc_usage', 'qc_name', 'qc_remarks',
            'otsarea'
        ]
        widgets = {
            'establishment_remarks': forms.Textarea(attrs={'rows': 3}),
            'remarks': forms.Textarea(attrs={'rows': 3}),
            'qc_remarks': forms.Textarea(attrs={'rows': 3}),
        }


class PolygonFeatureForm(forms.ModelForm):
    class Meta:
        model = PolygonFeature
        fields = ['gisid', 'type', 'coordinates']
        widgets = {
            'coordinates': forms.Textarea(attrs={'rows': 5, 'class': 'json-editor'}),
        }


class SurveyorForm(forms.ModelForm):
    class Meta:
        model = Surveyor
        fields = ['employee_id', 'department', 'data', 'mobile', 'is_active']
        widgets = {
            'department': forms.TextInput(attrs={'class': 'form-control'}),
            'mobile': forms.TextInput(attrs={'class': 'form-control'}),
        }


class UserRegistrationForm(forms.Form):
    username = forms.CharField(max_length=150, widget=forms.TextInput(attrs={'class': 'form-control'}))
    email = forms.EmailField(widget=forms.EmailInput(attrs={'class': 'form-control'}))
    password = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control'}))
    password2 = forms.CharField(label='Confirm Password', widget=forms.PasswordInput(attrs={'class': 'form-control'}))
    role = forms.ChoiceField(
        choices=[('surveyor', 'Surveyor'), ('admin', 'Admin'), ('cbe', 'CBE'), ('taxcollector', 'Tax Collector')],
        widget=forms.Select(attrs={'class': 'form-control'})
    )


class LoginForm(forms.Form):
    username = forms.CharField(max_length=150, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Username'}))
    password = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Password'}))