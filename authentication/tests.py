from django.test import TestCase
from django.contrib.auth.models import User
from rest_framework.test import APIClient
from rest_framework import status
from .models import RegistrationVerifyCode, Profile, PasswordResetCode

class AuthTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.register_url = '/auth/register/'
        self.verify_url = '/auth/register/verify/'
        self.login_url = '/auth/login/'

    def test_registration_flow(self):
        # 1. Register
        data = {
            'email': 'test@example.com',
            'first_name': 'Test',
            'last_name': 'User',
            'password': 'password123',
            'confirm_password': 'password123',
            'gender': 'Male'
        }
        response = self.client.post(self.register_url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        user = User.objects.get(email='test@example.com')
        self.assertFalse(user.is_active)
        
        verify_code = RegistrationVerifyCode.objects.get(user=user).code
        
        # 2. Verify
        verify_data = {
            'email': 'test@example.com',
            'code': verify_code,
            'gender': 'Male'
        }
        response = self.client.post(self.verify_url, verify_data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        user.refresh_from_db()
        self.assertTrue(user.is_active)
        self.assertTrue(Profile.objects.filter(user=user).exists())

        # 3. Login
        login_data = {
            'email': 'test@example.com',
            'password': 'password123'
        }
        response = self.client.post(self.login_url, login_data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)

    def test_password_reset_flow(self):
        user = User.objects.create_user(username='reset@example.com', email='reset@example.com', password='oldpassword')
        
        # 1. Request reset
        response = self.client.post('/auth/password-reset/request/', {'email': 'reset@example.com'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        reset_code = PasswordResetCode.objects.get(user=user).code
        
        # 2. Verify code
        response = self.client.post('/auth/password-reset/verify/', {'email': 'reset@example.com', 'code': reset_code})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # 3. Change password
        change_data = {
            'email': 'reset@example.com',
            'code': reset_code,
            'new_password': 'newpassword123',
            'confirm_password': 'newpassword123'
        }
        response = self.client.post('/auth/password-reset/change/', change_data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # 4. Verify login with new password
        login_data = {'email': 'reset@example.com', 'password': 'newpassword123'}
        response = self.client.post(self.login_url, login_data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_authenticated_password_change(self):
        user = User.objects.create_user(username='auth@example.com', email='auth@example.com', password='oldpassword')
        self.client.force_authenticate(user=user)
        
        change_data = {
            'new_password': 'newpassword123',
            'confirm_password': 'newpassword123'
        }
        response = self.client.post('/auth/password-reset/change/', change_data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verify login with new password
        self.client.force_authenticate(user=None)
        login_data = {'email': 'auth@example.com', 'password': 'newpassword123'}
        response = self.client.post(self.login_url, login_data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
