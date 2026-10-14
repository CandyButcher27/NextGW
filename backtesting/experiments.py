"""Run several strategies over the same backtest period and record how the run was set up."""

from __future__ import annotations

import json
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence

import pandas as pd

from backtesting.simulator import (
    RESULT_COLUMNS,
    ScoringConfig,
    Strategy,
    TransitionFn,
    simulate,
)
from planning.state import PlanningState

RESULTS_FILE = "results.csv"
METADATA_FILE = "metadata.json"


def run_experiment(
    name: str,
    strategies: Sequence[Strategy],
    data: pd.DataFrame,
    season: str,
    start_gw: int,
    end_gw: int,
    initial_state: PlanningState,
    transition_fn: TransitionFn,
    output_dir: str | Path,
    features: Sequence[str],
    config: dict[str, Any] | None = None,
    scoring: ScoringConfig | None = None,
) -> pd.DataFrame:
    """Simulate every strategy from the same ``initial_state`` and save results with metadata.

    Writes ``<output_dir>/<name>/results.csv`` (``RESULT_COLUMNS``, all strategies stacked) and
    ``metadata.json`` recording the data period, features, strategy names, scoring values and
    ``config`` (put seeds and model settings there). Returns the stacked results.
    """
    if not strategies:
        raise ValueError("run_experiment needs at least one strategy")
    names = [strategy.name for strategy in strategies]
    if len(set(names)) != len(names):
        raise ValueError(f"Strategy names must be unique: {names}")
    scoring = scoring or ScoringConfig()

    results = pd.concat(
        [
            simulate(strategy, data, season, start_gw, end_gw, initial_state, transition_fn, scoring)
            for strategy in strategies
        ],
        ignore_index=True,
    )

    run_dir = Path(output_dir) / name
    run_dir.mkdir(parents=True, exist_ok=True)
    results.to_csv(run_dir / RESULTS_FILE, index=False, columns=RESULT_COLUMNS)
    metadata = {
        "name": name,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "data_period": {"season": season, "start_gw": start_gw, "end_gw": end_gw},
        "features": list(features),
        "strategies": names,
        "scoring": asdict(scoring),
        "initial_state": {
            "gameweek": initial_state.gameweek,
            "budget": initial_state.budget,
            "free_transfers": initial_state.free_transfers,
            "squad_size": len(initial_state.squad),
        },
        "config": config or {},
    }
    (run_dir / METADATA_FILE).write_text(json.dumps(metadata, indent=2, default=str), encoding="utf-8")
    return results
