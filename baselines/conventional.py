from __future__ import annotations

from collections import Counter
from dataclasses import dataclass

import pandas as pd

from baselines.common import active_pool, player_registry, recent_minutes, squad_ids
from prediction.form_forecast import rolling_form
from fpl.lineup import solve_optimal_lineup
from fpl.rules import DEFAULT_CONFIG, FPLRulesConfig
from planning.actions import GWPlan, TransferAction
from planning.state import PlanningState


@dataclass
class ConventionalStrategy:
    name: str = "conventional"
    form_window: int = 4
    absence_window: int = 2
    config: FPLRulesConfig = DEFAULT_CONFIG

    def decide(self, state: PlanningState, history: pd.DataFrame, season: str, gameweek: int) -> GWPlan:
        registry = player_registry(history, season)
        form = rolling_form(history, season, self.form_window)
        minutes = recent_minutes(history, season, self.absence_window)
        squad = {pid: registry[pid] for pid in squad_ids(state.squad)}
        transfers = []

        absent = [pid for pid in squad if minutes.get(pid, 0.0) == 0.0]
        if absent and state.free_transfers >= 1:
            out = squad[min(absent, key=lambda pid: form.get(pid, 0.0))]
            clubs = Counter(p.team for p in squad.values() if p.team != out.team)
            funds = state.budget + out.price
            options = [
                p for p in active_pool(history, season, registry)
                if p.position == out.position
                and p.player_id not in squad
                and p.price <= funds + 1e-6
                and minutes.get(p.player_id, 0.0) > 0
                and clubs[p.team] < self.config.max_players_per_club
            ]
            if options:
                best = max(options, key=lambda p: form.get(p.player_id, 0.0))
                transfers.append(TransferAction(player_out=out.player_id, player_in=best.player_id))
                del squad[out.player_id]
                squad[best.player_id] = best

        lineup = solve_optimal_lineup({pid: p.position for pid, p in squad.items()}, form, self.config)
        return GWPlan(transfers=transfers, lineup=lineup.to_action())
