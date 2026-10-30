"""Tests for CSP engine, constraints, heuristics, and search algorithms."""

from __future__ import annotations

import unittest
from fpl.csp import (
    CSP,
    AllDifferentConstraint,
    BinaryConstraint,
    CountConstraint,
    FunctionalConstraint,
    SumConstraint,
    UnaryConstraint,
    ac3,
    backtracking_search,
    forward_checking,
    lcv_heuristic,
    min_conflicts,
    mrv_heuristic,
)


class TestCSPEngine(unittest.TestCase):
    def test_map_coloring_csp(self):
        """Classic Australia map coloring problem."""
        variables = ["WA", "NT", "SA", "Q", "NSW", "V", "T"]
        domains = {v: ["red", "green", "blue"] for v in variables}
        csp = CSP(variables, domains)

        edges = [
            ("WA", "NT"), ("WA", "SA"),
            ("NT", "SA"), ("NT", "Q"),
            ("SA", "Q"), ("SA", "NSW"), ("SA", "V"),
            ("Q", "NSW"),
            ("NSW", "V"),
        ]

        for u, v in edges:
            csp.add_constraint(BinaryConstraint(u, v, lambda val_u, val_v: val_u != val_v))

        # Solve with backtracking search + MRV + LCV + Forward Checking
        solution = backtracking_search(
            csp,
            select_unassigned_variable=mrv_heuristic,
            order_domain_values=lcv_heuristic,
            inference=forward_checking,
        )

        self.assertIsNotNone(solution)
        self.assertEqual(len(solution), len(variables))

        # Verify all edge constraints hold
        for u, v in edges:
            self.assertNotEqual(solution[u], solution[v])

    def test_ac3_arc_consistency(self):
        """Verify AC-3 prunes impossible domain values."""
        csp = CSP(["A", "B"], {"A": [1, 2, 3], "B": [1, 2]})
        # Constraint: A < B
        csp.add_constraint(BinaryConstraint("A", "B", lambda a, b: a < b))

        result = ac3(csp)
        self.assertTrue(result)
        # For A < B with B in {1, 2}, A must be 1. 2 and 3 should be pruned.
        self.assertEqual(csp.domains["A"], [1])
        # For B, 1 cannot be greater than any A in {1}, so B can only be 2.
        self.assertEqual(csp.domains["B"], [2])

    def test_ac3_inconsistency_detection(self):
        """AC-3 should return False when no solution is possible."""
        csp = CSP(["A", "B"], {"A": [2, 3], "B": [1]})
        # Constraint: A < B (impossible since all A > all B)
        csp.add_constraint(BinaryConstraint("A", "B", lambda a, b: a < b))

        result = ac3(csp)
        self.assertFalse(result)

    def test_all_different_constraint(self):
        variables = ["X1", "X2", "X3"]
        domains = {v: [1, 2, 3] for v in variables}
        csp = CSP(variables, domains)
        csp.add_constraint(AllDifferentConstraint(variables))

        sol = backtracking_search(csp)
        self.assertIsNotNone(sol)
        self.assertEqual(len(set(sol.values())), 3)

    def test_sum_constraint(self):
        variables = ["A", "B", "C"]
        domains = {"A": [2.0, 5.0], "B": [3.0, 7.0], "C": [1.0, 4.0]}
        csp = CSP(variables, domains)
        # Sum must be <= 8.0
        csp.add_constraint(SumConstraint(variables, max_sum=8.0))

        sol = backtracking_search(csp)
        self.assertIsNotNone(sol)
        total = sum(sol.values())
        self.assertLessEqual(total, 8.0)

    def test_count_constraint(self):
        variables = ["p1", "p2", "p3", "p4"]
        domains = {v: ["DEF", "MID"] for v in variables}
        csp = CSP(variables, domains)
        # Exactly 2 DEF
        csp.add_constraint(
            CountConstraint(variables, predicate=lambda pos: pos == "DEF", min_count=2, max_count=2)
        )

        sol = backtracking_search(csp)
        self.assertIsNotNone(sol)
        def_count = sum(1 for pos in sol.values() if pos == "DEF")
        self.assertEqual(def_count, 2)

    def test_find_all_solutions(self):
        variables = ["A", "B"]
        domains = {"A": [1, 2], "B": [1, 2]}
        csp = CSP(variables, domains)
        csp.add_constraint(BinaryConstraint("A", "B", lambda a, b: a != b))

        solutions = backtracking_search(csp, find_all=True)
        self.assertIsInstance(solutions, list)
        self.assertEqual(len(solutions), 2)


def test_map_coloring():
    suite = unittest.TestLoader().loadTestsFromTestCase(TestCSPEngine)
    runner = unittest.TextTestRunner()
    result = runner.run(suite)
    assert result.wasSuccessful()


if __name__ == "__main__":
    unittest.main()
