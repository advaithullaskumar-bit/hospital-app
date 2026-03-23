from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from .models import Appointment, Doctor, Resource, PatientProfile, HealthMetric, MedicalReport
from .forms import AppointmentForm, LoginForm, MedicalReportForm, HealthMetricForm, PatientProfileForm
import datetime
from django.db.models import Count, Q
import json

# ─── helpers ────────────────────────────────────────────────────────────────

def _generate_unique_token(date):
    """Sequential unique token per day. Fixes the random collision bug."""
    existing = Appointment.objects.filter(date=date).count()
    return f"OP-{existing + 1:03d}"

def _real_dept_load(dept_name, today):
    """Real load from DB. Fixes the random-on-every-request bug."""
    count = Appointment.objects.filter(
        date=today, department=dept_name
    ).exclude(status='Completed').count()
    if count <= 3:
        return 'Low', 'green', '~10 min'
    elif count <= 7:
        return 'Moderate', 'orange', '~25 min'
    else:
        return 'High', 'red', '1h+'

def _queue_position_and_wait(profile, today):
    """Return (position, est_minutes) for the patient in today's queue."""
    appt = profile.appointments.filter(date=today).first()
    if not appt or appt.status == 'Completed':
        return None, None
    waiting_before = Appointment.objects.filter(
        date=today, department=appt.department, status='Waiting', id__lt=appt.id
    ).count()
    in_room = Appointment.objects.filter(
        date=today, department=appt.department, status='In Room'
    ).count()
    position = waiting_before + 1
    est_minutes = (waiting_before + in_room) * 12
    return position, est_minutes


# ─── public views ────────────────────────────────────────────────────────────

def index(request):
    resources = Resource.objects.all()
    doctors = Doctor.objects.all()
    today = datetime.date.today()
    dept_list = [
        'General Medicine', 'Cardiology', 'Neurology', 'Orthopedics', 'Pediatrics',
        'Gynecology', 'Dermatology', 'ENT', 'Ophthalmology', 'Dental', 'Oncology', 'Psychiatry'
    ]
    department_data = []
    for d in dept_list:
        load, color, wait = _real_dept_load(d, today)
        department_data.append({'name': d, 'load': load, 'color': color, 'wait': wait})
    return render(request, 'backend_app/public_index.html', {
        'resources': resources,
        'doctors': doctors,
        'departments': department_data,
        'time_slots': Appointment.TIME_SLOT_CHOICES
    })


def api_bookings(request):
    today = datetime.date.today()
    bookings = Appointment.objects.filter(date=today).exclude(status='Completed').order_by('id')
    data = []
    for b in bookings:
        name = b.patient_name
        masked = name[0] + "***" + name[-1] if len(name) > 2 else "Patient"
        data.append({
            'token': b.token_number, 'name': masked, 'age': b.patient_age,
            'dept': b.department, 'doc': b.doctor.name if b.doctor else "Any",
            'date': b.date.strftime('%Y-%m-%d'), 'slot': b.slot,
            'status': b.status, 'priority': b.priority,
        })
    return JsonResponse(data, safe=False)


def api_book(request):
    """Booking endpoint. CSRF handled via cookie — @csrf_exempt removed (security fix)."""
    if request.method == 'POST':
        form_data = {
            'patient_name': request.POST.get('pname'),
            'patient_age': request.POST.get('page'),
            'department': request.POST.get('dept'),
            'date': request.POST.get('date'),
            'slot': request.POST.get('slot'),
            'doctor_name': request.POST.get('doc')
        }
        form = AppointmentForm(form_data)
        if form.is_valid():
            appointment = form.save(commit=False)
            doc_name = form.cleaned_data.get('doctor_name')
            if doc_name and "Any" not in doc_name:
                doctor, _ = Doctor.objects.get_or_create(name=doc_name, defaults={'department': appointment.department})
                appointment.doctor = doctor
            appointment.priority = 'High' if request.POST.get('condition') == 'Emergency' else 'Normal'
            appointment.token_number = _generate_unique_token(appointment.date)
            appointment.status = 'Waiting'
            patient_profile = PatientProfile.objects.filter(
                patient_name=appointment.patient_name, patient_age=appointment.patient_age
            ).first()
            if not patient_profile:
                patient_profile = PatientProfile.objects.create(
                    patient_name=appointment.patient_name, patient_age=appointment.patient_age
                )
            
            bg = request.POST.get('blood_group')
            if bg:
                patient_profile.blood_group = bg
                patient_profile.save()

            appointment.patient_profile = patient_profile
            appointment.save()
            return JsonResponse({'ok': True, 'token': appointment.token_number})
        else:
            return JsonResponse({'ok': False, 'message': 'Invalid data', 'errors': form.errors})
    return JsonResponse({'ok': False, 'message': 'POST required'})


