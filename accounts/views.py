from datetime import date

from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from budgets.models import Budget, Expense
from groups.services import compute_net_balances

from .forms import ProfileForm, RegisterForm, UserUpdateForm


def register(request):
    if request.user.is_authenticated:
        return redirect("accounts:dashboard")

    if request.method == "POST":
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, f"Welcome, {user.username}! Your account has been created.")
            return redirect("accounts:dashboard")
    else:
        form = RegisterForm()

    return render(request, "registration/register.html", {"form": form})


@login_required
def dashboard(request):
    today = date.today()

    current_budgets = Budget.objects.filter(user=request.user, year=today.year, month=today.month).select_related("category")
    total_budgeted = sum((b.monthly_limit for b in current_budgets), start=0)
    total_spent = sum((b.spent_amount for b in current_budgets), start=0)

    recent_expenses = Expense.objects.filter(user=request.user).select_related("category")[:5]
    over_budget_categories = [b for b in current_budgets if b.is_over_budget]

    group_summaries = []
    total_net_across_groups = 0
    for group in request.user.expense_groups.all():
        balances = compute_net_balances(group)
        my_balance = balances.get(request.user.id, 0)
        if my_balance != 0:
            group_summaries.append({"group": group, "balance": my_balance})
        total_net_across_groups += my_balance

    return render(request, "accounts/dashboard.html", {
        "current_budgets": current_budgets,
        "total_budgeted": total_budgeted,
        "total_spent": total_spent,
        "recent_expenses": recent_expenses,
        "over_budget_categories": over_budget_categories,
        "group_summaries": group_summaries,
        "total_net_across_groups": total_net_across_groups,
        "current_month_name": today.strftime("%B %Y"),
    })


@login_required
def profile(request):
    if request.method == "POST":
        user_form = UserUpdateForm(request.POST, instance=request.user)
        profile_form = ProfileForm(request.POST, request.FILES, instance=request.user.profile)

        if user_form.is_valid() and profile_form.is_valid():
            user_form.save()
            profile_form.save()
            messages.success(request, "Profile updated.")
            return redirect("accounts:profile")
    else:
        user_form = UserUpdateForm(instance=request.user)
        profile_form = ProfileForm(instance=request.user.profile)

    return render(request, "accounts/profile.html", {"user_form": user_form, "profile_form": profile_form})
