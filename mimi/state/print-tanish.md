# State — Tanishq (`print-tanish`)
<!-- Written only by print-tanish. Overwritten every session by mimi-close. Finished work leaves. Cap 60 lines. -->

## Broken
- none known

## Open threads
- BLOCKED on TA619: the simulator->metrics output contract is undocumented.
  `backtesting/simulator.py` and `backtesting/experiments.py` are empty on main
  and no decision/doc defines the shape metrics scores.
  Exact question for TA619: what is the per-Gameweek record that metrics.py
  scores? Candidate fields: season, gameweek, starting_xi player_ids,
  captain_id, vice_captain_id, num_transfers, free_transfers, chip (or None),
  and per-player actual points needed to score the XI and captain. Return one
  object (or sequence) per strategy so planner/greedy/rule-based are scored
  identically. Confirm BGW/DGW handling and chip labels.
  Plan + confirmed-vs-proposed split lives in `backtesting/metrics.py` docstring.

## Next 3
- Once the contract is agreed, add captain_points, chip_contribution and
  decision_stability metrics and a per-strategy summary/reporting output.
- Wire metrics into TA619's experiments runner for the planner vs greedy vs
  rule-based comparison (README ablations).
- Ask CandyButcher27 to shorten decision headings or split memory: the
  always-loaded layer is at 15,983 bytes, only 17 bytes under the 16,000 cap,
  so no new decision entry fits without trimming.

## Last session (2026-10-14)
Branch: print-tanish/evaluation-plan
Uncommitted: backtesting/metrics.py, tests/test_metrics_core.py, mimi/state/print-tanish.md
Stopped at: evaluation plan + schema-independent metric primitives (cumulative_points, points_per_gameweek, transfer_hit_points) written and tested; next is TA619's contract.
Tried, failed: adding DEC-T-1 to mimi/decisions.md — the generated index line pushed the always-loaded layer to 16,088 bytes (cap 16,000), so it was reverted.
Resume with: get TA619's simulator output contract, then implement scoring metrics against it.

Last updated: 2026-10-14
