# NextGW — rules for every coding agent

This file is binding for every agent (Codex, OpenCode, Claude Code, Cursor, anything else) working in this repo. Read all of it before the first action of every session. If a user request conflicts with a rule here, stop, quote the rule, and ask the user; do not break the rule. `MUST` / `NEVER` mean exactly that.

Project: an FPL planner that searches 4-Gameweek sequences of transfers, starting XI, captain and chips under uncertain player forecasts, and backtests it against a greedy 1-GW strategy and a rule-based strategy. 8 people, each owning one module.

## 1. Session start — MUST run, in order, before any other work
1. `git status --short`. If there are uncommitted changes you did not make this session, stop and ask the user what they are.
2. Identify who you are working for: run `gh api user --jq .login`. That GitHub username is the user.
   - If it fails (gh not installed or not logged in), tell the user to run `gh auth login`, then retry. Do not continue without it.
   - If the current branch is `<other-username>/<topic>` for a different username, stop and ask the user. Never work on another person's branch.
3. Get the latest `main` before reading anything else: `git fetch origin`, then `gh pr list --author @me --state open`.
   - The user has an open PR → `git checkout <that-branch> && git pull --ff-only && git merge origin/main`. On conflict, follow section 7 before anything else.
   - No open PR → `git checkout main && git pull --ff-only`.
4. If step 3 changed `AGENTS.md` (it is listed in the pull or merge output), this file is out of date in your context. Re-read `AGENTS.md` from the top and restart section 1.
5. Read `teammates/<github-username>.md` and `teammates/PLAYBOOK.md` in full. Your file lists the only paths you may touch; the playbook gives the exact git, PR, conflict and CI steps. Follow both. If there is no file for that username, stop and ask the user to get one added by `CandyButcher27`.
6. No open PR → create the branch now: `git checkout -b <github-username>/<topic>`.
7. `uv sync`
8. Read `mimi/MIMI.md`, `mimi/STATE.md` (the memory block at the bottom of this file) and your own `mimi/state/<github-username>.md`.

## 2. Who owns what
The user is the GitHub username from section 1. Never guess it from the branch name or the git author name.

| Person | GitHub | Owns |
|---|---|---|
| Harsh Gunda | `Harsh1331` | `data/`, `tests/test_data_*` |
| Jhavi Dasari | `djahnavi180506` | `prediction/`, `tests/test_prediction_*` |
| Hrithik Shukla | `hritikshukla144` | `uncertainty/`, `tests/test_uncertainty_*` |
| Tarun RK | `TarunPK15` | `fpl/`, `tests/test_fpl_*` |
| Vidhan Jain | `Vidhan-J28` | `planning/`, `tests/test_planning_*` |
| Triyansh Agarwaal | `TA619` | `baselines/`, `backtesting/simulator.py`, `backtesting/experiments.py`, `tests/test_baselines_*`, `tests/test_backtesting_*` |
| Tanishq | `print-tanish` | `backtesting/metrics.py`, `tests/test_metrics_*` |
| Aryaman Srivastava | `CandyButcher27` | everything not listed above: `dashboard/`, `configs/`, `scripts/`, `.github/`, top-level pipeline, `AGENTS.md`, `CLAUDE.md`, `.gitignore`, `.gitattributes` |

Shared by everyone: `mimi/` (except `mimi/STATE.md`, which only `CandyButcher27` writes, and `mimi/state/<github-username>.md`, which only that person writes), `pyproject.toml`, `uv.lock`, `notebooks/<github-username>_*.ipynb` (your own only).
`.github/CODEOWNERS` is the machine-readable copy of this table. CI fails any PR that touches a path its author does not own. `teammates/<github-username>.md` repeats each person's paths with their dependencies and known mistakes.

## 3. Scope — the rule that prevents most conflicts
- You MUST only create, edit, rename or delete files the user owns (section 2) plus the shared files.
- NEVER edit another owner's file, even for a one-line fix, a typo, an import, or to make a test pass. Instead: stop, tell the user exactly what change is needed and why, and draft a short message they can send to the owner.
- NEVER work around another module (copying its code, monkey-patching it, re-implementing it in your module). Use its public interface, or ask for a change.
- If the module you depend on does not exist yet, write against the interface agreed in `mimi/decisions.md`. If there is none, stop and ask the user to agree it with the owner.

## 4. Interfaces between modules
- A module's public interface is whatever other modules import from it. Keep it small: plain functions, dataclasses, and pandas DataFrames with documented columns.
- Changing a public function's name, arguments, return type, or a DataFrame's columns is an interface change. Before making it: the user MUST confirm the consuming owners agreed. Record it in `mimi/decisions.md` as `DEC-<initials>-<n>` with the new signature.
- Never break an interface silently. Add the new version, move consumers over (by their owners), then remove the old one.

