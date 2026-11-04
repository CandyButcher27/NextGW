from __future__ import annotations

from dataclasses import dataclass
from functools import partial

import pandas as pd

from baselines.common import active_pool, player_registry, rolling_form
from fpl.transfers import transition_fn
from planning.actions import GWPlan
from planning.objective import PlanningObjective
from planning.search import PlanningSearch
from planning.state import PlanningState


@dataclass
class GreedyStrategy:
    name: str = "greedy"
    form_window: int = 4
    transfer_cost: float = 4.0

    def decide(self, state: PlanningState, history: pd.DataFrame, season: str, gameweek: int) -> GWPlan:
        registry = player_registry(history, season)
        forecast = rolling_form(history, season, self.form_window)
        search = PlanningSearch(
            PlanningObjective({gameweek: forecast}, transfer_cost=self.transfer_cost),
            horizon=1,
            candidate_pool=active_pool(history, season, registry),
            player_registry=registry,
        )
        return search.plan(state, [], partial(transition_fn, player_registry=registry))[0]
