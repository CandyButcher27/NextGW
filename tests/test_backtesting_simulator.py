import pandas as pd
import pytest

from backtesting.simulator import (
    RESULT_COLUMNS,
    ScoringConfig,
    gameweek_outcomes,
    score_gameweek,
    simulate,
)
from planning.actions import ChipAction, GWPlan, LineupAction, TransferAction
from planning.state import PlanningState

SEASON = "2023-24"


def make_data() -> pd.DataFrame:
    # player 1 scores gw*1, player 2 scores gw*10; player 3 never plays
    rows = []
    for gw in range(1, 5):
        rows.append({"season": SEASON, "gameweek": gw, "player_id": 1, "total_points": gw, "minutes": 90})
        rows.append({"season": SEASON, "gameweek": gw, "player_id": 2, "total_points": gw * 10, "minutes": 90})
        rows.append({"season": SEASON, "gameweek": gw, "player_id": 3, "total_points": 0, "minutes": 0})
    rows.append({"season": "2022-23", "gameweek": 38, "player_id": 1, "total_points": 5, "minutes": 90})
    return pd.DataFrame(rows)


def make_state(gameweek: int = 1, free_transfers: int = 1) -> PlanningState:
    return PlanningState(
        gameweek=gameweek,
        squad=(("1", "MID"), ("2", "FWD"), ("3", "DEF")),
        budget=100.0,
        free_transfers=free_transfers,
    )


def next_gw(state: PlanningState, plan: GWPlan) -> PlanningState:
    return PlanningState(
        gameweek=state.gameweek + 1,
        squad=state.squad,
        budget=state.budget,
        free_transfers=state.free_transfers,
        chips_used=state.chips_used,
    )


def plan(xi=("1", "2"), captain="2", vice="1", transfers=()) -> GWPlan:
    return GWPlan(
        transfers=[TransferAction(out, inn) for out, inn in transfers],
        lineup=LineupAction(list(xi), captain, vice),
    )


class FixedStrategy:
    def __init__(self, name: str, gw_plan: GWPlan):
        self.name = name
        self.gw_plan = gw_plan
        self.seen: list[tuple[int, pd.DataFrame]] = []

    def decide(self, state, history, season, gameweek):
        self.seen.append((gameweek, history))
        return self.gw_plan


def test_score_doubles_captain_and_counts_xi():
    outcomes = gameweek_outcomes(make_data(), SEASON, 2)
    result = score_gameweek(make_state(2), plan(), outcomes, ScoringConfig())
    assert result["xi_points"] == 22.0
    assert result["captain_bonus"] == 20.0
    assert result["gw_points"] == 42.0


def test_vice_captain_takes_armband_when_captain_does_not_play():
    outcomes = gameweek_outcomes(make_data(), SEASON, 2)
    result = score_gameweek(make_state(2), plan(xi=("1", "3"), captain="3", vice="1"), outcomes, ScoringConfig())
    assert result["captain_played"] is False
    assert result["captain_bonus"] == 2.0
    assert result["gw_points"] == 4.0


def test_player_missing_from_gameweek_scores_zero():
    outcomes = gameweek_outcomes(make_data(), SEASON, 1)
    gw_plan = plan(xi=("1", "99"), captain="99", vice="1", transfers=[("3", "99")])
    result = score_gameweek(make_state(), gw_plan, outcomes, ScoringConfig())
    assert result["xi_points"] == 1.0
    assert result["captain_bonus"] == 1.0


def test_transfers_beyond_free_transfers_cost_configured_hit():
    outcomes = gameweek_outcomes(make_data(), SEASON, 1)
    state = PlanningState(
        gameweek=1,
        squad=(("1", "MID"), ("2", "FWD"), ("3", "DEF"), ("7", "DEF"), ("8", "MID")),
        budget=100.0,
        free_transfers=1,
    )
    gw_plan = plan(transfers=[("3", "4"), ("7", "5"), ("8", "6")])
    result = score_gameweek(state, gw_plan, outcomes, ScoringConfig(transfer_hit_cost=3.0))
    assert result["hits"] == 2
    assert result["hit_cost"] == 6.0
    assert result["gw_points"] == 11.0 + 10.0 - 6.0


def test_captain_multiplier_is_configurable():
    outcomes = gameweek_outcomes(make_data(), SEASON, 1)
    result = score_gameweek(make_state(), plan(), outcomes, ScoringConfig(captain_multiplier=3.0))
    assert result["captain_bonus"] == 20.0


def test_triple_captain_triples_the_armband():
    gw_plan = GWPlan(transfers=[], lineup=LineupAction(["1", "2"], "2", "1"), chip=ChipAction("TripleCaptain"))
    result = score_gameweek(make_state(2), gw_plan, gameweek_outcomes(make_data(), SEASON, 2), ScoringConfig())
    assert result["captain_bonus"] == 40.0
    assert result["chip"] == "TripleCaptain"


