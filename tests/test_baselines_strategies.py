import pandas as pd

from baselines.common import active_pool, player_registry
from prediction.form_forecast import rolling_form
from baselines.conventional import ConventionalStrategy
from baselines.greedy import GreedyStrategy
from fpl.transfers import transition_fn
from planning.state import PlanningState

SEASON = "2023-24"
POSITIONS = ["GK"] * 2 + ["DEF"] * 5 + ["MID"] * 5 + ["FWD"] * 3


def make_history(points: dict[str, list[int]], minutes: dict[str, list[int]] | None = None) -> pd.DataFrame:
    positions = {f"p{i}": pos for i, pos in enumerate(POSITIONS)}
    positions.update({"sub_mid": "MID", "star_mid": "MID"})
    rows = []
    for pid, pos in positions.items():
        for gw in range(1, 5):
            pts = points.get(pid, [2, 2, 2, 2])[gw - 1]
            mins = (minutes or {}).get(pid, [90, 90, 90, 90])[gw - 1]
            rows.append(
                {
                    "season": SEASON, "gameweek": gw, "player_id": pid, "web_name": pid, "position": pos,
                    "team": f"T_{pid}", "price": 5.0, "total_points": pts, "minutes": mins,
                }
            )
    return pd.DataFrame(rows)


def make_state() -> PlanningState:
    return PlanningState(5, tuple(sorted((f"p{i}", pos) for i, pos in enumerate(POSITIONS))), 0.0, 1)


def squad_after(state: PlanningState, plan) -> set[str]:
    squad = {pid for pid, _ in state.squad}
    squad -= {t.player_out for t in plan.transfers}
    return squad | {t.player_in for t in plan.transfers}


def test_rolling_form_uses_last_window_gameweeks():
    history = make_history({"p0": [10, 0, 4, 6]})
    assert rolling_form(history, SEASON, 2)["p0"] == 5.0


def test_active_pool_skips_players_missing_from_latest_gameweek():
    history = make_history({})
    history = history.loc[~((history["player_id"] == "sub_mid") & (history["gameweek"] == 4))]
    pool_ids = {p.player_id for p in active_pool(history, SEASON, player_registry(history, SEASON))}
    assert "sub_mid" not in pool_ids
    assert "star_mid" in pool_ids


def test_greedy_buys_in_form_player_with_free_transfer():
    history = make_history({"star_mid": [12, 12, 12, 12], "p7": [0, 0, 0, 0]})
    state = make_state()
    plan = GreedyStrategy().decide(state, history, SEASON, 5)
    assert [(t.player_out, t.player_in) for t in plan.transfers] == [("p7", "star_mid")]
    assert plan.lineup.captain == "star_mid"
    assert set(plan.lineup.starting_xi) <= squad_after(state, plan)
    transition_fn(state, plan, player_registry=player_registry(history, SEASON))


def test_conventional_holds_when_everyone_plays():
    history = make_history({"star_mid": [12, 12, 12, 12]})
    plan = ConventionalStrategy().decide(make_state(), history, SEASON, 5)
    assert plan.transfers == []


def test_conventional_replaces_absent_player_with_best_form():
    history = make_history(
        {"star_mid": [12, 12, 12, 12], "sub_mid": [3, 3, 3, 3]},
        minutes={"p8": [90, 90, 0, 0]},
    )
    state = make_state()
    plan = ConventionalStrategy().decide(state, history, SEASON, 5)
    assert [(t.player_out, t.player_in) for t in plan.transfers] == [("p8", "star_mid")]
    assert set(plan.lineup.starting_xi) <= squad_after(state, plan)
    transition_fn(state, plan, player_registry=player_registry(history, SEASON))
