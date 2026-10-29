"""Monte Carlo scenario generation for FPL planning.

This module generates reproducible, plausible future performance scenarios
for multiple players across multiple Gameweeks. Scenarios can be used by
the planning module for uncertainty-aware optimization.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np
import numpy.typing as npt
import pandas as pd

from uncertainty.distributions import (
    UncertaintyDistribution,
    create_distribution_from_prediction,
)


@dataclass(frozen=True)
class PlayerScenario:
    """Scenario outcomes for a single player across multiple Gameweeks.
    
    Attributes:
        player_id: Unique player identifier.
        season: Season identifier (e.g., "2024-25").
        gameweeks: Array of gameweek numbers (n_gameweeks,).
        scenarios: Array of sampled point values (n_scenarios, n_gameweeks).
        pred_means: Expected point values (n_gameweeks,).
        pred_stds: Standard deviations (n_gameweeks,), may contain NaN.
    """
    player_id: int
    season: str
    gameweeks: npt.NDArray[np.int64]
    scenarios: npt.NDArray[np.float64]
    pred_means: npt.NDArray[np.float64]
    pred_stds: npt.NDArray[np.float64]
    
    def __post_init__(self):
        """Validate array shapes and types."""
        if self.scenarios.ndim != 2:
            raise ValueError(
                f"scenarios must be 2D array (n_scenarios, n_gameweeks), "
                f"got shape {self.scenarios.shape}"
            )
        n_scenarios, n_gameweeks = self.scenarios.shape
        if len(self.gameweeks) != n_gameweeks:
            raise ValueError(
                f"gameweeks length ({len(self.gameweeks)}) must match "
                f"scenarios second dimension ({n_gameweeks})"
            )
        if len(self.pred_means) != n_gameweeks:
            raise ValueError(
                f"pred_means length ({len(self.pred_means)}) must match "
                f"n_gameweeks ({n_gameweeks})"
            )
        if len(self.pred_stds) != n_gameweeks:
            raise ValueError(
                f"pred_stds length ({len(self.pred_stds)}) must match "
                f"n_gameweeks ({n_gameweeks})"
            )
    
    @property
    def n_scenarios(self) -> int:
        """Number of scenarios."""
        return self.scenarios.shape[0]
    
    @property
    def n_gameweeks(self) -> int:
        """Number of gameweeks."""
        return self.scenarios.shape[1]
    
    def scenario_means(self) -> npt.NDArray[np.float64]:
        """Mean points per gameweek across all scenarios."""
        return np.mean(self.scenarios, axis=0)
    
    def scenario_stds(self) -> npt.NDArray[np.float64]:
        """Standard deviation per gameweek across all scenarios."""
        return np.std(self.scenarios, axis=0, ddof=1)
    
    def quantile(self, level: float) -> npt.NDArray[np.float64]:
        """Compute quantile per gameweek across scenarios.
        
        Args:
            level: Quantile level (e.g., 0.10 for 10th percentile).
            
        Returns:
            Array of quantile values per gameweek.
        """
        return np.quantile(self.scenarios, level, axis=0)


@dataclass
class ScenarioResult:
    """Complete scenario generation result for multiple players.
    
    This is the primary output of scenario generation, containing
    sampled outcomes for all players across the planning horizon.
    
    Attributes:
        n_scenarios: Number of scenarios generated.
        season: Season identifier.
        player_scenarios: Dict mapping player_id to PlayerScenario.
        metadata: Additional information about the generation process.
    """
    n_scenarios: int
    season: str
    player_scenarios: dict[int, PlayerScenario]
    metadata: dict[str, Any] = field(default_factory=dict)
    
    def get_player(self, player_id: int) -> PlayerScenario | None:
        """Get scenarios for a specific player.
        
        Args:
            player_id: The player to retrieve.
            
        Returns:
            PlayerScenario if found, None otherwise.
        """
        return self.player_scenarios.get(player_id)
    
    def to_array(self) -> npt.NDArray[np.float64]:
        """Convert to 3D numpy array [n_scenarios, n_players, n_gameweeks].
        
        Players are ordered by sorted player_id. Gameweeks must be consistent
        across all players (will raise ValueError if not).
        
        Returns:
            3D array of scenario outcomes.
            
        Raises:
            ValueError: If players have inconsistent gameweeks.
        """
        if not self.player_scenarios:
            return np.array([]).reshape(self.n_scenarios, 0, 0)
        
        # Get gameweeks from first player (all must match)
        first_player = next(iter(self.player_scenarios.values()))
        expected_gameweeks = first_player.gameweeks
        
        # Validate all players have same gameweeks
        for player_id, ps in self.player_scenarios.items():
            if not np.array_equal(ps.gameweeks, expected_gameweeks):
                raise ValueError(
                    f"Player {player_id} has gameweeks {ps.gameweeks}, "
                    f"expected {expected_gameweeks}"
                )
        
        # Build 3D array
        sorted_players = sorted(self.player_scenarios.keys())
        arrays = [self.player_scenarios[pid].scenarios for pid in sorted_players]
        return np.stack(arrays, axis=1)  # [n_scenarios, n_players, n_gameweeks]
    
    def to_dataframe(self) -> pd.DataFrame:
        """Convert to long-format DataFrame.
        
        Returns a DataFrame with columns:
        - scenario_id: Scenario number (0 to n_scenarios-1)
        - player_id: Player identifier
        - gameweek: Gameweek number
        - points: Sampled points for this scenario/player/GW
        - pred_mean: Expected points (repeated for convenience)
        """
        rows = []
        for player_id, ps in self.player_scenarios.items():
            for scenario_idx in range(ps.n_scenarios):
                for gw_idx, gameweek in enumerate(ps.gameweeks):
                    rows.append({
                        "scenario_id": scenario_idx,
                        "player_id": player_id,
                        "gameweek": int(gameweek),
                        "points": float(ps.scenarios[scenario_idx, gw_idx]),
                        "pred_mean": float(ps.pred_means[gw_idx]),
                    })
        return pd.DataFrame(rows)
    
    def summary_stats(self) -> pd.DataFrame:
        """Compute summary statistics per player/gameweek.
        
        Returns DataFrame with columns:
        - player_id, gameweek, pred_mean, sample_mean, sample_std,
          p10, p25, p50, p75, p90
        """
        rows = []
        for player_id, ps in self.player_scenarios.items():
            for gw_idx, gameweek in enumerate(ps.gameweeks):
                scenario_values = ps.scenarios[:, gw_idx]
                rows.append({
                    "player_id": player_id,
                    "gameweek": int(gameweek),
                    "pred_mean": float(ps.pred_means[gw_idx]),
                    "sample_mean": float(np.mean(scenario_values)),
                    "sample_std": float(np.std(scenario_values, ddof=1)),
                    "p10": float(np.percentile(scenario_values, 10)),
                    "p25": float(np.percentile(scenario_values, 25)),
                    "p50": float(np.percentile(scenario_values, 50)),
                    "p75": float(np.percentile(scenario_values, 75)),
                    "p90": float(np.percentile(scenario_values, 90)),
                })
        return pd.DataFrame(rows)


class ScenarioGenerator:
    """Generates Monte Carlo scenarios from prediction forecasts.
    
    This class provides a flexible interface for generating scenarios from
    various input formats. It supports the prediction module's DataFrame
    output format (DEC-JD-1) as well as manual distribution specifications.
    
    Example:
        >>> generator = ScenarioGenerator(seed=42)
        >>> # From prediction DataFrame
        >>> result = generator.from_predictions(pred_df, n_scenarios=100)
        >>> # From distributions directly
        >>> result = generator.from_distributions(distribution_map, n_scenarios=100)
    """
    
    def __init__(self, seed: int | None = None):
        """Initialize the scenario generator.
        
        Args:
            seed: Random seed for reproducibility. If None, uses random seed.
        """
        self.seed = seed
        self._rng = np.random.default_rng(seed)
    
    def from_predictions(
        self,
        predictions_df: pd.DataFrame,
        n_scenarios: int = 100,
        player_id_col: str = "player_id",
        season_col: str = "season",
        gameweek_col: str = "gameweek",
        pred_mean_col: str = "pred_mean",
        pred_std_col: str = "pred_std",
        quantiles_col: str = "quantiles",
    ) -> ScenarioResult:
        """Generate scenarios from a prediction DataFrame.
        
        This is the primary entry point for using output from the prediction
        module (DEC-JD-1 format).
        
        Args:
            predictions_df: DataFrame with prediction outputs.
            n_scenarios: Number of scenarios to generate per player/GW.
            player_id_col: Column name for player identifier.
            season_col: Column name for season.
            gameweek_col: Column name for gameweek.
            pred_mean_col: Column name for predicted mean points.
            pred_std_col: Column name for predicted std (may have NaN).
            quantiles_col: Column name for quantiles dict (may have NaN/empty dicts).
            
        Returns:
            ScenarioResult with sampled outcomes.
            
        Raises:
            ValueError: If required columns missing or invalid data.
        """
        if predictions_df.empty:
            raise ValueError("predictions_df cannot be empty")
        
        required_cols = [player_id_col, season_col, gameweek_col, pred_mean_col]
        missing = [c for c in required_cols if c not in predictions_df.columns]
        if missing:
            raise ValueError(f"Missing required columns: {missing}")
        
        if n_scenarios < 1:
            raise ValueError(f"n_scenarios must be >= 1, got {n_scenarios}")
        
        # Group by player to build PlayerScenario objects
        player_groups = predictions_df.groupby(player_id_col)
        player_scenarios: dict[int, PlayerScenario] = {}
        
        # Get season (assume single season)
        seasons = predictions_df[season_col].unique()
        if len(seasons) != 1:
            raise ValueError(
                f"Expected exactly one season, got {len(seasons)}: {seasons}"
            )
        season = str(seasons[0])
        
        for player_id, group in player_groups:
            player_id = int(player_id)
            
            # Sort by gameweek
            group = group.sort_values(gameweek_col)
            gameweeks = group[gameweek_col].to_numpy(dtype=np.int64)
            pred_means = group[pred_mean_col].to_numpy(dtype=np.float64)
            
            # Get stds (may be NaN)
            if pred_std_col in group.columns:
                pred_stds = group[pred_std_col].to_numpy(dtype=np.float64)
            else:
                pred_stds = np.full(len(group), np.nan, dtype=np.float64)
            
            # Get quantiles (may be empty dicts or NaN)
            quantiles_list = []
            if quantiles_col in group.columns:
                for q in group[quantiles_col]:
                    if isinstance(q, dict) and q:
                        quantiles_list.append(q)
                    else:
                        quantiles_list.append({})
            else:
                quantiles_list = [{} for _ in range(len(group))]
            
            # Create distributions and sample
            scenario_matrix = np.zeros((n_scenarios, len(group)), dtype=np.float64)
            
            for i, (mean, std, quants) in enumerate(zip(pred_means, pred_stds, quantiles_list)):
                # Handle NaN std
                std_val = float(std) if not np.isnan(std) else None
                
                dist = create_distribution_from_prediction(
                    pred_mean=float(mean),
                    pred_std=std_val,
                    quantiles=quants if quants else None,
                )
                
                # Sample with a unique seed derived from base seed, player, and GW
                if self.seed is not None:
                    sample_seed = self.seed + player_id * 10000 + int(gameweeks[i])
                else:
                    sample_seed = None
                
                scenario_matrix[:, i] = dist.sample(n=n_scenarios, seed=sample_seed)
            
            player_scenarios[player_id] = PlayerScenario(
                player_id=player_id,
                season=season,
                gameweeks=gameweeks,
                scenarios=scenario_matrix,
                pred_means=pred_means,
                pred_stds=pred_stds,
            )
        
        return ScenarioResult(
            n_scenarios=n_scenarios,
            season=season,
            player_scenarios=player_scenarios,
            metadata={
                "generator_seed": self.seed,
                "n_players": len(player_scenarios),
                "n_gameweeks": len(predictions_df[gameweek_col].unique()),
            },
        )
    
    def from_distributions(
        self,
        distributions: dict[tuple[int, int], UncertaintyDistribution],
        season: str,
        n_scenarios: int = 100,
    ) -> ScenarioResult:
        """Generate scenarios from pre-built uncertainty distributions.
        
        Args:
            distributions: Mapping from (player_id, gameweek) to distribution.
            season: Season identifier.
            n_scenarios: Number of scenarios to generate.
            
        Returns:
            ScenarioResult with sampled outcomes.
        """
        if not distributions:
            raise ValueError("distributions cannot be empty")
        
        if n_scenarios < 1:
            raise ValueError(f"n_scenarios must be >= 1, got {n_scenarios}")
        
        # Group by player
        player_gameweeks: dict[int, list[int]] = {}
        player_dists: dict[int, list[UncertaintyDistribution]] = {}
        
        for (player_id, gameweek), dist in distributions.items():
            if player_id not in player_gameweeks:
                player_gameweeks[player_id] = []
                player_dists[player_id] = []
            player_gameweeks[player_id].append(gameweek)
            player_dists[player_id].append(dist)
        
        # Build PlayerScenario objects
        player_scenarios: dict[int, PlayerScenario] = {}
        
        for player_id in player_gameweeks:
            # Sort by gameweek
            gws_and_dists = sorted(
                zip(player_gameweeks[player_id], player_dists[player_id]),
                key=lambda x: x[0],
            )
            gameweeks = np.array([gw for gw, _ in gws_and_dists], dtype=np.int64)
            dists = [d for _, d in gws_and_dists]
            
            # Sample scenarios
            scenario_matrix = np.zeros((n_scenarios, len(gameweeks)), dtype=np.float64)
            pred_means = np.zeros(len(gameweeks), dtype=np.float64)
            pred_stds = np.zeros(len(gameweeks), dtype=np.float64)
            
            for i, dist in enumerate(dists):
                pred_means[i] = dist.pred_mean
                pred_stds[i] = dist.pred_std if dist.pred_std is not None else np.nan
                
                # Sample with unique seed
                if self.seed is not None:
                    sample_seed = self.seed + player_id * 10000 + int(gameweeks[i])
                else:
                    sample_seed = None
                
                scenario_matrix[:, i] = dist.sample(n=n_scenarios, seed=sample_seed)
            
            player_scenarios[player_id] = PlayerScenario(
                player_id=player_id,
                season=season,
                gameweeks=gameweeks,
                scenarios=scenario_matrix,
                pred_means=pred_means,
                pred_stds=pred_stds,
            )
        
        return ScenarioResult(
            n_scenarios=n_scenarios,
            season=season,
            player_scenarios=player_scenarios,
            metadata={
                "generator_seed": self.seed,
                "n_players": len(player_scenarios),
                "source": "manual_distributions",
            },
        )


def generate_scenarios_from_predictions(
    predictions_df: pd.DataFrame,
    n_scenarios: int = 100,
    seed: int | None = None,
) -> ScenarioResult:
    """Convenience function to generate scenarios from predictions.
    
    This is a thin wrapper around ScenarioGenerator for simple use cases.
    
    Args:
        predictions_df: Prediction DataFrame from prediction module.
        n_scenarios: Number of scenarios to generate.
        seed: Random seed for reproducibility.
        
    Returns:
        ScenarioResult with sampled outcomes.
        
    Example:
        >>> pred_df = predictor.predict_horizon("2024-25", as_of_gw=10, horizon=4)
        >>> scenarios = generate_scenarios_from_predictions(pred_df, n_scenarios=100, seed=42)
        >>> # Access scenarios for player 123
        >>> player_123 = scenarios.get_player(123)
        >>> print(player_123.scenarios.shape)  # (100, 4) for 100 scenarios, 4 GWs
    """
    generator = ScenarioGenerator(seed=seed)
    return generator.from_predictions(predictions_df, n_scenarios=n_scenarios)
