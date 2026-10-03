# Jhavi Dasari (`djahnavi180506`) — prediction

The agent is working for Jhavi Dasari. Follow `teammates/PLAYBOOK.md` for every git, PR and CI step. This file only adds what is specific to Jhavi Dasari.

## You may create, edit, rename or delete only these
- `prediction/`
- `tests/test_prediction_*.py`
- `notebooks/djahnavi180506_*.ipynb`
- shared: `mimi/` (only your own lines in `mimi/STATE.md`), `pyproject.toml`, `uv.lock`

Every other path belongs to someone else. If a change is needed there, stop and draft a message the user can send to its owner (`AGENTS.md` section 2 lists owners).

Branch names: `djahnavi180506/<topic>`.

## Depends on
- `data/` (Harsh1331). Read its public functions; never copy or patch them.

## Used by
- `uncertainty/` (hritikshukla144) and `planning/` (Vidhan-J28) consume your predictions.

## Watch out
- No leakage: a prediction for Gameweek t may use only data from before the Gameweek t deadline.
- Never commit trained model files. Train them in code and seed every random process.
