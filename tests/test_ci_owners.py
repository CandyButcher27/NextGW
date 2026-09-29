from pathlib import Path

from scripts.check_owners import owners, parse, violations

RULES = parse(Path(".github/CODEOWNERS").read_text(encoding="utf-8"))


def test_module_owner_and_default():
    assert owners(RULES, "fpl/rules.py") == {"tarunpk15"}
    assert owners(RULES, "tests/test_fpl_squad.py") == {"tarunpk15"}
    assert owners(RULES, "backtesting/metrics.py") == {"print-tanish"}
    assert owners(RULES, "dashboard/app.py") == {"candybutcher27"}


def test_shared_paths_allow_everyone():
    assert violations(RULES, "Harsh1331", ["mimi/STATE.md", "uv.lock", "pyproject.toml", "data/ingestion/fetch.py"]) == []


def test_foreign_paths_rejected():
    assert violations(RULES, "Harsh1331", ["planning/search.py", "notebooks/TA619_eda.ipynb", "AGENTS.md"]) == [
        "planning/search.py",
        "notebooks/TA619_eda.ipynb",
        "AGENTS.md",
    ]
