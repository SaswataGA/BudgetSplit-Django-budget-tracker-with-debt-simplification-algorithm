from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.views.generic import CreateView, DeleteView, ListView, UpdateView

from .forms import BudgetForm, CategoryForm, ExpenseForm
from .models import Budget, Category, Expense


class UserScopedQuerysetMixin(LoginRequiredMixin):
    """
    Shared mixin for every CRUD view in this app: always scope the
    queryset to request.user, so there is NO code path where a user
    could view, edit, or delete another user's data merely by guessing
    a different primary key in the URL (a common real-world
    authorization bug -- "Insecure Direct Object Reference").
    """

    def get_queryset(self):
        return super().get_queryset().filter(user=self.request.user)


# ----------------------------- Categories -----------------------------

class CategoryListView(UserScopedQuerysetMixin, ListView):
    model = Category
    template_name = "budgets/category_list.html"
    context_object_name = "categories"


class CategoryCreateView(LoginRequiredMixin, CreateView):
    model = Category
    form_class = CategoryForm
    template_name = "budgets/category_form.html"
    success_url = reverse_lazy("budgets:category_list")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def form_valid(self, form):
        form.instance.user = self.request.user
        messages.success(self.request, f"Category '{form.instance.name}' created.")
        return super().form_valid(form)


class CategoryUpdateView(UserScopedQuerysetMixin, UpdateView):
    model = Category
    form_class = CategoryForm
    template_name = "budgets/category_form.html"
    success_url = reverse_lazy("budgets:category_list")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def form_valid(self, form):
        messages.success(self.request, f"Category '{form.instance.name}' updated.")
        return super().form_valid(form)


class CategoryDeleteView(UserScopedQuerysetMixin, DeleteView):
    model = Category
    template_name = "budgets/category_confirm_delete.html"
    success_url = reverse_lazy("budgets:category_list")

    def form_valid(self, form):
        messages.success(self.request, f"Category '{self.object.name}' deleted.")
        return super().form_valid(form)


# ----------------------------- Budgets -----------------------------

class BudgetListView(UserScopedQuerysetMixin, ListView):
    model = Budget
    template_name = "budgets/budget_list.html"
    context_object_name = "budgets"


class BudgetCreateView(LoginRequiredMixin, CreateView):
    model = Budget
    form_class = BudgetForm
    template_name = "budgets/budget_form.html"
    success_url = reverse_lazy("budgets:budget_list")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def form_valid(self, form):
        form.instance.user = self.request.user
        messages.success(self.request, "Budget created.")
        return super().form_valid(form)


class BudgetUpdateView(UserScopedQuerysetMixin, UpdateView):
    model = Budget
    form_class = BudgetForm
    template_name = "budgets/budget_form.html"
    success_url = reverse_lazy("budgets:budget_list")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def form_valid(self, form):
        messages.success(self.request, "Budget updated.")
        return super().form_valid(form)


class BudgetDeleteView(UserScopedQuerysetMixin, DeleteView):
    model = Budget
    template_name = "budgets/budget_confirm_delete.html"
    success_url = reverse_lazy("budgets:budget_list")

    def form_valid(self, form):
        messages.success(self.request, "Budget deleted.")
        return super().form_valid(form)


# ----------------------------- Expenses -----------------------------
# Implemented as function-based views (rather than CBVs like the
# sections above) because the list view needs custom search/filter/
# pagination logic that reads more clearly as explicit control flow
# than as generic-view method overrides.

@login_required
def expense_list(request):
    expenses = Expense.objects.filter(user=request.user).select_related("category")

    search_query = request.GET.get("q", "").strip()
    if search_query:
        expenses = expenses.filter(description__icontains=search_query)

    category_id = request.GET.get("category", "")
    if category_id:
        expenses = expenses.filter(category_id=category_id)

    start_date = request.GET.get("start", "")
    if start_date:
        expenses = expenses.filter(date__gte=start_date)

    end_date = request.GET.get("end", "")
    if end_date:
        expenses = expenses.filter(date__lte=end_date)

    paginator = Paginator(expenses, 10)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    categories = Category.objects.filter(user=request.user)

    return render(request, "budgets/expense_list.html", {
        "page_obj": page_obj,
        "categories": categories,
        "search_query": search_query,
        "selected_category": category_id,
        "start_date": start_date,
        "end_date": end_date,
    })


@login_required
def expense_create(request):
    if request.method == "POST":
        form = ExpenseForm(request.POST, user=request.user)
        if form.is_valid():
            expense = form.save(commit=False)
            expense.user = request.user
            expense.save()
            messages.success(request, "Expense added.")
            return redirect("budgets:expense_list")
    else:
        form = ExpenseForm(user=request.user)

    return render(request, "budgets/expense_form.html", {"form": form, "is_edit": False})


@login_required
def expense_update(request, pk):
    expense = get_object_or_404(Expense, pk=pk, user=request.user)

    if request.method == "POST":
        form = ExpenseForm(request.POST, instance=expense, user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "Expense updated.")
            return redirect("budgets:expense_list")
    else:
        form = ExpenseForm(instance=expense, user=request.user)

    return render(request, "budgets/expense_form.html", {"form": form, "is_edit": True})


@login_required
def expense_delete(request, pk):
    expense = get_object_or_404(Expense, pk=pk, user=request.user)

    if request.method == "POST":
        expense.delete()
        messages.success(request, "Expense deleted.")
        return redirect("budgets:expense_list")

    return render(request, "budgets/expense_confirm_delete.html", {"expense": expense})
