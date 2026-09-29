# State
<!-- Now only. Overwritten every session. Finished work leaves. Cap 60 lines. -->

Goal: FPL planner that searches 4-GW sequences of transfers/XI/captain/chips under uncertain player forecasts, backtested against greedy 1-GW and rule-based baselines.

## Deployed
nothing deployed; course project, demo track. Repo workflow (CI, Claude review, branch protection) live on GitHub, see mimi/memory/external.md

## Broken
- none known

## Open threads
- Collaborator invites pending (7 members), expected accepted 2026-10-01
- Module interfaces not yet agreed (planning doc checklist: agree all interfaces before integration)
- Unconfirmed: GitHub username mapping djahnavi180506 = Jhavi Dasari, TA619 = Triyansh Agarwaal (used in AGENTS.md and .github/CODEOWNERS)
- Planning doc says "Planner API from Aryaman"; AGENTS.md gives planning/ to Vidhan Jain. Not yet confirmed with the team

## Next 3
1. Each owner opens a PR with the public function signatures of their module (stubs only); record agreed interfaces in mimi/decisions.md
2. Harsh: data sources + clean player-GW dataset schema
3. Tarun: FPL rules spec as constraints in fpl/

## Last session (2026-09-30)
Branch: main
Uncommitted: mimi/ memory updates only
Stopped at: repo setup done (scaffold, AGENTS.md rulebook, CODEOWNERS ownership CI, Claude review gate, protection, README, About); team onboarding next
Tried, failed: `astral-sh/setup-uv@v10` (no floating major tag, see ISS-AS-1)
Resume with: `gh api repos/CandyButcher27/NextGW/collaborators --jq '.[].login'` to confirm invites accepted, then send the team onboarding message

Last updated: 2026-09-30
