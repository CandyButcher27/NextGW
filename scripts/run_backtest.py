import sys
import time
import tomllib
from pathlib import Path

import numpy as np
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


def run_season(config: dict, season: str, seed: int) -> pd.DataFrame:
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
    if seed:
        rng = np.random.default_rng([seed, start_gw])
        expected = {pid: pts * rng.lognormal(0.0, config["squad_noise"]) for pid, pts in expected.items()}
    squad = greedy_squad(active_pool(history, season, registry), expected, budget=config["budget"])
    initial_state = PlanningState(start_gw, squad.to_state_squad(), round(config["budget"] - squad.total_cost, 1), 1)

    strategies = [
        *(
            PlannerStrategy(name=f"planner-h{p['horizon']}-d{p.get('discount', 1.0)}", forecaster=forecaster, **p)
            for p in config["planners"]
        ),
        GreedyStrategy(forecaster=forecaster),
        ConventionalStrategy(),
    ]
    return run_experiment(
        name=f"{config['name']}/{season}/seed{seed}",
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
    runs = []
    for season in config["seasons"]:
        for seed in range(config["squad_seeds"]):
            runs.append(run_season(config, season, seed).assign(seed=seed))
    results = pd.concat(runs, ignore_index=True)
    totals = results.groupby(["strategy", "season", "seed"])["gw_points"].sum().unstack("strategy")
    baseline = totals["greedy"]
    summary = pd.DataFrame(
        {
            "mean_per_season": totals.mean(),
            "vs_greedy_mean": totals.sub(baseline, axis=0).mean(),
            "vs_greedy_se": totals.sub(baseline, axis=0).std() / np.sqrt(len(totals)),
            "wins_vs_greedy": (totals.sub(baseline, axis=0) > 0).sum(),
        }
    )
    print(totals.groupby(level="season").mean().T.round(0).to_string())
    print(summary.sort_values("mean_per_season", ascending=False).round(1).to_string())
    print(f"{len(totals)} runs (season x squad seed)")
    print(f"{time.time() - started:.0f}s, results in {Path(config['output_dir']) / config['name']}")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "configs/backtest.toml")
