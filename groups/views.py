from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render

from .forms import AddMemberForm, GroupExpenseForm, GroupForm, build_custom_split_forms
from .models import Group, GroupExpense, GroupExpenseSplit, GroupMembership
from .services import calculate_equal_splits, compute_net_balances, get_group_settlements


def _get_group_for_member_or_404(request, group_id):
    """
    Fetch a group, but ONLY if request.user is actually a member of it
    -- otherwise raise 404 rather than a generic PermissionDenied. This
    avoids leaking even the group's EXISTENCE to non-members (a 404
    tells an outsider nothing; a 403 would confirm the group_id is real).
    """
    group = get_object_or_404(Group, pk=group_id)
    if not group.is_member(request.user):
        from django.http import Http404
        raise Http404("Group not found.")
    return group


@login_required
def group_list(request):
    groups = request.user.expense_groups.all().order_by("-created_at")
    return render(request, "groups/group_list.html", {"groups": groups})


@login_required
def group_create(request):
    if request.method == "POST":
        form = GroupForm(request.POST)
        if form.is_valid():
            group = form.save(commit=False)
            group.created_by = request.user
            group.save()
            GroupMembership.objects.create(group=group, user=request.user)
            messages.success(request, f"Group '{group.name}' created. Add members from the group page.")
            return redirect("groups:group_detail", group_id=group.pk)
    else:
        form = GroupForm()

    return render(request, "groups/group_form.html", {"form": form})


@login_required
def group_detail(request, group_id):
    group = _get_group_for_member_or_404(request, group_id)

    balances = compute_net_balances(group)
    members_by_id = {m.id: m for m in group.members.all()}
    balance_rows = [
        {"user": members_by_id[uid], "balance": bal}
        for uid, bal in sorted(balances.items(), key=lambda item: item[1], reverse=True)
    ]

    settlements = get_group_settlements(group)
    expenses = group.expenses.select_related("paid_by").prefetch_related("splits__user")[:20]

    return render(request, "groups/group_detail.html", {
        "group": group,
        "balance_rows": balance_rows,
        "settlements": settlements,
        "expenses": expenses,
        "add_member_form": AddMemberForm(group=group),
    })


@login_required
def group_add_member(request, group_id):
    group = _get_group_for_member_or_404(request, group_id)

    if request.method == "POST":
        form = AddMemberForm(request.POST, group=group)
        if form.is_valid():
            GroupMembership.objects.create(group=group, user=form.cleaned_data["user"])
            messages.success(request, f"Added '{form.cleaned_data['username']}' to the group.")
        else:
            for error in form.errors.get("username", []):
                messages.error(request, error)

    return redirect("groups:group_detail", group_id=group.pk)


@login_required
def group_expense_add(request, group_id):
    group = _get_group_for_member_or_404(request, group_id)

    if request.method == "POST":
        form = GroupExpenseForm(request.POST, group=group)
        split_data = build_custom_split_forms(group, data=request.POST)

        if form.is_valid():
            split_type = form.cleaned_data["split_type"]
            total_amount = form.cleaned_data["amount"]
            member_ids = list(group.members.values_list("id", flat=True))

            try:
                if split_type == GroupExpense.SPLIT_EQUAL:
                    shares = calculate_equal_splits(total_amount, member_ids)
                else:
                    shares = _parse_custom_shares(split_data, total_amount)

                with transaction.atomic():
                    expense = form.save(commit=False)
                    expense.group = group
                    expense.save()

                    GroupExpenseSplit.objects.bulk_create([
                        GroupExpenseSplit(expense=expense, user_id=uid, amount_owed=amount)
                        for uid, amount in shares.items()
                    ])

                messages.success(request, f"Added expense '{expense.description}'.")
                return redirect("groups:group_detail", group_id=group.pk)

            except ValueError as exc:
                messages.error(request, str(exc))
    else:
        form = GroupExpenseForm(group=group)
        split_data = build_custom_split_forms(group)

    return render(request, "groups/expense_form.html", {
        "form": form,
        "group": group,
        "split_data": split_data,
    })


def _parse_custom_shares(split_data, total_amount):
    """
    Parse and validate the custom per-member split amounts submitted
    alongside the main expense form. Raises ValueError with a
    user-friendly message if the shares don't add up to the total.
    """
    shares = {}
    for user_id, entry in split_data.items():
        raw_value = entry["value"]
        if raw_value in (None, ""):
            shares[user_id] = Decimal("0.00")
            continue
        try:
            shares[user_id] = Decimal(str(raw_value)).quantize(Decimal("0.01"))
        except InvalidOperation:
            raise ValueError(f"'{raw_value}' is not a valid amount.")

    shares_total = sum(shares.values())
    # Allow a tiny rounding tolerance (1 cent) since custom splits are
    # typed by hand and people don't always account for rounding.
    if abs(shares_total - total_amount) > Decimal("0.01"):
        raise ValueError(
            f"Custom split amounts (total {shares_total}) must add up to the expense total ({total_amount})."
        )
    return shares


@login_required
def group_expense_delete(request, group_id, expense_id):
    group = _get_group_for_member_or_404(request, group_id)
    expense = get_object_or_404(GroupExpense, pk=expense_id, group=group)

    if request.method == "POST":
        expense.delete()
        messages.success(request, "Expense deleted.")
        return redirect("groups:group_detail", group_id=group.pk)

    return render(request, "groups/expense_confirm_delete.html", {"expense": expense, "group": group})
