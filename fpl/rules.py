"""Official FPL rules and constraint validation engine.

Every rule value (budget, squad size, club limit, transfer hits, formation boundaries,
chips) is fully configurable via `FPLRulesConfig`. Never hard-coded.
Authority: Official Premier League FPL rules (2026/27).
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Collection, Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class FPLRulesConfig:
    """Configurable FPL rules parameters.

    All defaults follow the official Premier League 2026/27 rules.
    """

    # Squad limits
    budget: float = 100.0
    squad_size: int = 15
    starting_xi_size: int = 11
    bench_size: int = 4
    max_players_per_club: int = 3

    # Position quotas in 15-player squad
    squad_gk_count: int = 2
    squad_def_count: int = 5
    squad_mid_count: int = 5
    squad_fwd_count: int = 3

    # Lineup formation limits (for starting XI)
    lineup_gk: int = 1
    lineup_min_def: int = 3
    lineup_max_def: int = 5
    lineup_min_mid: int = 2
    lineup_max_mid: int = 5
    lineup_min_fwd: int = 1
    lineup_max_fwd: int = 3

    # Transfers and hits
    transfer_hit_cost: float = 4.0
    max_free_transfers: int = 5  # Saved FTs cap (official 2024/25+ & 2026/27 rule)
    initial_free_transfers: int = 1
    free_transfers_per_gw: int = 1

    # Captaincy multipliers
    captain_multiplier: float = 2.0
    triple_captain_multiplier: float = 3.0

    # Pricing defaults
    default_player_price: float = 5.0

    # Chips
    valid_chips: frozenset[str] = field(
        default_factory=lambda: frozenset({"Wildcard", "FreeHit", "TripleCaptain", "BenchBoost"})
    )
    chip_limit_per_season: int = 1


DEFAULT_CONFIG = FPLRulesConfig()


def is_valid_formation(
    gk: int,
    def_: int,
    mid: int,
    fwd: int,
    config: FPLRulesConfig = DEFAULT_CONFIG,
) -> bool:
    """Check whether a positional combination (GK, DEF, MID, FWD) forms a valid starting XI."""
    total = gk + def_ + mid + fwd
    if total != config.starting_xi_size:
        return False
    if gk != config.lineup_gk:
        return False
    if not (config.lineup_min_def <= def_ <= config.lineup_max_def):
        return False
    if not (config.lineup_min_mid <= mid <= config.lineup_max_mid):
        return False
    if not (config.lineup_min_fwd <= fwd <= config.lineup_max_fwd):
        return False
    return True


def get_valid_formations(config: FPLRulesConfig = DEFAULT_CONFIG) -> list[tuple[int, int, int, int]]:
    """Return all valid (GK, DEF, MID, FWD) combinations for starting XI."""
    valid: list[tuple[int, int, int, int]] = []
    gk = config.lineup_gk
    for d in range(config.lineup_min_def, config.lineup_max_def + 1):
        for m in range(config.lineup_min_mid, config.lineup_max_mid + 1):
            for f in range(config.lineup_min_fwd, config.lineup_max_fwd + 1):
                if is_valid_formation(gk, d, m, f, config):
                    valid.append((gk, d, m, f))
    return sorted(valid)


def validate_squad(
    squad: Sequence[Any],
    config: FPLRulesConfig = DEFAULT_CONFIG,
) -> tuple[bool, list[str]]:
    """Validate that a squad satisfies all FPL squad composition rules.

    Each item in squad can be a Player dataclass, dict, or tuple/object with:
    - player_id
    - position ("GK", "DEF", "MID", "FWD")
    - price / cost (float)
    - team / club (str or int)
    """
    errors: list[str] = []

    if len(squad) != config.squad_size:
        errors.append(f"Squad size must be {config.squad_size}, got {len(squad)}.")

    # Extract attributes safely
    player_ids: list[str] = []
    positions: list[str] = []
    clubs: list[str] = []
    total_cost: float = 0.0

    for idx, p in enumerate(squad):
        if hasattr(p, "player_id"):
            pid = str(p.player_id)
            pos = getattr(p, "position", "")
            cost = getattr(p, "price", getattr(p, "cost", 0.0))
            club = str(getattr(p, "team", getattr(p, "club", getattr(p, "team_id", ""))))
        elif isinstance(p, dict):
            pid = str(p.get("player_id", idx))
            pos = p.get("position", "")
            cost = p.get("price", p.get("cost", 0.0))
            club = str(p.get("team", p.get("club", p.get("team_id", ""))))
        elif isinstance(p, (tuple, list)) and len(p) >= 2:
            pid = str(p[0])
            pos = str(p[1])
            cost = float(p[2]) if len(p) > 2 else 0.0
            club = str(p[3]) if len(p) > 3 else ""
        else:
            pid = str(p)
            pos = ""
            cost = 0.0
            club = ""

        player_ids.append(pid)
        positions.append(pos)
        clubs.append(club)
        total_cost += float(cost)

    # 1. Uniqueness check
    if len(player_ids) != len(set(player_ids)):
        duplicates = [pid for pid, count in Counter(player_ids).items() if count > 1]
        errors.append(f"Duplicate players found in squad: {duplicates}")

    # 2. Position quota check
    pos_counts = Counter(positions)
    if pos_counts.get("GK", 0) != config.squad_gk_count:
        errors.append(f"Expected {config.squad_gk_count} GKs, got {pos_counts.get('GK', 0)}.")
    if pos_counts.get("DEF", 0) != config.squad_def_count:
        errors.append(f"Expected {config.squad_def_count} DEFs, got {pos_counts.get('DEF', 0)}.")
    if pos_counts.get("MID", 0) != config.squad_mid_count:
        errors.append(f"Expected {config.squad_mid_count} MIDs, got {pos_counts.get('MID', 0)}.")
    if pos_counts.get("FWD", 0) != config.squad_fwd_count:
        errors.append(f"Expected {config.squad_fwd_count} FWDs, got {pos_counts.get('FWD', 0)}.")

    # 3. Budget check
    if round(total_cost, 2) > round(config.budget, 2):
        errors.append(f"Total squad cost £{total_cost:.1f}m exceeds budget £{config.budget:.1f}m.")

    # 4. Club limit check
    non_empty_clubs = [c for c in clubs if c]
    club_counts = Counter(non_empty_clubs)
    for club_name, count in club_counts.items():
        if count > config.max_players_per_club:
            errors.append(
                f"Club limit exceeded for '{club_name}': {count} players (max {config.max_players_per_club})."
            )

    return (len(errors) == 0, errors)


def validate_lineup(
    starting_xi: Sequence[str],
    captain: str,
    vice_captain: str,
    squad_positions: Mapping[str, str],
    config: FPLRulesConfig = DEFAULT_CONFIG,
) -> tuple[bool, list[str]]:
    """Validate that a starting XI, captain, and vice-captain satisfy FPL formation rules.

    Parameters
    ----------
    starting_xi : Sequence of player_id strings
        The 11 starting players.
    captain : str
        The chosen captain player_id.
    vice_captain : str
        The chosen vice-captain player_id.
    squad_positions : Mapping of {player_id: position}
        Known position mapping for squad members.
    config : FPLRulesConfig
        Rules configuration.
    """
    errors: list[str] = []

    # 1. Size check
    if len(starting_xi) != config.starting_xi_size:
        errors.append(f"Starting XI must contain {config.starting_xi_size} players, got {len(starting_xi)}.")

    # 2. Player uniqueness
    xi_ids = [str(pid) for pid in starting_xi]
    if len(xi_ids) != len(set(xi_ids)):
        errors.append("Duplicate players in starting XI.")

    # 3. Formation check
    pos_counts: Counter[str] = Counter()
    for pid in xi_ids:
        pos = squad_positions.get(pid)
        if pos is None:
            errors.append(f"Unknown position for starting XI player '{pid}'.")
        else:
            pos_counts[pos] += 1

    gk = pos_counts.get("GK", 0)
    def_ = pos_counts.get("DEF", 0)
    mid = pos_counts.get("MID", 0)
    fwd = pos_counts.get("FWD", 0)

    if not is_valid_formation(gk, def_, mid, fwd, config):
        errors.append(
            f"Invalid formation: {gk} GK, {def_} DEF, {mid} MID, {fwd} FWD. "
            f"Must be {config.lineup_gk} GK, {config.lineup_min_def}-{config.lineup_max_def} DEF, "
            f"{config.lineup_min_mid}-{config.lineup_max_mid} MID, {config.lineup_min_fwd}-{config.lineup_max_fwd} FWD."
        )

    # 4. Captaincy checks
    cap_str = str(captain)
    vc_str = str(vice_captain)

    if cap_str not in xi_ids:
        errors.append(f"Captain '{cap_str}' is not in the starting XI.")
    if vc_str not in xi_ids:
        errors.append(f"Vice-captain '{vc_str}' is not in the starting XI.")
    if cap_str == vc_str:
        errors.append("Captain and vice-captain must be different players.")

    return (len(errors) == 0, errors)


def validate_chip(
    chip_name: str,
    chips_used: Collection[str],
    config: FPLRulesConfig = DEFAULT_CONFIG,
) -> tuple[bool, list[str]]:
    """Validate chip usage rules."""
    errors: list[str] = []
    if chip_name not in config.valid_chips:
        errors.append(f"Unknown chip '{chip_name}'. Valid chips are: {sorted(list(config.valid_chips))}.")
    else:
        used_count = sum(1 for c in chips_used if c == chip_name)
        if used_count >= config.chip_limit_per_season:
            errors.append(
                f"Chip '{chip_name}' has reached its season limit of {config.chip_limit_per_season} "
                f"(used {used_count} times)."
            )
    return (len(errors) == 0, errors)


def auto_substitute(
    starting_xi: Sequence[str],
    bench: Sequence[str],
    player_positions: Mapping[str, str],
    player_minutes: Mapping[str, float],
    config: FPLRulesConfig = DEFAULT_CONFIG,
) -> tuple[list[str], list[tuple[str, str]]]:
    """Execute official FPL automatic substitutions when starting players play 0 minutes.

    Rules:
    - If starting GK plays 0 minutes, substitute bench GK (if bench GK played > 0 minutes).
    - For outfield starters who played 0 minutes:
        Traverse the outfield bench players in priority order (sub 1, sub 2, sub 3).
        A substitute is brought on if they played > 0 minutes and the resulting XI formation
        remains legal (>=3 DEF, >=2 MID, >=1 FWD).
    - Each bench player can be used at most once.

    Returns
    -------
    final_xi : list[str]
        The starting XI after all legal auto-substitutions.
    substitutions_made : list[tuple[str, str]]
        List of (player_out, player_in) substitutions.
    """
    final_xi = [str(p) for p in starting_xi]
    bench_list = [str(p) for p in bench]
    subs_made: list[tuple[str, str]] = []

    def played(pid: str) -> bool:
        return player_minutes.get(pid, 0.0) > 0

    # 1. Goalkeeper substitution
    gks_in_xi = [p for p in final_xi if player_positions.get(p) == "GK"]
    bench_gks = [p for p in bench_list if player_positions.get(p) == "GK"]

    if gks_in_xi and not played(gks_in_xi[0]) and bench_gks and played(bench_gks[0]):
        out_gk = gks_in_xi[0]
        in_gk = bench_gks[0]
        final_xi[final_xi.index(out_gk)] = in_gk
        subs_made.append((out_gk, in_gk))

    # 2. Outfield substitutions
    # Outfield bench players maintain their priority order (sub 1, sub 2, sub 3)
    available_bench_outfield = [
        p for p in bench_list
        if player_positions.get(p) != "GK" and played(p) and p not in [s[1] for s in subs_made]
    ]

    outfield_unplayed = [
        p for p in final_xi
        if player_positions.get(p) != "GK" and not played(p)
    ]

    for unplayed_starter in outfield_unplayed:
        for candidate_sub in list(available_bench_outfield):
            # Test candidate substitution for formation legality
            test_xi = list(final_xi)
            test_xi[test_xi.index(unplayed_starter)] = candidate_sub

            counts: Counter[str] = Counter(player_positions.get(p, "") for p in test_xi)
            if is_valid_formation(
                counts.get("GK", 0),
                counts.get("DEF", 0),
                counts.get("MID", 0),
                counts.get("FWD", 0),
                config,
            ):
                # Valid substitution
                final_xi[final_xi.index(unplayed_starter)] = candidate_sub
                subs_made.append((unplayed_starter, candidate_sub))
                available_bench_outfield.remove(candidate_sub)
                break

    return final_xi, subs_made


def resolve_captain(
    captain: str,
    vice_captain: str,
    player_minutes: Mapping[str, float],
    chip_name: str | None = None,
    config: FPLRulesConfig = DEFAULT_CONFIG,
) -> tuple[str, float]:
    """Resolve the active captain and multiplier.

    - If captain plays > 0 minutes: captain gets multiplier.
    - Else if vice_captain plays > 0 minutes: vice_captain gets multiplier.
    - Else: captain retained with 1.0 multiplier (no bonus).
    - If TripleCaptain chip active: multiplier is 3.0 (configurable).
    """
    base_mult = (
        config.triple_captain_multiplier
        if chip_name == "TripleCaptain"
        else config.captain_multiplier
    )

    cap_str = str(captain)
    vc_str = str(vice_captain)

    if player_minutes.get(cap_str, 0.0) > 0:
        return cap_str, base_mult
    elif player_minutes.get(vc_str, 0.0) > 0:
        return vc_str, base_mult
    else:
        return cap_str, 1.0


def calculate_transfer_hits(
    num_transfers: int,
    free_transfers: int,
    chip_name: str | None = None,
    config: FPLRulesConfig = DEFAULT_CONFIG,
) -> tuple[int, float]:
    """Calculate the number of hits and points deducted for transfers.

    Wildcard and FreeHit chips provide unlimited free transfers (0 hit cost).
    """
    if chip_name in ("Wildcard", "FreeHit"):
        return (0, 0.0)

    hits = max(0, num_transfers - free_transfers)
    hit_cost = hits * config.transfer_hit_cost
    return (hits, hit_cost)