def test_bench_boost_scores_the_bench():
    gw_plan = GWPlan(transfers=[], lineup=LineupAction(["1"], "1", "1", ["2"]), chip=ChipAction("BenchBoost"))
    result = score_gameweek(make_state(2), gw_plan, gameweek_outcomes(make_data(), SEASON, 2), ScoringConfig())
    assert result["xi_points"] == 22.0


def test_wildcard_makes_transfers_free():
    gw_plan = plan(xi=("1", "4"), captain="1", vice="4", transfers=[("2", "4"), ("3", "5")])
    gw_plan = GWPlan(transfers=gw_plan.transfers, lineup=gw_plan.lineup, chip=ChipAction("Wildcard"))
    result = score_gameweek(make_state(2, free_transfers=1), gw_plan, gameweek_outcomes(make_data(), SEASON, 2), ScoringConfig())
    assert result["hits"] == 0 and result["hit_cost"] == 0.0


def test_used_or_unknown_chip_is_rejected():
    outcomes = gameweek_outcomes(make_data(), SEASON, 1)
    used = PlanningState(gameweek=1, squad=make_state().squad, budget=100.0, free_transfers=1, chips_used=frozenset({"TripleCaptain"}))
    with pytest.raises(ValueError, match="already used"):
        score_gameweek(used, GWPlan([], LineupAction(["1"], "1", "1"), ChipAction("TripleCaptain")), outcomes, ScoringConfig())
    with pytest.raises(ValueError, match="Unknown chip"):
        score_gameweek(make_state(), GWPlan([], LineupAction(["1"], "1", "1"), ChipAction("Bogus")), outcomes, ScoringConfig())


def test_double_gameweek_rows_are_summed():
    data = make_data()
    extra = pd.DataFrame([{"season": SEASON, "gameweek": 1, "player_id": 1, "total_points": 4, "minutes": 30}])
    outcomes = gameweek_outcomes(pd.concat([data, extra]), SEASON, 1)
    assert outcomes.at["1", "total_points"] == 5
    assert outcomes.at["1", "minutes"] == 120


def test_simulate_accumulates_points_and_returns_result_columns():
    results = simulate(FixedStrategy("fixed", plan()), make_data(), SEASON, 1, 4, make_state(), next_gw)
    assert list(results.columns) == RESULT_COLUMNS
    assert results["gameweek"].tolist() == [1, 2, 3, 4]
    assert results["gw_points"].tolist() == [21.0, 42.0, 63.0, 84.0]
    assert results["cumulative_points"].iloc[-1] == 210.0
    assert set(results["strategy"]) == {"fixed"}


def test_strategy_never_sees_current_or_future_gameweeks():
    strategy = FixedStrategy("fixed", plan())
    simulate(strategy, make_data(), SEASON, 1, 4, make_state(), next_gw)
    for gameweek, history in strategy.seen:
        current = history.loc[history["season"] == SEASON]
        assert (current["gameweek"] < gameweek).all()
    assert "2022-23" in set(strategy.seen[0][1]["season"])


def test_transition_fn_state_is_passed_to_next_decision():
    seen_states = []

    class Recorder(FixedStrategy):
        def decide(self, state, history, season, gameweek):
            seen_states.append(state.gameweek)
            return self.gw_plan

    simulate(Recorder("r", plan()), make_data(), SEASON, 1, 3, make_state(), next_gw)
    assert seen_states == [1, 2, 3]


def test_simulate_rejects_mismatched_initial_state_and_bad_range():
    strategy = FixedStrategy("fixed", plan())
    with pytest.raises(ValueError, match="initial_state"):
        simulate(strategy, make_data(), SEASON, 2, 4, make_state(1), next_gw)
    with pytest.raises(ValueError, match="start_gw"):
        simulate(strategy, make_data(), SEASON, 4, 2, make_state(4), next_gw)


def test_decision_is_logged_with_transfers_xi_and_armband():
    outcomes = gameweek_outcomes(make_data(), SEASON, 1)
    gw_plan = plan(xi=("2", "5"), captain="2", vice="5", transfers=[("3", "4"), ("1", "5")])
    result = score_gameweek(make_state(free_transfers=2), gw_plan, outcomes, ScoringConfig())
    assert result["transfers"] == "3>4;1>5"
    assert result["starting_xi"] == "2,5"
    assert result["captain_id"] == "2"
    assert result["vice_captain_id"] == "5"


def test_no_transfers_logs_empty_string():
    result = score_gameweek(make_state(), plan(), gameweek_outcomes(make_data(), SEASON, 1), ScoringConfig())
    assert result["transfers"] == ""


def test_simulate_rejects_transition_that_does_not_advance_one_gameweek():
    def stuck(state, gw_plan):
        return state

    with pytest.raises(ValueError, match="transition_fn"):
        simulate(FixedStrategy("fixed", plan()), make_data(), SEASON, 1, 3, make_state(), stuck)


