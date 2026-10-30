"""Squad representation, validation, and CSP-based squad selection for FPL."""

from __future__ import annotations

from collections import Counter, defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from .csp import (
    CSP,
    AllDifferentConstraint,
    CountConstraint,
    FunctionalConstraint,
    SumConstraint,
    backtracking_search,
    mrv_heuristic,
)
from .rules import DEFAULT_CONFIG, FPLRulesConfig, validate_squad


@dataclass(frozen=True)
class Player:
    """Represents a Premier League player with FPL attributes."""

    player_id: str
    name: str
    position: str  # "GK", "DEF", "MID", "FWD"
    team: str      # Club name or identifier (e.g., "ARS", "MCI", "1", "2")
    price: float   # Price in £m (e.g., 10.5)
    status: str = "a"

    def __repr__(self) -> str:
        return f"Player({self.player_id}, '{self.name}', {self.position}, {self.team}, £{self.price}m)"


class Squad:
    """Represents a 15-player FPL squad."""

    def __init__(self, players: Sequence[Player]) -> None:
        self.players: list[Player] = list(players)
        self._player_map: dict[str, Player] = {p.player_id: p for p in self.players}

    def __len__(self) -> int:
        return len(self.players)

    def __iter__(self):
        return iter(self.players)

    def __contains__(self, player_id: str | Player) -> bool:
        pid = player_id.player_id if isinstance(player_id, Player) else str(player_id)
        return pid in self._player_map

    def get(self, player_id: str) -> Player | None:
        """Get player by player_id."""
        return self._player_map.get(str(player_id))

    @property
    def player_ids(self) -> list[str]:
        return [p.player_id for p in self.players]

    @property
    def total_cost(self) -> float:
        return round(sum(p.price for p in self.players), 2)

    @property
    def positions(self) -> dict[str, str]:
        """Map of player_id to position."""
        return {p.player_id: p.position for p in self.players}

    @property
    def gk(self) -> list[Player]:
        return [p for p in self.players if p.position == "GK"]

    @property
    def defenders(self) -> list[Player]:
        return [p for p in self.players if p.position == "DEF"]

    @property
    def midfielders(self) -> list[Player]:
        return [p for p in self.players if p.position == "MID"]

    @property
    def forwards(self) -> list[Player]:
        return [p for p in self.players if p.position == "FWD"]

    @property
    def by_team(self) -> dict[str, list[Player]]:
        teams: dict[str, list[Player]] = defaultdict(list)
        for p in self.players:
            teams[p.team].append(p)
        return dict(teams)

    def validate(self, config: FPLRulesConfig = DEFAULT_CONFIG) -> tuple[bool, list[str]]:
        """Validate this squad against FPL rules."""
        return validate_squad(self.players, config)

    def to_state_squad(self) -> tuple[tuple[str, str], ...]:
        """Convert squad to sorted tuple of (player_id, position) for PlanningState."""
        return tuple(sorted((p.player_id, p.position) for p in self.players))

    @classmethod
    def from_state_squad(
        cls,
        state_squad: tuple[Any, ...] | Mapping[str, str],
        player_registry: Mapping[str, Player] | None = None,
    ) -> Squad:
        """Instantiate Squad from a PlanningState squad representation."""
        players: list[Player] = []
        if isinstance(state_squad, dict):
            items = state_squad.items()
        else:
            items = state_squad

        for item in items:
            if isinstance(item, (tuple, list)) and len(item) >= 2:
                pid, pos = str(item[0]), str(item[1])
            elif hasattr(item, "player_id"):
                pid, pos = str(item.player_id), str(item.position)
            else:
                pid, pos = str(item), "MID"

            if player_registry and pid in player_registry:
                players.append(player_registry[pid])
            else:
                players.append(Player(player_id=pid, name=pid, position=pos, team="UNK", price=5.0))

        return cls(players)


def create_squad_selection_csp(
    player_pool: Sequence[Player],
    config: FPLRulesConfig = DEFAULT_CONFIG,
    budget: float | None = None,
) -> CSP:
    """Formulate FPL squad selection as a formal CSP.

    Variables:
        gk_0, gk_1: 2 Goalkeepers
        def_0 .. def_4: 5 Defenders
        mid_0 .. mid_4: 5 Midfielders
        fwd_0 .. fwd_2: 3 Forwards
    Constraints:
        1. AllDifferentConstraint across all 15 variables.
        2. SumConstraint on total price <= budget.
        3. Club limit: Count of players for any team <= max_players_per_club.
    """
    total_budget = budget if budget is not None else config.budget

    # Group candidate players by position
    pool_by_pos: dict[str, list[Player]] = defaultdict(list)
    for p in player_pool:
        pool_by_pos[p.position].append(p)

    variables: list[str] = []
    domains: dict[str, list[Any]] = {}

    # Define variables and position domains
    for i in range(config.squad_gk_count):
        v = f"gk_{i}"
        variables.append(v)
        domains[v] = pool_by_pos["GK"]

    for i in range(config.squad_def_count):
        v = f"def_{i}"
        variables.append(v)
        domains[v] = pool_by_pos["DEF"]

    for i in range(config.squad_mid_count):
        v = f"mid_{i}"
        variables.append(v)
        domains[v] = pool_by_pos["MID"]

    for i in range(config.squad_fwd_count):
        v = f"fwd_{i}"
        variables.append(v)
        domains[v] = pool_by_pos["FWD"]

    csp = CSP(variables, domains)

    # 1. All players must be distinct
    csp.add_constraint(AllDifferentConstraint(variables))

    # 2. Budget constraint
    csp.add_constraint(
        SumConstraint(
            variables,
            max_sum=total_budget,
            value_fn=lambda p: p.price,
        )
    )

    # 3. Club limit constraint
    def club_limit_predicate(assignment: dict[str, Any]) -> bool:
        team_counts: Counter[str] = Counter()
        for p in assignment.values():
            if p.team and p.team != "UNK":
                team_counts[p.team] += 1
                if team_counts[p.team] > config.max_players_per_club:
                    return False
        return True

    csp.add_constraint(FunctionalConstraint(variables, club_limit_predicate))

    return csp


def solve_squad(
    player_pool: Sequence[Player],
    budget: float = 100.0,
    config: FPLRulesConfig = DEFAULT_CONFIG,
    expected_points: Mapping[str, float] | None = None,
) -> Squad | None:
    """Solve for a valid 15-player squad satisfying all FPL rules and budget.

    If expected_points are provided, prioritizes higher-scoring players in domain ordering.
    """
    sorted_pool = list(player_pool)
    if expected_points:
        sorted_pool.sort(key=lambda p: expected_points.get(p.player_id, 0.0), reverse=True)
    else:
        # Sort by value (price ascending to easily find feasible assignments)
        sorted_pool.sort(key=lambda p: p.price)

    csp = create_squad_selection_csp(sorted_pool, config, budget=budget)
    
    # Custom domain ordering to pick highest points / best value first
    def order_domain(c: CSP, var: str, assignment: dict[str, Any]) -> list[Any]:
        return list(c.domains[var])

    solution = backtracking_search(
        csp,
        select_unassigned_variable=mrv_heuristic,
        order_domain_values=order_domain,
        inference=None,  # Optimization for speed on large domains
    )

    if solution:
        return Squad(list(solution.values()))
    return None
