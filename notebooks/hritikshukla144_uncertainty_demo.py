"""
Uncertainty Module Demo: Comparing Deterministic vs. Scenario-Based Planning

This script demonstrates the uncertainty module's ability to:
1. Generate scenarios from prediction forecasts
2. Compare deterministic planning (using expected values) with uncertainty-aware planning
3. Show the impact of uncertainty on decision-making

Usage:
    uv run python notebooks/hritikshukla144_uncertainty_demo.py

Output:
    - Prints summary statistics comparing deterministic vs scenario-based approaches
    - Demonstrates how uncertainty affects expected utility calculations
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from uncertainty import generate_scenarios_from_predictions, create_simple_gaussian
from uncertainty.scenarios import ScenarioGenerator


def create_sample_predictions(
    n_players: int = 15,
    n_gameweeks: int = 4,
    seed: int = 42,
) -> pd.DataFrame:
    """Create synthetic prediction data for demonstration.
    
    This simulates the output from the prediction module (DEC-JD-1 format).
    """
    rng = np.random.default_rng(seed)
    
    rows = []
    for player_id in range(1, n_players + 1):
        # Some players have high uncertainty, others low
        base_points = rng.uniform(2, 8)
        uncertainty_level = rng.choice(["low", "medium", "high"])
        
        if uncertainty_level == "low":
            pred_std = rng.uniform(0.5, 1.5)
        elif uncertainty_level == "medium":
            pred_std = rng.uniform(1.5, 2.5)
        else:  # high
            pred_std = rng.uniform(2.5, 4.0)
        
        for gw in range(1, n_gameweeks + 1):
            pred_mean = base_points + rng.normal(0, 0.5)  # Slight week-to-week variation
            pred_mean = max(0.5, pred_mean)  # Ensure positive
            
            # Generate quantiles based on Gaussian approximation
            quantiles = {
                "p10": max(0.0, pred_mean - 1.28 * pred_std),
                "p25": max(0.0, pred_mean - 0.67 * pred_std),
                "p50": pred_mean,
                "p75": pred_mean + 0.67 * pred_std,
                "p90": pred_mean + 1.28 * pred_std,
            }
            
            rows.append({
                "season": "2024-25",
                "gameweek": gw,
                "player_id": player_id,
                "pred_mean": round(pred_mean, 2),
                "pred_std": round(pred_std, 2),
                "quantiles": {k: round(v, 2) for k, v in quantiles.items()},
                "uncertainty_status": f"PROVISIONAL — {uncertainty_level} uncertainty",
            })
    
    return pd.DataFrame(rows)


def deterministic_expected_value(
    predictions_df: pd.DataFrame,
    selected_players: list[int],
    gameweek: int,
) -> float:
    """Calculate expected points using only deterministic means.
    
    This represents the baseline planning approach without uncertainty.
    """
    gw_data = predictions_df[
        (predictions_df["gameweek"] == gameweek) &
        (predictions_df["player_id"].isin(selected_players))
    ]
    return gw_data["pred_mean"].sum()


def scenario_expected_value(
    scenario_result,
    selected_players: list[int],
    gameweek: int,
) -> tuple[float, float]:
    """Calculate expected points and uncertainty from scenarios.
    
    Returns:
        (mean_points, std_of_points)
    """
    total_points_per_scenario = []
    
    for scenario_idx in range(scenario_result.n_scenarios):
        scenario_total = 0.0
        for player_id in selected_players:
            ps = scenario_result.get_player(player_id)
            if ps is None:
                continue
            gw_idx = np.where(ps.gameweeks == gameweek)[0]
            if len(gw_idx) > 0:
                scenario_total += ps.scenarios[scenario_idx, gw_idx[0]]
        total_points_per_scenario.append(scenario_total)
    
    return float(np.mean(total_points_per_scenario)), float(np.std(total_points_per_scenario, ddof=1))


def compare_selection_strategies(
    predictions_df: pd.DataFrame,
    scenario_result,
    n_select: int = 5,
):
    """Compare different player selection strategies.
    
    Strategies:
    1. Deterministic best (highest predicted means)
    2. Low uncertainty (prioritize players with low std)
    3. Balanced (consider both mean and uncertainty)
    """
    # Strategy 1: Deterministic - pick players with highest predicted means
    mean_by_player = predictions_df.groupby("player_id")["pred_mean"].mean()
    deterministic_selection = mean_by_player.nlargest(n_select).index.tolist()
    
    # Strategy 2: Low uncertainty - pick players with lowest std (among decent performers)
    # Filter to players with at least average expected points
    avg_points = predictions_df["pred_mean"].mean()
    decent_players = predictions_df[predictions_df["pred_mean"] >= avg_points]
    std_by_player = decent_players.groupby("player_id")["pred_std"].mean()
    low_uncertainty_selection = std_by_player.nsmallest(n_select).index.tolist()
    
    # Strategy 3: Balanced - use Sharpe-like ratio (mean / std)
    player_stats = predictions_df.groupby("player_id").agg({
        "pred_mean": "mean",
        "pred_std": "mean",
    })
    player_stats["sharpe"] = player_stats["pred_mean"] / (player_stats["pred_std"] + 0.1)
    balanced_selection = player_stats["sharpe"].nlargest(n_select).index.tolist()
    
    results = []
    for name, selection in [
        ("Deterministic", deterministic_selection),
        ("Low Uncertainty", low_uncertainty_selection),
        ("Balanced", balanced_selection),
    ]:
        for gw in predictions_df["gameweek"].unique():
            det_ev = deterministic_expected_value(predictions_df, selection, gw)
            scen_ev, scen_std = scenario_expected_value(scenario_result, selection, gw)
            
            results.append({
                "strategy": name,
                "gameweek": gw,
                "det_ev": det_ev,
                "scen_ev": scen_ev,
                "scen_std": scen_std,
                "selection": selection,
            })
    
    return pd.DataFrame(results)


def demonstrate_conditional_value_at_risk(
    scenario_result,
    player_ids: list[int],
    gameweek: int,
    alpha: float = 0.10,
):
    """Demonstrate CVaR (Conditional Value at Risk) calculation.
    
    CVaR represents the expected outcome in the worst alpha% of scenarios.
    This is useful for risk-averse planning.
    """
    total_points_per_scenario = []
    
    for scenario_idx in range(scenario_result.n_scenarios):
        scenario_total = 0.0
        for player_id in player_ids:
            ps = scenario_result.get_player(player_id)
            if ps is None:
                continue
            gw_idx = np.where(ps.gameweeks == gameweek)[0]
            if len(gw_idx) > 0:
                scenario_total += ps.scenarios[scenario_idx, gw_idx[0]]
        total_points_per_scenario.append(scenario_total)
    
    points_array = np.array(total_points_per_scenario)
    
    # Calculate VaR (Value at Risk) - the alpha-quantile
    var = np.percentile(points_array, alpha * 100)
    
    # Calculate CVaR (Conditional Value at Risk) - average of worst alpha% scenarios
    cvar = points_array[points_array <= var].mean()
    
    return {
        "mean": float(np.mean(points_array)),
        "std": float(np.std(points_array, ddof=1)),
        "var_10": float(var),
        "cvar_10": float(cvar),
    }


def main():
    """Run the uncertainty demonstration."""
    print("=" * 70)
    print("FPL AI Planner - Uncertainty Module Demonstration")
    print("=" * 70)
    
    # Create sample predictions
    print("\n1. Creating sample prediction data...")
    predictions_df = create_sample_predictions(n_players=15, n_gameweeks=4, seed=42)
    print(f"   Generated {len(predictions_df)} predictions for {predictions_df['player_id'].nunique()} players")
    print(f"   Across {predictions_df['gameweek'].nunique()} gameweeks")
    
    # Generate scenarios
    print("\n2. Generating Monte Carlo scenarios...")
    n_scenarios = 1000
    scenario_result = generate_scenarios_from_predictions(
        predictions_df,
        n_scenarios=n_scenarios,
        seed=42,
    )
    print(f"   Generated {scenario_result.n_scenarios} scenarios")
    print(f"   For {len(scenario_result.player_scenarios)} players")
    
    # Show scenario statistics for a few players
    print("\n3. Scenario statistics for sample players:")
    sample_players = [1, 2, 3]
    for player_id in sample_players:
        ps = scenario_result.get_player(player_id)
        pred_data = predictions_df[predictions_df["player_id"] == player_id].iloc[0]
        
        print(f"\n   Player {player_id}:")
        print(f"     Predicted mean: {pred_data['pred_mean']:.2f} ± {pred_data['pred_std']:.2f}")
        
        for gw_idx, gw in enumerate(ps.gameweeks[:2]):  # Show first 2 gameweeks
            gw_scenarios = ps.scenarios[:, gw_idx]
            print(f"     GW {gw}: scenarios mean={gw_scenarios.mean():.2f}, "
                  f"std={gw_scenarios.std(ddof=1):.2f}, "
                  f"p10={np.percentile(gw_scenarios, 10):.2f}, "
                  f"p90={np.percentile(gw_scenarios, 90):.2f}")
    
    # Compare selection strategies
    print("\n4. Comparing player selection strategies:")
    comparison_df = compare_selection_strategies(predictions_df, scenario_result, n_select=5)
    
    # Show average across gameweeks for each strategy
    strategy_summary = comparison_df.groupby("strategy").agg({
        "det_ev": "mean",
        "scen_ev": "mean",
        "scen_std": "mean",
    }).round(2)
    
    print("\n   Strategy Comparison (averaged across gameweeks):")
    print(strategy_summary.to_string())
    
    # Demonstrate risk metrics
    print("\n5. Risk metrics demonstration (CVaR):")
    sample_team = [1, 2, 3, 4, 5]
    for gw in [1, 2]:
        metrics = demonstrate_conditional_value_at_risk(
            scenario_result, sample_team, gw, alpha=0.10
        )
        print(f"\n   Gameweek {gw}:")
        print(f"     Expected points: {metrics['mean']:.2f} ± {metrics['std']:.2f}")
        print(f"     VaR (10% worst): {metrics['var_10']:.2f}")
        print(f"     CVaR (avg of 10% worst): {metrics['cvar_10']:.2f}")
    
    # Show reproducibility
    print("\n6. Verifying reproducibility:")
    result1 = generate_scenarios_from_predictions(predictions_df, n_scenarios=100, seed=123)
    result2 = generate_scenarios_from_predictions(predictions_df, n_scenarios=100, seed=123)
    
    ps1 = result1.get_player(1)
    ps2 = result2.get_player(1)
    
    if np.array_equal(ps1.scenarios, ps2.scenarios):
        print("   [OK] Scenarios are reproducible with same seed")
    else:
        print("   [WARNING] Scenarios differ with same seed!")
    
    # Different seed produces different results
    result3 = generate_scenarios_from_predictions(predictions_df, n_scenarios=100, seed=456)
    ps3 = result3.get_player(1)
    
    if not np.array_equal(ps1.scenarios, ps3.scenarios):
        print("   [OK] Different seeds produce different scenarios")
    else:
        print("   [WARNING] Different seeds produce same scenarios!")
    
    print("\n" + "=" * 70)
    print("Demonstration complete!")
    print("=" * 70)
    print("\nKey takeaways:")
    print("- The uncertainty module generates reproducible Monte Carlo scenarios")
    print("- Scenarios capture prediction uncertainty from residual distributions")
    print("- Risk metrics (VaR, CVaR) help with risk-averse decision making")
    print("- Different selection strategies can be evaluated under uncertainty")
    print("\nFor integration with the planning module:")
    print("- Use ScenarioResult.to_array() for 3D array access [scenario, player, gw]")
    print("- Use ScenarioResult.to_dataframe() for long-format DataFrame")
    print("- Use ScenarioResult.summary_stats() for summary statistics")


if __name__ == "__main__":
    main()
