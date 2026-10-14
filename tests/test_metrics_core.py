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
