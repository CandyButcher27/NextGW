"""Proposed planner-facing predictor interface and artifact loading."""

from __future__ import annotations

import pickle
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from data.leakage import get_pre_deadline_history
from prediction.predict import predict_gameweek
from prediction.model import PlayerPointsModel

ARTIFACT_VERSION = 1
QUANTILE_LEVELS: tuple[float, ...] = (0.10, 0.25, 0.50, 0.75, 0.90)


@dataclass
class Predictor:
    """Planner-facing, **PROPOSED** API pending consumer sign-off.

    The artifact contains a fitted model, player history, optional future fixture rows,
    and the season to forecast. See ``prediction/ASSUMPTIONS.md`` for the artifact and
    forecast contracts.
    """

    model: PlayerPointsModel
    history: pd.DataFrame
    fixtures: pd.DataFrame
    season: str

    @classmethod
    def load(cls, path: str | Path) -> "Predictor":
        """Load a trusted local predictor artifact written by ``save_predictor_artifact``."""
        with Path(path).open("rb") as artifact_file:
            artifact = pickle.load(artifact_file)  # noqa: S301 - artifact must be trusted
        if not isinstance(artifact, dict) or artifact.get("artifact_version") != ARTIFACT_VERSION:
            raise ValueError(f"Unsupported predictor artifact; expected version {ARTIFACT_VERSION}")
        model = artifact.get("model")
        history = artifact.get("history")
        fixtures = artifact.get("fixtures", pd.DataFrame())
        season = artifact.get("season")
        if not isinstance(model, PlayerPointsModel):
            raise ValueError("Predictor artifact is missing a fitted PlayerPointsModel")
        if not isinstance(history, pd.DataFrame):
            raise ValueError("Predictor artifact is missing the historical player-Gameweek DataFrame")
        if not isinstance(fixtures, pd.DataFrame):
            raise ValueError("Predictor artifact fixtures must be a pandas DataFrame")
        if not fixtures.empty:
            missing_fixture_keys = {"season", "gameweek", "player_id"} - set(fixtures.columns)
            if missing_fixture_keys:
                raise ValueError(
                    f"Predictor artifact fixtures are missing keys: {sorted(missing_fixture_keys)}"
                )
        if not isinstance(season, str) or not season:
            raise ValueError("Predictor artifact must specify the forecast season")
        return cls(model=model, history=history, fixtures=fixtures, season=season)

    def predict_player_gw(self, player_id: int, gameweek: int) -> dict[str, Any]:
        """Forecast one player/Gameweek, returning mean, spread, and empirical quantiles."""
        fixtures = self.fixtures.loc[
            (self.fixtures.get("season", pd.Series(dtype=str)).astype(str) == self.season)
            & (pd.to_numeric(self.fixtures.get("gameweek", pd.Series(dtype=float)), errors="coerce") == gameweek)
            & (pd.to_numeric(self.fixtures.get("player_id", pd.Series(dtype=float)), errors="coerce") == player_id)
        ] if not self.fixtures.empty else pd.DataFrame()
        if fixtures.empty:
            fixtures = self._fallback_fixtures(self.season, gameweek, player_id=player_id)
        if fixtures.empty:
            raise ValueError(f"No historical player record or fixture found for player_id={player_id}")
        mean = float(
            predict_gameweek(self.model, self.history, fixtures).iloc[0]["predicted_points"]
        )
        position = str(fixtures.iloc[0].get("position", "UNKNOWN"))
        return self._prediction_summary(player_id, self.season, gameweek, mean, position)

    def predict_horizon(
        self,
        season: str,
        as_of_gw: int,
        horizon: int = 4,
    ) -> pd.DataFrame:
        """Forecast all available players for Gameweeks after ``as_of_gw``.

        Future Gameweeks are forecast independently from observed history available
        before each target deadline; predicted outcomes are not fed back recursively.
        """
        if horizon < 1:
            raise ValueError("horizon must be at least 1")
        if self.model.as_of_season is not None and self.model.as_of_gameweek is not None:
            model_cutoff = (self.model.as_of_season, self.model.as_of_gameweek)
            requested_origin = (season, as_of_gw)
            if model_cutoff > requested_origin:
                raise ValueError("Model training cutoff is later than the requested horizon origin")
        origin_history = get_pre_deadline_history(
            self.history, current_season=season, current_gameweek=as_of_gw + 1
        )
        rows: list[dict[str, Any]] = []
        for gameweek in range(as_of_gw + 1, as_of_gw + horizon + 1):
            fixtures = self.fixtures.loc[
                (self.fixtures["season"].astype(str) == season)
                & (pd.to_numeric(self.fixtures["gameweek"], errors="coerce") == gameweek)
            ].copy() if not self.fixtures.empty else pd.DataFrame()
            if fixtures.empty:
                fixtures = self._fallback_fixtures(
                    season, gameweek, history_source=origin_history
                )
            if fixtures.empty:
                continue
            forecasts = predict_gameweek(self.model, origin_history, fixtures)
            for forecast, fixture in zip(
                forecasts.itertuples(index=False), fixtures.itertuples(index=False), strict=True
            ):
                rows.append(
                    self._prediction_summary(
                        int(forecast.player_id),
                        str(forecast.season),
                        int(forecast.gameweek),
                        float(forecast.predicted_points),
                        str(getattr(fixture, "position", "UNKNOWN")),
                    )
                )
        return pd.DataFrame(
            rows,
            columns=[
                "season", "gameweek", "player_id", "pred_mean", "pred_std",
                "quantiles", "uncertainty_status",
            ],
        )

    def _fallback_fixtures(
        self,
        season: str,
        gameweek: int,
        *,
        player_id: int | None = None,
        history_source: pd.DataFrame | None = None,
    ) -> pd.DataFrame:
        source = self.history if history_source is None else history_source
        history = get_pre_deadline_history(
            source, current_season=season, current_gameweek=gameweek
        )
        if player_id is not None:
            history = history.loc[history["player_id"] == player_id]
        if history.empty:
            return pd.DataFrame(columns=["season", "gameweek", "player_id"])
        latest = history.sort_values(["season", "gameweek"]).groupby("player_id", as_index=False).tail(1)
        fixtures = latest.loc[:, [column for column in ("player_id", "position", "team") if column in latest]].copy()
        fixtures["season"] = season
        fixtures["gameweek"] = gameweek
        fixtures["opponent_team"] = "unknown"
        fixtures["was_home"] = pd.NA
        fixtures["matches_in_gw"] = 1
        return fixtures.reset_index(drop=True)

    def _prediction_summary(
        self,
        player_id: int,
        season: str,
        gameweek: int,
        pred_mean: float,
        position: str,
    ) -> dict[str, Any]:
        position = str(position).upper()
        position_residuals, calibration_source = self.model.calibration_for_position(position)
        residuals = np.asarray(position_residuals, dtype=float)
        if residuals.size >= 2:
            pred_std: float | None = float(np.std(residuals, ddof=1))
            quantiles = {
                f"p{int(level * 100):02d}": float(max(0.0, pred_mean + np.quantile(residuals, level)))
                for level in QUANTILE_LEVELS
            }
            uncertainty_status = (
                f"PROVISIONAL — {calibration_source} calibration for {position}; "
                "coverage has not been measured"
            )
        else:
            pred_std = None
            quantiles = {}
            uncertainty_status = "UNAVAILABLE — insufficient calibration residuals"
        return {
            "season": season,
            "gameweek": gameweek,
            "player_id": player_id,
            "pred_mean": pred_mean,
            "pred_std": pred_std,
            "quantiles": quantiles,
            "uncertainty_status": uncertainty_status,
        }


def save_predictor_artifact(
    path: str | Path,
    model: PlayerPointsModel,
    history: pd.DataFrame,
    fixtures: pd.DataFrame,
    season: str,
) -> Path:
    """Write a trusted local artifact that can be opened with ``Predictor.load``."""
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    artifact = {
        "artifact_version": ARTIFACT_VERSION,
        "model": model,
        "history": history,
        "fixtures": fixtures,
        "season": season,
    }
    with output_path.open("wb") as artifact_file:
        pickle.dump(artifact, artifact_file, protocol=pickle.HIGHEST_PROTOCOL)
    return output_path
