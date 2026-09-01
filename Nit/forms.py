from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from .models import CBE
from .models import Surveyor, Corporation, Building, CBE, TaxCollector, Ward, AssessmentData, Attendance


class UserRegistrationForm(UserCreationForm):
    email = forms.EmailField(required=True)
    first_name = forms.CharField(required=True)
    last_name = forms.CharField(required=True)
    role = forms.ChoiceField(choices=[
        ('surveyor', 'Surveyor'),
        ('cbe', 'CBE'),
        ('taxcollector', 'Tax Collector'),
    ])
    
    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email', 'password1', 'password2', 'role']


class SurveyorForm(forms.ModelForm):
    class Meta:
        model = Surveyor
        fields = ['phone', 'address', 'assigned_ward', 'is_active']
        widgets = {
            'phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Phone Number'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Address'}),
            'assigned_ward': forms.TextInput(attrs={'class': 'form-control'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class CBEForm(forms.ModelForm):
    class Meta:
        model = CBE
        fields = ['name', 'email', 'password', 'code', 'is_active']
        widgets = {
            'password': forms.PasswordInput(render_value=True),
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'code': forms.TextInput(attrs={'class': 'form-control'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

class TaxCollectorForm(forms.ModelForm):
    class Meta:
        model = TaxCollector
        fields = ['user', 'employee_id', 'phone', 'is_active']
        widgets = {
            'corporation': forms.Select(attrs={'class': 'form-control'}),
            'phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Phone Number'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class CorporationForm(forms.ModelForm):
    class Meta:
        model = Corporation
        fields = ['name', 'code', 'total_area']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'code': forms.TextInput(attrs={'class': 'form-control'}),
            'total_area': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
        }


class BuildingForm(forms.ModelForm):
    class Meta:
        model = Building
        fields = [
            'gis_id', 'building_name', 'building_number', 'area',
            'building_type', 'floors', 'construction_year',
            'owner_name', 'owner_contact', 'corporation',
            'ward', 'city', 'state', 'pincode', 'is_active'
        ]
        widgets = {
            'gis_id': forms.TextInput(attrs={'class': 'form-control'}),
            'building_name': forms.TextInput(attrs={'class': 'form-control'}),
            'building_number': forms.TextInput(attrs={'class': 'form-control'}),
            'area': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'building_type': forms.Select(attrs={'class': 'form-control'}),
            'floors': forms.NumberInput(attrs={'class': 'form-control'}),
            'construction_year': forms.NumberInput(attrs={'class': 'form-control'}),
            'owner_name': forms.TextInput(attrs={'class': 'form-control'}),
            'owner_contact': forms.TextInput(attrs={'class': 'form-control'}),
            'corporation': forms.Select(attrs={'class': 'form-control'}),
            'ward': forms.TextInput(attrs={'class': 'form-control'}),
            'city': forms.TextInput(attrs={'class': 'form-control'}),
            'state': forms.TextInput(attrs={'class': 'form-control'}),
            'pincode': forms.TextInput(attrs={'class': 'form-control'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class WardForm(forms.ModelForm):
    class Meta:
        model = Ward
        fields = ['name', 'ward_number', 'area_ha', 'population', 'is_active']  # Remove employee_id, phone, user
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'ward_number': forms.TextInput(attrs={'class': 'form-control'}),
            'area_ha': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'population': forms.NumberInput(attrs={'class': 'form-control'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class AssessmentDataForm(forms.ModelForm):
    class Meta:
        model = AssessmentData
        fields = ['gis_id', 'building', 'assessed_value', 'tax_amount', 'assessment_year', 'status']
        widgets = {
            'gis_id': forms.TextInput(attrs={'class': 'form-control'}),
            'building': forms.Select(attrs={'class': 'form-control'}),
            'assessed_value': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'tax_amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'assessment_year': forms.NumberInput(attrs={'class': 'form-control'}),
            'status': forms.Select(attrs={'class': 'form-control'}),
        }


class AttendanceForm(forms.ModelForm):
    class Meta:
        model = Attendance
        # Use the correct field names from your model
        fields = ['date', 'check_in_time', 'check_out_time', 'check_in_lat', 'check_in_lng', 
                  'check_out_lat', 'check_out_lng', 'inlocation', 'outlocation', 'status', 
                  'ward', 'remarks']
        widgets = {
            'date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'check_in_time': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'check_out_time': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'check_in_lat': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.000001'}),
            'check_in_lng': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.000001'}),
            'check_out_lat': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.000001'}),
            'check_out_lng': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.000001'}),
            'inlocation': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'outlocation': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'status': forms.Select(attrs={'class': 'form-control'}),
            'ward': forms.TextInput(attrs={'class': 'form-control'}),
            'remarks': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }


class LoginForm(forms.Form):
    username = forms.CharField(max_length=150, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Username'}))
    password = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Password'}))


class PasswordResetForm(forms.Form):
    email = forms.EmailField(widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Email'}))


class SetPasswordForm(forms.Form):
    password = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'New Password'}))
    confirm_password = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Confirm Password'}))

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        confirm_password = cleaned_data.get('confirm_password')
        if password and confirm_password and password != confirm_password:
            raise forms.ValidationError("Passwords don't match")
        return cleaned_data
