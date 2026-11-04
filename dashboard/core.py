from __future__ import annotations

from functools import partial
from pathlib import Path

import pandas as pd

from baselines.common import active_pool, player_registry
from data import get_pre_deadline_history
from fpl.squad import greedy_squad
from fpl.transfers import transition_fn
from planning.objective import PlanningObjective
from planning.search import PlanningSearch
from planning.state import PlanningState
from prediction.form_forecast import Forecaster


def load_runs(results_dir: str | Path) -> dict[str, pd.DataFrame]:
    runs: dict[str, list[pd.DataFrame]] = {}
    for path in sorted(Path(results_dir).glob("*/*/seed*/results.csv")):
        name, season, seed = path.parts[-4], path.parts[-3], path.parts[-2]
        runs.setdefault(name, []).append(pd.read_csv(path).assign(season=season, seed=int(seed.removeprefix("seed"))))
    return {name: pd.concat(frames, ignore_index=True) for name, frames in runs.items()}


def cumulative_by_gameweek(results: pd.DataFrame) -> pd.DataFrame:
    per_gw = results.groupby(["strategy", "season", "seed", "gameweek"])["gw_points"].sum().reset_index()
    per_gw["cumulative"] = per_gw.groupby(["strategy", "season", "seed"])["gw_points"].cumsum()
    greedy = per_gw[per_gw["strategy"] == "greedy"].set_index(["season", "seed", "gameweek"])["cumulative"]
    per_gw["gap_to_greedy"] = per_gw["cumulative"] - greedy.reindex(pd.MultiIndex.from_frame(per_gw[["season", "seed", "gameweek"]])).to_numpy()
    return per_gw.groupby(["strategy", "gameweek"])[["cumulative", "gap_to_greedy"]].mean().reset_index()


def gap_to_greedy(results: pd.DataFrame) -> pd.DataFrame:
    totals = results.groupby(["strategy", "season", "seed"])["gw_points"].sum().unstack("strategy")
    gaps = totals.sub(totals["greedy"], axis=0)
    return pd.DataFrame(
        {
            "mean_points": totals.mean(),
            "gap_to_greedy": gaps.mean(),
            "gap_se": gaps.std() / len(gaps) ** 0.5,
            "wins": (gaps > 0).sum(),
            "runs": len(gaps),
        }
    ).sort_values("mean_points", ascending=False)


def recommend_plan(
    data: pd.DataFrame,
    season: str,
    gameweek: int,
    forecaster: Forecaster,
    horizon: int = 4,
    transfer_value: float = 3.0,
    chips: tuple[str, ...] = (),
    budget: float = 100.0,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    history = get_pre_deadline_history(data, current_season=season, current_gameweek=gameweek)
    registry = player_registry(history, season)
    forecasts = forecaster(history, season, gameweek, horizon)
    squad = greedy_squad(active_pool(history, season, registry), forecasts[gameweek], budget=budget)
    state = PlanningState(gameweek, squad.to_state_squad(), round(budget - squad.total_cost, 1), 1)
    step = partial(transition_fn, player_registry=registry)
    search = PlanningSearch(
        PlanningObjective(forecasts, transfer_value=transfer_value),
        horizon=horizon,
        candidate_pool=active_pool(history, season, registry),
        player_registry=registry,
        chips=chips,
    )
    plans = search.plan(state, [], step)

    def name(pid: str) -> str:
        return registry[pid].name if pid in registry else pid

    summary, lineups = [], []
    for plan in plans:
        expected = forecasts.get(state.gameweek, {})
        lineup = plan.lineup
        summary.append(
            {
                "gameweek": state.gameweek,
                "transfers": ", ".join(f"{name(t.player_out)} → {name(t.player_in)}" for t in plan.transfers) or "none",
                "captain": name(lineup.captain),
                "vice_captain": name(lineup.vice_captain),
                "chip": plan.chip.chip_name if plan.chip else "",
                "expected_points": round(sum(expected.get(p, 0.0) for p in lineup.starting_xi) + expected.get(lineup.captain, 0.0), 1),
                "bank": state.budget,
                "free_transfers": state.free_transfers,
            }
        )
        for role, players in (("starter", lineup.starting_xi), ("bench", lineup.bench)):
            for pid in players:
                player = registry.get(pid)
                lineups.append(
                    {
                        "gameweek": state.gameweek,
                        "player": name(pid),
                        "position": player.position if player else "",
                        "team": player.team if player else "",
                        "price": player.price if player else None,
                        "role": "captain" if pid == lineup.captain else ("vice-captain" if pid == lineup.vice_captain else role),
                        "expected_points": round(expected.get(pid, 0.0), 2),
                    }
                )
        state = step(state, plan)
    return pd.DataFrame(summary), pd.DataFrame(lineups)
