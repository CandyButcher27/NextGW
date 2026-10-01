# State
<!-- Now only. Overwritten every session. Finished work leaves. Cap 60 lines. -->

Goal: FPL planner that searches 4-GW sequences of transfers/XI/captain/chips under uncertain player forecasts, backtested against greedy 1-GW and rule-based baselines.

## Deployed
nothing deployed; course project, demo track. Repo workflow (CI, Claude review, branch protection) live on GitHub, see mimi/memory/external.md

## Broken
- none known

## Open threads
- Collaborator invites pending (7 members), expected accepted 2026-10-01
- Module interfaces for prediction, uncertainty, fpl, planning, backtesting pending stubs from respective owners
- Unconfirmed: GitHub username mapping djahnavi180506 = Jhavi Dasari, TA619 = Triyansh Agarwaal (used in AGENTS.md and .github/CODEOWNERS)

## Next 3
1. Tarun: FPL rules spec as constraints in fpl/
2. Jhavi: ML prediction model and feature pipeline consuming data module
3. Vidhan: Planning state, actions and search stubs

## Last session (2026-10-01)
Branch: Harsh1331/raw-ingest
Completed: Data Engineering module implemented in data/ (schema validation, leakage prevention & shifted lags, raw ingestion with deterministic synthetic generation, DGW aggregation pipeline) and test suite in tests/test_data_*. Recorded DEC-HG-1.
Resume with: Open PR for Harsh1331/raw-ingest and hand off schema to Jhavi and Tarun.

Last updated: 2026-10-01
