# State
<!-- Now only. Overwritten every session. Finished work leaves. Cap 60 lines. -->

Goal: FPL planner that searches 4-GW sequences of transfers/XI/captain/chips under uncertain player forecasts, backtested against greedy 1-GW and rule-based baselines.

## Deployed
nothing deployed; course project, demo track. Repo workflow (CI, Claude review, branch protection, auto-merge) live on GitHub, see mimi/memory/external.md

## Broken
- none known

## Open threads
- Collaborator invites still pending for djahnavi180506 and hritikshukla144; they cannot push until accepted (see mimi/memory/external.md)
- Module interfaces for prediction, uncertainty, fpl, planning, backtesting pending stubs from respective owners
- Unconfirmed: GitHub username mapping djahnavi180506 = Jhavi Dasari, TA619 = Triyansh Agarwaal (used in AGENTS.md and .github/CODEOWNERS)
- Harsh: 3 unenforced review suggestions from PR #6 still open in data/pipeline.py: missing `kickoff_time` defaults to a fabricated constant and `was_home` to True; DGW aggregation depends on row order; `team_id` and `opponent_team_id` come from separate name maps

## Next 3
1. Tarun: FPL rules spec as constraints in fpl/
2. Jhavi: ML prediction model and feature pipeline consuming data module
3. Vidhan: replace mock transition_fn and candidate_plans in planning/ with FPL/CSP logic once fpl/ lands, then connect real scenarios to the objective

## Last session (2026-10-02)
Branch: Vidhan-J28/init
Uncommitted: none
Stopped at: Resolved Git Bot blockers (hashable state, flexible horizon, and objective tests). Ready for PR.
Tried, failed: none
Resume with: Open PR for professor review and begin integration with Tarun.

Last updated: 2026-10-02
