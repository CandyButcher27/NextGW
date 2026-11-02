import numpy as np
import pytest

from fpl.squad import Player
from fpl.transfers import transition_fn
from planning import plan, plan_with_utility
from planning.actions import TransferAction
from planning.state import PlanningState
from uncertainty.scenarios import PlayerScenario, ScenarioResult


def _squad() -> tuple[tuple[str, str], ...]:
    return (
        ("1", "GK"),
        ("2", "GK"),
        *((str(player_id), "DEF") for player_id in range(3, 8)),
        *((str(player_id), "MID") for player_id in range(8, 13)),
        *((str(player_id), "FWD") for player_id in range(13, 16)),
    )


def _sample(player_8: float) -> dict[int, dict[str, float]]:
    forecasts = {}
    for gameweek in range(1, 5):
        points = {str(player_id): 1.0 for player_id in range(1, 16)}
        points["8"] = player_8
        points["9"] = 9.0
        forecasts[gameweek] = points
    return forecasts


def _scenario_result() -> ScenarioResult:
    first = _sample(10.0)
    second = _sample(0.0)
    player_scenarios = {}
    for player_id in range(1, 16):
        values = np.array(
            [
                [first[gameweek][str(player_id)] for gameweek in range(1, 5)],
                [second[gameweek][str(player_id)] for gameweek in range(1, 5)],
            ],
            dtype=np.float64,
        )
        player_scenarios[player_id] = PlayerScenario(
            player_id=player_id,
            season="2026-27",
            gameweeks=np.arange(1, 5, dtype=np.int64),
            scenarios=values,
            pred_means=np.mean(values, axis=0),
            pred_stds=np.std(values, axis=0, ddof=1),
        )
    return ScenarioResult(
        n_scenarios=2,
        season="2026-27",
        player_scenarios=player_scenarios,
    )


def test_plan_uses_mean_of_all_scenario_samples_and_fpl_lineups() -> None:
    initial_state = PlanningState(
        gameweek=1,
        squad=_squad(),
        budget=0.0,
        free_transfers=1,
    )

    result = plan(initial_state, [_sample(10.0), _sample(0.0)], transition_fn)

    assert len(result) == 4
    assert all(not gameweek_plan.transfers for gameweek_plan in result)
    assert all(gameweek_plan.lineup.captain == "9" for gameweek_plan in result)
    assert all(gameweek_plan.lineup.vice_captain != "9" for gameweek_plan in result)

    scored_result = plan_with_utility(
        initial_state,
        [_sample(10.0), _sample(0.0)],
        transition_fn,
    )
    assert scored_result.plans == tuple(result)
    assert scored_result.expected_utility == 128.0


def test_plan_accepts_uncertainty_scenario_result() -> None:
    initial_state = PlanningState(
        gameweek=1,
        squad=_squad(),
        budget=0.0,
        free_transfers=1,
    )

    result = plan(initial_state, _scenario_result(), transition_fn)

    assert len(result) == 4
    assert all(gameweek_plan.lineup.captain == "9" for gameweek_plan in result)


def test_plan_searches_legal_transfer_candidates() -> None:
    from functools import partial

    initial_state = PlanningState(
        gameweek=1,
        squad=_squad(),
        budget=0.5,
        free_transfers=1,
    )
    player_registry = {
        player_id: Player(
            player_id=player_id,
            name=player_id,
            position=position,
            team=f"team-{player_id}",
            price=5.0,
        )
        for player_id, position in _squad()
    }
    target = Player("99", "Target", "MID", "team-99", 5.5)
    next_target = Player("100", "Next Target", "MID", "team-100", 5.5)
    player_registry[target.player_id] = target
    player_registry[next_target.player_id] = next_target
    forecasts = []
    for _ in range(2):
        sample = _sample(1.0)
        for gameweek in range(1, 5):
            sample[gameweek]["8"] = 0.0
            sample[gameweek]["99"] = 20.0
            sample[gameweek]["100"] = 19.0
        forecasts.append(sample)

    result = plan_with_utility(
        initial_state,
        forecasts,
        partial(transition_fn, player_registry=player_registry),
        candidate_pool=[target, next_target],
        player_registry=player_registry,
    )

    assert len(result.plans) == 4
    assert result.plans[0].transfers == [TransferAction("8", "99")]
    assert not result.plans[1].transfers
    assert result.expected_utility is not None
    assert result.expected_utility > 0.0
    assert plan(
        initial_state,
        forecasts,
        partial(transition_fn, player_registry=player_registry),
        candidate_pool=[target, next_target],
        player_registry=player_registry,
    ) == list(result.plans)


def test_transfer_search_requires_current_squad_metadata() -> None:
    from functools import partial

    initial_state = PlanningState(
        gameweek=1,
        squad=_squad(),
        budget=0.0,
        free_transfers=1,
    )
    target = Player("99", "Target", "MID", "team-99", 5.0)

    with pytest.raises(ValueError, match="metadata is required for current squad"):
        plan(
            initial_state,
            [_sample(1.0)],
            partial(transition_fn),
            candidate_pool=[target],
        )
