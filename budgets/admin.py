from django.contrib import admin

from .models import Budget, Category, Expense


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ["name", "user", "color", "created_at"]
    list_filter = ["color"]
    search_fields = ["name", "user__username"]


@admin.register(Budget)
class BudgetAdmin(admin.ModelAdmin):
    list_display = ["category", "user", "monthly_limit", "month", "year", "spent_amount", "percent_used"]
    list_filter = ["year", "month"]
    search_fields = ["user__username", "category__name"]


@admin.register(Expense)
class ExpenseAdmin(admin.ModelAdmin):
    list_display = ["description", "category", "user", "amount", "date"]
    list_filter = ["category", "date"]
    search_fields = ["description", "user__username"]
    date_hierarchy = "date"
