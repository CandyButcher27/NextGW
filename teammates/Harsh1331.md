# Harsh Gunda (`Harsh1331`) — data

The agent is working for Harsh Gunda. Follow `teammates/PLAYBOOK.md` for every git, PR and CI step. This file only adds what is specific to Harsh Gunda.

## You may create, edit, rename or delete only these
- `data/`
- `tests/test_data_*.py`
- `notebooks/Harsh1331_*.ipynb`
- `mimi/state/Harsh1331.md` (your session state; the only state file you write)
- shared: `mimi/ISSUES.md`, `mimi/decisions.md`, `mimi/memory/`, `pyproject.toml`, `uv.lock`

Every other path belongs to someone else. If a change is needed there, stop and draft a message the user can send to its owner (`AGENTS.md` section 2 lists owners).

Branch names: `Harsh1331/<topic>`.

## Depends on
- Nobody upstream. You produce the player-GW dataset everyone else reads.

## Used by
- `prediction/` (djahnavi180506) imports from `data/`. Renaming a column or function they use is an interface change (`AGENTS.md` section 4).

## Watch out
- You closed PR #5 and opened #6 for the same work. Do not do that again. Push fixes to the open PR (PLAYBOOK sections F and G).
- Three review suggestions from PR #6 are still open in `data/pipeline.py` (see `mimi/state/Harsh1331.md`). Fix them in a new branch, not by reopening anything.
- `data/raw/` and `data/processed/` are git-ignored. Never commit data files.
