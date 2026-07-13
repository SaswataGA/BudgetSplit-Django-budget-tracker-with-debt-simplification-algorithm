from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from .models import Budget, Category, Expense


class CategoryTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="alice", password="testpass123")
        self.other_user = User.objects.create_user(username="bob", password="testpass123")
        self.client.login(username="alice", password="testpass123")

    def test_create_category(self):
        response = self.client.post(reverse("budgets:category_add"), {"name": "Groceries", "color": "#198754"}, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(Category.objects.filter(user=self.user, name="Groceries").exists())

    def test_duplicate_category_name_for_same_user_rejected(self):
        Category.objects.create(user=self.user, name="Rent", color="#0d6efd")
        response = self.client.post(reverse("budgets:category_add"), {"name": "Rent", "color": "#dc3545"})
        self.assertContains(response, "already have a category")
        self.assertEqual(Category.objects.filter(user=self.user, name="Rent").count(), 1)

    def test_same_category_name_allowed_for_different_users(self):
        Category.objects.create(user=self.other_user, name="Rent", color="#0d6efd")
        response = self.client.post(reverse("budgets:category_add"), {"name": "Rent", "color": "#dc3545"}, follow=True)
        self.assertTrue(Category.objects.filter(user=self.user, name="Rent").exists())

    def test_category_list_only_shows_own_categories(self):
        Category.objects.create(user=self.user, name="Mine", color="#0d6efd")
        Category.objects.create(user=self.other_user, name="NotMine", color="#dc3545")
        response = self.client.get(reverse("budgets:category_list"))
        self.assertContains(response, "Mine")
        self.assertNotContains(response, "NotMine")

    def test_cannot_edit_another_users_category(self):
        # IDOR (Insecure Direct Object Reference) test: bob's category
        # should be completely inaccessible to alice, even by guessing
        # the URL/pk directly.
        bobs_category = Category.objects.create(user=self.other_user, name="Bob's Category", color="#0d6efd")
        response = self.client.get(reverse("budgets:category_edit", args=[bobs_category.pk]))
        self.assertEqual(response.status_code, 404)

    def test_cannot_delete_another_users_category(self):
        bobs_category = Category.objects.create(user=self.other_user, name="Bob's Category", color="#0d6efd")
        response = self.client.post(reverse("budgets:category_delete", args=[bobs_category.pk]))
        self.assertEqual(response.status_code, 404)
        self.assertTrue(Category.objects.filter(pk=bobs_category.pk).exists())  # still exists, untouched


class BudgetTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="alice", password="testpass123")
        self.category = Category.objects.create(user=self.user, name="Groceries", color="#198754")
        self.client.login(username="alice", password="testpass123")

    def test_create_budget(self):
        response = self.client.post(reverse("budgets:budget_add"), {
            "category": self.category.pk, "monthly_limit": "300.00", "month": "7", "year": "2026",
        }, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(Budget.objects.filter(user=self.user, category=self.category).exists())

    def test_duplicate_budget_for_same_category_and_month_rejected(self):
        Budget.objects.create(user=self.user, category=self.category, monthly_limit=Decimal("300.00"), year=2026, month=7)
        response = self.client.post(reverse("budgets:budget_add"), {
            "category": self.category.pk, "monthly_limit": "500.00", "month": "7", "year": "2026",
        })
        self.assertContains(response, "already have a budget")
        self.assertEqual(Budget.objects.filter(user=self.user, category=self.category, year=2026, month=7).count(), 1)

    def test_spent_amount_and_percent_used_calculation(self):
        budget = Budget.objects.create(user=self.user, category=self.category, monthly_limit=Decimal("200.00"), year=2026, month=7)
        Expense.objects.create(user=self.user, category=self.category, amount=Decimal("50.00"), date="2026-07-05")
        Expense.objects.create(user=self.user, category=self.category, amount=Decimal("30.00"), date="2026-07-10")

        self.assertEqual(budget.spent_amount, Decimal("80.00"))
        self.assertEqual(budget.percent_used, Decimal("40.0"))
        self.assertFalse(budget.is_over_budget)

    def test_is_over_budget_flag(self):
        budget = Budget.objects.create(user=self.user, category=self.category, monthly_limit=Decimal("100.00"), year=2026, month=7)
        Expense.objects.create(user=self.user, category=self.category, amount=Decimal("150.00"), date="2026-07-05")
        self.assertTrue(budget.is_over_budget)
        self.assertEqual(budget.percent_used, 100)  # capped at 100 even though 150% was spent

    def test_expense_outside_budget_month_not_counted(self):
        budget = Budget.objects.create(user=self.user, category=self.category, monthly_limit=Decimal("200.00"), year=2026, month=7)
        Expense.objects.create(user=self.user, category=self.category, amount=Decimal("999.00"), date="2026-08-01")  # different month
        self.assertEqual(budget.spent_amount, 0)


class ExpenseTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="alice", password="testpass123")
        self.category = Category.objects.create(user=self.user, name="Groceries", color="#198754")
        self.client.login(username="alice", password="testpass123")

    def test_create_expense(self):
        response = self.client.post(reverse("budgets:expense_add"), {
            "category": self.category.pk, "amount": "45.50", "description": "Weekly shop", "date": "2026-07-10",
        }, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(Expense.objects.filter(user=self.user, description="Weekly shop").exists())

    def test_expense_list_search_filters_by_description(self):
        Expense.objects.create(user=self.user, category=self.category, amount=10, description="Coffee shop", date="2026-07-01")
        Expense.objects.create(user=self.user, category=self.category, amount=20, description="Bookstore", date="2026-07-02")

        response = self.client.get(reverse("budgets:expense_list"), {"q": "coffee"})
        self.assertContains(response, "Coffee shop")
        self.assertNotContains(response, "Bookstore")

    def test_expense_list_filters_by_category(self):
        other_category = Category.objects.create(user=self.user, name="Entertainment", color="#dc3545")
        Expense.objects.create(user=self.user, category=self.category, amount=10, description="Groceries item", date="2026-07-01")
        Expense.objects.create(user=self.user, category=other_category, amount=20, description="Movie night", date="2026-07-02")

        response = self.client.get(reverse("budgets:expense_list"), {"category": other_category.pk})
        self.assertContains(response, "Movie night")
        self.assertNotContains(response, "Groceries item")

    def test_expense_list_pagination(self):
        for i in range(15):
            Expense.objects.create(user=self.user, category=self.category, amount=1, description=f"Item {i}", date="2026-07-01")

        response = self.client.get(reverse("budgets:expense_list"))
        self.assertEqual(len(response.context["page_obj"]), 10)  # page size is 10
        self.assertTrue(response.context["page_obj"].has_other_pages())

    def test_cannot_edit_another_users_expense(self):
        other_user = User.objects.create_user(username="bob", password="testpass123")
        other_category = Category.objects.create(user=other_user, name="Bob's Category", color="#0d6efd")
        bobs_expense = Expense.objects.create(user=other_user, category=other_category, amount=10, date="2026-07-01")

        response = self.client.get(reverse("budgets:expense_edit", args=[bobs_expense.pk]))
        self.assertEqual(response.status_code, 404)
