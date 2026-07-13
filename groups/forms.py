from decimal import Decimal

from django import forms
from django.contrib.auth.models import User

from .models import Group, GroupExpense


class GroupForm(forms.ModelForm):
    class Meta:
        model = Group
        fields = ["name"]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control", "placeholder": "e.g. Roommates, Japan Trip 2026"}),
        }


class AddMemberForm(forms.Form):
    """Adds an existing user to a group by username."""

    username = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "Username to add"}),
    )

    def __init__(self, *args, group=None, **kwargs):
        self.group = group
        super().__init__(*args, **kwargs)

    def clean_username(self):
        username = self.cleaned_data["username"].strip()
        try:
            user = User.objects.get(username__iexact=username)
        except User.DoesNotExist:
            raise forms.ValidationError(f"No user found with username '{username}'.")

        if self.group and self.group.is_member(user):
            raise forms.ValidationError(f"'{username}' is already a member of this group.")

        self.cleaned_data["user"] = user
        return username


class GroupExpenseForm(forms.ModelForm):
    """
    The base expense fields (description, amount, who paid, split type,
    date). Individual member share amounts for a CUSTOM split are
    handled separately in the view, since the number of share fields
    depends on how many members are in the group — a fully dynamic set
    of fields isn't a natural fit for a single static ModelForm.
    """

    class Meta:
        model = GroupExpense
        fields = ["description", "amount", "paid_by", "split_type", "date"]
        widgets = {
            "description": forms.TextInput(attrs={"class": "form-control", "placeholder": "e.g. Dinner, Groceries, Uber"}),
            "amount": forms.NumberInput(attrs={"class": "form-control", "step": "0.01", "min": "0.01"}),
            "paid_by": forms.Select(attrs={"class": "form-select"}),
            "split_type": forms.Select(attrs={"class": "form-select", "id": "id_split_type"}),
            "date": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
        }

    def __init__(self, *args, group=None, **kwargs):
        super().__init__(*args, **kwargs)
        if group is not None:
            self.fields["paid_by"].queryset = group.members.all()


def build_custom_split_forms(group, data=None):
    """
    Builds one small form per group member for entering a custom split
    amount, used only when split_type == 'custom'. Returned as a dict
    of {user_id: BoundField-like form} rather than a Django formset,
    since each field is genuinely independent (no shared validation
    across rows beyond "do they sum to the total", which the view
    checks explicitly).
    """
    forms_by_user = {}
    for member in group.members.all():
        prefix = f"split_{member.id}"
        field = forms.DecimalField(
            max_digits=10, decimal_places=2, min_value=Decimal("0"), required=False,
            widget=forms.NumberInput(attrs={"class": "form-control", "step": "0.01", "min": "0"}),
        )
        value = data.get(prefix) if data else None
        forms_by_user[member.id] = {
            "member": member,
            "field": field,
            "value": value,
        }
    return forms_by_user
