"""Tests for uncertainty.distributions module.

Tests cover:
- UncertaintyDistribution creation and sampling
- Quantile-based sampling
- Gaussian fallback sampling
- Factory functions
- Edge cases and error handling
- Reproducibility
"""

from __future__ import annotations

import numpy as np
import pytest

from uncertainty.distributions import (
    UncertaintyDistribution,
    create_distribution_from_prediction,
    create_simple_gaussian,
    estimate_from_residuals,
)


class TestUncertaintyDistribution:
    """Test UncertaintyDistribution class."""
    
    def test_creation_with_quantiles(self):
        """Test creating distribution with quantiles."""
        dist = UncertaintyDistribution(
            pred_mean=5.0,
            pred_std=2.0,
            quantiles={"p10": 2.0, "p25": 3.5, "p50": 5.0, "p75": 6.5, "p90": 8.0},
            distribution_type="empirical",
            sample_count=100,
            status="test",
        )
        assert dist.pred_mean == 5.0
        assert dist.pred_std == 2.0
        assert len(dist.quantiles) == 5
        assert dist.distribution_type == "empirical"
    
    def test_sample_with_quantiles_shape(self):
        """Test that sampling returns correct shape."""
        dist = UncertaintyDistribution(
            pred_mean=5.0,
            pred_std=2.0,
            quantiles={"p10": 2.0, "p50": 5.0, "p90": 8.0},
        )
        samples = dist.sample(n=100, seed=42)
        assert samples.shape == (100,)
        assert samples.dtype == np.float64
    
    def test_sample_non_negative(self):
        """Test that samples are non-negative (FPL constraint)."""
        dist = UncertaintyDistribution(
            pred_mean=1.0,
            pred_std=5.0,
            quantiles={"p10": -2.0, "p50": 1.0, "p90": 4.0},
        )
        samples = dist.sample(n=1000, seed=42)
        assert np.all(samples >= 0), "All samples should be non-negative"
    
    def test_sample_reproducibility(self):
        """Test that sampling is reproducible with same seed."""
        dist = UncertaintyDistribution(
            pred_mean=5.0,
            pred_std=2.0,
            quantiles={"p10": 2.0, "p50": 5.0, "p90": 8.0},
        )
        samples1 = dist.sample(n=100, seed=42)
        samples2 = dist.sample(n=100, seed=42)
        np.testing.assert_array_equal(samples1, samples2)
    
    def test_sample_different_seeds(self):
        """Test that different seeds produce different samples."""
        dist = UncertaintyDistribution(
            pred_mean=5.0,
            pred_std=2.0,
            quantiles={"p10": 2.0, "p50": 5.0, "p90": 8.0},
        )
        samples1 = dist.sample(n=100, seed=42)
        samples2 = dist.sample(n=100, seed=43)
        assert not np.array_equal(samples1, samples2)
    
    def test_sample_with_generator(self):
        """Test sampling with numpy Generator."""
        dist = UncertaintyDistribution(
            pred_mean=5.0,
            pred_std=2.0,
            quantiles={"p10": 2.0, "p50": 5.0, "p90": 8.0},
        )
        rng = np.random.default_rng(42)
        samples = dist.sample(n=100, seed=rng)
        assert samples.shape == (100,)
    
    def test_sample_invalid_n(self):
        """Test that n < 1 raises ValueError."""
        dist = UncertaintyDistribution(pred_mean=5.0, pred_std=2.0, quantiles={})
        with pytest.raises(ValueError, match="n must be at least 1"):
            dist.sample(n=0, seed=42)
        with pytest.raises(ValueError, match="n must be at least 1"):
            dist.sample(n=-1, seed=42)
    
    def test_gaussian_fallback_no_quantiles(self):
        """Test Gaussian fallback when no quantiles provided."""
        dist = UncertaintyDistribution(
            pred_mean=5.0,
            pred_std=2.0,
            quantiles={},
        )
        samples = dist.sample(n=1000, seed=42)
        # Should be roughly Gaussian around mean 5, std 2
        assert np.abs(np.mean(samples) - 5.0) < 0.5  # Tolerance for randomness
        assert np.abs(np.std(samples, ddof=1) - 2.0) < 0.5
    
    def test_deterministic_no_uncertainty(self):
        """Test deterministic sampling when no uncertainty info."""
        dist = UncertaintyDistribution(
            pred_mean=5.0,
            pred_std=None,
            quantiles={},
        )
        samples = dist.sample(n=100, seed=42)
        np.testing.assert_array_equal(samples, np.full(100, 5.0))
    
    def test_confidence_interval_from_quantiles(self):
        """Test CI extraction from available quantiles."""
        dist = UncertaintyDistribution(
            pred_mean=5.0,
            pred_std=2.0,
            quantiles={"p05": 1.0, "p95": 9.0},
        )
        lower, upper = dist.confidence_interval(level=0.90)
        assert lower == 1.0
        assert upper == 9.0
    
    def test_confidence_interval_gaussian_fallback(self):
        """Test CI with Gaussian fallback."""
        dist = UncertaintyDistribution(
            pred_mean=5.0,
            pred_std=2.0,
            quantiles={},
        )
        lower, upper = dist.confidence_interval(level=0.90)
        # 90% CI for N(5, 2) is approx [5 - 1.645*2, 5 + 1.645*2] = [1.71, 8.29]
        assert 1.5 < lower < 2.0
        assert 8.0 < upper < 8.5
    
    def test_confidence_interval_deterministic(self):
        """Test CI when no uncertainty available."""
        dist = UncertaintyDistribution(
            pred_mean=5.0,
            pred_std=None,
            quantiles={},
        )
        lower, upper = dist.confidence_interval(level=0.90)
        assert lower == 5.0
        assert upper == 5.0
    
    def test_confidence_interval_invalid_level(self):
        """Test that invalid confidence level raises error."""
        dist = UncertaintyDistribution(pred_mean=5.0, pred_std=2.0, quantiles={})
        with pytest.raises(ValueError, match="level must be in"):
            dist.confidence_interval(level=0.0)
        with pytest.raises(ValueError, match="level must be in"):
            dist.confidence_interval(level=1.0)
        with pytest.raises(ValueError, match="level must be in"):
            dist.confidence_interval(level=-0.1)


