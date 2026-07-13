"""
Tests for groups/services.py -- the debt simplification algorithm and
split calculation logic. Kept in a separate file from tests.py since
this is pure business logic worth testing thoroughly and independently
from the view/request layer.
"""

from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase

from .models import Group, GroupExpense, GroupExpenseSplit, GroupMembership
from .services import (
    calculate_equal_splits,
    compute_net_balances,
    get_group_settlements,
    simplify_debts,
)


class EqualSplitTests(TestCase):
    """Tests for calculate_equal_splits() -- pure function, no DB needed."""

    def test_splits_evenly_when_divisible(self):
        shares = calculate_equal_splits(Decimal("30.00"), [1, 2, 3])
        self.assertEqual(shares, {1: Decimal("10.00"), 2: Decimal("10.00"), 3: Decimal("10.00")})

    def test_splits_sum_exactly_to_total_when_not_evenly_divisible(self):
        shares = calculate_equal_splits(Decimal("10.00"), [1, 2, 3])
        self.assertEqual(sum(shares.values()), Decimal("10.00"))
        # No single share should be off by more than a cent from the others
        values = list(shares.values())
        self.assertLessEqual(max(values) - min(values), Decimal("0.01"))

    def test_single_member_gets_full_amount(self):
        shares = calculate_equal_splits(Decimal("42.50"), [1])
        self.assertEqual(shares, {1: Decimal("42.50")})

    def test_raises_on_empty_member_list(self):
        with self.assertRaises(ValueError):
            calculate_equal_splits(Decimal("10.00"), [])

    def test_large_group_split_still_sums_correctly(self):
        member_ids = list(range(1, 8))  # 7 people
        shares = calculate_equal_splits(Decimal("100.00"), member_ids)
        self.assertEqual(sum(shares.values()), Decimal("100.00"))


class NetBalanceTests(TestCase):
    """Tests for compute_net_balances() against a real (test) database."""

    def setUp(self):
        self.alice = User.objects.create_user(username="alice", password="x")
        self.bob = User.objects.create_user(username="bob", password="x")
        self.carol = User.objects.create_user(username="carol", password="x")
        self.group = Group.objects.create(name="Trip", created_by=self.alice)
        for user in [self.alice, self.bob, self.carol]:
            GroupMembership.objects.create(group=self.group, user=user)

    def _add_expense(self, paid_by, amount, splits):
        expense = GroupExpense.objects.create(
            group=self.group, paid_by=paid_by, description="Test", amount=amount, split_type="equal"
        )
        for user, owed in splits.items():
            GroupExpenseSplit.objects.create(expense=expense, user=user, amount_owed=owed)
        return expense

    def test_balances_are_zero_with_no_expenses(self):
        balances = compute_net_balances(self.group)
        self.assertTrue(all(b == 0 for b in balances.values()))

    def test_single_expense_balances_correctly(self):
        # Alice pays $90, split equally 3 ways ($30 each)
        self._add_expense(self.alice, Decimal("90.00"), {
            self.alice: Decimal("30.00"), self.bob: Decimal("30.00"), self.carol: Decimal("30.00"),
        })
        balances = compute_net_balances(self.group)
        self.assertEqual(balances[self.alice.id], Decimal("60.00"))   # paid 90, owes 30 -> net +60
        self.assertEqual(balances[self.bob.id], Decimal("-30.00"))
        self.assertEqual(balances[self.carol.id], Decimal("-30.00"))

    def test_balances_always_sum_to_zero_across_multiple_expenses(self):
        self._add_expense(self.alice, Decimal("90.00"), {
            self.alice: Decimal("30.00"), self.bob: Decimal("30.00"), self.carol: Decimal("30.00"),
        })
        self._add_expense(self.bob, Decimal("30.00"), {
            self.alice: Decimal("10.00"), self.bob: Decimal("10.00"), self.carol: Decimal("10.00"),
        })
        balances = compute_net_balances(self.group)
        self.assertEqual(sum(balances.values()), Decimal("0.00"))


