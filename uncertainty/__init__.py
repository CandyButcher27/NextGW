"""Uncertainty module for FPL AI Planner.

This module provides tools for representing uncertainty in player point
predictions and generating Monte Carlo scenarios for robust planning.

Public API:
    - UncertaintyDistribution: Represents uncertainty for a single prediction.
    - create_distribution_from_prediction: Factory from prediction module output.
    - create_simple_gaussian: Create Gaussian uncertainty for testing.
    - estimate_from_residuals: Calibrate from historical residuals.
    - ScenarioGenerator: Generate multi-player, multi-GW scenarios.
    - ScenarioResult: Container for complete scenario results.
    - PlayerScenario: Container for individual player scenarios.
    - generate_scenarios_from_predictions: Convenience function.
"""

from __future__ import annotations

from uncertainty.distributions import (
    UncertaintyDistribution,
    create_distribution_from_prediction,
    create_simple_gaussian,
    estimate_from_residuals,
)
from uncertainty.scenarios import (
    ScenarioGenerator,
    ScenarioResult,
    PlayerScenario,
    generate_scenarios_from_predictions,
)

__all__ = [
    # Distributions
    "UncertaintyDistribution",
    "create_distribution_from_prediction",
    "create_simple_gaussian",
    "estimate_from_residuals",
    # Scenarios
    "ScenarioGenerator",
    "ScenarioResult",
    "PlayerScenario",
    "generate_scenarios_from_predictions",
]
