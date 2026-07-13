from datetime import date

from django.contrib.auth.models import User
from django.core.validators import MinValueValidator
from django.db import models
from django.urls import reverse


class Category(models.Model):
    """A personal spending category, e.g. 'Groceries', 'Rent', 'Entertainment'."""

    COLOR_CHOICES = [
        ("#0d6efd", "Blue"), ("#198754", "Green"), ("#dc3545", "Red"),
        ("#fd7e14", "Orange"), ("#6f42c1", "Purple"), ("#20c997", "Teal"),
        ("#d63384", "Pink"), ("#6c757d", "Gray"),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="categories")
    name = models.CharField(max_length=50)
    color = models.CharField(max_length=7, choices=COLOR_CHOICES, default="#0d6efd")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = "categories"
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(fields=["user", "name"], name="unique_category_per_user")
        ]

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse("budgets:category_list")


class Budget(models.Model):
    """A monthly spending limit set by a user for one category."""

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="budgets")
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name="budgets")
    monthly_limit = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0.01)])
    year = models.PositiveIntegerField(default=date.today().year)
    month = models.PositiveSmallIntegerField(default=date.today().month)  # 1-12
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-year", "-month", "category__name"]
        constraints = [
            models.UniqueConstraint(fields=["user", "category", "year", "month"], name="unique_budget_per_month")
        ]

    def __str__(self):
        return f"{self.category.name} budget for {self.month}/{self.year}"

    def get_absolute_url(self):
        return reverse("budgets:budget_list")

    @property
    def spent_amount(self):
        """Total actually spent in this category during this budget's month."""
        total = Expense.objects.filter(
            user=self.user, category=self.category, date__year=self.year, date__month=self.month,
        ).aggregate(models.Sum("amount"))["amount__sum"]
        return total or 0

    @property
    def remaining_amount(self):
        return self.monthly_limit - self.spent_amount

    @property
    def percent_used(self):
        if self.monthly_limit == 0:
            return 0
        return min(100, round((self.spent_amount / self.monthly_limit) * 100, 1))

    @property
    def is_over_budget(self):
        return self.spent_amount > self.monthly_limit


class Expense(models.Model):
    """A single personal expense record."""

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="expenses")
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name="expenses")
    amount = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0.01)])
    description = models.CharField(max_length=200, blank=True)
    date = models.DateField(default=date.today)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-date", "-created_at"]

    def __str__(self):
        return f"{self.category.name}: {self.amount} on {self.date}"

    def get_absolute_url(self):
        return reverse("budgets:expense_list")
