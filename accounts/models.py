from django.contrib.auth.models import User
from django.db import models
from django.urls import reverse


class Profile(models.Model):
    """
    Extends Django's built-in User model with additional fields via a
    OneToOneField, rather than swapping AUTH_USER_MODEL entirely.

    WHY THIS APPROACH: swapping the User model (a custom AUTH_USER_MODEL)
    is the "correct" long-term choice for a brand-new project, but it
    must be done before the FIRST migration ever runs -- it's extremely
    painful to change later. The Profile-extension pattern used here is
    the standard, safer alternative for adding extra fields to users
    without that irreversible up-front commitment, and is what most
    real Django projects that started with the default User model use.
    """

    CURRENCY_CHOICES = [
        ("USD", "US Dollar ($)"),
        ("EUR", "Euro (EUR)"),
        ("GBP", "British Pound (GBP)"),
        ("BDT", "Bangladeshi Taka (BDT)"),
        ("INR", "Indian Rupee (INR)"),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    avatar = models.ImageField(upload_to="avatars/", blank=True, null=True)
    currency = models.CharField(max_length=3, choices=CURRENCY_CHOICES, default="USD")
    bio = models.CharField(max_length=200, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username}'s profile"

    def get_absolute_url(self):
        return reverse("accounts:profile")

    @property
    def currency_symbol(self):
        symbols = {"USD": "$", "EUR": "\u20ac", "GBP": "\u00a3", "BDT": "\u09f3", "INR": "\u20b9"}
        return symbols.get(self.currency, "$")
