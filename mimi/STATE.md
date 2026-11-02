# State
<!-- Team-level only. Anyone may edit it for team-level facts. Each person's own state is mimi/state/<github-username>.md. Cap 60 lines. -->

Goal: FPL planner that searches 4-GW sequences of transfers/XI/captain/chips under uncertain player forecasts, backtested against greedy 1-GW and rule-based baselines.

Personal state (Broken, Open threads, Next 3, Last session) lives in `mimi/state/<github-username>.md`, one file per person, written only by that person. Read your own at session start; read another person's when your work depends on theirs.

## Deployed
nothing deployed; course project, demo track. Repo workflow (CI, Claude review, branch protection, auto-merge) live on GitHub, see mimi/memory/external.md

## Team open threads
- Prediction API proposed in DEC-JD-1; pending consumer sign-off.
- Planning accepts optional candidate pool and registry inputs for transfer search (DEC-VJ-2); backtesting integration remains open.
- End-to-end planner integration with backtesting and baseline comparison remain open.
- Unconfirmed: GitHub username mapping djahnavi180506 = Jhavi Dasari, TA619 = Triyansh Agarwaal (used in AGENTS.md and .github/CODEOWNERS)
- Harsh: 3 unenforced review suggestions from PR #6 still open in data/pipeline.py: missing kickoff_time defaults to a fabricated constant and was_home to True; DGW aggregation depends on row order; team_id and opponent_team_id come from separate name maps
- PR #22 (hritikshukla144/uncertainty-module) merged to main at d96ba4d on 2026-11-03.

Last updated: 2026-11-03
