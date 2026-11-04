# State — Aryaman Srivastava (`CandyButcher27`)
<!-- Written only by CandyButcher27. Overwritten every session by mimi-close. Finished work leaves. Cap 60 lines. -->

## Broken
- none known; `uv run pytest` 214 passed on main at the end of this session

## Open threads
- Chip timing: hold value is flat, so chips fire in GW5-6. Next: hold = best forecastable later gain, or reserve Bench Boost for double GWs.
- Wildcard / Free Hit planning needs whole-squad re-optimization (`greedy_squad` on window forecasts).
- Teammates whose files changed this session should pull main: Tarun (fpl), hritikshukla144 (uncertainty), TA619 (backtesting, baselines), Vidhan (planning), print-tanish (metrics), Harsh (data).

## Next 3
1. Chip timing from forecastable gains, tuned on dev 2023-24, tested on 2024-25.
2. Wildcard / Free Hit planning.
3. Dashboard for a recommended 4-GW plan.

## Last session (2026-11-04)
Branch: main
Stopped at: PRs #24-#38 merged: review fixes, admin co-ownership, baselines, MVP backtest, fixture and ML forecasters, multi-season paired evaluation, oracle diagnostic, discount, transfer cost, 2-transfer moves, retraining option, metrics, auto-subs, chips.
Tried, failed: discount (held out -105), 2-transfer moves (-55 to -91 on dev), in-season retraining (-64 to -72 on dev), fixture-heuristic forecasts for the planner (ties or trails greedy).
Resume with: chip timing on a `CandyButcher27/<topic>` branch from fresh main.

Last updated: 2026-11-04
