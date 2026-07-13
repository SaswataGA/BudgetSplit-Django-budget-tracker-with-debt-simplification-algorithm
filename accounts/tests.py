from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from .models import Profile


class RegistrationTests(TestCase):
    """Tests for account registration and the auto-created Profile signal."""

    def test_registration_creates_user_and_logs_in(self):
        response = self.client.post(reverse("accounts:register"), {
            "username": "newuser", "email": "newuser@example.com",
            "password1": "ComplexPass123!", "password2": "ComplexPass123!",
        }, follow=True)

        self.assertEqual(response.status_code, 200)
        self.assertTrue(User.objects.filter(username="newuser").exists())
        # follow=True should land us on the dashboard after auto-login
        self.assertRedirects(response, reverse("accounts:dashboard"))

    def test_registration_auto_creates_profile_via_signal(self):
        self.client.post(reverse("accounts:register"), {
            "username": "signaltest", "email": "signal@example.com",
            "password1": "ComplexPass123!", "password2": "ComplexPass123!",
        })
        user = User.objects.get(username="signaltest")
        self.assertTrue(Profile.objects.filter(user=user).exists())

    def test_registration_rejects_mismatched_passwords(self):
        response = self.client.post(reverse("accounts:register"), {
            "username": "baduser", "email": "bad@example.com",
            "password1": "ComplexPass123!", "password2": "DifferentPass456!",
        })
        self.assertEqual(response.status_code, 200)  # re-renders form with errors
        self.assertFalse(User.objects.filter(username="baduser").exists())

    def test_registration_rejects_duplicate_email(self):
        User.objects.create_user(username="existing", email="taken@example.com", password="x")
        response = self.client.post(reverse("accounts:register"), {
            "username": "another", "email": "taken@example.com",
            "password1": "ComplexPass123!", "password2": "ComplexPass123!",
        })
        self.assertFalse(User.objects.filter(username="another").exists())
        self.assertContains(response, "already exists")

    def test_superuser_created_outside_registration_view_still_gets_profile(self):
        # Confirms the signal fires for ANY User creation path, not just
        # our own registration view (e.g. createsuperuser, admin, shell).
        user = User.objects.create_superuser(username="admin_test", email="admin@example.com", password="x")
        self.assertTrue(Profile.objects.filter(user=user).exists())


class DashboardAccessTests(TestCase):
    """Tests for dashboard authentication requirements."""

    def setUp(self):
        self.user = User.objects.create_user(username="dashuser", password="testpass123")

    def test_dashboard_requires_login(self):
        response = self.client.get(reverse("accounts:dashboard"))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("accounts:login"), response.url)

    def test_dashboard_accessible_when_logged_in(self):
        self.client.login(username="dashuser", password="testpass123")
        response = self.client.get(reverse("accounts:dashboard"))
        self.assertEqual(response.status_code, 200)

    def test_root_url_redirects_anonymous_to_login(self):
        response = self.client.get(reverse("home"))
        self.assertEqual(response.status_code, 302)

    def test_root_url_redirects_authenticated_to_dashboard(self):
        self.client.login(username="dashuser", password="testpass123")
        response = self.client.get(reverse("home"), follow=True)
        self.assertRedirects(response, reverse("accounts:dashboard"))


class ProfileUpdateTests(TestCase):
    """Tests for editing profile information."""

    def setUp(self):
        self.user = User.objects.create_user(username="profileuser", password="testpass123", email="old@example.com")
        self.client.login(username="profileuser", password="testpass123")

    def test_profile_update_changes_currency_and_bio(self):
        response = self.client.post(reverse("accounts:profile"), {
            "first_name": "Test", "last_name": "User", "email": "old@example.com",
            "currency": "EUR", "bio": "Hello world",
        }, follow=True)
        self.assertEqual(response.status_code, 200)
        self.user.profile.refresh_from_db()
        self.assertEqual(self.user.profile.currency, "EUR")
        self.assertEqual(self.user.profile.bio, "Hello world")

    def test_profile_update_rejects_email_taken_by_another_user(self):
        User.objects.create_user(username="other", password="x", email="taken@example.com")
        response = self.client.post(reverse("accounts:profile"), {
            "first_name": "Test", "last_name": "User", "email": "taken@example.com",
            "currency": "USD", "bio": "",
        })
        self.assertContains(response, "already exists")
