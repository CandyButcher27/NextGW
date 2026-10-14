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
    result = score_gameweek(make_state(), plan(xi=("1", "99"), captain="99", vice="1"), outcomes, ScoringConfig())
    assert result["xi_points"] == 1.0
    assert result["captain_bonus"] == 1.0


def test_transfers_beyond_free_transfers_cost_configured_hit():
    outcomes = gameweek_outcomes(make_data(), SEASON, 1)
    gw_plan = plan(transfers=[("3", "4"), ("1", "5"), ("2", "6")])
    result = score_gameweek(make_state(free_transfers=1), gw_plan, outcomes, ScoringConfig(transfer_hit_cost=3.0))
    assert result["hits"] == 2
    assert result["hit_cost"] == 6.0
    assert result["gw_points"] == 11.0 + 10.0 - 6.0


def test_captain_multiplier_is_configurable():
    outcomes = gameweek_outcomes(make_data(), SEASON, 1)
    result = score_gameweek(make_state(), plan(), outcomes, ScoringConfig(captain_multiplier=3.0))
    assert result["captain_bonus"] == 20.0


def test_chips_are_rejected_until_supported():
    gw_plan = GWPlan(transfers=[], lineup=LineupAction(["1"], "1", "1"), chip=ChipAction("TripleCaptain"))
    with pytest.raises(ValueError, match="Chips"):
        score_gameweek(make_state(), gw_plan, gameweek_outcomes(make_data(), SEASON, 1), ScoringConfig())


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
    gw_plan = plan(xi=("1", "2"), captain="2", vice="1", transfers=[("3", "4"), ("1", "5")])
    result = score_gameweek(make_state(free_transfers=2), gw_plan, outcomes, ScoringConfig())
    assert result["transfers"] == "3>4;1>5"
    assert result["starting_xi"] == "1,2"
    assert result["captain_id"] == "2"
    assert result["vice_captain_id"] == "1"


def test_no_transfers_logs_empty_string():
    result = score_gameweek(make_state(), plan(), gameweek_outcomes(make_data(), SEASON, 1), ScoringConfig())
    assert result["transfers"] == ""


def test_simulate_rejects_transition_that_does_not_advance_one_gameweek():
    def stuck(state, gw_plan):
        return state

    with pytest.raises(ValueError, match="transition_fn"):
        simulate(FixedStrategy("fixed", plan()), make_data(), SEASON, 1, 3, make_state(), stuck)
