"""
Business logic for group expense splitting and debt simplification —
kept out of views.py and models.py deliberately (a "service layer"),
since this logic is complex enough to deserve its own tests independent
of the request/response cycle or the ORM.
"""

from decimal import ROUND_HALF_UP, Decimal
from typing import Dict, List, NamedTuple

from django.contrib.auth.models import User

from .models import Group, GroupExpenseSplit

TWO_PLACES = Decimal("0.01")


def calculate_equal_splits(total_amount: Decimal, member_ids: List[int]) -> Dict[int, Decimal]:
    """
    Split `total_amount` equally among `member_ids`, distributing any
    leftover penny(s) from integer-cent rounding to the first N
    members rather than losing/gaining a cent overall.

    e.g. splitting $10.00 three ways gives $3.34, $3.33, $3.33 — NOT
    $3.33 three times (which would only sum to $9.99).
    """
    if not member_ids:
        raise ValueError("Cannot split an expense among zero members.")

    count = len(member_ids)
    base_share = (total_amount / count).quantize(TWO_PLACES, rounding=ROUND_HALF_UP)
    splits = {member_id: base_share for member_id in member_ids}

    distributed_total = base_share * count
    leftover_cents = int((total_amount - distributed_total) * 100)

    # Distribute leftover pennies one at a time to the first few members
    # (order doesn't matter fairness-wise for a difference of 1-2 cents).
    member_ids_sorted = sorted(member_ids)
    for i in range(abs(leftover_cents)):
        member_id = member_ids_sorted[i % count]
        adjustment = Decimal("0.01") if leftover_cents > 0 else Decimal("-0.01")
        splits[member_id] += adjustment

    return splits


def compute_net_balances(group: Group) -> Dict[int, Decimal]:
    """
    Compute each member's net balance in a group:
      positive balance = this person is OWED money overall (net creditor)
      negative balance = this person OWES money overall (net debtor)

    balance = (total this person paid for group expenses)
            - (total this person owes across all their splits)
    """
    balances: Dict[int, Decimal] = {member.id: Decimal("0.00") for member in group.members.all()}

    for expense in group.expenses.all():
        balances[expense.paid_by_id] = balances.get(expense.paid_by_id, Decimal("0.00")) + expense.amount

    splits = GroupExpenseSplit.objects.filter(expense__group=group).select_related("expense")
    for split in splits:
        balances[split.user_id] = balances.get(split.user_id, Decimal("0.00")) - split.amount_owed

    return {user_id: balance.quantize(TWO_PLACES) for user_id, balance in balances.items()}


class Settlement(NamedTuple):
    """One suggested payment: `from_user` pays `to_user` `amount`."""
    from_user: User
    to_user: User
    amount: Decimal


def simplify_debts(balances: Dict[int, Decimal], users_by_id: Dict[int, User]) -> List[Settlement]:
    """
    Given net balances per user, compute the MINIMUM set of payments
    needed to settle every debt in the group — the same "simplify
    debts" feature popularized by apps like Splitwise.

    ALGORITHM: greedy matching. Repeatedly pair the biggest creditor
    (most positive balance) with the biggest debtor (most negative
    balance), settle the smaller of the two amounts between them, and
    repeat. This is provably optimal in the number of transactions for
    this kind of net-balance settling and runs in O(n log n) using a
    sort per iteration (fine for typical group sizes of a handful to a
    few dozen people — this is not the bottleneck in a bill-splitting
    app).

    Without this step, a naive "everyone pays everyone they owe
    individually" approach could require far more transactions than
    necessary — e.g. if A owes B $10 and B owes C $10, the naive
    approach makes 2 payments; simplification makes A pay C directly
    instead, still 2 payments here, but the benefit compounds fast in
    larger groups with many crisscrossing expenses.
    """
    # Work on a mutable copy; ignore anyone already settled (balance == 0).
    remaining = {uid: bal for uid, bal in balances.items() if bal != 0}
    settlements: List[Settlement] = []

    while remaining:
        creditor_id = max(remaining, key=lambda uid: remaining[uid])
        debtor_id = min(remaining, key=lambda uid: remaining[uid])

        creditor_balance = remaining[creditor_id]
        debtor_balance = remaining[debtor_id]

        # Everyone left is within a rounding hair of zero -- nothing more to settle.
        if creditor_balance <= 0 or debtor_balance >= 0:
            break

        transfer_amount = min(creditor_balance, -debtor_balance)

        settlements.append(Settlement(
            from_user=users_by_id[debtor_id],
            to_user=users_by_id[creditor_id],
            amount=transfer_amount,
        ))

        remaining[creditor_id] -= transfer_amount
        remaining[debtor_id] += transfer_amount

        if remaining[creditor_id] == 0:
            del remaining[creditor_id]
        if debtor_id in remaining and remaining[debtor_id] == 0:
            del remaining[debtor_id]

    return settlements


def get_group_settlements(group: Group) -> List[Settlement]:
    """Convenience wrapper: compute balances and simplified settlements for a group in one call."""
    balances = compute_net_balances(group)
    users_by_id = {member.id: member for member in group.members.all()}
    return simplify_debts(balances, users_by_id)
