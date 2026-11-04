import sys
import time
import tomllib
from pathlib import Path

from backtesting.experiments import run_experiment
from baselines.common import active_pool, backtest_transition, form_forecast, player_registry
from baselines.conventional import ConventionalStrategy
from baselines.greedy import GreedyStrategy
from data import get_pre_deadline_history, load_clean_player_gw_data
from fpl.squad import greedy_squad
from planning.state import PlanningState
from planning.strategy import PlannerStrategy


def main(config_path: str) -> None:
    config = tomllib.loads(Path(config_path).read_text(encoding="utf-8"))
    season, start_gw = config["season"], config["start_gw"]
    data = load_clean_player_gw_data(season=season, auto_fetch=False)

    history = get_pre_deadline_history(data, current_season=season, current_gameweek=start_gw)
    registry = player_registry(history, season)
    expected = form_forecast(history, season, start_gw, 1)[start_gw]
    squad = greedy_squad(active_pool(history, season, registry), expected, budget=config["budget"])
    initial_state = PlanningState(start_gw, squad.to_state_squad(), round(config["budget"] - squad.total_cost, 1), 1)

    strategies = [
        PlannerStrategy(**config["planner"]),
        GreedyStrategy(),
        ConventionalStrategy(),
    ]
    started = time.time()
    results = run_experiment(
        name=config["name"],
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
    summary = results.groupby("strategy").agg(
        total=("gw_points", "sum"),
        per_gw=("gw_points", "mean"),
        transfers=("num_transfers", "sum"),
        hits=("hits", "sum"),
        captain_bonus=("captain_bonus", "sum"),
    )
    print(summary.sort_values("total", ascending=False).round(1).to_string())
    print(f"{time.time() - started:.0f}s, results in {Path(config['output_dir']) / config['name']}")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "configs/backtest.toml")
