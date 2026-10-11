# Decisions
<!-- One short entry per choice someone might argue again:
"## DEC-<n> — <choice>" heading, then
Why:
Rejected: <alternative> — <reason>
Reverse if: <condition that would change the answer>
Date:
Never edit an old entry's reasoning. Add a new one and mark the old "Superseded by DEC-<m>". -->

## DEC-AS-1 — Project memory (mimi/) is committed, not git-ignored
Why: 8 people each run their own agent; memory only helps if every clone sees the same bugs, decisions and state. Told by Aryaman 2026-09-30.
Rejected: mimi default (git-ignored, per-machine) — each member's agent would start blind to the others' work.
Reverse if: mimi/STATE.md merge conflicts cost more than the shared memory saves.
Date: 2026-09-30

## DEC-AS-2 — AGENTS.md is the single rulebook; CLAUDE.md only imports it
Why: most of the team uses Codex or OpenCode, which read AGENTS.md natively; one file avoids two rulebooks drifting. Told by Aryaman 2026-09-30.
Rejected: rules in CLAUDE.md with AGENTS.md pointing to it — Codex/OpenCode would read a pointer, not the rules.
Reverse if: the team standardises on Claude Code only.
Date: 2026-09-30

## DEC-AS-3 — Merges gated by CI + Claude review, 0 human approvals
Why: Aryaman expects teammates will not review each other's PRs. `ci` (pytest + path ownership from .github/CODEOWNERS) and `review` (claude-code-action against AGENTS.md) are required checks on main instead.
Rejected: GitHub "require review from code owners" — the PR author cannot approve their own PR, so every merge would wait on a reluctant human reviewer.
Reverse if: the team starts reviewing reliably, or the Claude review produces false blocks often enough to stall work.
Date: 2026-09-30

## DEC-AS-4 — Members run mimi close themselves; no agent rule forcing it before push
Why: Aryaman chose to instruct members directly (told 2026-09-30).
Rejected: AGENTS.md rule "run mimi-close before every push/PR" — offered, declined.
Reverse if: mimi/STATE.md goes stale because members forget.
Date: 2026-09-30

## DEC-HG-1 — Data Engineering public interface and player-GW schema
Why: prediction, fpl, and backtesting need a standardized, leakage-safe player-gameweek dataset. Standardized functions: `load_clean_player_gw_data(season, processed_dir, raw_dir, allow_synthetic=False, auto_fetch=True)`, `load_synthetic_player_gw_data(season, ...)`, `clean_raw_merged_gw(raw_df, season)`, `validate_player_gameweek_df(df)`, `compute_leakage_safe_lags(df, stat_cols, lags, rolling_windows)`, `get_pre_deadline_history(df, season, gw)`, `verify_no_future_leakage(feature_df, target_season, target_gw, forbidden_cols, allowed_target_cols)`. Synthetic data is strictly opt-in (`allow_synthetic=False`) to avoid accidental model training on noise. Schema includes identifiers, metadata, fixture details, and performance stats. DGWs aggregated to single GW records with matches_in_gw count.
Rejected: unaggregated fixture-level rows without GW rollup; silent fallback to synthetic data when raw files missing.
Reverse if: downstream models require within-GW sequential match forecasting.
Date: 2026-10-01

## DEC-JD-1 — PROPOSED — pending consumer sign-off: prediction API and uncertainty output
Status: PROPOSED — pending consumer sign-off from planning and other consumers.
API:
- `Predictor.load(path)` loads the predictor artifact.
- `predict_player_gw(player_id, gameweek)` returns one forecast with `pred_mean`, `pred_std`, and `quantiles`.
- `predict_horizon(season, as_of_gw, horizon=4)` returns forecasts for each available player across the requested upcoming Gameweeks.
Uncertainty output:
- Each forecast contains `pred_mean` (expected FPL points), `pred_std`, `quantiles`, and `uncertainty_status`.
- `pred_std` and `quantiles` use out-of-sample chronological residuals for the player's position when at least 30 calibration residuals are available for that position.
- `quantiles` contains empirical residual-adjusted `p10`, `p25`, `p50`, `p75`, and `p90` values, clipped to zero. The quantiles remain nested under the `quantiles` field as specified by this proposed contract.
- If a position has fewer than 30 residuals, both `pred_std` and `quantiles` fall back to the pooled out-of-sample calibration residuals. If fewer than two pooled residuals exist, `pred_std` is `None`, `quantiles` is empty, and `uncertainty_status` is `UNAVAILABLE — insufficient calibration residuals`.
- With position-specific calibration, `uncertainty_status` is `PROVISIONAL — position calibration for {POSITION}; coverage has not been measured`; with pooled fallback it is `PROVISIONAL — pooled_fallback calibration for {POSITION}; coverage has not been measured`.
- These intervals are PROVISIONAL; coverage has not been measured.
- Calibration residuals come from the latest training season, scored by a model trained on earlier seasons. The final chronological holdout is excluded from model fitting and calibration.
Why: The planner needs a stable way to load a trained predictor and request point forecasts and uncertainty without invoking training code. This contract gives a basic uncertainty output while keeping its current calibration limits visible.
Rejected: Treating the interface or intervals as approved/calibrated — consumer owners have not signed off and predictive coverage has not been evaluated.
Reverse if: Consumer owners agree a different signature, return shape, or uncertainty representation.
Date: 2026-10-02

## DEC-AS-5 — PRs merge themselves: author arms auto-merge, nobody merges by hand
Why: Aryaman wants the workflow hands-off and does not want to watch PRs (told 2026-10-02). PR #6 sat green until someone merged it. Repo auto-merge was enabled and AGENTS.md section 6 now requires `gh pr merge --auto --squash` right after `gh pr create` (PR #7).
Rejected: require 1 approval from CandyButcher27 so only he merges — puts him back in the loop on every PR. Restricting who may merge — not available on a user-owned repo.
Reverse if: a PR merges that should not have, because the Claude review approved something wrong.
Date: 2026-10-02

## DEC-AS-6 — Session state is per person; mimi/STATE.md is team-level and admin-only
Why: every mimi-close overwrote the single shared mimi/STATE.md, so every PR conflicted on it, and PR #9 corrupted a teammate's line while rewriting it. Each person now writes only `mimi/state/<github-username>.md`; `mimi/STATE.md` keeps goal, deployment and team threads, written only by CandyButcher27. CODEOWNERS enforces both through the `ci` ownership check.
Rejected: keep one STATE.md with "edit only your own lines" — tried in AGENTS.md, conflicts and corruption continued. A union merge driver in .gitattributes — silently duplicates or interleaves sections.
Reverse if: mimi-close gains native per-user state, or the team shrinks to one or two people.
Date: 2026-10-03
