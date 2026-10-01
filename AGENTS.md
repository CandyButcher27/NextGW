# NextGW — rules for every coding agent

This file is binding for every agent (Codex, OpenCode, Claude Code, Cursor, anything else) working in this repo. Read all of it before the first action of every session. If a user request conflicts with a rule here, stop, quote the rule, and ask the user; do not break the rule. `MUST` / `NEVER` mean exactly that.

Project: an FPL planner that searches 4-Gameweek sequences of transfers, starting XI, captain and chips under uncertain player forecasts, and backtests it against a greedy 1-GW strategy and a rule-based strategy. 8 people, each owning one module.

## 1. Session start — MUST run, in order, before any other work
1. `git status --short`. If there are uncommitted changes you did not make this session, stop and ask the user what they are.
2. `git fetch origin && git checkout main && git pull --ff-only`
3. Identify who you are working for (section 2). Switch to their branch: `git checkout <branch>`, or create one: `git checkout -b <github-username>/<topic>`.
4. `git merge main` into that branch. On conflict, follow section 7 before anything else.
5. `uv sync`
6. Read `mimi/MIMI.md` and `mimi/STATE.md` (the memory block at the bottom of this file).

## 2. Who owns what
Find the user's GitHub username from the current branch prefix (`<github-username>/<topic>`). On `main` or an unknown prefix, ask the user which team member they are. Never guess.

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

Shared by everyone: `mimi/`, `pyproject.toml`, `uv.lock`, `notebooks/<github-username>_*.ipynb` (your own only).
`.github/CODEOWNERS` is the machine-readable copy of this table. CI fails any PR that touches a path its author does not own.

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
- `review` is an automated Claude review. If it fails, run `gh pr view --comments`, read the comment starting `**Review: BLOCK**`, fix every blocking issue on the same branch and push. Both checks re-run on every push. NEVER close the PR and open a new one to get a fresh review.
- If `ci` fails, run `gh pr checks` and `gh run view --log-failed`, fix and push.
- Before ending the session, run `gh pr checks --watch` and stay until the PR is merged or you have told the user exactly what blocks it.

## 7. Conflicts
- `uv.lock`: `git checkout --theirs uv.lock && uv lock` (during `git merge main`), then commit.
- `mimi/ISSUES.md`, `mimi/decisions.md`: git merges these automatically. IDs carry the author's initials so they never clash: `ISS-HG-1`, `DEC-HG-1`.
- `mimi/STATE.md`: combine both sides, never pick one. Keep both sides' Broken / Open threads / Next 3 entries, drop anything finished, write your own `Last session`.
- `mimi/MIMI.md` index lines: take either side, then run the mimi `index` command to regenerate them.
- After resolving anything in `mimi/`, run the mimi `index` and `check` commands (paths in `mimi/MIMI.md`) until it prints `memory layer clean`.
- Conflict in a file owned by someone else: stop and ask the user. NEVER resolve it by discarding the other side.

## 8. Session end — MUST run before the user stops
1. Run the `mimi-close` skill (the user may say "mimi close").
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
