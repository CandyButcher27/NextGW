"""Historical Gameweek replay: strategies decide before each deadline, real outcomes score them.

The simulator does not check FPL legality (squad, formation, budget, club limits) and does not
apply automatic substitutions. Both belong to the ``fpl`` module; until it lands, legality is
whatever ``transition_fn`` enforces. Chips are not supported yet.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Protocol

import pandas as pd

from data.leakage import get_pre_deadline_history
from planning.actions import GWPlan
from planning.state import PlanningState

TransitionFn = Callable[[PlanningState, GWPlan], PlanningState]

RESULT_COLUMNS: list[str] = [
    "strategy",
    "season",
    "gameweek",
    "num_transfers",
    "free_transfers",
    "hits",
    "hit_cost",
    "xi_points",
    "captain_id",
    "captain_played",
    "captain_bonus",
    "gw_points",
    "cumulative_points",
]


class Strategy(Protocol):
    """A decision policy replayed by the simulator.

    ``history`` holds only player-Gameweek rows from before the ``gameweek`` deadline.
    """

    name: str

    def decide(
        self,
        state: PlanningState,
        history: pd.DataFrame,
        season: str,
        gameweek: int,
    ) -> GWPlan: ...


@dataclass(frozen=True)
class ScoringConfig:
    """FPL scoring values the simulator applies; pass different values to change the rules."""

    transfer_hit_cost: float = 4.0
    captain_multiplier: float = 2.0


def gameweek_outcomes(data: pd.DataFrame, season: str, gameweek: int) -> pd.DataFrame:
    """Return realised ``total_points`` and ``minutes`` for one Gameweek, indexed by str player_id.

    Player ids are strings because ``planning`` identifies players by string.
    """
    rows = data.loc[(data["season"] == season) & (data["gameweek"] == gameweek)]
    outcomes = rows.groupby(rows["player_id"].astype(str))[["total_points", "minutes"]].sum()
    return outcomes


def score_gameweek(
    state: PlanningState,
    plan: GWPlan,
    outcomes: pd.DataFrame,
    scoring: ScoringConfig,
) -> dict[str, object]:
    """Score one decision against realised outcomes.

    Players with no row in ``outcomes`` score 0 and count as not having played. If the captain
    played 0 minutes, the vice-captain receives the captain multiplier instead.
    """
    if plan.chip is not None:
        raise ValueError(f"Chips are not supported by the simulator yet: {plan.chip.chip_name}")

    def points(player_id: str) -> float:
        key = str(player_id)
        return float(outcomes.at[key, "total_points"]) if key in outcomes.index else 0.0

    def played(player_id: str) -> bool:
        key = str(player_id)
        return key in outcomes.index and float(outcomes.at[key, "minutes"]) > 0

    lineup = plan.lineup
    xi_points = sum(points(pid) for pid in lineup.starting_xi)
    captain_played = played(lineup.captain)
    armband = lineup.captain if captain_played else lineup.vice_captain
    captain_bonus = (scoring.captain_multiplier - 1.0) * points(armband)

    num_transfers = len(plan.transfers)
    hits = max(0, num_transfers - state.free_transfers)
    hit_cost = hits * scoring.transfer_hit_cost

    return {
        "num_transfers": num_transfers,
        "free_transfers": state.free_transfers,
        "hits": hits,
        "hit_cost": hit_cost,
        "xi_points": xi_points,
        "captain_id": str(lineup.captain),
        "captain_played": captain_played,
        "captain_bonus": captain_bonus,
        "gw_points": xi_points + captain_bonus - hit_cost,
    }


def simulate(
    strategy: Strategy,
    data: pd.DataFrame,
    season: str,
    start_gw: int,
    end_gw: int,
    initial_state: PlanningState,
    transition_fn: TransitionFn,
    scoring: ScoringConfig | None = None,
) -> pd.DataFrame:
    """Replay ``strategy`` over Gameweeks ``start_gw``..``end_gw`` (inclusive) of ``season``.

    Before each deadline the strategy sees only ``get_pre_deadline_history`` rows. Its plan is
    scored on that Gameweek's realised points, then ``transition_fn(state, plan)`` gives the
    next state. Returns one row per Gameweek with ``RESULT_COLUMNS``.
    """
    if start_gw > end_gw:
        raise ValueError("start_gw must not be after end_gw")
    if initial_state.gameweek != start_gw:
        raise ValueError(
            f"initial_state is for GW {initial_state.gameweek}, expected start_gw {start_gw}"
        )
    scoring = scoring or ScoringConfig()

    state = initial_state
    cumulative = 0.0
    rows: list[dict[str, object]] = []
    for gameweek in range(start_gw, end_gw + 1):
        history = get_pre_deadline_history(data, current_season=season, current_gameweek=gameweek)
        plan = strategy.decide(state, history, season, gameweek)
        result = score_gameweek(state, plan, gameweek_outcomes(data, season, gameweek), scoring)
        cumulative += float(result["gw_points"])
        rows.append(
            {
                "strategy": strategy.name,
                "season": season,
                "gameweek": gameweek,
                **result,
                "cumulative_points": cumulative,
            }
        )
        state = transition_fn(state, plan)
    return pd.DataFrame(rows, columns=RESULT_COLUMNS)