## 5. Code conventions
- Python 3.11. Type hints on every public function.
- Dependencies: `uv add <pkg>` / `uv add --dev <pkg>` only. NEVER `pip install`, NEVER `requirements.txt`, NEVER `conda`. Run things with `uv run <cmd>`.
- Reusable logic lives in the owner's package. Notebooks are for exploration only and never imported.
- Tests: pytest, in `tests/test_<module>_<topic>.py`. Run `uv run pytest` before every commit. NEVER delete, skip, or weaken a test to make CI pass.
- Config values (dates, horizons, seeds, FPL rule values) go in `configs/` or function arguments, not hard-coded deep in logic. FPL rule values must stay configurable; the official Premier League pages are the authority for 2026/27 rules.
- Randomness: every random process takes an explicit seed.
- No leakage: a feature or simulated decision for Gameweek t may only use information available before the Gameweek t deadline. No later outcomes, prices, transfers or injury news.
- Data: `data/raw/` and `data/processed/` are git-ignored and rebuilt by code. NEVER commit data files, model binaries, `.venv/`, `.env`, API keys or credentials.
- Every experiment records its data period, features and config next to its output.
- Keep it small: get the end-to-end pipeline working before adding chips, models or a longer horizon.

## 6. Git
- Branch: `<github-username>/<topic>`, e.g. `Harsh1331/raw-ingest`. One topic per branch.
- NEVER commit or push to `main`. NEVER `git push --force` or `--force-with-lease`. NEVER `git rebase` a pushed branch. NEVER `--no-verify`.
- Stage files by name after checking `git status`. NEVER `git add -A` / `git add .` without reviewing what it stages.
- Commits are small, one logical change each, with a conventional prefix: `feat:`, `fix:`, `test:`, `refactor:`, `docs:`, `chore:`. Subject ≤ 50 chars, imperative.
- Before opening a PR, and again before merging: `git merge main`, `uv run pytest` passes, push.
- PR into `main`: title in conventional-commit form; body says what changed, why, and how it was tested. Keep PRs small and merge within a few days; long-lived branches cause the conflicts.
- PRs are squash-merged. `main` is protected: it needs a PR, a green `ci` check and a green `review` check, and the branch must be up to date with `main`.
- Right after `gh pr create`, you MUST run `gh pr merge --auto --squash`. GitHub then merges the PR by itself once `ci` and `review` are green. Nobody approves or merges by hand; do not wait for `CandyButcher27`.
- One open PR per topic. NEVER close a PR to open a new one for the same work, for any reason: a blocked review, red CI, or a conflict. Push the fix to the same branch (playbook sections D, F, G).
- After a PR merges, NEVER commit on that branch again. Delete it and branch from fresh `main` (playbook section E).
- `review` is an automated Claude review. If it fails, run `gh pr view --comments`, read the comment starting `**Review: BLOCK**`, fix every blocking issue on the same branch and push. Both checks re-run on every push.
- If `ci` fails, run `gh pr checks` and `gh run view --log-failed`, fix and push.
- Before ending the session, run `gh pr checks --watch` and stay until the PR is merged or you have told the user exactly what blocks it.

## 7. Conflicts
- `uv.lock`: `git checkout --theirs uv.lock && uv lock` (during `git merge main`), then commit.
- `mimi/ISSUES.md`, `mimi/decisions.md`: git merges these automatically. IDs carry the author's initials so they never clash: `ISS-HG-1`, `DEC-HG-1`.
- `mimi/STATE.md` and `mimi/state/*.md` never conflict: each has a single writer (plus `CandyButcher27` as admin). If one shows up in your diff and it is not yours, undo it: `git checkout origin/main -- <path>`.
- `mimi/MIMI.md` index lines: take either side, then run the mimi `index` command to regenerate them.
- After resolving anything in `mimi/`, run the mimi `index` and `check` commands (paths in `mimi/MIMI.md`) until it prints `memory layer clean`.
- Conflict in a file owned by someone else: stop and ask the user. NEVER resolve it by discarding the other side.

## 8. Session end — MUST run before the user stops
1. Run the `mimi-close` skill (the user may say "mimi close"). Where it says to overwrite `mimi/STATE.md`, overwrite `mimi/state/<github-username>.md` instead, with the same sections. Never write `mimi/STATE.md` unless the user is `CandyButcher27`; CI fails the PR if you do.
2. If `mimi/.gitignore` or `mimi/.ignore` exists, delete both. mimi's `init` recreates them; left in place, new memory files silently stop being shared.
3. Commit your code and the `mimi/` changes on your branch, push, and open or update the PR. Arm auto-merge and see it through (section 6).
4. Tell the user the PR link, whether it merged, and anything they must tell another owner.

## 9. Never
- Edit files outside the user's ownership (section 3).
- Edit `AGENTS.md`, `CLAUDE.md`, `.github/`, `scripts/`, `.gitignore` or `.gitattributes` unless the user is `CandyButcher27`.
- Add `mimi/` to any ignore file.
- Commit secrets, data files, or `.venv/`.
- Disable, skip or weaken tests or CI checks.
- Claim something works without running it.

<!-- memory-layer:start -->
@mimi/MIMI.md
If mimi/MIMI.md is not already in your context, read it and mimi/STATE.md before starting any task.
<!-- memory-layer:end -->
