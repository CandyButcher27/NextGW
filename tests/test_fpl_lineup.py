"""Tests for Lineup formation selection, CSP formation validation, and optimal lineup solver."""

from __future__ import annotations

import unittest
from planning.actions import LineupAction
from fpl.lineup import (
    Lineup,
    create_lineup_formation_csp,
    solve_optimal_lineup,
)
from fpl.rules import is_valid_formation, validate_lineup


class TestFPLLineup(unittest.TestCase):
    def setUp(self):
        # 15-player squad (2 GK, 5 DEF, 5 MID, 3 FWD)
        self.squad_positions = {
            "gk_1": "GK", "gk_2": "GK",
            "def_1": "DEF", "def_2": "DEF", "def_3": "DEF", "def_4": "DEF", "def_5": "DEF",
            "mid_1": "MID", "mid_2": "MID", "mid_3": "MID", "mid_4": "MID", "mid_5": "MID",
            "fwd_1": "FWD", "fwd_2": "FWD", "fwd_3": "FWD",
        }

    def test_lineup_formation_csp(self):
        csp = create_lineup_formation_csp(self.squad_positions)
        self.assertEqual(len(csp.variables), 11)

        # Assignment with 1 GK, 4 DEF, 4 MID, 2 FWD (4-4-2)
        assignment = {
            "xi_0": "gk_1",
            "xi_1": "def_1", "xi_2": "def_2", "xi_3": "def_3", "xi_4": "def_4",
            "xi_5": "mid_1", "xi_6": "mid_2", "xi_7": "mid_3", "xi_8": "mid_4",
            "xi_9": "fwd_1", "xi_10": "fwd_2",
        }
        self.assertTrue(csp.is_complete(assignment))

    def test_solve_optimal_lineup_maximizes_points(self):
        # High points for 3 forwards (should favor 3-4-3 or 3-5-2)
        expected_points = {
            "gk_1": 6.0, "gk_2": 2.0,
            "def_1": 8.0, "def_2": 7.0, "def_3": 6.0, "def_4": 2.0, "def_5": 1.0,
            "mid_1": 10.0, "mid_2": 9.0, "mid_3": 8.0, "mid_4": 7.0, "mid_5": 2.0,
            "fwd_1": 12.0, "fwd_2": 11.0, "fwd_3": 10.0,
        }

        lineup = solve_optimal_lineup(self.squad_positions, expected_points)

        # Verify sizes
        self.assertEqual(len(lineup.starting_xi), 11)
        self.assertEqual(len(lineup.bench), 4)

        # Verify formation is valid
        counts = {pos: 0 for pos in ("GK", "DEF", "MID", "FWD")}
        for pid in lineup.starting_xi:
            counts[self.squad_positions[pid]] += 1

        self.assertTrue(
            is_valid_formation(counts["GK"], counts["DEF"], counts["MID"], counts["FWD"])
        )

        # In this points profile:
        # All 3 FWDs (12, 11, 10 pts) and top 4 MIDs (10, 9, 8, 7 pts) and top 3 DEFs (8, 7, 6 pts) + gk_1 (6 pts)
        # Should form a 3-4-3!
        self.assertEqual(counts["GK"], 1)
        self.assertEqual(counts["DEF"], 3)
        self.assertEqual(counts["MID"], 4)
        self.assertEqual(counts["FWD"], 3)

        # Captain should be fwd_1 (12.0 pts), Vice-captain fwd_2 (11.0 pts)
        self.assertEqual(lineup.captain, "fwd_1")
        self.assertEqual(lineup.vice_captain, "fwd_2")

        # Bench should contain gk_2 (bench GK) and lowest predicted outfielders (def_4, def_5, mid_5)
        self.assertIn("gk_2", lineup.bench)
        self.assertIn("def_4", lineup.bench)
        self.assertIn("def_5", lineup.bench)
        self.assertIn("mid_5", lineup.bench)

        # LineupAction conversion
        action = lineup.to_action()
        self.assertIsInstance(action, LineupAction)
        self.assertEqual(action.captain, "fwd_1")
        self.assertEqual(action.vice_captain, "fwd_2")
        self.assertEqual(len(action.starting_xi), 11)

    def test_lineup_validation(self):
        lineup = solve_optimal_lineup(self.squad_positions)
        is_valid, errors = lineup.validate(self.squad_positions)
        self.assertTrue(is_valid, f"Lineup validation errors: {errors}")


def test_lineup():
    suite = unittest.TestLoader().loadTestsFromTestCase(TestFPLLineup)
    runner = unittest.TextTestRunner()
    result = runner.run(suite)
    assert result.wasSuccessful()


if __name__ == "__main__":
    unittest.main()
