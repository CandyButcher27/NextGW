"""Uncertainty distributions for FPL player point predictions.

This module provides distribution models for representing uncertainty in
player point predictions. It supports empirical distributions derived from
prediction residuals and simple parametric alternatives.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
import numpy.typing as npt


@dataclass(frozen=True)
class UncertaintyDistribution:
    """Represents the uncertainty distribution for a single player-GW forecast.
    
    This is a lightweight container that stores sufficient statistics for
    sampling from the uncertainty distribution. It supports both empirical
    distributions (from quantiles/residuals) and parametric distributions.
    
    Attributes:
        pred_mean: The point prediction (expected value).
        pred_std: Standard deviation of residuals (None if unavailable).
        quantiles: Mapping of quantile levels to values (e.g., {"p10": 2.5, ...}).
        distribution_type: "empirical" or "parametric".
        sample_count: Number of observations used to calibrate (0 if unknown).
        status: Human-readable status describing the uncertainty source.
    """
    pred_mean: float
    pred_std: float | None
    quantiles: dict[str, float]
    distribution_type: str = "empirical"
    sample_count: int = 0
    status: str = ""

    def sample(
        self,
        n: int = 1,
        seed: int | np.random.Generator | None = None,
    ) -> npt.NDArray[np.float64]:
        """Generate n samples from this uncertainty distribution.
        
        For empirical distributions with quantiles, uses linear interpolation
        between quantile points. Falls back to Gaussian if quantiles unavailable.
        All samples are clipped to non-negative values (FPL points cannot be < 0).
        
        Args:
            n: Number of samples to generate.
            seed: Random seed or Generator for reproducibility.
            
        Returns:
            Array of shape (n,) containing sampled point values.
            
        Raises:
            ValueError: If n < 1 or if distribution cannot be sampled.
        """
        if n < 1:
            raise ValueError(f"n must be at least 1, got {n}")
        
        rng = np.random.default_rng(seed)
        
        # Case 1: We have quantiles - sample using inverse CDF (quantile) interpolation
        if self.quantiles:
            samples = self._sample_from_quantiles(n, rng)
        # Case 2: We have std but no quantiles - use Gaussian approximation
        elif self.pred_std is not None and self.pred_std > 0:
            samples = rng.normal(loc=self.pred_mean, scale=self.pred_std, size=n)
        # Case 3: No uncertainty info - return deterministic point prediction
        else:
            samples = np.full(n, self.pred_mean, dtype=np.float64)
        
        # FPL points cannot be negative
        return np.maximum(samples, 0.0)
    
    def _sample_from_quantiles(
        self,
        n: int,
        rng: np.random.Generator,
    ) -> npt.NDArray[np.float64]:
        """Sample using linear interpolation between empirical quantiles.
        
        This treats the quantiles as points on the empirical CDF and performs
        linear interpolation between them. For values outside the quantile
        range, we extrapolate using the outermost quantile slopes.
        """
        if not self.quantiles:
            raise ValueError("Cannot sample from quantiles: no quantiles available")
        
        # Parse quantile levels and values
        quantile_items = []
        for key, value in self.quantiles.items():
            # Parse key like "p10" -> 0.10, "p25" -> 0.25, etc.
            if key.startswith("p") and key[1:].isdigit():
                level = int(key[1:]) / 100.0
                quantile_items.append((level, float(value)))
        
        if len(quantile_items) < 2:
            # Not enough quantiles for interpolation, fall back to Gaussian
            if self.pred_std is not None and self.pred_std > 0:
                return rng.normal(loc=self.pred_mean, scale=self.pred_std, size=n)
            return np.full(n, self.pred_mean, dtype=np.float64)
        
        # Sort by quantile level
        quantile_items.sort(key=lambda x: x[0])
        levels = np.array([item[0] for item in quantile_items])
        values = np.array([item[1] for item in quantile_items])
        
        # Generate uniform random quantile levels
        u = rng.uniform(0, 1, size=n)
        
        # Interpolate using numpy's interp (handles linear interpolation)
        # For extrapolation below first quantile or above last, we use the
        # slope from the nearest interval
        samples = np.interp(u, levels, values)
        
        return samples.astype(np.float64)
    
    def confidence_interval(self, level: float = 0.90) -> tuple[float, float]:
        """Return a confidence interval at the specified level.
        
        Args:
            level: Confidence level (e.g., 0.90 for 90% CI).
            
        Returns:
            Tuple of (lower, upper) bounds.
            
        Raises:
            ValueError: If level not in (0, 1) or unavailable quantiles.
        """
        if not 0 < level < 1:
            raise ValueError(f"level must be in (0, 1), got {level}")
        
        alpha = 1 - level
        lower_p = alpha / 2
        upper_p = 1 - lower_p
        
        # Try to get from quantiles
        if self.quantiles:
            # Parse available quantile levels
            available_quantiles = {}
            for key, value in self.quantiles.items():
                if key.startswith("p") and key[1:].isdigit():
                    level = int(key[1:]) / 100.0
                    available_quantiles[level] = value
            
            if available_quantiles:
                # Find closest available quantiles to desired levels
                available_levels = sorted(available_quantiles.keys())
                
                # Find closest level to lower_p (should be around alpha/2)
                lower_level = min(available_levels, key=lambda x: abs(x - lower_p))
                # Find closest level to upper_p (should be around 1 - alpha/2)
                upper_level = min(available_levels, key=lambda x: abs(x - upper_p))
                
                # Only use if they're distinct and roughly symmetric
                if lower_level < upper_level:
                    return (available_quantiles[lower_level], available_quantiles[upper_level])
        
        # Fall back to Gaussian approximation using standard normal quantiles
        if self.pred_std is not None and self.pred_std > 0:
            # Approximate standard normal quantiles (no scipy dependency)
            # Using common approximations:
            # p=0.05 -> ~-1.645, p=0.95 -> ~1.645 (for 90% CI)
            # p=0.025 -> ~-1.96, p=0.975 -> ~1.96 (for 95% CI)
            z_scores = {
                0.80: 1.282,
                0.90: 1.645,
                0.95: 1.960,
                0.99: 2.576,
            }
            # Find closest confidence level
            closest_level = min(z_scores.keys(), key=lambda x: abs(x - level))
            z = z_scores[closest_level]
            margin = z * self.pred_std
            return (max(0.0, self.pred_mean - margin), self.pred_mean + margin)
        
        # No uncertainty - return point estimate
        return (self.pred_mean, self.pred_mean)


def create_distribution_from_prediction(
    pred_mean: float,
    pred_std: float | None,
    quantiles: dict[str, float] | None,
    status: str = "",
    sample_count: int = 0,
) -> UncertaintyDistribution:
    """Factory function to create a distribution from prediction output.
    
    This is the primary way to create UncertaintyDistribution objects from
    the prediction module's output format (DEC-JD-1).
    
    Args:
        pred_mean: Point prediction (expected points).
        pred_std: Standard deviation of residuals (None if unavailable).
        quantiles: Mapping of quantile labels to values (e.g., {"p10": x, ...}).
        status: Human-readable status string from prediction module.
        sample_count: Number of calibration samples used.
        
    Returns:
        UncertaintyDistribution configured for the given prediction.
    """
    return UncertaintyDistribution(
        pred_mean=float(pred_mean),
        pred_std=float(pred_std) if pred_std is not None else None,
        quantiles=dict(quantiles) if quantiles else {},
        distribution_type="empirical" if quantiles else ("parametric" if pred_std else "deterministic"),
        sample_count=int(sample_count),
        status=str(status) if status else "",
    )


def create_simple_gaussian(
    mean: float,
    std: float,
    status: str = "synthetic-gaussian",
) -> UncertaintyDistribution:
    """Create a simple Gaussian uncertainty distribution.
    
    Useful for testing or when only mean and std are known.
    
    Args:
        mean: Expected value.
        std: Standard deviation (must be >= 0).
        status: Description of the distribution source.
        
    Returns:
        UncertaintyDistribution with Gaussian sampling.
        
    Raises:
        ValueError: If std < 0.
    """
    if std < 0:
        raise ValueError(f"std must be non-negative, got {std}")
    
    return UncertaintyDistribution(
        pred_mean=float(mean),
        pred_std=float(std) if std > 0 else None,
        quantiles={},  # Quantiles computed on-the-fly during sampling
        distribution_type="parametric",
        sample_count=0,
        status=status,
    )


def estimate_from_residuals(
    predictions: npt.NDArray[np.float64],
    actuals: npt.NDArray[np.float64],
    min_samples: int = 2,
) -> UncertaintyDistribution:
    """Estimate uncertainty distribution from historical prediction residuals.
    
    This is useful for backtesting or when you have historical prediction
    errors available. Computes empirical quantiles from residuals and adds
    them to a baseline prediction.
    
    Args:
        predictions: Array of historical point predictions.
        actuals: Array of actual observed outcomes.
        min_samples: Minimum samples needed for reliable estimation.
        
    Returns:
        UncertaintyDistribution calibrated on residuals.
        
    Raises:
        ValueError: If insufficient samples or mismatched lengths.
    """
    predictions = np.asarray(predictions, dtype=np.float64)
    actuals = np.asarray(actuals, dtype=np.float64)
    
    if len(predictions) != len(actuals):
        raise ValueError(
            f"predictions and actuals must have same length, "
            f"got {len(predictions)} and {len(actuals)}"
        )
    
    if len(predictions) < min_samples:
        raise ValueError(
            f"Need at least {min_samples} samples for uncertainty estimation, "
            f"got {len(predictions)}"
        )
    
    # Compute residuals (actual - predicted)
    residuals = actuals - predictions
    
    # Compute statistics
    pred_mean = float(np.mean(predictions))
    pred_std = float(np.std(residuals, ddof=1)) if len(residuals) > 1 else 0.0
    
    # Compute quantiles
    quantile_levels = [0.10, 0.25, 0.50, 0.75, 0.90]
    quantiles = {}
    for level in quantile_levels:
        residual_quantile = np.quantile(residuals, level)
        quantiles[f"p{int(level * 100):02d}"] = max(0.0, pred_mean + residual_quantile)
    
    return UncertaintyDistribution(
        pred_mean=pred_mean,
        pred_std=pred_std if pred_std > 0 else None,
        quantiles=quantiles,
        distribution_type="empirical",
        sample_count=len(predictions),
        status=f"calibrated-on-{len(predictions)}-residuals",
    )
