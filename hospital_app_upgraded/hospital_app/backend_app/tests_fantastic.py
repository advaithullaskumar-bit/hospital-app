from django.test import TestCase, Client
from django.urls import reverse

class FantasticFeatureTests(TestCase):
    def setUp(self):
        self.client = Client()
        from django.contrib.auth.models import User
        self.u = User.objects.create_user('demo', 'demo@example.com', 'demo')

    def test_lenient_login_success(self):
        # Should work with ANY username/password
        response = self.client.post(reverse('staff_login'), {'username': 'demo', 'password': 'demo'})
        self.assertEqual(response.status_code, 302) # Redirects to dashboard
        self.assertEqual(int(self.client.session['_auth_user_id']), self.u.pk)

    def test_lenient_login_failure(self):
        # Should fail if empty
        response = self.client.post(reverse('staff_login'), {'username': '', 'password': ''})
        self.assertEqual(response.status_code, 200) # stays on page
        self.assertContains(response, "Please fill in all fields.")
