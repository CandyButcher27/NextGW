# Vidhan Jain (`Vidhan-J28`) — planning

The agent is working for Vidhan Jain. Follow `teammates/PLAYBOOK.md` for every git, PR and CI step. This file only adds what is specific to Vidhan Jain.

## You may create, edit, rename or delete only these
- `planning/`
- `tests/test_planning_*.py`
- `notebooks/Vidhan-J28_*.ipynb`
- `mimi/state/Vidhan-J28.md` (your session state; the only state file you write)
- shared: `mimi/ISSUES.md`, `mimi/decisions.md`, `mimi/memory/`, `pyproject.toml`, `uv.lock`

Every other path belongs to someone else. If a change is needed there, stop and draft a message the user can send to its owner (`AGENTS.md` section 2 lists owners).

Branch names: `Vidhan-J28/<topic>`.

## Depends on
- `fpl/` (TarunPK15), `prediction/` (djahnavi180506), `uncertainty/` (hritikshukla144).

## Used by
- `backtesting/simulator.py` (TA619) runs your planner.

## Watch out
- You closed PR #9 and opened #10 for the same work. Do not do that again. Push fixes to the open PR (PLAYBOOK sections F and G).
- `tests/test_objective.py` on `main` does not match `tests/test_planning_*`, so CI treats it as CandyButcher27's file. Do not edit, rename or delete it; CandyButcher27 will rename it. Put new tests in `tests/test_planning_*.py`.
- In PR #9 you rewrote other people's lines in `mimi/STATE.md` and corrupted one. Write only `mimi/state/Vidhan-J28.md` now.
- The search horizon is an argument or config value, never a hard-coded `4`.
