# Prediction Module Assumptions

## Planner interface status

**PROPOSED — pending consumer sign-off.** The requested planner contract is:

- `Predictor.load(path)` loads a serialized local predictor artifact.
- `predict_player_gw(player_id, gameweek)` returns `pred_mean`, `pred_std`, and quantiles.
- `predict_horizon(season, as_of_gw, horizon=4)` returns forecasts for all players represented by the fixture schedule or available history.

`DEC-JD-1` records this contract as proposed. Consumer owners have not signed off; this module does not imply planner-owner approval.

The single-player result is a mapping with `pred_mean`, `pred_std`, `quantiles` (`p10`, `p25`, `p50`, `p75`, `p90`), and `uncertainty_status`. The horizon result is a DataFrame with one row per available player/Gameweek and the same forecast fields. With calibration residuals, the status identifies whether the position-specific or pooled fallback sample was used and says coverage has not been measured. With fewer than two pooled residuals, `pred_std` is `None`, `quantiles` is empty, and the status is unavailable due to insufficient residuals.

Artifacts are trusted local Python pickle files. They contain a fitted `PlayerPointsModel`, historical player-Gameweek rows, an optional fixture schedule, and the forecast season. Do not load artifacts from untrusted sources. `save_predictor_artifact` creates this format.

## Data assumptions

- Inputs follow the shared `data` player-Gameweek schema and have one row per player and Gameweek. Double Gameweeks are already aggregated; `matches_in_gw` records the number of fixtures.
- `total_points` is the supervised target. Performance statistics such as points, minutes, expected goals, expected assists, bonus, and BPS are only predictors after a one-or-more-Gameweek shift.
- The shared lag helper groups by player and season. Therefore prior-season form is not carried into the first Gameweek of a new season; missing early-season lags are imputed by the fitted model.
- `position`, `team`, `opponent_team`, `was_home`, `gameweek`, and `matches_in_gw` are assumed to be known before the target deadline when supplied as fixture context. Missing categories are imputed or treated as unknown.
- `price`, transfers, injury status, and unshifted performance columns are excluded. The processed historical files do not establish that those fields are deadline-time snapshots.
- Player identifiers are used to align records and form lags, but are not a model feature. Position/team/opponent categories unseen during training are ignored by the encoder.
- If fixture rows are absent, the API carries the latest known position/team forward and uses unknown opponent/home context. Such forecasts should be treated as lower-context predictions.
- A horizon forecast is frozen at `as_of_gw`: later observed results in the artifact history are excluded, and forecast outputs are not fed back into subsequent Gameweeks. Each horizon step uses observed pre-origin history only.

## Model and evaluation assumptions

- The point model is a deterministic `HistGradientBoostingRegressor` with seed 42 and the recorded settings in `prediction/train.py`.
- The 2024–25 chronological holdout is trained on 2022–23 and 2023–24. No 2024–25 outcomes are used to fit the model or calibrate its residual distribution.
- Evaluation reports all player-Gameweek rows present in the holdout, including players with zero minutes; it is not restricted to a manager's squad or likely starters.
- The training-mean baseline predicts the mean target points from data available before the holdout.
- The minutes-aware baseline estimates expected minutes from the player's previous five player-Gameweek rows, estimates points per 90 from the five most recent rows with positive minutes, and uses training-position averages when player history is unavailable. Fixture count scales expected minutes, capped at 90 per fixture.
- “Regular/high-minute” means the mean minutes across the five most recent pre-deadline rows is at least 60. “Low-minute” means below 60 or no pre-deadline history. These labels use no target-Gameweek minutes. Position metrics use the fixture row's position.

## Uncertainty assumptions

- Calibration residuals are out-of-sample forecasts from the latest season available to the model before its forecast cutoff, using a calibration model trained only on earlier seasons. For the 2024–25 holdout this means residuals from a 2023–24 calibration season, fit from 2022–23.
- Residuals are retained by position. When at least 30 out-of-sample residuals are available for the requested position, that position's residual sample supplies `pred_std` and the quantiles.
- If a position has fewer than 30 residuals, calibration falls back to the pooled out-of-sample residual distribution. If fewer than two pooled residuals exist, `pred_std` is `None` and `quantiles` is empty.
- `pred_std` is the sample standard deviation of the selected residual sample. Quantiles `p10`, `p25`, `p50`, `p75`, and `p90` are the point prediction plus the corresponding empirical residual quantile, clipped at zero. This is a position-level additive calibration, not a player-specific predictive distribution.
- Forecast output labels available intervals `PROVISIONAL — coverage has not been measured` and identifies whether position-specific or pooled-fallback residuals were used. `mimi/decisions.md` records the nested `quantiles` mapping as part of the proposed contract.
- Coverage and calibration sharpness have not been evaluated. Consumers should treat the intervals as provisional until a separate calibration evaluation is completed. If fewer than two calibration residuals are available, `pred_std` is `None` and `quantiles` is empty.