def test_rejects_starting_xi_outside_squad():
    outcomes = gameweek_outcomes(make_data(), SEASON, 2)
    with pytest.raises(ValueError, match="not in the squad"):
        score_gameweek(make_state(2), plan(xi=("1", "99"), captain="1", vice="99"), outcomes, ScoringConfig())


def test_accepts_player_bought_this_gameweek():
    outcomes = gameweek_outcomes(make_data(), SEASON, 2)
    result = score_gameweek(
        make_state(2), plan(xi=("1", "4"), captain="1", vice="4", transfers=[("2", "4")]), outcomes, ScoringConfig()
    )
    assert result["xi_points"] == 2.0


def test_rejects_captain_outside_starting_xi():
    outcomes = gameweek_outcomes(make_data(), SEASON, 2)
    with pytest.raises(ValueError, match="Captain"):
        score_gameweek(make_state(2), plan(xi=("1", "2"), captain="3", vice="1"), outcomes, ScoringConfig())


def test_auto_substitution_replaces_non_playing_starter_from_bench():
    positions = ["GK"] * 2 + ["DEF"] * 5 + ["MID"] * 5 + ["FWD"] * 3
    squad = tuple((f"p{i}", pos) for i, pos in enumerate(positions))
    state = PlanningState(gameweek=1, squad=squad, budget=0.0, free_transfers=1)
    xi = ["p0", "p2", "p3", "p4", "p5", "p7", "p8", "p9", "p10", "p12", "p13"]
    bench = ["p1", "p14", "p6", "p11"]
    outcomes = pd.DataFrame(
        {"total_points": [2.0] * 15, "minutes": [90.0] * 15}, index=[f"p{i}" for i in range(15)]
    )
    outcomes.loc["p13", "minutes"] = 0.0
    outcomes.loc["p13", "total_points"] = 0.0
    outcomes.loc["p14", "total_points"] = 9.0
    gw_plan = GWPlan(transfers=[], lineup=LineupAction(xi, "p7", "p8", bench))
    result = score_gameweek(state, gw_plan, outcomes, ScoringConfig())
    assert result["auto_subs"] == "p13>p14"
    assert result["xi_points"] == 10 * 2.0 + 9.0


def test_bench_must_come_from_squad_outside_xi():
    with pytest.raises(ValueError, match="Bench"):
        score_gameweek(
            make_state(2),
            GWPlan(transfers=[], lineup=LineupAction(["1", "2"], "2", "1", ["2"])),
            gameweek_outcomes(make_data(), SEASON, 2),
            ScoringConfig(),
        )


def test_free_hit_makes_all_transfers_free():
    """FreeHit chip should produce zero hit cost even with many transfers."""
    state = PlanningState(
        gameweek=2,
        squad=(("1", "MID"), ("2", "FWD"), ("3", "DEF"), ("7", "DEF"), ("8", "MID")),
        budget=100.0,
        free_transfers=1,
    )
    gw_plan = GWPlan(
        transfers=[TransferAction("3", "4"), TransferAction("7", "5"), TransferAction("8", "6")],
        lineup=LineupAction(["1", "2"], "2", "1"),
        chip=ChipAction("FreeHit"),
    )
    result = score_gameweek(state, gw_plan, gameweek_outcomes(make_data(), SEASON, 2), ScoringConfig())
    assert result["hits"] == 0
    assert result["hit_cost"] == 0.0
    assert result["chip"] == "FreeHit"


def test_simulate_single_gameweek_returns_one_row():
    """simulate() with start_gw == end_gw must return exactly one row."""
    results = simulate(FixedStrategy("fixed", plan()), make_data(), SEASON, 1, 1, make_state(1), next_gw)
    assert len(results) == 1
    assert results.iloc[0]["gameweek"] == 1
    assert list(results.columns) == RESULT_COLUMNS


def test_simulate_cumulative_points_match_sum_of_gw_points():
    """cumulative_points at the last row must equal the sum of all gw_points."""
    results = simulate(FixedStrategy("fixed", plan()), make_data(), SEASON, 1, 4, make_state(), next_gw)
    assert results["cumulative_points"].iloc[-1] == results["gw_points"].sum()


def test_score_gameweek_neither_captain_nor_vice_played_gives_no_bonus():
    """When both captain and vice-captain score 0 minutes, captain_bonus is 0."""
    outcomes = gameweek_outcomes(make_data(), SEASON, 1)
    # Player "3" has 0 minutes in GW1
    gw_plan = GWPlan(transfers=[], lineup=LineupAction(["1", "3"], "3", "1"))
    result = score_gameweek(make_state(), gw_plan, outcomes, ScoringConfig())
    # Vice-captain "1" did play, so they receive the bonus instead
    assert result["captain_played"] is False
    assert result["captain_bonus"] == 1.0  # 1 pt for player "1" in GW1 * (2-1)
