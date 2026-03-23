from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('api/bookings', views.api_bookings, name='api_bookings'),
    path('api/book', views.api_book, name='api_book'),
    path('api/triage', views.api_triage, name='api_triage'),
    path('api/chatbot', views.chatbot_api, name='chatbot_api'),
    path('api/tv-data', views.api_tv_data, name='api_tv_data'),
    path('tv', views.tv_board, name='tv_board'),

    # Staff
    path('staff/login', views.staff_login, name='staff_login'),
    path('staff/dashboard', views.staff_dashboard, name='staff_dashboard'),
    path('staff/update/<int:booking_id>', views.update_status, name='update_status'),
    path('staff/update-resource/<int:resource_id>', views.update_resource, name='update_resource'),
    path('staff/patients', views.patient_list, name='patient_list'),
    path('staff/patient/<int:profile_id>', views.patient_profile, name='patient_profile'),
    path('staff/upload-report', views.upload_medical_report, name='upload_medical_report'),
    path('staff/add-metric', views.add_health_metric, name='add_health_metric'),

    # Patient
    path('patient/login', views.patient_dashboard_access, name='patient_login'),
    path('patient/dashboard', views.patient_dashboard, name='patient_dashboard'),
    path('patient/logout', views.patient_logout, name='patient_logout'),

    # APIs
    path('api/health-metrics/<int:profile_id>', views.health_metrics_api, name='health_metrics_api'),

    path('api/clinical-brief/<int:profile_id>', views.api_clinical_brief, name='api_clinical_brief'),
    path('api/weekly-analytics', views.api_weekly_analytics, name='api_weekly_analytics'),
]
