"""FPL transfer rules, candidate plan generation, and PlanningState transition function."""

from __future__ import annotations

from collections import Counter
from collections.abc import Mapping, Sequence
from typing import Any

from planning.actions import GWPlan, LineupAction, TransferAction
from planning.state import PlanningState

from .lineup import solve_optimal_lineup
from .rules import (
    DEFAULT_CONFIG,
    FPLRulesConfig,
    calculate_transfer_hits,
    validate_chip,
    validate_squad,
)
from .squad import Player, Squad


def validate_transfers(
    current_squad: Squad | Sequence[Any],
    transfers: Sequence[TransferAction],
    bank: float = 0.0,
    config: FPLRulesConfig = DEFAULT_CONFIG,
    player_registry: Mapping[str, Player] | None = None,
) -> tuple[bool, list[str]]:
    """Validate that a proposed list of transfers leads to a legal squad and respects budget.

    Parameters
    ----------
    current_squad : Squad or Sequence of Players
        The existing 15-player squad before transfers.
    transfers : Sequence of TransferAction
        List of player_out -> player_in transfers.
    bank : float
        Current money in the bank.
    config : FPLRulesConfig
        Rules configuration.
    player_registry : Mapping of {player_id: Player}
        Known player metadata for resolving new transfers.
    """
    errors: list[str] = []

    # Parse squad players
    if isinstance(current_squad, Squad):
        squad_players = list(current_squad.players)
    else:
        squad_players = []
        for p in current_squad:
            if isinstance(p, Player):
                squad_players.append(p)
            elif isinstance(p, (tuple, list)) and len(p) >= 2:
                pid, pos = str(p[0]), str(p[1])
                cost = float(p[2]) if len(p) > 2 else 5.0
                team = str(p[3]) if len(p) > 3 else "UNK"
                squad_players.append(Player(pid, pid, pos, team, cost))
            else:
                squad_players.append(Player(str(p), str(p), "MID", "UNK", 5.0))

    squad_map = {p.player_id: p for p in squad_players}
    transferred_out = set()
    transferred_in = set()

    new_squad_players = list(squad_players)

    for t in transfers:
        out_id = str(t.player_out)
        in_id = str(t.player_in)

        # Check player_out exists in squad
        if out_id not in squad_map:
            errors.append(f"Transfer out failed: player '{out_id}' is not in current squad.")
            continue

        if out_id in transferred_out:
            errors.append(f"Player '{out_id}' cannot be transferred out more than once.")

        # Check player_in is not already in squad
        if in_id in squad_map and in_id not in transferred_out:
            errors.append(f"Transfer in failed: player '{in_id}' is already in squad.")

        if in_id in transferred_in:
            errors.append(f"Player '{in_id}' cannot be transferred in more than once.")

        transferred_out.add(out_id)
        transferred_in.add(in_id)

        # Resolve player_in object
        in_player = (
            player_registry.get(in_id)
            if player_registry and in_id in player_registry
            else None
        )
        if in_player is None:
            # Fall back to matching position and price of player_out if unspecified
            out_p = squad_map[out_id]
            in_player = Player(
                player_id=in_id,
                name=in_id,
                position=out_p.position,
                team="UNK",
                price=out_p.price,
            )

        # Apply transfer to squad copy
        for idx, p in enumerate(new_squad_players):
            if p.player_id == out_id:
                new_squad_players[idx] = in_player
                break

    # Validate resulting squad structure
    valid_struct, struct_errors = validate_squad(new_squad_players, config)
    if not valid_struct:
        errors.extend(struct_errors)

    # Budget check including bank
    total_new_cost = sum(p.price for p in new_squad_players)
    available_budget = sum(p.price for p in squad_players) + bank
    if round(total_new_cost, 2) > round(available_budget, 2):
        errors.append(
            f"Transfers exceed available funds: new cost £{total_new_cost:.1f}m > available £{available_budget:.1f}m."
        )

    return (len(errors) == 0, errors)


