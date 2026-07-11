from django.contrib.auth.models import User
from rest_framework import status
from rest_framework.test import APITestCase


class AuthTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="alice", email="alice@example.com", password="secretpass123"
        )
        self.login_url = "/api/auth/login/"
        self.refresh_url = "/api/auth/refresh/"

    def test_login_with_email_returns_token_pair(self):
        response = self.client.post(
            self.login_url,
            {"email": "alice@example.com", "password": "secretpass123"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)

    def test_login_is_case_insensitive_on_email(self):
        response = self.client.post(
            self.login_url,
            {"email": "ALICE@example.com", "password": "secretpass123"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_login_with_wrong_password_fails(self):
        response = self.client.post(
            self.login_url,
            {"email": "alice@example.com", "password": "nope"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertNotIn("access", response.data)

    def test_login_with_unknown_email_fails(self):
        response = self.client.post(
            self.login_url,
            {"email": "ghost@example.com", "password": "secretpass123"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_login_missing_fields_fails(self):
        response = self.client.post(self.login_url, {"email": ""}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_refresh_returns_new_access_token(self):
        login = self.client.post(
            self.login_url,
            {"email": "alice@example.com", "password": "secretpass123"},
            format="json",
        )
        refresh = login.data["refresh"]
        response = self.client.post(
            self.refresh_url, {"refresh": refresh}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)

    def test_inactive_user_cannot_login(self):
        self.user.is_active = False
        self.user.save()
        response = self.client.post(
            self.login_url,
            {"email": "alice@example.com", "password": "secretpass123"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_register_creates_user_and_returns_tokens(self):
        response = self.client.post(
            "/api/auth/register/",
            {"email": "new@example.com", "password": "freshpass123", "name": "New"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn("access", response.data)
        self.assertTrue(User.objects.filter(email="new@example.com").exists())

    def test_register_rejects_duplicate_email(self):
        response = self.client.post(
            "/api/auth/register/",
            {"email": "alice@example.com", "password": "freshpass123"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
