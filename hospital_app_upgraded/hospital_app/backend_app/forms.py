from django import forms
from .models import Appointment, Doctor, MedicalReport, HealthMetric, PatientProfile

class AppointmentForm(forms.ModelForm):
    doctor_name = forms.CharField(required=False, widget=forms.HiddenInput()) # Handle "Any" logic in view or clean

    class Meta:
        model = Appointment
        fields = ['patient_name', 'patient_age', 'department', 'date', 'slot']

    def clean_patient_age(self):
        age = self.cleaned_data.get('patient_age')
        if age < 0 or age > 150:
            raise forms.ValidationError("Please enter a valid age.")
        return age

class LoginForm(forms.Form):
    username = forms.CharField()
    password = forms.CharField(widget=forms.PasswordInput)

class MedicalReportForm(forms.ModelForm):
    class Meta:
        model = MedicalReport
        fields = ['patient_profile', 'report_type', 'title', 'description', 'report_file', 'report_date']
        widgets = {
            'report_date': forms.DateInput(attrs={'type': 'date'}),
            'description': forms.Textarea(attrs={'rows': 4}),
        }

class HealthMetricForm(forms.ModelForm):
    class Meta:
        model = HealthMetric
        fields = ['patient_profile', 'metric_type', 'value', 'unit', 'notes']
        widgets = {
            'notes': forms.Textarea(attrs={'rows': 3}),
        }

class PatientProfileForm(forms.ModelForm):
    class Meta:
        model = PatientProfile
        fields = ['patient_name', 'patient_age', 'phone', 'email', 'blood_group', 'allergies', 'medical_history']
        widgets = {
            'allergies': forms.Textarea(attrs={'rows': 3}),
            'medical_history': forms.Textarea(attrs={'rows': 4}),
        }

