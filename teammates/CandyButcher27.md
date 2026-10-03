# Aryaman Srivastava (`CandyButcher27`) — repo admin

The agent is working for Aryaman, the repo admin. Follow `teammates/PLAYBOOK.md` for git, PR and CI steps.

## You may create, edit, rename or delete only these
- Every path not owned by another teammate: `dashboard/`, `configs/`, `scripts/`, `.github/`, `teammates/`, top-level pipeline, `AGENTS.md`, `CLAUDE.md`, `README.md`, `.gitignore`, `.gitattributes`, and any test not matching another owner's `tests/test_<module>_*` pattern
- `notebooks/CandyButcher27_*.ipynb`
- shared: `mimi/`, `pyproject.toml`, `uv.lock`

Module code (`data/`, `prediction/`, `uncertainty/`, `fpl/`, `planning/`, `baselines/`, `backtesting/`) still belongs to its owner. CODEOWNERS gives the admin no exception there.

## Watch out
- When ownership changes, update the table in `AGENTS.md` section 2, `.github/CODEOWNERS`, and the teammate's file here together, in one PR.
- A new teammate needs a `teammates/<github-username>.md` file, or their agent stops at session start.
