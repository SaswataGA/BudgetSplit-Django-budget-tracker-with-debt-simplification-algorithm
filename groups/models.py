from datetime import date

from django.contrib.auth.models import User
from django.core.validators import MinValueValidator
from django.db import models
from django.urls import reverse


class Group(models.Model):
    """A group of people sharing expenses, e.g. 'Roommates' or 'Japan Trip 2026'."""

    name = models.CharField(max_length=100)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name="created_groups")
    members = models.ManyToManyField(User, through="GroupMembership", related_name="expense_groups")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse("groups:group_detail", args=[self.pk])

    def is_member(self, user):
        return self.members.filter(pk=user.pk).exists()


class GroupMembership(models.Model):
    """
    Through-model for the Group <-> User many-to-many relationship.

    A plain ManyToManyField would work for "who is in this group", but
    using an explicit through-model lets us record WHEN each member
    joined, and gives us a natural place to add per-membership fields
    later (e.g. a "nickname within this group") without a schema
    migration that changes the relationship's shape.
    """

    group = models.ForeignKey(Group, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["group", "user"], name="unique_group_membership")
        ]

    def __str__(self):
        return f"{self.user.username} in {self.group.name}"


class GroupExpense(models.Model):
    """A single shared expense within a group, paid by one member and split among some/all members."""

    SPLIT_EQUAL = "equal"
    SPLIT_CUSTOM = "custom"
    SPLIT_TYPE_CHOICES = [
        (SPLIT_EQUAL, "Split equally"),
        (SPLIT_CUSTOM, "Custom amounts"),
    ]

    group = models.ForeignKey(Group, on_delete=models.CASCADE, related_name="expenses")
    paid_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name="paid_group_expenses")
    description = models.CharField(max_length=200)
    amount = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0.01)])
    date = models.DateField(default=date.today)
    split_type = models.CharField(max_length=10, choices=SPLIT_TYPE_CHOICES, default=SPLIT_EQUAL)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-date", "-created_at"]

    def __str__(self):
        return f"{self.description} ({self.amount}) in {self.group.name}"

    def get_absolute_url(self):
        return reverse("groups:group_detail", args=[self.group.pk])


class GroupExpenseSplit(models.Model):
    """
    One member's individual share of a GroupExpense.

    Storing each member's exact owed amount explicitly (rather than
    just recording the split_type and recomputing shares on the fly)
    means a group's split history stays accurate even if the group's
    membership changes later, or if a custom split was deliberately
    uneven. This mirrors how real bill-splitting apps store history.
    """

    expense = models.ForeignKey(GroupExpense, on_delete=models.CASCADE, related_name="splits")
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="expense_splits")
    amount_owed = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["expense", "user"], name="unique_split_per_user_per_expense")
        ]

    def __str__(self):
        return f"{self.user.username} owes {self.amount_owed} for {self.expense.description}"
