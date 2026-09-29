# External systems
<!-- Only what the code cannot tell you: provider quirks, deferred constraints, what the deploy runs,
which credentials reach what, environment traps. Move a topic to its own file once it passes ~40 lines. -->

Last verified: 2026-09-30

## Why can't I push to main / why is my PR not mergeable (GitHub branch protection)
Repo CandyButcher27/NextGW (public). main protection, set 2026-09-30 via `gh api`, not in the repo:
- required status checks `ci` and `review`, strict (branch must be up to date with main)
- PR required, 0 approvals; force-push and branch deletion blocked
- enforce_admins off: only CandyButcher27 can push to main directly
- merge method: squash only; head branches auto-deleted after merge
Check with `gh api repos/CandyButcher27/NextGW/branches/main/protection`.

## Claude PR review: whose credentials, what it costs
- `review` workflow authenticates with repo secret `CLAUDE_CODE_OAUTH_TOKEN`, created 2026-09-30 by Aryaman (CandyButcher27) with `claude setup-token`. Every review draws on Aryaman's Claude subscription quota.
- If reviews hit subscription limits: switch to an `ANTHROPIC_API_KEY` secret and the `anthropic_api_key` input.
- Measured 2026-09-30 (n=3 runs): ~30 s per review. PR #2 approved; PR #3 with 4 planted violations (requirements.txt, unseeded random, hard-coded budget/squad size, no tests) was blocked with all 4 found.
- A run that returns no structured verdict fails the check (fail closed).

## Collaborators and GitHub usernames
Invites sent 2026-09-30, pending acceptance: Harsh1331, djahnavi180506, hritikshukla144, TarunPK15, Vidhan-J28, TA619, print-tanish. Owner: CandyButcher27.
