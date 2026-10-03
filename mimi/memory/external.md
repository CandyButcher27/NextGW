# External systems
<!-- Only what the code cannot tell you: provider quirks, deferred constraints, what the deploy runs,
which credentials reach what, environment traps. Move a topic to its own file once it passes ~40 lines. -->

Last verified: 2026-10-02

## Why can't I push to main / why is my PR not mergeable (GitHub branch protection)
Repo CandyButcher27/NextGW (public). main protection, set 2026-09-30 via `gh api`, not in the repo:
- required status checks `ci` and `review`, strict (branch must be up to date with main)
- PR required, 0 approvals; force-push and branch deletion blocked
- enforce_admins off: only CandyButcher27 can push to main directly
- merge method: squash only; head branches auto-deleted after merge
- auto-merge allowed since 2026-10-02 (`allow_auto_merge`, a repo setting, not part of protection). A PR armed with `gh pr merge --auto --squash` merges itself once both checks are green (first use: PR #7). See DEC-AS-5.
- Collaborators hold the `write` role, so they can merge their own green PR. A user-owned repo cannot limit who merges; only the required checks gate it.
Check with `gh api repos/CandyButcher27/NextGW/branches/main/protection`.

## Why did nobody tell me my PR is stuck (failed checks, no reminders)
A red `ci` or `review` leaves the PR open with no timeout, no auto-close and no reminder. GitHub sends the pusher one "Run failed" notification per run, subject to their personal notification settings; Aryaman is not notified. Armed auto-merge waits silently. No chat alert exists (offered 2026-10-02, deferred until PRs rot unnoticed).

## Claude PR review: whose credentials, what it costs
- `review` workflow authenticates with repo secret `CLAUDE_CODE_OAUTH_TOKEN`, created 2026-09-30 by Aryaman (CandyButcher27) with `claude setup-token`. Every review draws on Aryaman's Claude subscription quota.
- If reviews hit subscription limits: switch to an `ANTHROPIC_API_KEY` secret and the `anthropic_api_key` input.
- Measured 2026-09-30 (n=3 runs): ~30 s per review. PR #2 approved; PR #3 with 4 planted violations (requirements.txt, unseeded random, hard-coded budget/squad size, no tests) was blocked with all 4 found.
- First real PRs, 2026-10-01 (n=3 runs): 49 s and 52 s on PR #6 (+1751 lines), 30 s on PR #7 (docs). PR #6 was blocked for a silent synthetic-data fallback, then approved after the fix.
- Only blocking issues gate the merge. The up-to-3 suggestions per review are not enforced or tracked anywhere but the PR comment.
- A run that returns no structured verdict fails the check (fail closed).

## Collaborators and GitHub usernames
Invites sent 2026-09-30. Accepted as of 2026-10-03 (`write` role): Harsh1331, djahnavi180506, TarunPK15, Vidhan-J28, TA619, print-tanish. Still pending, cannot push yet: hritikshukla144. Owner: CandyButcher27.
Check with `gh api repos/CandyButcher27/NextGW/invitations --jq '.[].invitee.login'`.
