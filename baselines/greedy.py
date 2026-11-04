from __future__ import annotations

from planning.strategy import PlannerStrategy


def GreedyStrategy(**kwargs) -> PlannerStrategy:
    return PlannerStrategy(**{"name": "greedy", **kwargs, "horizon": 1})