class TestFactoryFunctions:
    """Test factory functions for creating distributions."""
    
    def test_create_distribution_from_prediction_full(self):
        """Test factory with all fields."""
        quantiles = {"p10": 2.0, "p50": 5.0, "p90": 8.0}
        dist = create_distribution_from_prediction(
            pred_mean=5.0,
            pred_std=2.0,
            quantiles=quantiles,
            status="position-calibration",
            sample_count=100,
        )
        assert dist.pred_mean == 5.0
        assert dist.pred_std == 2.0
        assert dist.quantiles == quantiles
        assert dist.distribution_type == "empirical"
        assert dist.status == "position-calibration"
        assert dist.sample_count == 100
    
    def test_create_distribution_from_prediction_no_quantiles(self):
        """Test factory without quantiles."""
        dist = create_distribution_from_prediction(
            pred_mean=5.0,
            pred_std=2.0,
            quantiles=None,
        )
        assert dist.pred_std == 2.0
        assert dist.quantiles == {}
        assert dist.distribution_type == "parametric"
    
    def test_create_distribution_from_prediction_no_std(self):
        """Test factory without std."""
        dist = create_distribution_from_prediction(
            pred_mean=5.0,
            pred_std=None,
            quantiles=None,
        )
        assert dist.pred_std is None
        assert dist.distribution_type == "deterministic"
    
    def test_create_simple_gaussian_valid(self):
        """Test creating Gaussian distribution."""
        dist = create_simple_gaussian(mean=5.0, std=2.0, status="test")
        assert dist.pred_mean == 5.0
        assert dist.pred_std == 2.0
        assert dist.distribution_type == "parametric"
        assert dist.status == "test"
    
    def test_create_simple_gaussian_zero_std(self):
        """Test Gaussian with zero std becomes deterministic."""
        dist = create_simple_gaussian(mean=5.0, std=0.0)
        assert dist.pred_std is None
        samples = dist.sample(n=100, seed=42)
        np.testing.assert_array_equal(samples, np.full(100, 5.0))
    
    def test_create_simple_gaussian_negative_std_raises(self):
        """Test that negative std raises ValueError."""
        with pytest.raises(ValueError, match="std must be non-negative"):
            create_simple_gaussian(mean=5.0, std=-1.0)
    
    def test_estimate_from_residuals_valid(self):
        """Test calibration from historical residuals."""
        # Simulate predictions and actuals with known bias/std
        predictions = np.array([5.0, 6.0, 7.0, 5.0, 6.0])
        actuals = np.array([4.0, 7.0, 6.0, 6.0, 5.0])  # Residuals: -1, +1, -1, +1, -1
        
        dist = estimate_from_residuals(predictions, actuals)
        
        assert dist.pred_mean == pytest.approx(5.8, rel=0.1)  # Mean of predictions
        assert dist.pred_std is not None
        assert dist.pred_std > 0
        assert dist.sample_count == 5
        assert dist.distribution_type == "empirical"
        assert "p50" in dist.quantiles
    
    def test_estimate_from_residuals_mismatched_lengths(self):
        """Test that mismatched lengths raise error."""
        with pytest.raises(ValueError, match="same length"):
            estimate_from_residuals(
                predictions=np.array([1.0, 2.0]),
                actuals=np.array([1.0]),
            )
    
    def test_estimate_from_residuals_insufficient_samples(self):
        """Test that too few samples raise error."""
        with pytest.raises(ValueError, match="at least"):
            estimate_from_residuals(
                predictions=np.array([1.0]),
                actuals=np.array([1.0]),
                min_samples=2,
            )


