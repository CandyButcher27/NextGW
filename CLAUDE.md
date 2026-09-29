# NextGW — FPL multi-Gameweek planner

8-person course project. Everyone works through their own coding agent. These rules exist to keep main green and avoid merge conflicts.

## Before any work — every session, no exceptions
1. `git checkout main && git pull` — get the latest code and the latest mimi memory.
2. Switch to your own branch and bring it up to date: `git checkout <your-branch> && git merge main` (create it with `git checkout -b <name>/<topic>` if it does not exist).
3. `uv sync` — someone may have added a dependency.
If the pull or merge conflicts, resolve it before writing any new code (see "Conflicts" below).

## Ownership — only edit files you own
| Owner | Owns |
|---|---|
| Harsh Gunda | `data/` |
| Jhavi Dasari | `prediction/` |
| Hrithik Shukla | `uncertainty/` |
| Tarun RK | `fpl/` |
| Vidhan Jain | `planning/` |
| Triyansh Agarwaal | `baselines/`, `backtesting/simulator.py`, `backtesting/experiments.py` |
| Tanishq | `backtesting/metrics.py` |
| Aryaman Srivastava | `dashboard/`, `configs/`, top-level pipeline, `pyproject.toml`, `CLAUDE.md`, `AGENTS.md` |

- Tests: `tests/test_<your-module>_*.py`. Never edit another owner's test file.
- Notebooks: `notebooks/<your-name>_<topic>.ipynb`. Never edit another person's notebook. Reusable logic moves into your package, not into notebooks.
- Need a change in someone else's module? Ask the owner, or open a PR and request their review. Do not let your agent "quickly fix" another module.
- Changing a public function signature or output format of your own module is an interface change: tell every consumer first (see the planning doc's interface table) and record it in `mimi/decisions.md`.

## Branches, commits, PRs
- Branch name: `<firstname>/<topic>`, e.g. `harsh/raw-ingest`. Never commit to main directly.
- Small commits with conventional prefixes: `feat:`, `fix:`, `test:`, `refactor:`, `docs:`, `chore:`.
- Push at least once per working session. Open a PR into main as soon as a piece works; keep PRs small and short-lived (merge within a few days).
- Before opening or merging a PR: `git merge main` into your branch, then `uv run pytest` must pass.
- Squash-merge PRs on GitHub.

## Dependencies
- Use uv only: `uv add <pkg>`, `uv add --dev <pkg>`, `uv run <cmd>`. Never `pip install`, never `requirements.txt`.
- Commit `pyproject.toml` and `uv.lock` together.

## Conflicts
- `uv.lock`: take main's version, then regenerate: `git checkout --theirs uv.lock && uv lock` (during a `git merge main`), then commit.
- `mimi/ISSUES.md`, `mimi/decisions.md`: append-only; git merges them automatically (union). Use IDs with your initials so they never clash: `ISS-HG-1`, `DEC-HG-1`.
- `mimi/STATE.md`: combine, do not pick a side. Keep both sides' Broken / Open threads / Next 3 entries, drop anything finished, write your own `Last session`.
- `mimi/MIMI.md` index lines: accept either side, then run `index` (below) to regenerate.
- After resolving anything in `mimi/`, run `python "$HOME/.claude/skills/mimi/memlayer.py" index .` and `... check .` until clean.
- Conflict in someone else's module: stop and ask the owner. Never resolve it by discarding their changes.

## Ending a session
Run `mimi close`, then commit the `mimi/` changes on your branch together with your code and push. `mimi/` is committed on purpose — never add it to any `.gitignore`. The mimi `init` command recreates `mimi/.gitignore` and `mimi/.ignore` every time it runs; if either file exists, delete both before committing, or new memory files silently stop being shared.

## Project rules (from the team planning doc)
- No future information in historical features or backtests: no later outcomes, prices, transfers or injury news when simulating an earlier Gameweek.
- All data transformations are reproducible by code. `data/raw/` and `data/processed/` are git-ignored; regenerate them with the ingestion script.
- Every model/experiment records its data period, features and config.
- FPL rule values stay configurable; the official Premier League pages are the authority for 2026/27 rules.
- Get the full pipeline working small before adding chips, models or a longer horizon. The UI comes last.

<!-- memory-layer:start -->
@mimi/MIMI.md
If mimi/MIMI.md is not already in your context, read it and mimi/STATE.md before starting any task.
<!-- memory-layer:end -->
