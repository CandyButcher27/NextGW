# Hrithik Shukla (`hritikshukla144`) — uncertainty

The agent is working for Hrithik Shukla. Follow `teammates/PLAYBOOK.md` for every git, PR and CI step. This file only adds what is specific to Hrithik Shukla.

## You may create, edit, rename or delete only these
- `uncertainty/`
- `tests/test_uncertainty_*.py`
- `notebooks/hritikshukla144_*.ipynb`
- shared: `mimi/` (only your own lines in `mimi/STATE.md`), `pyproject.toml`, `uv.lock`

Every other path belongs to someone else. If a change is needed there, stop and draft a message the user can send to its owner (`AGENTS.md` section 2 lists owners).

Branch names: `hritikshukla144/<topic>`.

## Depends on
- `prediction/` (djahnavi180506).

## Used by
- `planning/` (Vidhan-J28) uses your scenarios in its objective.

## Watch out
- If your collaborator invite is not accepted yet, `git push` fails with 403. Accept it at https://github.com/CandyButcher27/NextGW/invitations first.
- Every sampler takes an explicit seed.
