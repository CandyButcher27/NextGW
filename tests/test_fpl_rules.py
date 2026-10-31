"""Tests for FPL rules validation, formations, auto-substitutions, and scoring rules."""

from __future__ import annotations

import unittest
from fpl.rules import (
    DEFAULT_CONFIG,
    FPLRulesConfig,
    auto_substitute,
    calculate_transfer_hits,
    get_valid_formations,
    is_valid_formation,
    resolve_captain,
    validate_chip,
    validate_lineup,
    validate_squad,
)


class TestFPLRules(unittest.TestCase):
    def test_official_valid_formations(self):
        """All 8 standard FPL formations must be valid."""
        expected_formations = [
            (1, 3, 4, 3),
            (1, 3, 5, 2),
            (1, 4, 3, 3),
            (1, 4, 4, 2),
            (1, 4, 5, 1),
            (1, 5, 2, 3),
            (1, 5, 3, 2),
            (1, 5, 4, 1),
        ]
        valid_formations = get_valid_formations()
        self.assertEqual(sorted(valid_formations), sorted(expected_formations))

        for gk, d, m, f in expected_formations:
            self.assertTrue(is_valid_formation(gk, d, m, f))

    def test_invalid_formations(self):
        # 2 Goalkeepers
        self.assertFalse(is_valid_formation(2, 4, 4, 1))
        # Fewer than 3 Defenders
        self.assertFalse(is_valid_formation(1, 2, 5, 3))
        # Fewer than 1 Forward
        self.assertFalse(is_valid_formation(1, 5, 5, 0))
        # 12 players total
        self.assertFalse(is_valid_formation(1, 4, 4, 3))
        # 10 players total
        self.assertFalse(is_valid_formation(1, 4, 3, 2))

    def test_validate_squad_success(self):
        # Create a valid 15-player squad (2 GK, 5 DEF, 5 MID, 3 FWD, budget <= 100, max 3/team)
        squad = []
        # Assign teams so no team has more than 3 players (15 players across 8 teams)
        teams = ["ARS", "CHE", "LIV", "MCI", "MUN", "NEW", "TOT", "AVL"]
        # 2 GKs
        for i in range(2):
            squad.append({"player_id": f"gk_{i}", "position": "GK", "price": 4.5, "team": teams[i]})
        # 5 DEFs
        for i in range(5):
            squad.append({"player_id": f"def_{i}", "position": "DEF", "price": 5.0, "team": teams[i + 2]})
        # 5 MIDs
        for i in range(5):
            squad.append({"player_id": f"mid_{i}", "position": "MID", "price": 6.0, "team": teams[i]})
        # 3 FWDs
        for i in range(3):
            squad.append({"player_id": f"fwd_{i}", "position": "FWD", "price": 7.0, "team": teams[i + 5]})

        is_valid, errors = validate_squad(squad)
        self.assertTrue(is_valid, f"Errors: {errors}")
        self.assertEqual(len(errors), 0)

    def test_validate_squad_budget_exceeded(self):
        squad = []
        for i in range(2):
            squad.append({"player_id": f"gk_{i}", "position": "GK", "price": 10.0, "team": f"T{i}"})
        for i in range(5):
            squad.append({"player_id": f"def_{i}", "position": "DEF", "price": 10.0, "team": f"T{i}"})
        for i in range(5):
            squad.append({"player_id": f"mid_{i}", "position": "MID", "price": 10.0, "team": f"T{i}"})
        for i in range(3):
            squad.append({"player_id": f"fwd_{i}", "position": "FWD", "price": 10.0, "team": f"T{i}"})
        # Total cost = 150.0m > 100.0m
        is_valid, errors = validate_squad(squad)
        self.assertFalse(is_valid)
        self.assertTrue(any("exceeds budget" in err for err in errors))

    def test_validate_squad_club_limit_exceeded(self):
        squad = []
        # 4 players from ARS
        for i in range(2):
            squad.append({"player_id": f"gk_{i}", "position": "GK", "price": 4.5, "team": "ARS"})
        for i in range(2):
            squad.append({"player_id": f"def_{i}", "position": "DEF", "price": 4.5, "team": "ARS"})
        for i in range(2, 5):
            squad.append({"player_id": f"def_{i}", "position": "DEF", "price": 4.5, "team": f"T{i}"})
        for i in range(5):
            squad.append({"player_id": f"mid_{i}", "position": "MID", "price": 4.5, "team": f"T{i}"})
        for i in range(3):
            squad.append({"player_id": f"fwd_{i}", "position": "FWD", "price": 4.5, "team": f"T{i}"})

        is_valid, errors = validate_squad(squad)
        self.assertFalse(is_valid)
        self.assertTrue(any("Club limit exceeded for 'ARS'" in err for err in errors))

    def test_validate_lineup_captaincy(self):
        xi = ["gk_0", "def_0", "def_1", "def_2", "def_3", "mid_0", "mid_1", "mid_2", "mid_3", "fwd_0", "fwd_1"]
        pos_map = {
            "gk_0": "GK",
            "def_0": "DEF", "def_1": "DEF", "def_2": "DEF", "def_3": "DEF",
            "mid_0": "MID", "mid_1": "MID", "mid_2": "MID", "mid_3": "MID",
            "fwd_0": "FWD", "fwd_1": "FWD",
        }

        # Valid lineup (4-4-2)
        is_valid, errors = validate_lineup(xi, captain="mid_0", vice_captain="fwd_0", squad_positions=pos_map)
        self.assertTrue(is_valid, f"Errors: {errors}")

        # Captain not in starting XI
        is_valid, errors = validate_lineup(xi, captain="bench_player", vice_captain="fwd_0", squad_positions=pos_map)
        self.assertFalse(is_valid)
        self.assertTrue(any("is not in the starting XI" in err for err in errors))

        # Captain equals vice-captain
        is_valid, errors = validate_lineup(xi, captain="mid_0", vice_captain="mid_0", squad_positions=pos_map)
        self.assertFalse(is_valid)
        self.assertTrue(any("must be different players" in err for err in errors))

    def test_auto_substitute_goalkeeper(self):
        starting_xi = ["gk_starter", "d1", "d2", "d3", "m1", "m2", "m3", "m4", "f1", "f2", "f3"]
        bench = ["gk_sub", "d4", "m5", "f4"]
        positions = {
            "gk_starter": "GK", "gk_sub": "GK",
            "d1": "DEF", "d2": "DEF", "d3": "DEF", "d4": "DEF",
            "m1": "MID", "m2": "MID", "m3": "MID", "m4": "MID", "m5": "MID",
            "f1": "FWD", "f2": "FWD", "f3": "FWD", "f4": "FWD",
        }
        # Starting GK played 0 minutes, sub GK played 90
        minutes = {p: 90.0 for p in starting_xi + bench}
        minutes["gk_starter"] = 0.0

        final_xi, subs = auto_substitute(starting_xi, bench, positions, minutes)
        self.assertIn("gk_sub", final_xi)
        self.assertNotIn("gk_starter", final_xi)
        self.assertEqual(subs, [("gk_starter", "gk_sub")])

    def test_auto_substitute_formation_rule(self):
        """If starter played 0 mins, sub must maintain legal formation (min 3 DEF)."""
        # Starting in 3-4-3 (d1, d2, d3). If d1 played 0 mins, sub cannot be a forward
        # because defenders would drop to 2 (invalid). Must pick a defender!
        starting_xi = ["gk1", "d1", "d2", "d3", "m1", "m2", "m3", "m4", "f1", "f2", "f3"]
        # Bench priority: sub 1 is f4, sub 2 is d4
        bench = ["gk_sub", "f4", "d4", "m5"]
        positions = {
            "gk1": "GK", "gk_sub": "GK",
            "d1": "DEF", "d2": "DEF", "d3": "DEF", "d4": "DEF",
            "m1": "MID", "m2": "MID", "m3": "MID", "m4": "MID", "m5": "MID",
            "f1": "FWD", "f2": "FWD", "f3": "FWD", "f4": "FWD",
        }
        minutes = {p: 90.0 for p in starting_xi + bench}
        minutes["d1"] = 0.0

        final_xi, subs = auto_substitute(starting_xi, bench, positions, minutes)
        # f4 cannot be subbed in because formation would be 2-4-4 (illegal DEF count = 2).
        # d4 should be subbed in instead to keep 3 DEF!
        self.assertIn("d4", final_xi)
        self.assertNotIn("f4", final_xi)
        self.assertEqual(subs, [("d1", "d4")])

    def test_resolve_captaincy_and_chips(self):
        # 1. Normal captain played
        minutes = {"cap": 90.0, "vc": 90.0}
        c, mult = resolve_captain("cap", "vc", minutes)
        self.assertEqual((c, mult), ("cap", 2.0))

        # 2. Captain unplayed, vice-captain played
        minutes = {"cap": 0.0, "vc": 90.0}
        c, mult = resolve_captain("cap", "vc", minutes)
        self.assertEqual((c, mult), ("vc", 2.0))

        # 3. Triple Captain chip
        minutes = {"cap": 90.0, "vc": 90.0}
        c, mult = resolve_captain("cap", "vc", minutes, chip_name="TripleCaptain")
        self.assertEqual((c, mult), ("cap", 3.0))

    def test_calculate_transfer_hits(self):
        # 1 FT, 1 transfer -> 0 hits
        self.assertEqual(calculate_transfer_hits(1, 1), (0, 0.0))
        # 1 FT, 2 transfers -> 1 hit = 4.0
        self.assertEqual(calculate_transfer_hits(2, 1), (1, 4.0))
        # Wildcard -> 0 hit cost regardless of transfer count
        self.assertEqual(calculate_transfer_hits(5, 1, chip_name="Wildcard"), (0, 0.0))

    def test_validate_chip_season_limit(self):
        # Valid unused chip
        is_valid, errors = validate_chip("Wildcard", chips_used=[])
        self.assertTrue(is_valid, f"Errors: {errors}")

        # Used chip reaches season limit
        is_valid, errors = validate_chip("Wildcard", chips_used=["Wildcard"])
        self.assertFalse(is_valid)
        self.assertTrue(any("season limit" in err for err in errors))

        # Config allowing multiple chips (e.g. 2 Wildcards per season)
        config_two_wc = FPLRulesConfig(chip_limit_per_season=2)
        is_valid, errors = validate_chip("Wildcard", chips_used=["Wildcard"], config=config_two_wc)
        self.assertTrue(is_valid, f"Errors: {errors}")


def test_rules():
    suite = unittest.TestLoader().loadTestsFromTestCase(TestFPLRules)
    runner = unittest.TextTestRunner()
    result = runner.run(suite)
    assert result.wasSuccessful()


if __name__ == "__main__":
    unittest.main()
