from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator

class Doctor(models.Model):
    name = models.CharField(max_length=100)
    department = models.CharField(max_length=100)
    specialization = models.CharField(max_length=200, blank=True)

    def __str__(self):
        return f"{self.name} ({self.department})"

class PatientProfile(models.Model):
    BLOOD_GROUP_CHOICES = [
        ('A+', 'A+'), ('A-', 'A-'),
        ('B+', 'B+'), ('B-', 'B-'),
        ('AB+', 'AB+'), ('AB-', 'AB-'),
        ('O+', 'O+'), ('O-', 'O-'),
    ]
    
    patient_name = models.CharField(max_length=100)
    patient_age = models.IntegerField()
    phone = models.CharField(max_length=15, blank=True)
    email = models.EmailField(blank=True)
    blood_group = models.CharField(max_length=3, choices=BLOOD_GROUP_CHOICES, blank=True)
    allergies = models.TextField(blank=True)
    medical_history = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.patient_name} (Age: {self.patient_age})"

class Appointment(models.Model):
    STATUS_CHOICES = [
        ('Waiting', 'Waiting'),
        ('In Room', 'In Room'),
        ('In Lab', 'In Lab'),
        ('In Radiology', 'In Radiology'),
        ('Completed', 'Completed'),
    ]
    
    PRIORITY_CHOICES = [
        ('Normal', 'Normal'),
        ('High', 'High (Critical)'),
    ]
    
    TIME_SLOT_CHOICES = [
        ('09:00-10:00', '9:00 AM - 10:00 AM'),
        ('10:00-11:00', '10:00 AM - 11:00 AM'),
        ('11:00-12:00', '11:00 AM - 12:00 PM'),
        ('12:00-13:00', '12:00 PM - 1:00 PM'),
        ('14:00-15:00', '2:00 PM - 3:00 PM'),
        ('15:00-16:00', '3:00 PM - 4:00 PM'),
        ('16:00-17:00', '4:00 PM - 5:00 PM'),
        ('17:00-18:00', '5:00 PM - 6:00 PM'),
    ]

    patient_name = models.CharField(max_length=100)
    patient_age = models.IntegerField()
    patient_profile = models.ForeignKey(PatientProfile, on_delete=models.SET_NULL, null=True, blank=True, related_name='appointments')
    doctor = models.ForeignKey(Doctor, on_delete=models.SET_NULL, null=True, blank=True)
    department = models.CharField(max_length=100)
    date = models.DateField()
    slot = models.CharField(max_length=50, choices=TIME_SLOT_CHOICES)
    token_number = models.CharField(max_length=50)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Waiting')
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='Normal')
    
    def __str__(self):
        return f"{self.token_number} - {self.patient_name}"

class HealthMetric(models.Model):
    METRIC_TYPE_CHOICES = [
        ('blood_pressure', 'Blood Pressure'),
        ('heart_rate', 'Heart Rate'),
        ('temperature', 'Temperature'),
        ('oxygen_level', 'Oxygen Level'),
        ('blood_sugar', 'Blood Sugar'),
        ('weight', 'Weight'),
    ]
    
    patient_profile = models.ForeignKey(PatientProfile, on_delete=models.CASCADE, related_name='health_metrics')
    metric_type = models.CharField(max_length=20, choices=METRIC_TYPE_CHOICES)
    value = models.FloatField()
    unit = models.CharField(max_length=20)  # e.g., "mmHg", "bpm", "°F", "%", "mg/dL", "kg"
    recorded_at = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True)
    
    class Meta:
        ordering = ['-recorded_at']
    
    def __str__(self):
        return f"{self.patient_profile.patient_name} - {self.metric_type}: {self.value} {self.unit}"

class MedicalReport(models.Model):
    REPORT_TYPE_CHOICES = [
        ('xray', 'X-Ray'),
        ('blood_test', 'Blood Test'),
        ('mri', 'MRI Scan'),
        ('ct_scan', 'CT Scan'),
        ('ultrasound', 'Ultrasound'),
        ('ecg', 'ECG'),
        ('urine_test', 'Urine Test'),
        ('biopsy', 'Biopsy'),
        ('other', 'Other'),
    ]
    
    patient_profile = models.ForeignKey(PatientProfile, on_delete=models.CASCADE, related_name='medical_reports')
    report_type = models.CharField(max_length=20, choices=REPORT_TYPE_CHOICES)
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    report_file = models.FileField(upload_to='medical_reports/', blank=True, null=True)
    report_date = models.DateField()
    uploaded_at = models.DateTimeField(auto_now_add=True)
    uploaded_by = models.CharField(max_length=100, blank=True)  # Staff name
    
    class Meta:
        ordering = ['-report_date']
    
    def __str__(self):
        return f"{self.patient_profile.patient_name} - {self.get_report_type_display()} ({self.report_date})"

class Resource(models.Model):
    name = models.CharField(max_length=100) # Casualty, Ward, ICU, Oxygen, Blood
    total_count = models.IntegerField(default=0)
    used_count = models.IntegerField(default=0)
    status_text = models.CharField(max_length=100) # e.g. "3 beds free"
    details_text = models.CharField(max_length=100) # e.g. "9 used / 12 total"
    
    def __str__(self):
        return self.name