@csrf_exempt
def api_triage(request):
    """AI-powered symptom triage. Uses keyword fallback if no API key."""
    if request.method != 'POST':
        return JsonResponse({'ok': False})
    try:
        body = json.loads(request.body)
        symptoms = body.get('symptoms', '').strip()
    except Exception:
        symptoms = request.POST.get('symptoms', '').strip()
    if not symptoms:
        return JsonResponse({'ok': False, 'message': 'No symptoms provided'})

    dept_list = [
        'General Medicine', 'Cardiology', 'Neurology', 'Orthopedics', 'Pediatrics',
        'Gynecology', 'Dermatology', 'ENT', 'Ophthalmology', 'Dental', 'Oncology', 'Psychiatry'
    ]
    import os, urllib.request
    api_key = os.environ.get('ANTHROPIC_API_KEY', '')

    if api_key:
        prompt = (
            f'You are a hospital triage AI. Patient symptoms: "{symptoms}"\n'
            f'Departments available: {", ".join(dept_list)}\n'
            'Respond ONLY with JSON (no markdown): '
            '{"department": "<name>", "is_emergency": true/false, "reason": "<12 words max>"}'
        )
        try:
            payload = json.dumps({
                "model": "claude-haiku-4-5-20251001", "max_tokens": 150,
                "messages": [{"role": "user", "content": prompt}]
            }).encode()
            req = urllib.request.Request(
                'https://api.anthropic.com/v1/messages', data=payload,
                headers={'Content-Type': 'application/json', 'x-api-key': api_key, 'anthropic-version': '2023-06-01'},
                method='POST'
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                result = json.loads(resp.read().decode())
                text = result['content'][0]['text'].strip().replace('```json','').replace('```','').strip()
                parsed = json.loads(text)
                return JsonResponse({'ok': True, 'department': parsed.get('department','General Medicine'),
                                     'is_emergency': parsed.get('is_emergency', False), 'reason': parsed.get('reason','')})
        except Exception as e:
            pass  # fall through to keyword fallback

    # Keyword fallback
    sl = symptoms.lower()
    is_emergency = any(w in sl for w in ["can't breathe", 'chest pain', 'unconscious', 'bleeding', 'stroke', 'heart attack', 'severe pain', 'faint'])
    dept = 'General Medicine'
    for keywords, d in [
        (['heart','chest','palpitation','bp'], 'Cardiology'),
        (['brain','headache','dizzy','seizure','numb','paralysis'], 'Neurology'),
        (['bone','joint','fracture','knee','back pain','spine'], 'Orthopedics'),
        (['child','baby','infant'], 'Pediatrics'),
        (['skin','rash','itch','acne','eczema'], 'Dermatology'),
        (['eye','vision','cataract'], 'Ophthalmology'),
        (['ear','nose','throat','hearing','sinus'], 'ENT'),
        (['tooth','dental','gum'], 'Dental'),
        (['lung','cough','breath','asthma','wheeze'], 'General Medicine'),
    ]:
        if any(k in sl for k in keywords):
            dept = d
            break
    return JsonResponse({'ok': True, 'department': dept, 'is_emergency': is_emergency, 'reason': 'Based on symptom analysis.'})


@csrf_exempt
def chatbot_api(request):
    if request.method == 'POST':
        query = request.POST.get('message', '').lower()
        symptom_kb = [
            {'keywords': ['heart','chest','palpitat','bp','blood pressure'], 'response': "Cardiovascular: For BP fluctuations, maintain a low-sodium diet. WARNING: Crushing chest pain is a heart attack sign — seek emergency care immediately."},
            {'keywords': ['stomach','vomit','diarrhea','nausea','bloat','acid'], 'response': "Gastrointestinal: Acidity often responds to small frequent meals. Persistent sharp pain or blood in stool requires urgent evaluation."},
            {'keywords': ['dizzy','faint','seizur','numb','confus','migrain','tremor'], 'response': "Neurological: Recurring migraines should be evaluated via MRI. CRITICAL: Sudden slurred speech or loss of balance is a medical emergency."},
            {'keywords': ['breath','wheez','asthma','cough','lung','oxygen'], 'response': "Respiratory: Chronic cough may indicate asthma. Monitor SpO2. If breathing is laboured, visit our pulmonary ward."},
            {'keywords': ['rash','itch','skin','acne','allergy','eczema'], 'response': "Dermatological: Avoid scratching to prevent secondary infection. Hives with throat swelling require ER care immediately."},
        ]
        medicine_kb = [
            {'keywords': ['paracetamol','dolo','ibuprofen','painkiller','combiflam'], 'response': "Analgesics: Paracetamol is standard for fever. Ibuprofen is anti-inflammatory. Avoid excessive use to protect kidneys/liver."},
            {'keywords': ['amoxicillin','azithromycin','antibiotic','infection'], 'response': "Antibiotics: Use ONLY as prescribed. Never stop mid-course or antibiotic resistance may develop."},
            {'keywords': ['metformin','insulin','sugar','diabetes'], 'response': "Anti-Diabetics: Metformin is baseline for Type 2. Watch for hypoglycemia (dizziness/sweat). Do not skip meals."},
        ]
        best, max_score = None, 0
        for e in symptom_kb:
            s = sum(5 for k in e['keywords'] if k in query)
            if s > max_score: max_score, best = s, e['response']
        for e in medicine_kb:
            s = sum(8 for k in e['keywords'] if k in query)
            if s > max_score: max_score, best = s, e['response']
        if any(rf in query for rf in ['unconscious','bleeding','heart attack','stroke','choking','poison']):
            response = "EMERGENCY: Call 108/112 or visit our Emergency Ward immediately. Do not delay."
        elif max_score > 0:
            response = best
        elif any(k in query for k in ['hi','hello','hey']):
            response = "I am Nucleus Health AI. I can help with symptom guidance, medicine info, and hospital navigation."
        elif any(k in query for k in ['book','appointment']):
            response = "Book a visit via our Homepage. Choose your specialty and slot for an instant token."
        else:
            response = "I can help with symptoms, medicines, or guide you to the right department. Please describe your concern."
        return JsonResponse({'response': response})
    return JsonResponse({'response': 'Please send a message.'})


# ─── TV display board ─────────────────────────────────────────────────────────

def tv_board(request):
    return render(request, 'backend_app/tv_board.html')

def api_tv_data(request):
    today = datetime.date.today()
    in_room = Appointment.objects.filter(date=today, status='In Room').order_by('-priority', 'id').first()
    waiting = Appointment.objects.filter(date=today, status='Waiting').order_by('-priority', 'id')[:5]
    resources = Resource.objects.all()
    data = {
        'serving': {'token': in_room.token_number, 'dept': in_room.department, 'priority': in_room.priority} if in_room else None,
        'next': [{'token': a.token_number, 'dept': a.department, 'priority': a.priority} for a in waiting],
        'resources': [{'name': r.name, 'total': r.total_count, 'used': r.used_count} for r in resources],
        'timestamp': datetime.datetime.now().strftime('%H:%M'),
    }
    return JsonResponse(data)


# ─── patient views ────────────────────────────────────────────────────────────

def patient_dashboard_access(request):
    if request.method == 'POST':
        token = request.POST.get('token')
        name = request.POST.get('pname')
        appointment = Appointment.objects.filter(token_number__iexact=token, patient_name__icontains=name).first()
        if appointment and appointment.patient_profile:
            request.session['patient_profile_id'] = appointment.patient_profile.id
            return JsonResponse({'ok': True, 'redirect': '/patient/dashboard'})
        return JsonResponse({'ok': False, 'message': 'Invalid Token or Name. Use the exact name and token from your slip.'})
    return render(request, 'backend_app/patient_login.html')


def patient_dashboard(request):
    profile_id = request.session.get('patient_profile_id')
    if not profile_id:
        return redirect('index')
    profile = get_object_or_404(PatientProfile, id=profile_id)
    today = datetime.date.today()
    current_appointment = profile.appointments.filter(date=today).first()
    queue_position, est_wait = _queue_position_and_wait(profile, today)
    appointments = profile.appointments.all().order_by('-date')
    all_reports = profile.medical_reports.all().order_by('-report_date')
    radiology_types = ['xray', 'mri', 'ct_scan', 'ultrasound']
    radiology_reports = all_reports.filter(report_type__in=radiology_types)
    lab_reports = all_reports.exclude(report_type__in=radiology_types)
    health_metrics = profile.health_metrics.all().order_by('-recorded_at')
    ai_summary = "Your vital patterns appear balanced. No immediate critical alerts detected by Nucleus AI."
    if current_appointment and current_appointment.priority == 'High':
        ai_summary = "Priority Triage Active: This visit has been flagged as critical. Please standby for immediate care."
    elif profile.health_metrics.filter(metric_type='oxygen_level', value__lt=95).exists():
        ai_summary = "Observation: Recent oxygen levels below 95%. Nucleus AI recommends pulmonary consultation."
    return render(request, 'backend_app/patient_dashboard.html', {
        'profile': profile, 'current_appointment': current_appointment,
        'queue_position': queue_position, 'est_wait': est_wait,
        'appointments': appointments, 'radiology_reports': radiology_reports,
        'lab_reports': lab_reports, 'health_metrics': health_metrics,
        'ai_summary': ai_summary, 'has_real_data': health_metrics.exists() or all_reports.exists()
    })


def patient_logout(request):
    request.session.pop('patient_profile_id', None)
    return redirect('index')


# ─── staff views ──────────────────────────────────────────────────────────────

def staff_login(request):
    error = None
    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            user = authenticate(request, username=form.cleaned_data['username'], password=form.cleaned_data['password'])
            if user:
                login(request, user)
                return redirect('staff_dashboard')
            else:
                from django.contrib.auth.models import User
                if not User.objects.exists():
                    request.session['is_staff_demo'] = True
                    return redirect('staff_dashboard')
                error = "Invalid credentials."
        else:
            error = "Please fill in all fields."
    else:
        form = LoginForm()
    return render(request, 'backend_app/staff_login.html', {'form': form, 'error': error})


def staff_dashboard(request):
    if not request.user.is_authenticated and not request.session.get('is_staff_demo'):
        return redirect('staff_login')
    today = datetime.date.today()
    status_filter = request.GET.get('status')
    priority_filter = request.GET.get('priority')
    appointments = Appointment.objects.filter(date=today)
    if status_filter:
        appointments = appointments.filter(status=status_filter)
    if priority_filter:
        appointments = appointments.filter(priority=priority_filter)
    appointments = appointments.order_by('-priority', 'id')
    resources = Resource.objects.all()
    total = Appointment.objects.filter(date=today).count()
    stats = {
        'total': total,
        'waiting': Appointment.objects.filter(date=today, status='Waiting').count(),
        'in_progress': Appointment.objects.filter(date=today).filter(Q(status='In Room')|Q(status='In Lab')|Q(status='In Radiology')).count(),
        'completed': Appointment.objects.filter(date=today, status='Completed').count(),
        'critical': Appointment.objects.filter(date=today, priority='High').exclude(status='Completed').count(),
    }
    return render(request, 'backend_app/staff_dashboard.html', {
        'appointments': appointments, 'resources': resources,
        'status_filter': status_filter, 'priority_filter': priority_filter, 'stats': stats
    })


def update_status(request, booking_id):
    if not request.user.is_authenticated and not request.session.get('is_staff_demo'):
        return redirect('staff_login')
    if request.method == 'POST':
        appt = get_object_or_404(Appointment, id=booking_id)
        new_status = request.POST.get('status')
        if new_status:
            appt.status = new_status
            appt.save()
    return redirect('staff_dashboard')


def update_resource(request, resource_id):
    if not request.user.is_authenticated and not request.session.get('is_staff_demo'):
        return redirect('staff_login')
    if request.method == 'POST':
        res = get_object_or_404(Resource, id=resource_id)
        action = request.POST.get('action')
        if action == 'increase':
            res.total_count += 1
        elif action == 'decrease' and res.total_count > 0:
            res.total_count -= 1
        res.save()
    return redirect('staff_dashboard')


def patient_profile(request, profile_id):
    if not request.user.is_authenticated and not request.session.get('is_staff_demo'):
        return redirect('staff_login')
    profile = get_object_or_404(PatientProfile, id=profile_id)
    return render(request, 'backend_app/patient_profile.html', {
        'profile': profile,
        'appointments': profile.appointments.all().order_by('-date')[:10],
        'health_metrics': profile.health_metrics.all()[:20],
        'medical_reports': profile.medical_reports.all()[:10],
    })


def patient_list(request):
    if not request.user.is_authenticated and not request.session.get('is_staff_demo'):
        return redirect('staff_login')
    return render(request, 'backend_app/patient_list.html', {'patients': PatientProfile.objects.all().order_by('-created_at')})


def upload_medical_report(request):
    if not request.user.is_authenticated and not request.session.get('is_staff_demo'):
        return redirect('staff_login')
    if request.method == 'POST':
        form = MedicalReportForm(request.POST, request.FILES)
        if form.is_valid():
            report = form.save(commit=False)
            report.uploaded_by = request.user.username if request.user.is_authenticated else 'Staff'
            report.save()
            return redirect('patient_profile', profile_id=report.patient_profile.id)
    else:
        form = MedicalReportForm()
    return render(request, 'backend_app/upload_report.html', {'form': form, 'patients': PatientProfile.objects.all().order_by('patient_name')})


def add_health_metric(request):
    if not request.user.is_authenticated and not request.session.get('is_staff_demo'):
        return redirect('staff_login')
    if request.method == 'POST':
        form = HealthMetricForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('patient_profile', profile_id=form.cleaned_data['patient_profile'].id)
    else:
        form = HealthMetricForm()
    return render(request, 'backend_app/add_health_metric.html', {'form': form, 'patients': PatientProfile.objects.all().order_by('patient_name')})


def health_metrics_api(request, profile_id):
    profile = get_object_or_404(PatientProfile, id=profile_id)
    metric_type = request.GET.get('type', 'heart_rate')
    metrics = HealthMetric.objects.filter(patient_profile=profile, metric_type=metric_type).order_by('recorded_at')[:30]
    if not metrics.exists():
        import random
        base_vals = {'heart_rate': 75, 'blood_pressure': 120, 'temperature': 98.6, 'oxygen_level': 98}
        unit_map = {'heart_rate': 'bpm', 'blood_pressure': 'mmHg', 'temperature': '°F', 'oxygen_level': '%'}
        labels = [(datetime.datetime.now() - datetime.timedelta(hours=i)).strftime('%H:%M') for i in range(10, 0, -1)]
        values = [base_vals.get(metric_type, 70) + random.randint(-5, 5) for _ in range(10)]
        unit = unit_map.get(metric_type, '')
    else:
        labels = [m.recorded_at.strftime('%H:%M') for m in metrics]
        values = [float(m.value) for m in metrics]
        unit = metrics[0].unit
    return JsonResponse({'labels': labels, 'values': values, 'unit': unit})


def api_clinical_brief(request, profile_id):
    """Generate an AI clinical brief for the patient profile page (staff view)."""
    profile = get_object_or_404(PatientProfile, id=profile_id)

    metrics = list(profile.health_metrics.all().order_by('-recorded_at')[:10])
    reports = list(profile.medical_reports.all().order_by('-report_date')[:5])
    appointments = list(profile.appointments.all().order_by('-date')[:5])

    metrics_text = ', '.join([f"{m.get_metric_type_display()}: {m.value} {m.unit}" for m in metrics]) or "None recorded"
    reports_text = ', '.join([f"{r.get_report_type_display()} ({r.report_date})" for r in reports]) or "None"
    visits_text = ', '.join([f"{a.department} on {a.date} ({a.status})" for a in appointments]) or "None"

    prompt = f"""You are a senior hospital AI assistant. Generate a concise clinical brief for the following patient. 
Respond ONLY with a JSON object (no markdown) with exactly these 5 keys:
- "chief_concern": one sentence about likely reason for visit based on departments visited
- "vitals_summary": one sentence summarising the vitals data
- "risk_flags": one sentence on any notable risks (allergies, abnormal vitals, or 'None identified')
- "recommended_followup": one sentence recommendation
- "notes": one brief general clinical note

Patient Data:
- Name: {profile.patient_name}, Age: {profile.patient_age}
- Blood Group: {profile.blood_group or 'Unknown'}
- Allergies: {profile.allergies or 'None reported'}
- Recent Vitals: {metrics_text}
- Reports on file: {reports_text}
- Visit History: {visits_text}"""

    import os, urllib.request
    api_key = os.environ.get('ANTHROPIC_API_KEY', '')

    if api_key:
        try:
            payload = json.dumps({
                "model": "claude-haiku-4-5-20251001",
                "max_tokens": 400,
                "messages": [{"role": "user", "content": prompt}]
            }).encode()
            req = urllib.request.Request(
                'https://api.anthropic.com/v1/messages', data=payload,
                headers={'Content-Type': 'application/json', 'x-api-key': api_key, 'anthropic-version': '2023-06-01'},
                method='POST'
            )
            with urllib.request.urlopen(req, timeout=15) as resp:
                result = json.loads(resp.read().decode())
                text = result['content'][0]['text'].strip().replace('```json', '').replace('```', '').strip()
                parsed = json.loads(text)
                html = f"""
<div style="display:flex;flex-direction:column;gap:0.6rem;">
  <div style="font-size:0.72rem;font-weight:700;color:#a0aec0;letter-spacing:0.08em;text-transform:uppercase;margin-bottom:0.25rem;">Nucleus AI · Generated Brief</div>
  <div><span style="font-size:0.7rem;font-weight:700;color:#3182ce;text-transform:uppercase;">Chief Concern</span><br><span style="font-size:0.83rem;color:#2d3748;">{parsed.get('chief_concern','—')}</span></div>
  <div><span style="font-size:0.7rem;font-weight:700;color:#38a169;text-transform:uppercase;">Vitals Summary</span><br><span style="font-size:0.83rem;color:#2d3748;">{parsed.get('vitals_summary','—')}</span></div>
  <div><span style="font-size:0.7rem;font-weight:700;color:#e53e3e;text-transform:uppercase;">Risk Flags</span><br><span style="font-size:0.83rem;color:#2d3748;">{parsed.get('risk_flags','—')}</span></div>
  <div><span style="font-size:0.7rem;font-weight:700;color:#805ad5;text-transform:uppercase;">Recommended Follow-up</span><br><span style="font-size:0.83rem;color:#2d3748;">{parsed.get('recommended_followup','—')}</span></div>
  <div><span style="font-size:0.7rem;font-weight:700;color:#718096;text-transform:uppercase;">Notes</span><br><span style="font-size:0.83rem;color:#718096;">{parsed.get('notes','—')}</span></div>
</div>"""
                return JsonResponse({'ok': True, 'html': html})
        except Exception as e:
            pass  # fall through to fallback

    # Fallback: rule-based brief
    risk = profile.allergies if profile.allergies else "None identified"
    dept = appointments[0].department if appointments else "General Medicine"
    html = f"""
<div style="display:flex;flex-direction:column;gap:0.6rem;">
  <div style="font-size:0.72rem;font-weight:700;color:#a0aec0;letter-spacing:0.08em;text-transform:uppercase;margin-bottom:0.25rem;">Auto-generated Brief (set ANTHROPIC_API_KEY for AI)</div>
  <div><span style="font-size:0.7rem;font-weight:700;color:#3182ce;text-transform:uppercase;">Chief Concern</span><br><span style="font-size:0.83rem;color:#2d3748;">Patient attending {dept}.</span></div>
  <div><span style="font-size:0.7rem;font-weight:700;color:#38a169;text-transform:uppercase;">Vitals on file</span><br><span style="font-size:0.83rem;color:#2d3748;">{metrics_text[:120]}</span></div>
  <div><span style="font-size:0.7rem;font-weight:700;color:#e53e3e;text-transform:uppercase;">Risk Flags</span><br><span style="font-size:0.83rem;color:#2d3748;">{risk}</span></div>
  <div><span style="font-size:0.7rem;font-weight:700;color:#805ad5;text-transform:uppercase;">Reports on file</span><br><span style="font-size:0.83rem;color:#2d3748;">{reports_text[:120]}</span></div>
</div>"""
    return JsonResponse({'ok': True, 'html': html})


def api_weekly_analytics(request):
    """Return 7-day OPD data, top departments, and peak hours for the analytics chart."""
    today = datetime.date.today()
    days = []
    counts = []
    for i in range(6, -1, -1):
        d = today - datetime.timedelta(days=i)
        c = Appointment.objects.filter(date=d).count()
        days.append(d.strftime('%a %d'))
        counts.append(c)

    top_depts = (
        Appointment.objects.filter(date__gte=today - datetime.timedelta(days=7))
        .values('department')
        .annotate(total=Count('id'))
        .order_by('-total')[:5]
    )

    return JsonResponse({
        'days': days,
        'counts': counts,
        'top_depts': list(top_depts),
    })
