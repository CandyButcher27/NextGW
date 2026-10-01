"""Ingestion package for NextGW data module."""

from data.ingestion.fetch import (
    fetch_github_season_merged_gw,
    fetch_live_bootstrap,
    fetch_live_fixtures,
    generate_synthetic_raw_data,
    get_raw_season_dir,
)

__all__ = [
    "fetch_github_season_merged_gw",
    "fetch_live_bootstrap",
    "fetch_live_fixtures",
    "generate_synthetic_raw_data",
    "get_raw_season_dir",
]
