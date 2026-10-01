"""Data Engineering module for NextGW.

Provides raw data ingestion, leakage-safe historical transformations,
schema definitions, and standardized player-gameweek datasets.
"""

from data.schema import (
    ALL_REQUIRED_COLUMNS,
    FIXTURE_COLUMNS,
    IDENTIFIER_COLUMNS,
    METADATA_COLUMNS,
    PERFORMANCE_COLUMNS,
    POSITION_ID_TO_NAME,
    POSITION_NAME_TO_ID,
    PRE_DEADLINE_COLUMNS,
    ValidationResult,
    validate_player_gameweek_df,
)
from data.leakage import (
    compute_leakage_safe_lags,
    get_pre_deadline_history,
    verify_no_future_leakage,
)
from data.pipeline import (
    clean_raw_merged_gw,
    load_clean_player_gw_data,
    load_synthetic_player_gw_data,
    process_and_save_season,
)
from data.ingestion.fetch import (
    fetch_github_season_merged_gw,
    fetch_live_bootstrap,
    fetch_live_fixtures,
    generate_synthetic_raw_data,
)

__all__ = [
    "ALL_REQUIRED_COLUMNS",
    "FIXTURE_COLUMNS",
    "IDENTIFIER_COLUMNS",
    "METADATA_COLUMNS",
    "PERFORMANCE_COLUMNS",
    "POSITION_ID_TO_NAME",
    "POSITION_NAME_TO_ID",
    "PRE_DEADLINE_COLUMNS",
    "ValidationResult",
    "clean_raw_merged_gw",
    "compute_leakage_safe_lags",
    "fetch_github_season_merged_gw",
    "fetch_live_bootstrap",
    "fetch_live_fixtures",
    "generate_synthetic_raw_data",
    "get_pre_deadline_history",
    "load_clean_player_gw_data",
    "load_synthetic_player_gw_data",
    "process_and_save_season",
    "validate_player_gameweek_df",
    "verify_no_future_leakage",
]