class DebtSimplificationTests(TestCase):
    """Tests for simplify_debts() -- the core 'minimize number of payments' algorithm."""

    def setUp(self):
        self.alice = User.objects.create_user(username="alice", password="x")
        self.bob = User.objects.create_user(username="bob", password="x")
        self.carol = User.objects.create_user(username="carol", password="x")
        self.users_by_id = {self.alice.id: self.alice, self.bob.id: self.bob, self.carol.id: self.carol}

    def test_no_settlements_needed_when_all_balanced(self):
        balances = {self.alice.id: Decimal("0.00"), self.bob.id: Decimal("0.00")}
        settlements = simplify_debts(balances, self.users_by_id)
        self.assertEqual(settlements, [])

    def test_simple_two_person_debt(self):
        balances = {self.alice.id: Decimal("50.00"), self.bob.id: Decimal("-50.00")}
        settlements = simplify_debts(balances, self.users_by_id)
        self.assertEqual(len(settlements), 1)
        self.assertEqual(settlements[0].from_user, self.bob)
        self.assertEqual(settlements[0].to_user, self.alice)
        self.assertEqual(settlements[0].amount, Decimal("50.00"))

    def test_three_person_scenario_resolves_with_minimum_transactions(self):
        # Alice is owed 60, Bob owes 30, Carol owes 30
        balances = {
            self.alice.id: Decimal("60.00"),
            self.bob.id: Decimal("-30.00"),
            self.carol.id: Decimal("-30.00"),
        }
        settlements = simplify_debts(balances, self.users_by_id)
        # Should take exactly 2 payments (not 3+) -- one from each debtor to Alice
        self.assertEqual(len(settlements), 2)
        total_paid_to_alice = sum(s.amount for s in settlements if s.to_user == self.alice)
        self.assertEqual(total_paid_to_alice, Decimal("60.00"))

    def test_settlements_fully_resolve_all_balances_to_zero(self):
        """
        The critical correctness property: after applying every
        suggested settlement, every balance must land at exactly zero.
        This is checked across several different balance scenarios.
        """
        scenarios = [
            {self.alice.id: Decimal("50.00"), self.bob.id: Decimal("-50.00")},
            {self.alice.id: Decimal("60.00"), self.bob.id: Decimal("-30.00"), self.carol.id: Decimal("-30.00")},
            {self.alice.id: Decimal("-25.50"), self.bob.id: Decimal("15.25"), self.carol.id: Decimal("10.25")},
        ]

        for balances in scenarios:
            settlements = simplify_debts(dict(balances), self.users_by_id)
            resulting_balances = dict(balances)
            for s in settlements:
                resulting_balances[s.from_user.id] += s.amount
                resulting_balances[s.to_user.id] -= s.amount

            for user_id, balance in resulting_balances.items():
                self.assertEqual(balance, Decimal("0.00"), f"Balance for user {user_id} did not settle to zero")

    def test_settlement_never_produces_more_transactions_than_naive_pairwise_would(self):
        # 4 people, several small debts -- simplification should never need
        # more than (number_of_people - 1) transactions.
        balances = {
            self.alice.id: Decimal("40.00"),
            self.bob.id: Decimal("20.00"),
            self.carol.id: Decimal("-30.00"),
        }
        dave = User.objects.create_user(username="dave", password="x")
        users_by_id = {**self.users_by_id, dave.id: dave}
        balances[dave.id] = Decimal("-30.00")

        settlements = simplify_debts(balances, users_by_id)
        self.assertLessEqual(len(settlements), len(balances) - 1)


class FullGroupSettlementIntegrationTest(TestCase):
    """End-to-end test combining real expenses -> balances -> settlements."""

    def test_realistic_trip_scenario(self):
        alice = User.objects.create_user(username="alice", password="x")
        bob = User.objects.create_user(username="bob", password="x")
        carol = User.objects.create_user(username="carol", password="x")

        group = Group.objects.create(name="Japan Trip", created_by=alice)
        for user in [alice, bob, carol]:
            GroupMembership.objects.create(group=group, user=user)

        # Alice pays for the $90 dinner
        dinner = GroupExpense.objects.create(group=group, paid_by=alice, description="Dinner", amount=Decimal("90.00"), split_type="equal")
        for user in [alice, bob, carol]:
            GroupExpenseSplit.objects.create(expense=dinner, user=user, amount_owed=Decimal("30.00"))

        # Bob pays for the $30 cab
        cab = GroupExpense.objects.create(group=group, paid_by=bob, description="Cab", amount=Decimal("30.00"), split_type="equal")
        for user in [alice, bob, carol]:
            GroupExpenseSplit.objects.create(expense=cab, user=user, amount_owed=Decimal("10.00"))

        settlements = get_group_settlements(group)

        # Expected: Carol owes 40, Bob owes 10 (net), both pay Alice
        settlement_map = {s.from_user.username: (s.to_user.username, s.amount) for s in settlements}
        self.assertEqual(settlement_map["carol"], ("alice", Decimal("40.00")))
        self.assertEqual(settlement_map["bob"], ("alice", Decimal("10.00")))
