"""Tests for uncertainty.scenarios module.

Tests cover:
- PlayerScenario creation and validation
- ScenarioResult operations
- ScenarioGenerator from DataFrames
- ScenarioGenerator from distributions
- Reproducibility
- Edge cases and error handling
- Integration with prediction format
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from uncertainty.distributions import UncertaintyDistribution, create_simple_gaussian
from uncertainty.scenarios import (
    PlayerScenario,
    ScenarioGenerator,
    ScenarioResult,
    generate_scenarios_from_predictions,
)


class TestPlayerScenario:
    """Test PlayerScenario dataclass."""
    
    def test_creation_valid(self):
        """Test valid PlayerScenario creation."""
        ps = PlayerScenario(
            player_id=123,
            season="2024-25",
            gameweeks=np.array([11, 12, 13, 14]),
            scenarios=np.random.rand(100, 4),
            pred_means=np.array([5.0, 6.0, 5.5, 6.5]),
            pred_stds=np.array([2.0, 2.1, 1.9, 2.2]),
        )
        assert ps.player_id == 123
        assert ps.season == "2024-25"
        assert ps.n_scenarios == 100
        assert ps.n_gameweeks == 4
    
    def test_shape_validation_wrong_scenarios_dim(self):
        """Test that wrong scenarios dimension raises error."""
        with pytest.raises(ValueError, match="scenarios must be 2D"):
            PlayerScenario(
                player_id=123,
                season="2024-25",
                gameweeks=np.array([11]),
                scenarios=np.random.rand(100),  # 1D instead of 2D
                pred_means=np.array([5.0]),
                pred_stds=np.array([2.0]),
            )
    
    def test_shape_validation_mismatched_gameweeks(self):
        """Test that mismatched gameweeks raise error."""
        with pytest.raises(ValueError, match="gameweeks length"):
            PlayerScenario(
                player_id=123,
                season="2024-25",
                gameweeks=np.array([11, 12, 13]),  # 3 gameweeks
                scenarios=np.random.rand(100, 4),  # 4 scenarios columns
                pred_means=np.array([5.0, 6.0, 5.5, 6.5]),
                pred_stds=np.array([2.0, 2.1, 1.9, 2.2]),
            )
    
    def test_scenario_means(self):
        """Test scenario_means method."""
        scenarios = np.array([
            [1.0, 2.0, 3.0],
            [3.0, 4.0, 5.0],
            [5.0, 6.0, 7.0],
        ])  # 3 scenarios, 3 GWs
        ps = PlayerScenario(
            player_id=123,
            season="2024-25",
            gameweeks=np.array([1, 2, 3]),
            scenarios=scenarios,
            pred_means=np.array([3.0, 4.0, 5.0]),
            pred_stds=np.array([1.0, 1.0, 1.0]),
        )
        means = ps.scenario_means()
        np.testing.assert_array_almost_equal(means, [3.0, 4.0, 5.0])
    
    def test_scenario_stds(self):
        """Test scenario_stds method."""
        scenarios = np.array([
            [1.0, 2.0],
            [3.0, 4.0],
            [5.0, 6.0],
        ])
        ps = PlayerScenario(
            player_id=123,
            season="2024-25",
            gameweeks=np.array([1, 2]),
            scenarios=scenarios,
            pred_means=np.array([3.0, 4.0]),
            pred_stds=np.array([1.0, 1.0]),
        )
        stds = ps.scenario_stds()
        expected = [np.std([1.0, 3.0, 5.0], ddof=1), np.std([2.0, 4.0, 6.0], ddof=1)]
        np.testing.assert_array_almost_equal(stds, expected)
    
    def test_quantile(self):
        """Test quantile method."""
        scenarios = np.array([
            [1.0, 10.0],
            [2.0, 20.0],
            [3.0, 30.0],
            [4.0, 40.0],
        ])
        ps = PlayerScenario(
            player_id=123,
            season="2024-25",
            gameweeks=np.array([1, 2]),
            scenarios=scenarios,
            pred_means=np.array([2.5, 25.0]),
            pred_stds=np.array([1.0, 10.0]),
        )
        q50 = ps.quantile(0.50)
        np.testing.assert_array_almost_equal(q50, [2.5, 25.0])


class TestScenarioResult:
    """Test ScenarioResult operations."""
    
    @pytest.fixture
    def sample_result(self):
        """Create a sample ScenarioResult for testing."""
        ps1 = PlayerScenario(
            player_id=101,
            season="2024-25",
            gameweeks=np.array([11, 12, 13, 14]),
            scenarios=np.random.rand(50, 4),
            pred_means=np.array([5.0, 6.0, 5.5, 6.5]),
            pred_stds=np.array([2.0, 2.1, 1.9, 2.2]),
        )
        ps2 = PlayerScenario(
            player_id=102,
            season="2024-25",
            gameweeks=np.array([11, 12, 13, 14]),
            scenarios=np.random.rand(50, 4),
            pred_means=np.array([4.0, 5.0, 4.5, 5.5]),
            pred_stds=np.array([1.5, 1.6, 1.4, 1.7]),
        )
        return ScenarioResult(
            n_scenarios=50,
            season="2024-25",
            player_scenarios={101: ps1, 102: ps2},
        )
    
    def test_get_player_existing(self, sample_result):
        """Test retrieving existing player."""
        ps = sample_result.get_player(101)
        assert ps is not None
        assert ps.player_id == 101
    
    def test_get_player_missing(self, sample_result):
        """Test retrieving missing player returns None."""
        ps = sample_result.get_player(999)
        assert ps is None
    
    def test_to_array_shape(self, sample_result):
        """Test to_array returns correct shape."""
        arr = sample_result.to_array()
        assert arr.shape == (50, 2, 4)  # n_scenarios, n_players, n_gameweeks
    
    def test_to_array_empty(self):
        """Test to_array with empty result."""
        result = ScenarioResult(
            n_scenarios=50,
            season="2024-25",
            player_scenarios={},
        )
        arr = result.to_array()
        assert arr.shape == (50, 0, 0)
    
    def test_to_array_inconsistent_gameweeks(self):
        """Test that inconsistent gameweeks raise error."""
        ps1 = PlayerScenario(
            player_id=101,
            season="2024-25",
            gameweeks=np.array([11, 12, 13, 14]),
            scenarios=np.random.rand(50, 4),
            pred_means=np.array([5.0, 6.0, 5.5, 6.5]),
            pred_stds=np.array([2.0, 2.1, 1.9, 2.2]),
        )
        ps2 = PlayerScenario(
            player_id=102,
            season="2024-25",
            gameweeks=np.array([11, 12, 13]),  # Different!
            scenarios=np.random.rand(50, 3),
            pred_means=np.array([4.0, 5.0, 4.5]),
            pred_stds=np.array([1.5, 1.6, 1.4]),
        )
        result = ScenarioResult(
            n_scenarios=50,
            season="2024-25",
            player_scenarios={101: ps1, 102: ps2},
        )
        with pytest.raises(ValueError, match="gameweeks"):
            result.to_array()
    
    def test_to_dataframe(self, sample_result):
        """Test to_dataframe conversion."""
        df = sample_result.to_dataframe()
        # 50 scenarios * 2 players * 4 gameweeks = 400 rows
        assert len(df) == 400
        assert set(df.columns) == {"scenario_id", "player_id", "gameweek", "points", "pred_mean"}
        assert df["scenario_id"].min() == 0
        assert df["scenario_id"].max() == 49
        assert set(df["player_id"].unique()) == {101, 102}
        assert set(df["gameweek"].unique()) == {11, 12, 13, 14}
    
    def test_summary_stats(self, sample_result):
        """Test summary_stats method."""
        df = sample_result.summary_stats()
        # 2 players * 4 gameweeks = 8 rows
        assert len(df) == 8
        expected_cols = {
            "player_id", "gameweek", "pred_mean", "sample_mean",
            "sample_std", "p10", "p25", "p50", "p75", "p90",
        }
        assert set(df.columns) == expected_cols


class TestScenarioGeneratorFromPredictions:
    """Test ScenarioGenerator.from_predictions method."""
    
    @pytest.fixture
    def sample_predictions_df(self):
        """Create a sample predictions DataFrame."""
        rows = []
        for player_id in [101, 102, 103]:
            for gameweek in [11, 12, 13, 14]:
                rows.append({
                    "season": "2024-25",
                    "gameweek": gameweek,
                    "player_id": player_id,
                    "pred_mean": 5.0 + player_id * 0.01 + gameweek * 0.1,
                    "pred_std": 2.0,
                    "quantiles": {
                        "p10": 3.0, "p25": 4.0, "p50": 5.0, "p75": 6.0, "p90": 7.0,
                    },
                })
        return pd.DataFrame(rows)
    
    def test_from_predictions_basic(self, sample_predictions_df):
        """Test basic scenario generation from DataFrame."""
        generator = ScenarioGenerator(seed=42)
        result = generator.from_predictions(sample_predictions_df, n_scenarios=100)
        
        assert result.n_scenarios == 100
        assert result.season == "2024-25"
        assert len(result.player_scenarios) == 3
        assert result.metadata["generator_seed"] == 42
        assert result.metadata["n_players"] == 3
        assert result.metadata["n_gameweeks"] == 4
    
    def test_from_predictions_reproducibility(self, sample_predictions_df):
        """Test that same seed produces same results."""
        generator1 = ScenarioGenerator(seed=42)
        result1 = generator1.from_predictions(sample_predictions_df, n_scenarios=100)
        
        generator2 = ScenarioGenerator(seed=42)
        result2 = generator2.from_predictions(sample_predictions_df, n_scenarios=100)
        
        for player_id in [101, 102, 103]:
            ps1 = result1.get_player(player_id)
            ps2 = result2.get_player(player_id)
            np.testing.assert_array_equal(ps1.scenarios, ps2.scenarios)
    
    def test_from_predictions_different_seeds(self, sample_predictions_df):
        """Test that different seeds produce different results."""
        generator1 = ScenarioGenerator(seed=42)
        result1 = generator1.from_predictions(sample_predictions_df, n_scenarios=100)
        
        generator2 = ScenarioGenerator(seed=43)
        result2 = generator2.from_predictions(sample_predictions_df, n_scenarios=100)
        
        # At least one player should have different scenarios
        all_equal = True
        for player_id in [101, 102, 103]:
            ps1 = result1.get_player(player_id)
            ps2 = result2.get_player(player_id)
            if not np.array_equal(ps1.scenarios, ps2.scenarios):
                all_equal = False
                break
        assert not all_equal
    
    def test_from_predictions_empty_df_raises(self):
        """Test that empty DataFrame raises error."""
        generator = ScenarioGenerator(seed=42)
        with pytest.raises(ValueError, match="cannot be empty"):
            generator.from_predictions(pd.DataFrame(), n_scenarios=100)
    
    def test_from_predictions_missing_columns(self):
        """Test that missing columns raise error."""
        generator = ScenarioGenerator(seed=42)
        df = pd.DataFrame({"player_id": [101], "pred_mean": [5.0]})  # Missing season, gameweek
        with pytest.raises(ValueError, match="Missing required columns"):
            generator.from_predictions(df, n_scenarios=100)
    
    def test_from_predictions_invalid_n_scenarios(self, sample_predictions_df):
        """Test that n_scenarios < 1 raises error."""
        generator = ScenarioGenerator(seed=42)
        with pytest.raises(ValueError, match="n_scenarios must be >= 1"):
            generator.from_predictions(sample_predictions_df, n_scenarios=0)
    
    def test_from_predictions_multiple_seasons_raises(self):
        """Test that multiple seasons raise error."""
        df = pd.DataFrame({
            "season": ["2024-25", "2023-24"],
            "gameweek": [11, 11],
            "player_id": [101, 101],
            "pred_mean": [5.0, 5.0],
        })
        generator = ScenarioGenerator(seed=42)
        with pytest.raises(ValueError, match="exactly one season"):
            generator.from_predictions(df, n_scenarios=100)
    
    def test_from_predictions_with_nan_std(self):
        """Test handling of NaN std values."""
        df = pd.DataFrame({
            "season": ["2024-25", "2024-25"],
            "gameweek": [11, 12],
            "player_id": [101, 101],
            "pred_mean": [5.0, 6.0],
            "pred_std": [2.0, np.nan],  # One NaN
            "quantiles": [{"p50": 5.0}, {"p50": 6.0}],
        })
        generator = ScenarioGenerator(seed=42)
        result = generator.from_predictions(df, n_scenarios=100)
        
        ps = result.get_player(101)
        assert ps.n_scenarios == 100
        assert ps.n_gameweeks == 2
        # Should still have scenarios (using quantiles)
        assert not np.any(np.isnan(ps.scenarios))


class TestScenarioGeneratorFromDistributions:
    """Test ScenarioGenerator.from_distributions method."""
    
    def test_from_distributions_basic(self):
        """Test basic scenario generation from distributions."""
        distributions = {
            (101, 11): create_simple_gaussian(5.0, 2.0),
            (101, 12): create_simple_gaussian(6.0, 2.0),
            (102, 11): create_simple_gaussian(4.0, 1.5),
            (102, 12): create_simple_gaussian(5.0, 1.5),
        }
        
        generator = ScenarioGenerator(seed=42)
        result = generator.from_distributions(
            distributions=distributions,
            season="2024-25",
            n_scenarios=100,
        )
        
        assert result.n_scenarios == 100
        assert result.season == "2024-25"
        assert len(result.player_scenarios) == 2
        
        # Check player 101 has 2 gameweeks
        ps101 = result.get_player(101)
        assert ps101.n_gameweeks == 2
        assert list(ps101.gameweeks) == [11, 12]
    
    def test_from_distributions_empty_raises(self):
        """Test that empty distributions raise error."""
        generator = ScenarioGenerator(seed=42)
        with pytest.raises(ValueError, match="cannot be empty"):
            generator.from_distributions({}, season="2024-25", n_scenarios=100)
    
    def test_from_distributions_invalid_n_scenarios(self):
        """Test that n_scenarios < 1 raises error."""
        distributions = {(101, 11): create_simple_gaussian(5.0, 2.0)}
        generator = ScenarioGenerator(seed=42)
        with pytest.raises(ValueError, match="n_scenarios must be >= 1"):
            generator.from_distributions(distributions, season="2024-25", n_scenarios=0)


class TestConvenienceFunction:
    """Test generate_scenarios_from_predictions convenience function."""
    
    def test_convenience_function(self):
        """Test the convenience wrapper."""
        df = pd.DataFrame({
            "season": ["2024-25"] * 4,
            "gameweek": [11, 12, 13, 14],
            "player_id": [101] * 4,
            "pred_mean": [5.0, 6.0, 5.5, 6.5],
            "pred_std": [2.0] * 4,
        })
        
        result = generate_scenarios_from_predictions(df, n_scenarios=50, seed=42)
        
        assert result.n_scenarios == 50
        assert result.season == "2024-25"
        assert len(result.player_scenarios) == 1
        
        ps = result.get_player(101)
        assert ps.n_gameweeks == 4
        assert ps.scenarios.shape == (50, 4)


class TestScenarioStatistics:
    """Test statistical properties of generated scenarios."""
    
    def test_scenario_means_approximate_pred_means(self):
        """Test that scenario means approximate predicted means."""
        df = pd.DataFrame({
            "season": ["2024-25"] * 100,
            "gameweek": list(range(1, 101)),
            "player_id": [101] * 100,
            "pred_mean": np.random.uniform(3, 8, 100),
            "pred_std": np.random.uniform(1.5, 2.5, 100),
        })
        
        result = generate_scenarios_from_predictions(df, n_scenarios=1000, seed=42)
        ps = result.get_player(101)
        
        # Sample means should be close to predicted means
        sample_means = ps.scenario_means()
        max_diff = np.max(np.abs(sample_means - ps.pred_means))
        assert max_diff < 0.5  # Tolerance for random sampling
    
    def test_scenario_non_negative(self):
        """Test that all scenario values are non-negative."""
        df = pd.DataFrame({
            "season": ["2024-25"] * 10,
            "gameweek": list(range(1, 11)),
            "player_id": [101] * 10,
            "pred_mean": [1.0] * 10,  # Low mean
            "pred_std": [3.0] * 10,   # High std (would produce negatives without clipping)
        })
        
        result = generate_scenarios_from_predictions(df, n_scenarios=1000, seed=42)
        ps = result.get_player(101)
        
        assert np.all(ps.scenarios >= 0), "All scenario values should be non-negative"


class TestIntegrationWithPredictionFormat:
    """Test integration with prediction module output format (DEC-JD-1)."""
    
    def test_handles_prediction_df_with_quantiles_column(self):
        """Test handling of prediction DataFrame with nested quantiles."""
        df = pd.DataFrame({
            "season": ["2024-25"] * 2,
            "gameweek": [11, 12],
            "player_id": [101, 101],
            "pred_mean": [5.0, 6.0],
            "pred_std": [2.0, 2.0],
            "quantiles": [
                {"p10": 3.0, "p25": 4.0, "p50": 5.0, "p75": 6.0, "p90": 7.0},
                {"p10": 4.0, "p25": 5.0, "p50": 6.0, "p75": 7.0, "p90": 8.0},
            ],
        })
        
        result = generate_scenarios_from_predictions(df, n_scenarios=100, seed=42)
        ps = result.get_player(101)
        
        assert ps.n_scenarios == 100
        assert ps.n_gameweeks == 2
    
    def test_handles_missing_quantiles_column(self):
        """Test handling when quantiles column is missing."""
        df = pd.DataFrame({
            "season": ["2024-25"] * 2,
            "gameweek": [11, 12],
            "player_id": [101, 101],
            "pred_mean": [5.0, 6.0],
            "pred_std": [2.0, 2.0],
            # No quantiles column
        })
        
        result = generate_scenarios_from_predictions(df, n_scenarios=100, seed=42)
        ps = result.get_player(101)
        
        assert ps.n_scenarios == 100
        assert ps.n_gameweeks == 2
