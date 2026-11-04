# Issues
<!-- Append-only, one entry per bug:
"## ISS-<n> — <title>" heading, then
Symptom: exact error text or observed behavior
Cause: root cause
Fix: commit hash
Test: the test that fails without the fix
Status: open | fixed -->

## ISS-AS-1 — CI fails: Unable to resolve action `astral-sh/setup-uv@v10`
Symptom: `##[error]Unable to resolve action `astral-sh/setup-uv@v10`, unable to find version `v10`` in the ci job "Set up job" step (run 36642364155).
Cause: astral-sh/setup-uv publishes only exact release tags (e.g. v10.2.0), no floating major tag. actions/checkout does publish `v7`.
Fix: cf39ddf (pin `astral-sh/setup-uv@v10.2.0`)
Test: none; verified by green ci run 36642429779 on throwaway PR #1.
Status: fixed

## ISS-AS-2 — Backtest accepts illegal transfers and lineups
Symptom: `fpl.transition_fn` turned a 15-man squad into 14 when buying an owned player and set an overspent bank to `0.0`; `score_gameweek` scored XI ids not in the squad.
Cause: no membership or bank checks in `transition_fn`; budget clamped with `max(0.0, ...)`; simulator never compared the XI with the squad.
Fix: aab58d9 (#25)
Test: tests/test_fpl_transfers.py::test_transition_fn_rejects_overspend, tests/test_backtesting_simulator.py::test_rejects_starting_xi_outside_squad
Status: fixed

## ISS-AS-3 — Sampled points clipped at 0 inflate scenario means
Symptom: `create_simple_gaussian(2.0, 3.0).sample(200_000).mean()` returned 2.46.
Cause: `UncertaintyDistribution.sample` applied `np.maximum(samples, 0.0)`; FPL points go negative.
Fix: aab58d9 (#25)
Test: tests/test_uncertainty_distributions.py::test_sample_keeps_negative_points_and_mean
Status: fixed

## ISS-AS-4 — Real-season load returns synthetic data
Symptom: `load_clean_player_gw_data(season="2023-24")` returned 40 players instead of about 865.
Cause: `load_synthetic_player_gw_data()` defaulted to `data/raw` and `data/processed`, overwriting the real raw CSV and the processed cache.
Fix: 289676b (#28); defaults now `data/raw/synthetic`, `data/processed/synthetic`
Test: tests/test_data_pipeline.py::test_load_synthetic_default_paths_never_touch_real_data
Status: fixed

## ISS-AS-5 — Planner churns players it just bought
Symptom: 4-GW planner bought player 309 in GW10 and sold him in GW12 (2024-25); planner 1804 pts vs greedy 1989.
Cause: `generate_candidate_plans` chose sells and buys by the current GW forecast only, so lookahead stacked myopic moves.
Fix: fe8bf76 (#30), `ranking_points` summed over the remaining window
Test: tests/test_fpl_transfers.py::test_candidates_rank_transfers_by_ranking_points
Status: fixed
