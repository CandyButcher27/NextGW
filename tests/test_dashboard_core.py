import pandas as pd

from dashboard.core import cumulative_by_gameweek, gap_to_greedy, load_runs, recommend_plan
from tests.test_baselines_strategies import SEASON, make_history


def write_run(root, season, seed, points):
    rows = [
        {"strategy": s, "gameweek": gw, "gw_points": p}
        for s, per_gw in points.items()
        for gw, p in enumerate(per_gw, start=1)
    ]
    path = root / "demo" / season / f"seed{seed}"
    path.mkdir(parents=True)
    pd.DataFrame(rows).to_csv(path / "results.csv", index=False)


def test_load_runs_and_gap_to_greedy(tmp_path):
    write_run(tmp_path, "2024-25", 0, {"greedy": [10, 10], "planner": [12, 12]})
    write_run(tmp_path, "2024-25", 1, {"greedy": [10, 10], "planner": [9, 10]})
    results = load_runs(tmp_path)["demo"]
    gaps = gap_to_greedy(results)
    assert gaps.loc["planner", "gap_to_greedy"] == 1.5
    assert gaps.loc["planner", "wins"] == 1
    curve = cumulative_by_gameweek(results)
    row = curve.set_index(["strategy", "gameweek"]).loc[("planner", 2)]
    assert row["cumulative"] == 21.5 and row["gap_to_greedy"] == 1.5


def test_recommend_plan_returns_four_legal_gameweeks():
    history = make_history({"star_mid": [12, 12, 12, 12]})
    data = pd.concat([history, history.assign(gameweek=5, total_points=0)], ignore_index=True)

    def forecaster(history, season, gameweek, horizon):
        points = {pid: 2.0 for pid in history["player_id"].astype(str)} | {"star_mid": 12.0}
        return {gw: points for gw in range(gameweek, gameweek + horizon)}

    summary, lineups = recommend_plan(data, SEASON, 5, forecaster, budget=80.0)
    assert list(summary["gameweek"]) == [5, 6, 7, 8]
    assert (summary["captain"] == "star_mid").all()
    assert (lineups.groupby("gameweek")["player"].count() == 15).all()
