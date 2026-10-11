"""Prediction APIs for single-player and whole-Gameweek point forecasts."""

from __future__ import annotations

from collections.abc import Mapping

import pandas as pd

from data.leakage import get_pre_deadline_history
from prediction.features import FEATURE_COLUMNS, KEY_COLUMNS, build_feature_frame
from prediction.model import PlayerPointsModel


def predict_gameweek(
    model: PlayerPointsModel,
    history: pd.DataFrame,
    fixtures: pd.DataFrame,
) -> pd.DataFrame:
    """Predict points for fixture rows using only pre-deadline historical outcomes.

    ``fixtures`` must describe one season/Gameweek and include one row per player fixture.
    It may be built from the historical data during backtesting; any outcomes present in
    those rows are ignored by feature construction.
    """
    missing = [column for column in KEY_COLUMNS if column not in fixtures.columns]
    if missing:
        raise ValueError(f"fixtures is missing required key columns: {missing}")
    if fixtures.empty:
        return pd.DataFrame(columns=[*KEY_COLUMNS, "predicted_points"])
    targets = fixtures.loc[:, ["season", "gameweek"]].drop_duplicates()
    if len(targets) != 1:
        raise ValueError("fixtures must contain exactly one season and Gameweek")
    season = str(targets.iloc[0]["season"])
    gameweek = int(targets.iloc[0]["gameweek"])
    if model.as_of_season is not None:
        if (season, gameweek) < (model.as_of_season, int(model.as_of_gameweek or 0)):
            raise ValueError("Cannot predict before the model's training cutoff")

    pre_deadline_history = get_pre_deadline_history(
        history, current_season=season, current_gameweek=gameweek
    )
    combined = pd.concat([pre_deadline_history, fixtures], ignore_index=True, sort=False)
    feature_frame = build_feature_frame(combined).tail(len(fixtures))
    raw_prediction = model.estimator.predict(feature_frame.loc[:, list(FEATURE_COLUMNS)])
    prediction = pd.Series(raw_prediction, index=fixtures.index).clip(lower=0.0)
    result = fixtures.loc[:, list(KEY_COLUMNS)].copy()
    result["predicted_points"] = prediction.to_numpy()
    return result.reset_index(drop=True)


def predict_player_points(
    model: PlayerPointsModel,
    history: pd.DataFrame,
    player_id: int,
    season: str,
    gameweek: int,
    fixture_context: Mapping[str, object] | None = None,
) -> float:
    """Return one player's expected FPL points for a requested Gameweek.

    ``fixture_context`` can supply known deadline-time fields such as ``opponent_team``,
    ``was_home``, and ``matches_in_gw``. If omitted, the latest known position and team
    are carried forward, with unknown opponent/home context.
    """
    pre_deadline_history = get_pre_deadline_history(
        history, current_season=season, current_gameweek=gameweek
    )
    player_history = pre_deadline_history.loc[pre_deadline_history["player_id"] == player_id]
    fixture: dict[str, object] = {
        "season": season,
        "gameweek": gameweek,
        "player_id": player_id,
        "position": "unknown",
        "team": "unknown",
        "opponent_team": "unknown",
        "was_home": None,
        "matches_in_gw": 1,
    }
    if not player_history.empty:
        latest = player_history.sort_values(["season", "gameweek"]).iloc[-1]
        fixture.update({key: latest[key] for key in ("position", "team") if key in latest.index})
    if fixture_context:
        fixture.update(fixture_context)
    fixture_rows = pd.DataFrame([fixture])
    result = predict_gameweek(model, pre_deadline_history, fixture_rows)
    return float(result.iloc[0]["predicted_points"])
