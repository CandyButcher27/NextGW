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


def test_model_forecaster_uses_only_decision_history(tmp_path):
    from data import get_pre_deadline_history, load_synthetic_player_gw_data
    from prediction.form_forecast import model_forecaster
    from prediction.train import train_model

    data = load_synthetic_player_gw_data(season=SEASON, raw_dir=tmp_path / "raw", processed_dir=tmp_path / "proc", num_players=12, num_gws=10)
    model = train_model(data, as_of_season=SEASON, as_of_gameweek=6)
    schedule = fixture_schedule(data)
    history = get_pre_deadline_history(data, current_season=SEASON, current_gameweek=6)

    full = model_forecaster(model, schedule)(history, SEASON, 6, 4)
    assert sorted(full) == [6, 7, 8, 9]
    assert len(full[6]) == data["player_id"].nunique()
    assert model_forecaster(model, schedule)(history, SEASON, 6, 1) == {6: full[6]}

    blank = {key: teams for key, teams in schedule.items() if key != (SEASON, 7)}
    assert model_forecaster(model, blank)(history, SEASON, 6, 2)[7] == {}
