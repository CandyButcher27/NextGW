import json

import pandas as pd
import pytest

from backtesting.experiments import METADATA_FILE, RESULTS_FILE, run_experiment
from backtesting.simulator import RESULT_COLUMNS, ScoringConfig
from planning.actions import GWPlan, LineupAction
from planning.state import PlanningState

SEASON = "2023-24"


def make_data() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {"season": SEASON, "gameweek": gw, "player_id": pid, "total_points": pts, "minutes": 90}
            for gw in (1, 2)
            for pid, pts in ((1, 2), (2, 6))
        ]
    )


def initial_state() -> PlanningState:
    return PlanningState(gameweek=1, squad=(("1", "MID"), ("2", "FWD")), budget=100.0, free_transfers=1)


def next_gw(state, plan):
    return PlanningState(state.gameweek + 1, state.squad, state.budget, state.free_transfers, state.chips_used)


class CaptainStrategy:
    def __init__(self, name: str, captain: str):
        self.name = name
        self.captain = captain

    def decide(self, state, history, season, gameweek):
        return GWPlan(transfers=[], lineup=LineupAction(["1", "2"], self.captain, "1"))


def run(tmp_path, strategies, **kwargs):
    return run_experiment(
        name="smoke",
        strategies=strategies,
        data=make_data(),
        season=SEASON,
        start_gw=1,
        end_gw=2,
        initial_state=initial_state(),
        transition_fn=next_gw,
        output_dir=tmp_path,
        features=["form_5", "minutes_5"],
        **kwargs,
    )


def test_run_experiment_stacks_all_strategies(tmp_path):
    results = run(tmp_path, [CaptainStrategy("cap1", "1"), CaptainStrategy("cap2", "2")])
    assert len(results) == 4
    totals = results.groupby("strategy")["gw_points"].sum()
    assert totals["cap1"] == 20.0
    assert totals["cap2"] == 28.0


def test_run_experiment_writes_results_and_metadata(tmp_path):
    run(
        tmp_path,
        [CaptainStrategy("cap2", "2")],
        config={"seed": 7, "horizon": 4},
        scoring=ScoringConfig(transfer_hit_cost=4.0, captain_multiplier=2.0),
    )
    run_dir = tmp_path / "smoke"
    saved = pd.read_csv(run_dir / RESULTS_FILE)
    assert list(saved.columns) == RESULT_COLUMNS
    metadata = json.loads((run_dir / METADATA_FILE).read_text(encoding="utf-8"))
    assert metadata["data_period"] == {"season": SEASON, "start_gw": 1, "end_gw": 2}
    assert metadata["features"] == ["form_5", "minutes_5"]
    assert metadata["strategies"] == ["cap2"]
    assert metadata["config"] == {"seed": 7, "horizon": 4}
    assert metadata["scoring"] == {"transfer_hit_cost": 4.0, "captain_multiplier": 2.0}
    assert metadata["initial_state"]["gameweek"] == 1


def test_run_experiment_rejects_empty_or_duplicate_strategies(tmp_path):
    with pytest.raises(ValueError, match="at least one"):
        run(tmp_path, [])
    with pytest.raises(ValueError, match="unique"):
        run(tmp_path, [CaptainStrategy("same", "1"), CaptainStrategy("same", "2")])
