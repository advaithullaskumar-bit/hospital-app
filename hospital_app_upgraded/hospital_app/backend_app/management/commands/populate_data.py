from django.core.management.base import BaseCommand
from backend_app.models import Doctor, Resource, PatientProfile, HealthMetric, Appointment
import random
import datetime

class Command(BaseCommand):
    help = 'Populates the database with initial data including Patient Profiles and Metrics'

    def handle(self, *args, **kwargs):
        self.stdout.write("Checking and populating data...")

        # Resources
        if not Resource.objects.exists():
            Resource.objects.create(name='Casualty Beds', total_count=20, used_count=5, status_text='Available', details_text='Emergency Ward')
            Resource.objects.create(name='ICU Beds', total_count=10, used_count=8, status_text='Critical', details_text='Intensive Care')
            Resource.objects.create(name='Oxygen Tanks', total_count=50, used_count=12, status_text='Good Supply', details_text='Main Store')
            Resource.objects.create(name='Ambulance', total_count=5, used_count=1, status_text='Standby', details_text='24/7 Service')
            self.stdout.write(self.style.SUCCESS('Created Resources'))

        # Doctors
        dept_list = [
            'General Medicine', 'Cardiology', 'Neurology', 'Orthopedics', 'Pediatrics'
        ]
        
        for dept in dept_list:
            if not Doctor.objects.filter(department=dept).exists():
                name = f"Dr. {random.choice(['Smith', 'Patel', 'Lee', 'Gupta', 'Chen', 'Kumar'])} ({dept[:3]})"
                Doctor.objects.create(name=name, department=dept, specialization=f"Expert in {dept}")
                self.stdout.write(self.style.SUCCESS(f'Created Doctor for {dept}'))

        # Patient Profiles
        if not PatientProfile.objects.exists():
            patients = [
                {'name': 'John Doe', 'age': 45, 'blood': 'O+'},
                {'name': 'Jane Smith', 'age': 32, 'blood': 'A-'},
                {'name': 'Alice Brown', 'age': 28, 'blood': 'B+'},
            ]
            for p in patients:
                profile = PatientProfile.objects.create(
                    patient_name=p['name'],
                    patient_age=p['age'],
                    blood_group=p['blood'],
                    phone=f"+91 98765{random.randint(10000, 99999)}",
                    allergies="None" if random.random() > 0.3 else "Peanuts, Dust"
                )
                
                # Add sample metrics
                metric_types = ['heart_rate', 'temperature', 'oxygen_level', 'blood_pressure']
                units = {'heart_rate': 'bpm', 'temperature': '°F', 'oxygen_level': '%', 'blood_pressure': 'mmHg'}
                
                for m_type in metric_types:
                    for i in range(5):
                        val = random.randint(60, 100) if m_type == 'heart_rate' else random.uniform(97.0, 101.0) if m_type == 'temperature' else random.randint(95, 100) if m_type == 'oxygen_level' else random.randint(110, 140)
                        HealthMetric.objects.create(
                            patient_profile=profile,
                            metric_type=m_type,
                            value=round(val, 1),
                            unit=units[m_type]
                        )
                
                # Add sample appointment
                Appointment.objects.create(
                    patient_name=p['name'],
                    patient_age=p['age'],
                    patient_profile=profile,
                    department='General Medicine',
                    date=datetime.date.today(),
                    slot='09:00-10:00',
                    token_number=f"OP-{random.randint(100, 999)}",
                    status='Waiting'
                )
            self.stdout.write(self.style.SUCCESS('Created Sample Patients, Metrics, and Appointments'))

        self.stdout.write(self.style.SUCCESS('Data population complete.'))

