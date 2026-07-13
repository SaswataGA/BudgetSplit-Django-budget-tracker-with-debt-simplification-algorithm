from django.contrib import admin

from .models import Group, GroupExpense, GroupExpenseSplit, GroupMembership


class GroupMembershipInline(admin.TabularInline):
    model = GroupMembership
    extra = 1


@admin.register(Group)
class GroupAdmin(admin.ModelAdmin):
    list_display = ["name", "created_by", "created_at", "member_count"]
    search_fields = ["name", "created_by__username"]
    inlines = [GroupMembershipInline]

    def member_count(self, obj):
        return obj.members.count()


class GroupExpenseSplitInline(admin.TabularInline):
    model = GroupExpenseSplit
    extra = 0


@admin.register(GroupExpense)
class GroupExpenseAdmin(admin.ModelAdmin):
    list_display = ["description", "group", "paid_by", "amount", "split_type", "date"]
    list_filter = ["split_type", "date", "group"]
    search_fields = ["description", "group__name"]
    inlines = [GroupExpenseSplitInline]
