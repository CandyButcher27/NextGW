"""Lineup and formation selection, optimization, and auto-substitutions for FPL."""

from __future__ import annotations

from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from planning.actions import LineupAction

from .csp import (
    CSP,
    AllDifferentConstraint,
    CountConstraint,
    backtracking_search,
    mrv_heuristic,
)
from .rules import (
    DEFAULT_CONFIG,
    FPLRulesConfig,
    auto_substitute,
    get_valid_formations,
    is_valid_formation,
    validate_lineup,
)


@dataclass(frozen=True)
class Lineup:
    """A complete FPL matchday lineup selection."""

    starting_xi: tuple[str, ...]
    bench: tuple[str, ...]  # (Sub GK, Sub 1, Sub 2, Sub 3)
    captain: str
    vice_captain: str
    chip: str | None = None

    def to_action(self) -> LineupAction:
        """Convert to a Planning LineupAction."""
        return LineupAction(
            starting_xi=list(self.starting_xi),
            captain=str(self.captain),
            vice_captain=str(self.vice_captain),
        )

    def validate(
        self,
        squad_positions: Mapping[str, str],
        config: FPLRulesConfig = DEFAULT_CONFIG,
    ) -> tuple[bool, list[str]]:
        """Validate lineup against official FPL formation rules."""
        return validate_lineup(
            self.starting_xi,
            self.captain,
            self.vice_captain,
            squad_positions,
            config,
        )


def create_lineup_formation_csp(
    squad_positions: Mapping[str, str],
    config: FPLRulesConfig = DEFAULT_CONFIG,
) -> CSP:
    """Formulate Starting XI selection from a 15-player squad as a CSP.

    Variables:
        xi_0 .. xi_10: The 11 starting positions.
    Domain:
        All 15 squad player_ids.
    Constraints:
        1. AllDifferentConstraint (11 unique players).
        2. Exactly 1 GK.
        3. Between 3 and 5 DEF.
        4. Between 2 and 5 MID.
        5. Between 1 and 3 FWD.
    """
    variables = [f"xi_{i}" for i in range(config.starting_xi_size)]
    player_ids = list(squad_positions.keys())
    domains = {v: list(player_ids) for v in variables}

    csp = CSP(variables, domains)
    csp.add_constraint(AllDifferentConstraint(variables))

    # Positional count constraints
    csp.add_constraint(
        CountConstraint(
            variables,
            predicate=lambda pid: squad_positions.get(pid) == "GK",
            min_count=config.lineup_gk,
            max_count=config.lineup_gk,
        )
    )
    csp.add_constraint(
        CountConstraint(
            variables,
            predicate=lambda pid: squad_positions.get(pid) == "DEF",
            min_count=config.lineup_min_def,
            max_count=config.lineup_max_def,
        )
    )
    csp.add_constraint(
        CountConstraint(
            variables,
            predicate=lambda pid: squad_positions.get(pid) == "MID",
            min_count=config.lineup_min_mid,
            max_count=config.lineup_max_mid,
        )
    )
    csp.add_constraint(
        CountConstraint(
            variables,
            predicate=lambda pid: squad_positions.get(pid) == "FWD",
            min_count=config.lineup_min_fwd,
            max_count=config.lineup_max_fwd,
        )
    )

    return csp


def solve_optimal_lineup(
    squad: Mapping[str, str] | Sequence[Any],
    expected_points: Mapping[str, float] | None = None,
    config: FPLRulesConfig = DEFAULT_CONFIG,
) -> Lineup:
    """Select the optimal legal starting XI, captain, vice-captain, and bench order.

    Evaluates valid formation structures (3-5-2, 3-4-3, 4-4-2, 4-3-3, 4-5-1, 5-4-1, 5-3-2, 5-2-3)
    to maximize expected points from the Starting XI.

    Parameters
    ----------
    squad : Mapping of {player_id: position} or Sequence of Player/dict/tuples
        The 15-player squad.
    expected_points : Mapping of {player_id: pts}
        Predicted points per player for the upcoming Gameweek.
    config : FPLRulesConfig
        Rules configuration.
    """
    # Parse squad into positions mapping
    positions: dict[str, str] = {}
    if isinstance(squad, Mapping):
        positions = {str(k): str(v) for k, v in squad.items()}
    else:
        for p in squad:
            if hasattr(p, "player_id"):
                positions[str(p.player_id)] = str(p.position)
            elif isinstance(p, dict):
                positions[str(p["player_id"])] = str(p["position"])
            elif isinstance(p, (tuple, list)) and len(p) >= 2:
                positions[str(p[0])] = str(p[1])
            else:
                positions[str(p)] = "MID"

    pts = expected_points or {}

    # Separate players by position and sort descending by expected points
    by_pos: dict[str, list[str]] = {"GK": [], "DEF": [], "MID": [], "FWD": []}
    for pid, pos in positions.items():
        by_pos.setdefault(pos, []).append(pid)

    for pos in by_pos:
        by_pos[pos].sort(key=lambda pid: pts.get(pid, 0.0), reverse=True)

    # Evaluate each valid formation to find the highest-scoring combination
    valid_formations = get_valid_formations(config)
    best_score = -float("inf")
    best_xi: list[str] = []

    for gk_c, def_c, mid_c, fwd_c in valid_formations:
        if (
            len(by_pos["GK"]) < gk_c
            or len(by_pos["DEF"]) < def_c
            or len(by_pos["MID"]) < mid_c
            or len(by_pos["FWD"]) < fwd_c
        ):
            continue

        selected_xi = (
            by_pos["GK"][:gk_c]
            + by_pos["DEF"][:def_c]
            + by_pos["MID"][:mid_c]
            + by_pos["FWD"][:fwd_c]
        )

        score = sum(pts.get(pid, 0.0) for pid in selected_xi)
        if score > best_score:
            best_score = score
            best_xi = selected_xi

    # Fallback to CSP solver if simple formation iteration didn't find one
    if not best_xi:
        csp = create_lineup_formation_csp(positions, config)
        sol = backtracking_search(csp, select_unassigned_variable=mrv_heuristic)
        if sol:
            best_xi = list(sol.values())
        else:
            # Emergency fallback: pick first 11
            best_xi = list(positions.keys())[: config.starting_xi_size]

    # Bench: remaining 4 players
    starting_set = set(best_xi)
    bench_gk = [p for p in by_pos["GK"] if p not in starting_set]
    bench_outfield = [
        p for p in (by_pos["DEF"] + by_pos["MID"] + by_pos["FWD"])
        if p not in starting_set
    ]
    # Bench outfield sorted by expected points descending
    bench_outfield.sort(key=lambda pid: pts.get(pid, 0.0), reverse=True)
    bench = tuple(bench_gk + bench_outfield)

    # Captain and Vice-Captain: highest and second-highest predicted starters
    sorted_xi_by_pts = sorted(best_xi, key=lambda pid: pts.get(pid, 0.0), reverse=True)
    captain = sorted_xi_by_pts[0]
    vice_captain = sorted_xi_by_pts[1] if len(sorted_xi_by_pts) > 1 else captain

    return Lineup(
        starting_xi=tuple(best_xi),
        bench=bench,
        captain=captain,
        vice_captain=vice_captain,
    )

