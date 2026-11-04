from __future__ import annotations

from dataclasses import dataclass, field
from functools import partial

import pandas as pd

from baselines.common import active_pool, player_registry
from fpl.transfers import transition_fn
from planning.actions import GWPlan
from planning.objective import PlanningObjective
from planning.search import PlanningSearch
from planning.state import PlanningState
from prediction.form_forecast import Forecaster, form_forecast


@dataclass
class PlannerStrategy:
    name: str = "planner"
    horizon: int = 4
    beam_width: int = 10
    transfer_cost: float = 4.0
    discount: float = 1.0
    transfer_value: float = 0.0
    forecaster: Forecaster = field(default=form_forecast)

    def decide(self, state: PlanningState, history: pd.DataFrame, season: str, gameweek: int) -> GWPlan:
        registry = player_registry(history, season)
        search = PlanningSearch(
            PlanningObjective(
                self.forecaster(history, season, gameweek, self.horizon),
                transfer_cost=self.transfer_cost,
                discount=self.discount,
                transfer_value=self.transfer_value,
            ),
            beam_width=self.beam_width,
            horizon=self.horizon,
            candidate_pool=active_pool(history, season, registry),
            player_registry=registry,
        )
        return search.plan(state, [], partial(transition_fn, player_registry=registry))[0]
