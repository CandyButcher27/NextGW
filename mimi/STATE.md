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
3. Vidhan: Planning state, actions and search stubs

## Last session (2026-10-02)
Branch: CandyButcher27/session-memory
Uncommitted: none
Stopped at: data module merged (PR #6); auto-merge enabled and required by AGENTS.md section 6 (PR #7, see DEC-AS-5); next is telling the team to pull main so their agents pick up the new rule
Tried, failed: none
Resume with: `gh pr list --state open` to see whether new PRs arm auto-merge; `gh api repos/CandyButcher27/NextGW/invitations --jq '.[].invitee.login'` for the two pending invites

Last updated: 2026-10-02
