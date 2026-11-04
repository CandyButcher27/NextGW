import sys
import time
import tomllib
from pathlib import Path

import pandas as pd

from backtesting.experiments import run_experiment
from baselines.common import active_pool, backtest_transition, player_registry
from baselines.conventional import ConventionalStrategy
from baselines.greedy import GreedyStrategy
from data import get_pre_deadline_history, load_clean_player_gw_data
from fpl.squad import greedy_squad
from planning.state import PlanningState
from planning.strategy import PlannerStrategy
from prediction.form_forecast import fixture_forecaster, fixture_schedule, form_forecast


def oracle_forecaster(data: pd.DataFrame):
    """Leaks realised points on purpose: an upper bound for what better forecasts could buy. Never a result."""
    actual = data.groupby(["gameweek", data["player_id"].astype(str)])["total_points"].sum()
    by_gw = {gw: points.droplevel(0).to_dict() for gw, points in actual.groupby(level=0)}
    return lambda history, season, gameweek, horizon: {gw: by_gw.get(gw, {}) for gw in range(gameweek, gameweek + horizon)}


def run_season(config: dict, season: str) -> pd.DataFrame:
    start_gw = config["start_gw"]
    data = load_clean_player_gw_data(season=season, auto_fetch=False)
    history = get_pre_deadline_history(data, current_season=season, current_gameweek=start_gw)
    registry = player_registry(history, season)
    forecaster = {
        "form": lambda: form_forecast,
        "fixture": lambda: fixture_forecaster(fixture_schedule(data)),
        "oracle": lambda: oracle_forecaster(data),
    }[config["forecaster"]]()
    expected = fixture_forecaster(fixture_schedule(data))(history, season, start_gw, 1)[start_gw]
    squad = greedy_squad(active_pool(history, season, registry), expected, budget=config["budget"])
    initial_state = PlanningState(start_gw, squad.to_state_squad(), round(config["budget"] - squad.total_cost, 1), 1)

    planner = config["planner"]
    strategies = [
        *(
            PlannerStrategy(name=f"planner-h{h}", horizon=h, beam_width=planner["beam_width"], forecaster=forecaster)
            for h in planner["horizons"]
        ),
        GreedyStrategy(forecaster=forecaster),
        ConventionalStrategy(),
    ]
    return run_experiment(
        name=f"{config['name']}/{season}",
        strategies=strategies,
        data=data,
        season=season,
        start_gw=start_gw,
        end_gw=config["end_gw"],
        initial_state=initial_state,
        transition_fn=backtest_transition(data, season),
        output_dir=config["output_dir"],
        features=config["features"],
        config=config,
    )


def main(config_path: str) -> None:
    config = tomllib.loads(Path(config_path).read_text(encoding="utf-8"))
    started = time.time()
    results = pd.concat([run_season(config, season) for season in config["seasons"]], ignore_index=True)
    per_season = results.pivot_table(index="strategy", columns="season", values="gw_points", aggfunc="sum")
    per_season["total"] = per_season.sum(axis=1)
    activity = results.groupby("strategy").agg(transfers=("num_transfers", "sum"), hits=("hits", "sum"), captain_bonus=("captain_bonus", "sum"))
    print(per_season.join(activity).sort_values("total", ascending=False).round(0).to_string())
    print(f"{time.time() - started:.0f}s, results in {Path(config['output_dir']) / config['name']}")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "configs/backtest.toml")
