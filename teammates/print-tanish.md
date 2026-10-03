# Tanishq (`print-tanish`) — backtesting metrics

The agent is working for Tanishq. Follow `teammates/PLAYBOOK.md` for every git, PR and CI step. This file only adds what is specific to Tanishq.

## You may create, edit, rename or delete only these
- `backtesting/metrics.py`
- `backtesting/__init__.py` (shared with TA619)
- `tests/test_metrics_*.py`
- `notebooks/print-tanish_*.ipynb`
- shared: `mimi/` (only your own lines in `mimi/STATE.md`), `pyproject.toml`, `uv.lock`

Every other path belongs to someone else. If a change is needed there, stop and draft a message the user can send to its owner (`AGENTS.md` section 2 lists owners).

Branch names: `print-tanish/<topic>`.

## Depends on
- `backtesting/simulator.py` (TA619) output.

## Used by
- The final experiments and the dashboard.

## Watch out
- Everything else in `backtesting/` (`simulator.py`, `experiments.py`) is TA619's. Never edit it.
- `backtesting/__init__.py` is shared with TA619. Change it only in small commits and merge `main` first to avoid conflicts.
- Name tests `tests/test_metrics_*.py`. `tests/test_backtesting_*` belongs to TA619 and CI fails your PR if you touch it.