def transition_fn(
    state: PlanningState,
    plan: GWPlan,
    config: FPLRulesConfig = DEFAULT_CONFIG,
    player_registry: Mapping[str, Player] | None = None,
) -> PlanningState:
    """State transition function for FPL planning and simulation.

    Contract:
        (state: PlanningState, plan: GWPlan) -> PlanningState
    Advances gameweek by 1, applies transfers, updates budget, rolls free transfers,
    and records chip usage.

    Parameters
    ----------
    state : PlanningState
        The current planning state before deadline.
    plan : GWPlan
        The transfers, lineup, and optional chip for the upcoming Gameweek.
    config : FPLRulesConfig
        Rules configuration (defaults to official 2026/27 rules).
    player_registry : Mapping of {player_id: Player}
        Optional player lookup for position and price resolution.
    """
    next_gw = state.gameweek + 1
    chip_name = plan.chip.chip_name if plan.chip else None

    # Parse current squad
    current_squad_list: list[tuple[str, str]] = []
    if isinstance(state.squad, dict):
        current_squad_list = [(str(k), str(v)) for k, v in state.squad.items()]
    elif isinstance(state.squad, (tuple, list)):
        for item in state.squad:
            if isinstance(item, (tuple, list)) and len(item) >= 2:
                current_squad_list.append((str(item[0]), str(item[1])))
            else:
                current_squad_list.append((str(item), "MID"))
    else:
        current_squad_list = list(state.squad)

    squad_dict = dict(current_squad_list)
    new_budget = float(state.budget)

    # Apply transfers if any
    num_transfers = len(plan.transfers) if plan.transfers else 0
    if plan.transfers:
        for t in plan.transfers:
            out_id = str(t.player_out)
            in_id = str(t.player_in)

            # Look up price and position
            out_pos = squad_dict.get(out_id, "MID")
            out_price = (
                player_registry[out_id].price
                if player_registry and out_id in player_registry
                else 5.0
            )

            if player_registry and in_id in player_registry:
                in_player = player_registry[in_id]
                in_pos = in_player.position
                in_price = in_player.price
            else:
                in_pos = out_pos
                in_price = out_price

            # Remove out, add in
            if out_id in squad_dict:
                del squad_dict[out_id]
            squad_dict[in_id] = in_pos

            # Update bank budget
            new_budget = new_budget + out_price - in_price

    # Roll free transfers
    # Official 2024/25+ & 2026/27 rule:
    # 1. Saving up to 5 FTs.
    # 2. Free Transfers are NOT lost when playing Wildcard or Free Hit!
    if chip_name in ("Wildcard", "FreeHit"):
        # FTs carry over and increment
        next_ft = min(config.max_free_transfers, state.free_transfers + config.free_transfers_per_gw)
    else:
        # Normal transfer hit logic
        remaining_ft = max(0, state.free_transfers - num_transfers)
        next_ft = min(config.max_free_transfers, remaining_ft + config.free_transfers_per_gw)

    # Update chips_used
    new_chips_used = set(state.chips_used)
    if chip_name:
        new_chips_used.add(chip_name)

    # FreeHit special handling:
    # Squad changes revert back to pre-FreeHit squad at the next Gameweek
    if chip_name == "FreeHit":
        final_squad_tuple = tuple(sorted(current_squad_list))
        final_budget = state.budget
    else:
        final_squad_tuple = tuple(sorted(squad_dict.items()))
        final_budget = max(0.0, round(new_budget, 2))

    return PlanningState(
        gameweek=next_gw,
        squad=final_squad_tuple,
        budget=final_budget,
        free_transfers=next_ft,
        chips_used=frozenset(new_chips_used),
    )


def generate_candidate_plans(
    state: PlanningState,
    candidate_pool: Sequence[Player] | None = None,
    expected_points: Mapping[str, float] | None = None,
    config: FPLRulesConfig = DEFAULT_CONFIG,
    max_transfers: int = 1,
    top_k_candidates: int = 3,
) -> list[GWPlan]:
    """Generate legal candidate plans for beam search in planning.

    Directly replaces stub `PlanningSearch._get_candidate_plans(state)`.

    Generates:
    - 0-transfer plan (just optimal lineup)
    - 1-transfer plans (transferring out the lowest-scoring squad player for top candidates
      of the same position respecting budget and club limit)

    Parameters
    ----------
    state : PlanningState
        The current planning state.
    candidate_pool : Sequence of Player
        Available players in the transfer market.
    expected_points : Mapping of {player_id: pts}
        Predicted points for the current gameweek.
    config : FPLRulesConfig
        Rules configuration.
    max_transfers : int
        Maximum number of transfers per candidate branch (typically 1 for search efficiency).
    top_k_candidates : int
        Number of top candidate incoming players to consider per position.
    """
    pts = expected_points or {}
    candidates: list[GWPlan] = []

    # Parse current squad
    squad_dict: dict[str, str] = {}
    if isinstance(state.squad, dict):
        squad_dict = {str(k): str(v) for k, v in state.squad.items()}
    elif isinstance(state.squad, (tuple, list)):
        for item in state.squad:
            if isinstance(item, (tuple, list)) and len(item) >= 2:
                squad_dict[str(item[0])] = str(item[1])
            else:
                squad_dict[str(item)] = "MID"

    # 1. Base candidate: 0 transfers (Bank the FT)
    base_lineup = solve_optimal_lineup(squad_dict, pts, config)
    candidates.append(
        GWPlan(
            transfers=[],
            lineup=base_lineup.to_action(),
            chip=None,
        )
    )

    if max_transfers < 1 or not candidate_pool:
        return candidates

    # 2. 1-Transfer candidates
    # Find lowest projected squad players in each position
    squad_by_pos: dict[str, list[str]] = {"GK": [], "DEF": [], "MID": [], "FWD": []}
    for pid, pos in squad_dict.items():
        squad_by_pos.setdefault(pos, []).append(pid)

    pool_by_pos: dict[str, list[Player]] = {"GK": [], "DEF": [], "MID": [], "FWD": []}
    for p in candidate_pool:
        if p.player_id not in squad_dict:
            pool_by_pos.setdefault(p.position, []).append(p)

    # Sort available incoming pool by expected points descending
    for pos in pool_by_pos:
        pool_by_pos[pos].sort(key=lambda p: pts.get(p.player_id, 0.0), reverse=True)

    for pos, squad_pids in squad_by_pos.items():
        if not squad_pids or not pool_by_pos[pos]:
            continue

        # Out candidate: player in squad with lowest expected points
        out_pid = min(squad_pids, key=lambda pid: pts.get(pid, 0.0))

        # Try top K replacements in that position
        for in_player in pool_by_pos[pos][:top_k_candidates]:
            transfer = TransferAction(player_out=out_pid, player_in=in_player.player_id)

            # Test resulting squad lineup
            new_squad = dict(squad_dict)
            del new_squad[out_pid]
            new_squad[in_player.player_id] = pos

            lineup = solve_optimal_lineup(new_squad, pts, config)
            candidates.append(
                GWPlan(
                    transfers=[transfer],
                    lineup=lineup.to_action(),
                    chip=None,
                )
            )

    return candidates
