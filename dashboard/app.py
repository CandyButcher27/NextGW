from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st

from backtesting.metrics import summarize
from dashboard.core import cumulative_by_gameweek, gap_to_greedy, load_runs, recommend_plan
from data import load_clean_player_gw_data
from prediction.form_forecast import fixture_forecaster, fixture_schedule, model_forecaster
from prediction.train import train_model

ROOT = Path(__file__).resolve().parents[1]
SERIES = {
    "light": ["#2a78d6", "#eb6834", "#1baf7a", "#eda100"],
    "dark": ["#3987e5", "#d95926", "#199e70", "#c98500"],
}

st.set_page_config(page_title="NextGW", layout="wide")


def theme_mode() -> str:
    return "dark" if getattr(getattr(st.context, "theme", None), "type", "light") == "dark" else "light"


def strategy_colors(strategies: list[str]) -> alt.Scale:
    mode = theme_mode()
    planners = sorted(s for s in strategies if s.startswith("planner"))
    order = planners[:1] + ["greedy", "conventional"] + planners[1:2]
    order = [s for s in order if s in strategies]
    return alt.Scale(domain=order, range=SERIES[mode][: len(order)])


@st.cache_data
def runs() -> dict[str, pd.DataFrame]:
    return load_runs(ROOT / "results")


@st.cache_data
def season_data(season: str) -> pd.DataFrame:
    return load_clean_player_gw_data(season=season, processed_dir=ROOT / "data/processed", raw_dir=ROOT / "data/raw", auto_fetch=False)


@st.cache_resource
def trained_model(season: str, gameweek: int):
    earlier = [s for s in available_seasons() if s < season]
    training = pd.concat([*(season_data(s) for s in earlier), season_data(season)], ignore_index=True)
    return train_model(training, as_of_season=season, as_of_gameweek=gameweek)


def available_seasons() -> list[str]:
    return sorted(p.parent.name for p in (ROOT / "data/raw").glob("*/merged_gw.csv") if p.parent.name != "synthetic")


def results_page() -> None:
    all_runs = runs()
    if not all_runs:
        st.info("No backtest results yet. Run `uv run python scripts/run_backtest.py configs/model.toml`.")
        return
    name = st.selectbox("Backtest run", sorted(all_runs), index=sorted(all_runs).index("model-heldout") if "model-heldout" in all_runs else 0)
    results = all_runs[name]
    seasons = sorted(results["season"].unique())
    picked = st.multiselect("Seasons", seasons, default=seasons)
    results = results[results["season"].isin(picked)]
    if results.empty:
        return

    gaps = gap_to_greedy(results)
    planners = [s for s in gaps.index if s.startswith("planner")]
    best = gaps.loc[planners, "mean_points"].idxmax() if planners else None
    cols = st.columns(4)
    if best:
        cols[0].metric(f"{best} vs greedy", f"{gaps.loc[best, 'gap_to_greedy']:+.0f} pts", help="Mean paired gap per season run")
        cols[1].metric("Planner wins", f"{int(gaps.loc[best, 'wins'])} / {int(gaps.loc[best, 'runs'])}")
        cols[2].metric("Standard error", f"{gaps.loc[best, 'gap_se']:.0f} pts")
    cols[3].metric("Runs (season × squad)", int(gaps["runs"].iloc[0]))

    curve = cumulative_by_gameweek(results)
    scale = strategy_colors(list(curve["strategy"].unique()))
    color = alt.Color("strategy:N", scale=scale, legend=alt.Legend(title=None, orient="top"))
    nearest = alt.selection_point(nearest=True, on="pointerover", fields=["gameweek"], empty=False)
    st.markdown("**Cumulative points ahead of greedy** (mean over runs)")
    base = alt.Chart(curve).encode(
        x=alt.X("gameweek:Q", title="Gameweek", axis=alt.Axis(grid=False), scale=alt.Scale(nice=False)),
        y=alt.Y("gap_to_greedy:Q", title="Points vs greedy"),
    )
    lines = base.mark_line(strokeWidth=2).encode(color=color)
    hover = base.mark_point(size=80, filled=True).encode(color=color, opacity=alt.condition(nearest, alt.value(1), alt.value(0)))
    rule = (
        alt.Chart(curve)
        .mark_rule(color="gray", opacity=0.4)
        .encode(
            x="gameweek:Q",
            opacity=alt.condition(nearest, alt.value(0.4), alt.value(0)),
            tooltip=[alt.Tooltip("gameweek:Q", title="GW")]
            + [alt.Tooltip(s.replace(".", "\\.") + ":Q", title=s, format="+.0f") for s in scale.domain],
        )
        .transform_pivot("strategy", value="gap_to_greedy", groupby=["gameweek"])
        .add_params(nearest)
    )
    st.altair_chart((lines + hover + rule).properties(height=360), width="stretch")
    with st.expander("Chart data"):
        st.dataframe(curve.pivot(index="gameweek", columns="strategy", values="gap_to_greedy").round(1), width="stretch")

    st.subheader("Strategies")
    table = gaps.join(summarize(results).drop(columns=["points_per_run"]))
    st.dataframe(table.round(2), width="stretch")
    with st.expander("Per-Gameweek decisions"):
        strategy = st.selectbox("Strategy", sorted(results["strategy"].unique()))
        columns = ["season", "seed", "gameweek", "transfers", "captain_id", "chip", "auto_subs", "gw_points", "cumulative_points"]
        st.dataframe(results[results["strategy"] == strategy][columns], width="stretch", hide_index=True)