class TestDistributionProperties:
    """Test statistical properties of distributions."""
    
    def test_quantile_sampling_distribution(self):
        """Test that quantile sampling produces expected distribution."""
        # Create symmetric quantiles around mean
        dist = UncertaintyDistribution(
            pred_mean=5.0,
            pred_std=2.0,
            quantiles={
                "p10": 3.0,  # 10th percentile
                "p25": 4.0,  # 25th percentile
                "p50": 5.0,  # median
                "p75": 6.0,  # 75th percentile
                "p90": 7.0,  # 90th percentile
            },
        )
        
        samples = dist.sample(n=10000, seed=42)
        
        # Check approximate quantiles of samples match expected
        assert np.percentile(samples, 10) == pytest.approx(3.0, abs=0.5)
        assert np.percentile(samples, 50) == pytest.approx(5.0, abs=0.5)
        assert np.percentile(samples, 90) == pytest.approx(7.0, abs=0.5)
    
    def test_empirical_residual_distribution(self):
        """Test calibration produces correct residual distribution."""
        # Create predictions with known errors
        np.random.seed(42)
        true_means = np.full(1000, 5.0)
        # Add Gaussian noise with std=2
        actuals = true_means + np.random.normal(0, 2.0, 1000)
        predictions = true_means
        
        dist = estimate_from_residuals(predictions, actuals)
        
        # Sample and check statistics
        samples = dist.sample(n=5000, seed=42)
        
        # Mean should be close to 5
        assert np.mean(samples) == pytest.approx(5.0, abs=0.3)
        # Std should be reasonably close to 2 (quantile sampling approximates this)
        # Using a wider tolerance since quantile-based sampling is approximate
        assert 1.5 < np.std(samples, ddof=1) < 2.5
