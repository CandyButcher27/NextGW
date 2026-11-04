import pytest

from backtesting.metrics import (
    cumulative_points,
    points_per_gameweek,
    transfer_hit_points,
)


def test_cumulative_points_sums_gameweeks():
    assert cumulative_points([10.0, 20.0, 30.0]) == 60.0


def test_cumulative_points_empty_is_zero():
    assert cumulative_points([]) == 0.0


def test_cumulative_points_accepts_int_and_negative_net():
    assert cumulative_points([5, -4, 7]) == 8.0


def test_points_per_gameweek_average():
    assert points_per_gameweek([10.0, 20.0, 30.0]) == 20.0


def test_points_per_gameweek_empty_raises():
    with pytest.raises(ValueError):
        points_per_gameweek([])


def test_transfer_hit_points_within_free_transfers_is_free():
    assert transfer_hit_points(num_transfers=1, free_transfers=1) == 0
    assert transfer_hit_points(num_transfers=2, free_transfers=2) == 0


def test_transfer_hit_points_charges_only_the_excess():
    assert transfer_hit_points(num_transfers=2, free_transfers=1) == 4
    assert transfer_hit_points(num_transfers=3, free_transfers=1) == 8


def test_transfer_hit_points_cost_is_configurable():
    assert transfer_hit_points(num_transfers=2, free_transfers=0, cost_per_hit=8) == 16
    assert transfer_hit_points(num_transfers=2, free_transfers=0, cost_per_hit=0) == 0


def test_transfer_hit_points_rejects_negative_arguments():
    with pytest.raises(ValueError):
        transfer_hit_points(num_transfers=-1, free_transfers=0)
    with pytest.raises(ValueError):
        transfer_hit_points(num_transfers=1, free_transfers=-1)
    with pytest.raises(ValueError):
        transfer_hit_points(num_transfers=1, free_transfers=0, cost_per_hit=-4)


def test_xi_changes_counts_new_starters():
    from backtesting.metrics import xi_changes

    assert xi_changes(["1,2,3", "1,2,4", "5,6,4"]) == [1, 2]


def test_summarize_reports_per_run_means_and_stability():
    import pandas as pd

    from backtesting.metrics import summarize

    rows = []
    for seed in (0, 1):
        for gw, xi in ((1, "1,2"), (2, "1,3")):
            rows.append(
                {"strategy": "s", "season": "x", "seed": seed, "gameweek": gw, "starting_xi": xi, "gw_points": 10.0,
                 "num_transfers": 1, "hits": 0, "captain_bonus": 2.0, "decision_seconds": 0.5}
            )
    summary = summarize(pd.DataFrame(rows))
    assert summary.loc["s", "points_per_run"] == 20.0
    assert summary.loc["s", "xi_changes_per_gw"] == 1.0
    assert summary.loc["s", "transfers_per_run"] == 2.0
