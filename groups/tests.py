from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from .models import Group, GroupExpense, GroupExpenseSplit, GroupMembership


class GroupCreationTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="alice", password="testpass123")
        self.client.login(username="alice", password="testpass123")

    def test_create_group_auto_adds_creator_as_member(self):
        response = self.client.post(reverse("groups:group_create"), {"name": "Roommates"}, follow=True)
        self.assertEqual(response.status_code, 200)
        group = Group.objects.get(name="Roommates")
        self.assertTrue(group.is_member(self.user))
        self.assertEqual(group.created_by, self.user)


class GroupMembershipTests(TestCase):
    def setUp(self):
        self.alice = User.objects.create_user(username="alice", password="testpass123")
        self.bob = User.objects.create_user(username="bob", password="testpass123")
        self.group = Group.objects.create(name="Trip", created_by=self.alice)
        GroupMembership.objects.create(group=self.group, user=self.alice)
        self.client.login(username="alice", password="testpass123")

    def test_add_existing_user_by_username(self):
        response = self.client.post(reverse("groups:group_add_member", args=[self.group.pk]), {"username": "bob"}, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(self.group.is_member(self.bob))

    def test_add_nonexistent_username_fails_gracefully(self):
        response = self.client.post(reverse("groups:group_add_member", args=[self.group.pk]), {"username": "ghost"}, follow=True)
        self.assertEqual(response.status_code, 200)  # redirects back, doesn't crash
        self.assertFalse(self.group.members.filter(username="ghost").exists())

    def test_cannot_add_same_member_twice(self):
        GroupMembership.objects.create(group=self.group, user=self.bob)
        response = self.client.post(reverse("groups:group_add_member", args=[self.group.pk]), {"username": "bob"}, follow=True)
        self.assertEqual(self.group.members.filter(username="bob").count(), 1)

    def test_non_member_cannot_view_group_detail(self):
        # Carol isn't a member of this group at all.
        User.objects.create_user(username="carol", password="testpass123")
        self.client.logout()
        self.client.login(username="carol", password="testpass123")
        response = self.client.get(reverse("groups:group_detail", args=[self.group.pk]))
        # 404, not 403 -- deliberately doesn't confirm the group exists to a non-member.
        self.assertEqual(response.status_code, 404)

    def test_anonymous_user_redirected_to_login(self):
        self.client.logout()
        response = self.client.get(reverse("groups:group_detail", args=[self.group.pk]))
        self.assertEqual(response.status_code, 302)


class GroupExpenseViewTests(TestCase):
    def setUp(self):
        self.alice = User.objects.create_user(username="alice", password="testpass123")
        self.bob = User.objects.create_user(username="bob", password="testpass123")
        self.group = Group.objects.create(name="Trip", created_by=self.alice)
        GroupMembership.objects.create(group=self.group, user=self.alice)
        GroupMembership.objects.create(group=self.group, user=self.bob)
        self.client.login(username="alice", password="testpass123")

    def test_add_expense_with_equal_split_creates_correct_splits(self):
        response = self.client.post(reverse("groups:group_expense_add", args=[self.group.pk]), {
            "description": "Dinner", "amount": "50.00", "paid_by": self.alice.pk,
            "split_type": "equal", "date": "2026-07-10",
        }, follow=True)
        self.assertEqual(response.status_code, 200)

        expense = GroupExpense.objects.get(group=self.group, description="Dinner")
        splits = {s.user: s.amount_owed for s in expense.splits.all()}
        self.assertEqual(splits[self.alice], Decimal("25.00"))
        self.assertEqual(splits[self.bob], Decimal("25.00"))

    def test_add_expense_with_valid_custom_split(self):
        response = self.client.post(reverse("groups:group_expense_add", args=[self.group.pk]), {
            "description": "Groceries", "amount": "100.00", "paid_by": self.bob.pk,
            "split_type": "custom", "date": "2026-07-10",
            f"split_{self.alice.pk}": "70.00", f"split_{self.bob.pk}": "30.00",
        }, follow=True)
        self.assertEqual(response.status_code, 200)

        expense = GroupExpense.objects.get(group=self.group, description="Groceries")
        splits = {s.user: s.amount_owed for s in expense.splits.all()}
        self.assertEqual(splits[self.alice], Decimal("70.00"))
        self.assertEqual(splits[self.bob], Decimal("30.00"))

    def test_custom_split_not_summing_to_total_is_rejected(self):
        response = self.client.post(reverse("groups:group_expense_add", args=[self.group.pk]), {
            "description": "Groceries", "amount": "100.00", "paid_by": self.bob.pk,
            "split_type": "custom", "date": "2026-07-10",
            f"split_{self.alice.pk}": "70.00", f"split_{self.bob.pk}": "20.00",  # only sums to 90
        })
        self.assertEqual(response.status_code, 200)  # re-renders form, doesn't crash
        self.assertFalse(GroupExpense.objects.filter(group=self.group, description="Groceries").exists())
        self.assertContains(response, "must add up")

    def test_deleting_expense_cascades_to_splits(self):
        expense = GroupExpense.objects.create(
            group=self.group, paid_by=self.alice, description="Test", amount=Decimal("20.00"), split_type="equal"
        )
        GroupExpenseSplit.objects.create(expense=expense, user=self.alice, amount_owed=Decimal("10.00"))
        GroupExpenseSplit.objects.create(expense=expense, user=self.bob, amount_owed=Decimal("10.00"))

        self.client.post(reverse("groups:group_expense_delete", args=[self.group.pk, expense.pk]))

        self.assertFalse(GroupExpense.objects.filter(pk=expense.pk).exists())
        self.assertEqual(GroupExpenseSplit.objects.filter(expense_id=expense.pk).count(), 0)
