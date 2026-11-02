"""Tests for Squad representation, CSP squad selection, and conversion helpers."""

from __future__ import annotations

import unittest
from fpl.rules import FPLRulesConfig
from fpl.squad import (
    Player,
    Squad,
    create_squad_selection_csp,
    solve_squad,
)


class TestFPLSquad(unittest.TestCase):
    def setUp(self):
        # Create a mock player pool
        self.players = []
        # 4 GKs (2 ARS, 2 CHE)
        for i in range(4):
            team = "ARS" if i < 2 else "CHE"
            self.players.append(Player(f"gk_{i}", f"Goalkeeper {i}", "GK", team, 4.5 + i * 0.5))

        # 8 DEFs (2 MCI, 2 LIV, 2 TOT, 2 NEW)
        teams = ["MCI", "LIV", "TOT", "NEW"]
        for i in range(8):
            team = teams[i // 2]
            self.players.append(Player(f"def_{i}", f"Defender {i}", "DEF", team, 4.0 + (i % 3) * 0.5))

        # 8 MIDs (2 ARS, 2 MCI, 2 CHE, 2 LIV)
        teams_mid = ["ARS", "MCI", "CHE", "LIV"]
        for i in range(8):
            team = teams_mid[i // 2]
            self.players.append(Player(f"mid_{i}", f"Midfielder {i}", "MID", team, 5.0 + (i % 4) * 0.5))

        # 5 FWDs (2 AVL, 2 MUN, 1 EVE)
        teams_fwd = ["AVL", "AVL", "MUN", "MUN", "EVE"]
        for i in range(5):
            self.players.append(Player(f"fwd_{i}", f"Forward {i}", "FWD", teams_fwd[i], 6.0 + i * 0.5))

    def test_squad_properties_and_state_conversion(self):
        # Select first 15 players matching quota
        squad_players = (
            [p for p in self.players if p.position == "GK"][:2]
            + [p for p in self.players if p.position == "DEF"][:5]
            + [p for p in self.players if p.position == "MID"][:5]
            + [p for p in self.players if p.position == "FWD"][:3]
        )
        squad = Squad(squad_players)

        self.assertEqual(len(squad), 15)
        self.assertEqual(len(squad.gk), 2)
        self.assertEqual(len(squad.defenders), 5)
        self.assertEqual(len(squad.midfielders), 5)
        self.assertEqual(len(squad.forwards), 3)

        # State tuple representation
        state_tuple = squad.to_state_squad()
        self.assertIsInstance(state_tuple, tuple)
        self.assertEqual(len(state_tuple), 15)
        self.assertIn((squad_players[0].player_id, squad_players[0].position), state_tuple)

        # Reconstruct squad from state tuple
        registry = {p.player_id: p for p in self.players}
        reconstructed = Squad.from_state_squad(state_tuple, registry)
        self.assertEqual(len(reconstructed), 15)
        self.assertEqual(sorted(reconstructed.player_ids), sorted(squad.player_ids))

    def test_squad_selection_csp_formulation(self):
        csp = create_squad_selection_csp(self.players, budget=100.0)
        self.assertEqual(len(csp.variables), 15)
        # Check domain sizes match available candidates in position
        self.assertEqual(len(csp.domains["gk_0"]), 4)
        self.assertEqual(len(csp.domains["def_0"]), 8)
        self.assertEqual(len(csp.domains["mid_0"]), 8)
        self.assertEqual(len(csp.domains["fwd_0"]), 5)

    def test_solve_squad_validity(self):
        """Solver should produce a legal 15-player squad satisfying all FPL rules."""
        squad = solve_squad(self.players, budget=85.0)
        self.assertIsNotNone(squad)

        # Validate with official rules
        is_valid, errors = squad.validate(FPLRulesConfig(budget=85.0))
        self.assertTrue(is_valid, f"Validation errors: {errors}")
        self.assertLessEqual(squad.total_cost, 85.0)

        # Club limits: max 3 per club
        for club, club_players in squad.by_team.items():
            self.assertLessEqual(len(club_players), 3, f"Club {club} has {len(club_players)} players")


def test_squad():
    suite = unittest.TestLoader().loadTestsFromTestCase(TestFPLSquad)
    runner = unittest.TextTestRunner()
    result = runner.run(suite)
    assert result.wasSuccessful()


if __name__ == "__main__":
    unittest.main()
