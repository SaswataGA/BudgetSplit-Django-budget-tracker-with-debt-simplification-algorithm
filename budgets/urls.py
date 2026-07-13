from django.urls import path

from . import views

app_name = "budgets"

urlpatterns = [
    # Categories
    path("categories/", views.CategoryListView.as_view(), name="category_list"),
    path("categories/add/", views.CategoryCreateView.as_view(), name="category_add"),
    path("categories/<int:pk>/edit/", views.CategoryUpdateView.as_view(), name="category_edit"),
    path("categories/<int:pk>/delete/", views.CategoryDeleteView.as_view(), name="category_delete"),

    # Budgets
    path("", views.BudgetListView.as_view(), name="budget_list"),
    path("add/", views.BudgetCreateView.as_view(), name="budget_add"),
    path("<int:pk>/edit/", views.BudgetUpdateView.as_view(), name="budget_edit"),
    path("<int:pk>/delete/", views.BudgetDeleteView.as_view(), name="budget_delete"),

    # Expenses
    path("expenses/", views.expense_list, name="expense_list"),
    path("expenses/add/", views.expense_create, name="expense_add"),
    path("expenses/<int:pk>/edit/", views.expense_update, name="expense_edit"),
    path("expenses/<int:pk>/delete/", views.expense_delete, name="expense_delete"),
]
