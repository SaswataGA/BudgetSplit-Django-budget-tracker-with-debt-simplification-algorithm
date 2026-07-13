from datetime import date

from django import forms

from .models import Budget, Category, Expense

MONTH_CHOICES = [(i, date(2000, i, 1).strftime("%B")) for i in range(1, 13)]


class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ["name", "color"]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control", "placeholder": "e.g. Groceries"}),
            "color": forms.Select(attrs={"class": "form-select"}),
        }

    def __init__(self, *args, user=None, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)

    def clean_name(self):
        name = self.cleaned_data["name"].strip()
        existing = Category.objects.filter(user=self.user, name__iexact=name)
        if self.instance.pk:
            existing = existing.exclude(pk=self.instance.pk)
        if existing.exists():
            raise forms.ValidationError("You already have a category with this name.")
        return name


class BudgetForm(forms.ModelForm):
    month = forms.ChoiceField(choices=MONTH_CHOICES, widget=forms.Select(attrs={"class": "form-select"}))

    class Meta:
        model = Budget
        fields = ["category", "monthly_limit", "month", "year"]
        widgets = {
            "category": forms.Select(attrs={"class": "form-select"}),
            "monthly_limit": forms.NumberInput(attrs={"class": "form-control", "step": "0.01", "min": "0.01"}),
            "year": forms.NumberInput(attrs={"class": "form-control", "min": "2020", "max": "2100"}),
        }

    def __init__(self, *args, user=None, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)
        if user is not None:
            self.fields["category"].queryset = Category.objects.filter(user=user)

    def clean(self):
        cleaned_data = super().clean()
        category = cleaned_data.get("category")
        year = cleaned_data.get("year")
        month = cleaned_data.get("month")

        if category and year and month:
            existing = Budget.objects.filter(user=self.user, category=category, year=year, month=month)
            if self.instance.pk:
                existing = existing.exclude(pk=self.instance.pk)
            if existing.exists():
                raise forms.ValidationError(
                    f"You already have a budget for '{category.name}' in {date(2000, int(month), 1).strftime('%B')} {year}."
                )
        return cleaned_data


class ExpenseForm(forms.ModelForm):
    class Meta:
        model = Expense
        fields = ["category", "amount", "description", "date"]
        widgets = {
            "category": forms.Select(attrs={"class": "form-select"}),
            "amount": forms.NumberInput(attrs={"class": "form-control", "step": "0.01", "min": "0.01"}),
            "description": forms.TextInput(attrs={"class": "form-control", "placeholder": "Optional note"}),
            "date": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        if user is not None:
            self.fields["category"].queryset = Category.objects.filter(user=user)
