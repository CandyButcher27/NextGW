# Tarun RK (`TarunPK15`) — fpl

The agent is working for Tarun RK. Follow `teammates/PLAYBOOK.md` for every git, PR and CI step. This file only adds what is specific to Tarun RK.

## You may create, edit, rename or delete only these
- `fpl/`
- `tests/test_fpl_*.py`
- `notebooks/TarunPK15_*.ipynb`
- shared: `mimi/` (only your own lines in `mimi/STATE.md`), `pyproject.toml`, `uv.lock`

Every other path belongs to someone else. If a change is needed there, stop and draft a message the user can send to its owner (`AGENTS.md` section 2 lists owners).

Branch names: `TarunPK15/<topic>`.

## Depends on
- Nothing in the repo. FPL rules come from the official Premier League pages for 2026/27.

## Used by
- `planning/` (Vidhan-J28) is waiting on your transition and candidate-plan logic to replace its mocks.

## Watch out
- Every FPL rule value (budget, squad size, club limit, transfer hit, chip rules) is configurable through `configs/` or function arguments. Never hard-code it deep in logic.
- `configs/` is owned by CandyButcher27. If you need a new config file, ask the user to request it.
