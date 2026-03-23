from django.test import TestCase, Client
from django.urls import reverse
from .models import Appointment
import json
import datetime

class BookingTests(TestCase):
    def setUp(self):
        self.client = Client()

    def test_booking_flow(self):
        # 1. Check empty
        response = self.client.get(reverse('api_bookings'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(json.loads(response.content), [])

        # 2. Book
        # Use dynamic date
        today_str = datetime.date.today().strftime('%Y-%m-%d')
        data = {
            'pname': 'Test User',
            'page': '30',
            'dept': 'General',
            'doc': 'Dr. Test',
            'date': today_str,
            'slot': 'Morning'
        }
        response = self.client.post(reverse('api_book'), data)
        self.assertEqual(response.status_code, 200)
        res_json = json.loads(response.content)
        self.assertTrue(res_json['ok'])
        token = res_json['token']
        print(f"Got Token: {token}")

        # 3. Check bookings again
        response = self.client.get(reverse('api_bookings'))
        self.assertEqual(response.status_code, 200)
        bookings = json.loads(response.content)
        self.assertEqual(len(bookings), 1)
        self.assertEqual(bookings[0]['token'], token)
        # Expect masked name for privacy
        self.assertEqual(bookings[0]['name'], 'T***r')
