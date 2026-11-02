"""Tests for transfer validation, state transition function, and candidate generation."""

from __future__ import annotations

import unittest
from planning.actions import ChipAction, GWPlan, LineupAction, TransferAction
from planning.objective import PlanningObjective
from planning.search import PlanningSearch
from planning.state import PlanningState
from fpl.rules import FPLRulesConfig
from fpl.squad import Player, Squad
from fpl.transfers import (
    generate_candidate_plans,
    transition_fn,
    validate_transfers,
)


class TestFPLTransfers(unittest.TestCase):
    def setUp(self):
        # 15 players distributed across multiple clubs (<= 3 per club)
        teams_gk = ["ARS", "BHA"]
        teams_def = ["MCI", "MCI", "LIV", "LIV", "NEW"]
        teams_mid = ["LIV", "ARS", "ARS", "CHE", "CHE"]
        teams_fwd = ["TOT", "TOT", "AVL"]
        self.squad_players = [
            Player(f"gk_{i}", f"GK {i}", "GK", teams_gk[i], 5.0) for i in range(2)
        ] + [
            Player(f"def_{i}", f"DEF {i}", "DEF", teams_def[i], 5.0) for i in range(5)
        ] + [
            Player(f"mid_{i}", f"MID {i}", "MID", teams_mid[i], 7.0) for i in range(5)
        ] + [
            Player(f"fwd_{i}", f"FWD {i}", "FWD", teams_fwd[i], 8.0) for i in range(3)
        ]
        self.squad = Squad(self.squad_players)

    def test_validate_transfers_legal(self):
        registry = {
            "new_mid": Player("new_mid", "New Mid", "MID", "CHE", 7.0),
        }
        transfers = [TransferAction(player_out="mid_0", player_in="new_mid")]
        is_valid, errors = validate_transfers(self.squad, transfers, bank=1.0, player_registry=registry)
        self.assertTrue(is_valid, f"Transfer validation errors: {errors}")

    def test_validate_transfers_illegal_out(self):
        transfers = [TransferAction(player_out="unknown_player", player_in="new_mid")]
        is_valid, errors = validate_transfers(self.squad, transfers, bank=1.0)
        self.assertFalse(is_valid)
        self.assertTrue(any("is not in current squad" in err for err in errors))

    def test_validate_transfers_already_in_squad(self):
        # mid_1 is already in squad
        transfers = [TransferAction(player_out="mid_0", player_in="mid_1")]
        is_valid, errors = validate_transfers(self.squad, transfers, bank=1.0)
        self.assertFalse(is_valid)
        self.assertTrue(any("already in squad" in err for err in errors))

    def test_transition_fn_gw_progression(self):
        """Gameweek must increment by exactly 1 as required by backtest simulator."""
        initial_state = PlanningState(
            gameweek=1,
            squad=self.squad.to_state_squad(),
            budget=0.5,
            free_transfers=1,
        )

        plan = GWPlan(
            transfers=[],
            lineup=LineupAction(
                starting_xi=[p.player_id for p in self.squad_players[:11]],
                captain="mid_0",
                vice_captain="mid_1",
            ),
        )

        next_state = transition_fn(initial_state, plan)
        self.assertEqual(next_state.gameweek, 2)
        # Banked 1 FT -> next GW has 2 FTs
        self.assertEqual(next_state.free_transfers, 2)
        self.assertEqual(next_state.squad, initial_state.squad)

    def test_transition_fn_transfer_application(self):
        initial_state = PlanningState(
            gameweek=1,
            squad=self.squad.to_state_squad(),
            budget=2.0,
            free_transfers=2,
        )

        registry = {
            "super_mid": Player("super_mid", "Super Mid", "MID", "CHE", 8.0),
            "mid_0": Player("mid_0", "MID 0", "MID", "LIV", 7.0),
        }

        # 1 transfer: mid_0 (£7.0m) -> super_mid (£8.0m)
        plan = GWPlan(
            transfers=[TransferAction(player_out="mid_0", player_in="super_mid")],
            lineup=LineupAction(
                starting_xi=["super_mid"] + [p.player_id for p in self.squad_players[1:11]],
                captain="super_mid",
                vice_captain="mid_1",
            ),
        )

        next_state = transition_fn(initial_state, plan, player_registry=registry)
        self.assertEqual(next_state.gameweek, 2)

        # Budget: 2.0 + 7.0 - 8.0 = 1.0
        self.assertEqual(next_state.budget, 1.0)

        # Squad has super_mid and does not have mid_0
        squad_dict = dict(next_state.squad)
        self.assertIn("super_mid", squad_dict)
        self.assertNotIn("mid_0", squad_dict)

        # Free transfers: 2 - 1 = 1 remaining + 1 = 2 FTs
        self.assertEqual(next_state.free_transfers, 2)

    def test_transition_fn_free_transfers_cap(self):
        """Free transfers cannot accumulate past max_free_transfers (5)."""
        config = FPLRulesConfig(max_free_transfers=5)
        initial_state = PlanningState(
            gameweek=5,
            squad=self.squad.to_state_squad(),
            budget=0.0,
            free_transfers=5,
        )

        plan = GWPlan(
            transfers=[],
            lineup=LineupAction(
                starting_xi=[p.player_id for p in self.squad_players[:11]],
                captain="mid_0",
                vice_captain="mid_1",
            ),
        )

        next_state = transition_fn(initial_state, plan, config=config)
        self.assertEqual(next_state.free_transfers, 5)

    def test_transition_fn_chips(self):
        initial_state = PlanningState(
            gameweek=1,
            squad=self.squad.to_state_squad(),
            budget=1.0,
            free_transfers=1,
        )

        # Wildcard chip
        plan = GWPlan(
            transfers=[],
            lineup=LineupAction(
                starting_xi=[p.player_id for p in self.squad_players[:11]],
                captain="mid_0",
                vice_captain="mid_1",
            ),
            chip=ChipAction(chip_name="Wildcard"),
        )

        next_state = transition_fn(initial_state, plan)
        self.assertIn("Wildcard", next_state.chips_used)

        # Free Hit chip: squad reverts to original squad at next GW
        plan_fh = GWPlan(
            transfers=[TransferAction(player_out="mid_0", player_in="temp_player")],
            lineup=LineupAction(
                starting_xi=[p.player_id for p in self.squad_players[:11]],
                captain="mid_1",
                vice_captain="mid_2",
            ),
            chip=ChipAction(chip_name="FreeHit"),
        )
        next_state_fh = transition_fn(initial_state, plan_fh)
        self.assertIn("FreeHit", next_state_fh.chips_used)
        # Squad reverted back!
        self.assertEqual(next_state_fh.squad, initial_state.squad)

    def test_candidate_generation_and_search_integration(self):
        """Test candidate plan generation and integration with PlanningSearch."""
        initial_state = PlanningState(
            gameweek=0,
            squad=self.squad.to_state_squad(),
            budget=1.0,
            free_transfers=1,
        )

        candidate_pool = [
            Player("star_mid", "Star Mid", "MID", "MCI", 7.0),
        ]
        registry = {p.player_id: p for p in self.squad_players}
        pts = {
            "star_mid": 15.0,
            "mid_0": 1.0,
            "mid_1": 8.0,
        }

        candidates = generate_candidate_plans(
            initial_state,
            candidate_pool=candidate_pool,
            expected_points=pts,
            player_registry=registry,
        )

        self.assertGreaterEqual(len(candidates), 1)

        # Verify search can run with candidates and transition_fn
        point_forecasts = {
            0: pts,
            1: pts,
        }
        obj = PlanningObjective(point_forecasts)
        search = PlanningSearch(obj, beam_width=2, horizon=2)

        # Plug candidate generator into search
        search._get_candidate_plans = lambda state: generate_candidate_plans(
            state,
            candidate_pool=candidate_pool,
            expected_points=pts,
            player_registry=registry,
        )

        best_plans = search.plan(initial_state, [], transition_fn)
        self.assertEqual(len(best_plans), 2)
        # Search should have preferred transferring in star_mid
        transfer_ins = [
            t.player_in for plan in best_plans for t in plan.transfers
        ]
        self.assertIn("star_mid", transfer_ins)

    def test_transition_fn_raises_when_player_out_not_in_squad(self):
        initial_state = PlanningState(
            gameweek=1,
            squad=self.squad.to_state_squad(),
            budget=1.0,
            free_transfers=1,
        )
        plan = GWPlan(
            transfers=[TransferAction(player_out="non_existent_player", player_in="mid_new")],
            lineup=LineupAction(
                starting_xi=[p.player_id for p in self.squad_players[:11]],
                captain="mid_0",
                vice_captain="mid_1",
            ),
        )
        with self.assertRaises(ValueError) as ctx:
            transition_fn(initial_state, plan)
        self.assertIn("is not in current squad", str(ctx.exception))

    def test_candidate_generation_filters_unaffordable_players(self):
        initial_state = PlanningState(
            gameweek=0,
            squad=self.squad.to_state_squad(),
            budget=0.0,
            free_transfers=1,
        )
        candidate_pool = [
            Player("expensive_mid", "Expensive Mid", "MID", "BHA", 12.0),
        ]
        registry = {p.player_id: p for p in self.squad_players}
        candidates = generate_candidate_plans(
            initial_state,
            candidate_pool=candidate_pool,
            player_registry=registry,
        )
        transfer_ins = [
            t.player_in for plan in candidates for t in plan.transfers
        ]
        self.assertNotIn("expensive_mid", transfer_ins)

    def test_candidate_generation_filters_club_limit_exceeded(self):
        # Current squad has 3 LIV players: def_2, def_3, mid_0.
        # mid_1 is ARS. Setting mid_1 to lowest projected points forces mid_1 to be the candidate out.
        # Bringing in liv_mid (LIV) would yield 4 LIV players, which must be rejected.
        initial_state = PlanningState(
            gameweek=0,
            squad=self.squad.to_state_squad(),
            budget=5.0,
            free_transfers=1,
        )
        candidate_pool = [
            Player("liv_mid", "Liverpool Mid", "MID", "LIV", 7.0),
        ]
        registry = {p.player_id: p for p in self.squad_players}
        pts = {
            "mid_0": 5.0,
            "mid_1": -1.0,  # lowest points in MID -> selected as out_pid
            "mid_2": 5.0,
            "mid_3": 5.0,
            "mid_4": 5.0,
            "liv_mid": 10.0,
        }
        candidates = generate_candidate_plans(
            initial_state,
            candidate_pool=candidate_pool,
            expected_points=pts,
            player_registry=registry,
        )
        transfer_ins = [
            t.player_in for plan in candidates for t in plan.transfers
        ]
        self.assertNotIn("liv_mid", transfer_ins)


def test_transfers():
    suite = unittest.TestLoader().loadTestsFromTestCase(TestFPLTransfers)
    runner = unittest.TextTestRunner()
    result = runner.run(suite)
    assert result.wasSuccessful()


if __name__ == "__main__":
    unittest.main()
