# State
<!-- Team-level only. Anyone may edit it for team-level facts. Each person's own state is mimi/state/<github-username>.md. Cap 60 lines. -->

Goal: FPL planner that searches 4-GW sequences of transfers/XI/captain/chips under uncertain player forecasts, backtested against greedy 1-GW and rule-based baselines.

## Deployed
nothing deployed; course project, demo track. Repo workflow (CI, Claude review, branch protection, auto-merge) live on GitHub, see mimi/memory/external.md

## Status
- Backtests: `scripts/run_backtest.py configs/model.toml` (held-out 2024-25), `configs/model_fold2.toml` (2023-24); results in README.md.
- With ML forecasts the 4-GW planner beats greedy (+97..+111 on 2024-25, +68 on 2023-24, 6/6 runs each); with the fixture heuristic it does not.
- raw.githubusercontent.com is blocked for CandyButcher27; use `gh api -H "Accept: application/vnd.github.raw" repos/vaastav/Fantasy-Premier-League/contents/data/<season>/gws/merged_gw.csv`.
- CandyButcher27 co-owns every module (#26).

## Team open threads
- Chips fire in GW5-6 (flat hold value); Wildcard/Free Hit not planned.
- `fpl.solve_squad` hangs on a full pool; backtests use `greedy_squad`.
- Uncertainty scenarios reduce to the mean (linear objective).
- DEC-JD-1 still PROPOSED; strategies use the DEC-AS-9 `Forecaster`.
- Dashboard not started.
- Harsh: 3 PR #6 suggestions open in data/pipeline.py.

Last updated: 2026-11-04