def plan_page() -> None:
    seasons = available_seasons()
    if not seasons:
        st.info("No season data in data/raw. See the README for how to fetch it.")
        return
    left, right = st.columns([1, 3])
    with left:
        season = st.selectbox("Season", seasons, index=len(seasons) - 1)
        gameweek = st.slider("Decision Gameweek", 5, 35, 20)
        kind = st.radio("Forecasts", ["model", "fixture"], help="model: ML point model trained on data before this GW")
        transfer_value = st.slider("Transfer cost (planning only)", 0.0, 4.0, 3.0, 0.5)
        chips = st.multiselect("Chips available", ["TripleCaptain", "BenchBoost"])
        go = st.button("Plan next 4 Gameweeks", type="primary")
    if not go:
        right.caption("Builds the best squad for the chosen Gameweek from pre-deadline data, then plans 4 Gameweeks ahead.")
        return
    data = season_data(season)
    with right, st.spinner("Forecasting and searching..."):
        if kind == "model":
            if not any(s < season for s in seasons):
                st.warning("The model needs an earlier season to train on; using fixture forecasts.")
                forecaster = fixture_forecaster(fixture_schedule(data))
            else:
                forecaster = model_forecaster(trained_model(season, gameweek), fixture_schedule(data))
        else:
            forecaster = fixture_forecaster(fixture_schedule(data))
        summary, lineups = recommend_plan(data, season, gameweek, forecaster, transfer_value=transfer_value, chips=tuple(chips))
        st.subheader("Plan")
        st.dataframe(summary, width="stretch", hide_index=True)
        chart = (
            alt.Chart(summary)
            .mark_bar(cornerRadiusTopLeft=4, cornerRadiusTopRight=4, color=SERIES[theme_mode()][0], size=28)
            .encode(
                x=alt.X("gameweek:O", title="Gameweek", axis=alt.Axis(labelAngle=0)),
                y=alt.Y("expected_points:Q", title="Expected points (XI + captain)"),
                tooltip=["gameweek", "expected_points", "transfers", "captain", "chip"],
            )
            .properties(height=220)
        )
        st.altair_chart(chart, width="stretch")
        for gw, team in lineups.groupby("gameweek"):
            with st.expander(f"GW{gw} lineup", expanded=gw == gameweek):
                order = {"GK": 0, "DEF": 1, "MID": 2, "FWD": 3}
                team = team.assign(_o=team["role"].eq("bench").astype(int) * 10 + team["position"].map(order)).sort_values("_o")
                st.dataframe(team.drop(columns=["gameweek", "_o"]), width="stretch", hide_index=True)


st.title("NextGW")
st.caption("Multi-Gameweek FPL planning under uncertainty: 4-GW planner vs greedy 1-GW vs rule-based, on historical seasons.")
results_tab, plan_tab = st.tabs(["Backtest results", "4-GW plan"])
with results_tab:
    results_page()
with plan_tab:
    plan_page()
