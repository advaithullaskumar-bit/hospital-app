from django.test import TestCase, Client
from django.urls import reverse
from .models import Appointment

class ProfessionalViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        from django.contrib.auth.models import User
        self.u = User.objects.create_user('admin', 'admin@example.com', '123')

    def test_public_access(self):
        # Index should be 200
        response = self.client.get(reverse('index'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "CityCare Hospital")
        # self.assertNotContains(response, "Staff Login") # Link is present in nav now

    def test_staff_login_page(self):
        response = self.client.get(reverse('staff_login'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Staff Portal")

    def test_staff_dashboard_access(self):
        # Without login -> Redirect
        response = self.client.get(reverse('staff_dashboard'))
        self.assertEqual(response.status_code, 302)

        # Login
        self.client.post(reverse('staff_login'), {'username': 'admin', 'password': '123'})
        
        # With login -> 200
        response = self.client.get(reverse('staff_dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Doctor's Dashboard")
