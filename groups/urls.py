from django.urls import path

from . import views

app_name = "groups"

urlpatterns = [
    path("", views.group_list, name="group_list"),
    path("create/", views.group_create, name="group_create"),
    path("<int:group_id>/", views.group_detail, name="group_detail"),
    path("<int:group_id>/add-member/", views.group_add_member, name="group_add_member"),
    path("<int:group_id>/expenses/add/", views.group_expense_add, name="group_expense_add"),
    path("<int:group_id>/expenses/<int:expense_id>/delete/", views.group_expense_delete, name="group_expense_delete"),
]
