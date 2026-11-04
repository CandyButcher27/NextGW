import pandas as pd
import pytest

from prediction.form_forecast import fixture_factors, fixture_forecaster, fixture_schedule, per_match_form

SEASON = "2024-25"


def row(pid, gw, team, opp, home, pts, matches=1, minutes=90):
    return {
        "season": SEASON, "gameweek": gw, "player_id": pid, "team": team, "opponent_team": opp,
        "was_home": home, "matches_in_gw": matches, "total_points": pts, "minutes": minutes,
    }


def test_schedule_splits_double_gameweeks():
    data = pd.DataFrame([row(1, 3, "ARS", "10 & 7", True, 0, matches=2)])
    assert fixture_schedule(data)[(SEASON, 3)]["ARS"] == [("10", True), ("7", True)]


def test_per_match_form_divides_double_gameweek_points():
    history = pd.DataFrame([row(1, 1, "ARS", "2", True, 4), row(1, 2, "ARS", "2 & 3", True, 8, matches=2)])
    assert per_match_form(history, SEASON, 4)["1"] == pytest.approx(4.0)


def test_fixture_factors_mark_leaky_defence_as_easier():
    history = pd.DataFrame([row(i, 1, "X", "weak", True, 8) for i in range(5)] + [row(i, 1, "X", "strong", False, 2) for i in range(5, 10)])
    opponent, home = fixture_factors(history, SEASON, shrink=0.0)
    assert opponent["weak"] > 1.0 > opponent["strong"]
    assert home[True] > home[False]


def test_forecast_is_zero_in_blank_gameweek_and_doubles_in_double():
    history = pd.DataFrame([row(1, 1, "ARS", "2", True, 6), row(2, 1, "CHE", "1", False, 6)])
    schedule = {(SEASON, 2): {"ARS": [("2", True)]}, (SEASON, 3): {"ARS": [("2", True), ("2", True)]}}
    forecast = fixture_forecaster(schedule, shrink=1e9)(history, SEASON, 2, 2)
    assert forecast[2]["2"] == 0.0
    assert forecast[3]["1"] == pytest.approx(2 * forecast[2]["1"])
