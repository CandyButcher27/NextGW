"""Tests for data/ingestion/fetch.py: ingestion determinism and caching."""

from pathlib import Path
import pandas as pd
import pytest

from data.ingestion.fetch import generate_synthetic_raw_data, get_raw_season_dir


def test_generate_synthetic_raw_data_deterministic(tmp_path: Path):
    path1 = generate_synthetic_raw_data(
        season="2023-24", raw_base_dir=tmp_path / "run1", num_players=15, num_gws=5, seed=123
    )
    path2 = generate_synthetic_raw_data(
        season="2023-24", raw_base_dir=tmp_path / "run2", num_players=15, num_gws=5, seed=123
    )

    df1 = pd.read_csv(path1)
    df2 = pd.read_csv(path2)

    pd.testing.assert_frame_equal(df1, df2)


def test_generate_synthetic_raw_data_different_seeds(tmp_path: Path):
    path1 = generate_synthetic_raw_data(
        season="2023-24", raw_base_dir=tmp_path / "seed1", num_players=10, num_gws=3, seed=1
    )
    path2 = generate_synthetic_raw_data(
        season="2023-24", raw_base_dir=tmp_path / "seed2", num_players=10, num_gws=3, seed=2
    )

    df1 = pd.read_csv(path1)
    df2 = pd.read_csv(path2)

    # Different seeds should produce different point totals or values
    assert not df1["total_points"].equals(df2["total_points"])


def test_raw_season_dir():
    p = get_raw_season_dir("2023-24", raw_base_dir="test_raw")
    assert p == Path("test_raw/2023-24")
