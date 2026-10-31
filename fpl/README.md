# FPL Module — Rules, Constraints & CSP Framework

This module implements the **Fantasy Premier League (FPL) Rules** and a **Constraint Satisfaction Problem (CSP)** engine for **NextGW**. It enforces official Premier League 2026/27 constraints on squads, formations, transfers, chips, and automatic substitutions, and provides state transitions for multi-Gameweek planning and backtesting.

---

## Architecture Overview

```
fpl/
├── __init__.py      # Public exports for rules, CSP, squad, lineup, and transfers
├── csp.py           # General CSP engine (Variables, Domains, Constraints, AC-3, Backtracking, Min-Conflicts)
├── rules.py         # Official FPL rules specification, validation, auto-subs, and scoring rules
├── squad.py         # Squad representation, club/budget quotas, and CSP squad selection
├── lineup.py        # Starting XI formation solver, CSP lineup model, and captaincy logic
├── transfers.py     # Transfer validation, candidate plan generation, and PlanningState transition_fn
└── README.md        # Module documentation
```

---

## 1. Constraint Satisfaction Problem (CSP) Framework (`fpl/csp.py`)

A pure-Python implementation of classical AI CSP concepts based on Russell & Norvig (*Artificial Intelligence: A Modern Approach*, Chapter 6):

### Constraints
- **`UnaryConstraint`**: Single-variable predicates.
- **`BinaryConstraint`**: Two-variable relations.
- **`AllDifferentConstraint`**: Enforces pairwise distinct values across assigned variables.
- **`SumConstraint`**: Upper-bound / exact sum constraints (e.g., total price $\le$ budget).
- **`CountConstraint`**: Positional count boundaries (e.g., min/max DEF in lineup).
- **`FunctionalConstraint`**: Arbitrary multi-variable constraint evaluation (e.g., max 3 players per club).

### Algorithms & Heuristics
- **AC-3 (`ac3`)**: Arc consistency algorithm that prunes impossible domain values across binary constraints before or during search.
- **Forward Checking (`forward_checking`)**: Prunes inconsistent values from domains of unassigned neighbor variables during backtracking.
- **MRV (`mrv_heuristic`)**: Minimum Remaining Values variable selection, with Degree Heuristic tie-breaking.
- **LCV (`lcv_heuristic`)**: Least Constraining Value value ordering.
- **Backtracking Search (`backtracking_search`)**: Configurable search supporting single-solution finding or enumeration of all solutions (`find_all=True`).
- **Local Search (`min_conflicts`)**: Min-Conflicts heuristic search for large constraint satisfaction instances.

---

## 2. Official FPL Rules Engine (`fpl/rules.py`)

Every rule parameter is configurable via `FPLRulesConfig` with official 2026/27 defaults (never hard-coded):

- **Squad Composition:**
  - 15 players: 2 Goalkeepers (GK), 5 Defenders (DEF), 5 Midfielders (MID), 3 Forwards (FWD).
  - Maximum 3 players from any single Premier League club (`max_players_per_club = 3`).
  - Total squad cost must not exceed budget (`budget = 100.0m`).
- **Starting XI & Legal Formations:**
  - Exactly 11 starters: 1 GK, between 3 and 5 DEF, between 2 and 5 MID, between 1 and 3 FWD.
  - The 8 valid formations are strictly enforced: `3-5-2`, `3-4-3`, `4-4-2`, `4-3-3`, `4-5-1`, `5-4-1`, `5-3-2`, `5-2-3`.
  - Distinct Captain (2x multiplier) and Vice-Captain selected from the Starting XI.
- **Automatic Substitutions (`auto_substitute`):**
  - If starting GK plays 0 minutes, replaced by the bench GK (if bench GK played).
  - Unplayed outfield starters are replaced by bench outfielders in priority order (sub 1, sub 2, sub 3) **only if** the substitution maintains a legal formation (min 3 DEF, min 2 MID, min 1 FWD).
- **Chips:**
  - `Wildcard`: Unlimited free transfers for that GW; 0 hit cost.
  - `FreeHit`: Unlimited free transfers for that GW; squad reverts back to pre-FreeHit squad at next GW.
  - `TripleCaptain`: Captain multiplier increases to 3.0x (`triple_captain_multiplier = 3.0`).
  - `BenchBoost`: Points from all 4 bench players are counted.
- **Transfer Hits (`calculate_transfer_hits`):**
  - Transfers beyond available Free Transfers deduct 4 points each (`transfer_hit_cost = 4.0`).
  - 0 hit cost when Wildcard or Free Hit is active.

---

## 3. Squad Management (`fpl/squad.py`)

- **`Player` Dataclass:** `player_id`, `name`, `position` ("GK", "DEF", "MID", "FWD"), `team`, `price`, `status`.
- **`Squad` Class:** Manages the 15-player squad, validates rules, and provides bidirectional conversion to/from the `PlanningState.squad` sorted tuple `((player_id, position), ...)`.
- **`create_squad_selection_csp` & `solve_squad`:** Formulates and solves 15-player squad selection as a CSP satisfying all position quotas, budget limits, and club constraints.

---

## 4. Lineup & Formation Optimization (`fpl/lineup.py`)

- **`Lineup` Dataclass:** Holds Starting XI (11), Bench (4: sub GK + 3 ordered outfielders), Captain, Vice-Captain, and optional Chip.
- **`to_action()`:** Converts to `planning.actions.LineupAction` for search integration.
- **`create_lineup_formation_csp`:** Formulates Starting XI selection from the 15 squad players as a CSP.
- **`solve_optimal_lineup`:** Evaluates all valid formations to find the Starting XI that maximizes expected points, selects the top-scoring player as Captain, second-highest as Vice-Captain, and orders the bench.

---

## 5. Transfers & State Transitions (`fpl/transfers.py`)

- **`validate_transfers`:** Verifies outgoing players are in squad, incoming players are not duplicates, club limits are respected, and new squad remains within budget.
- **`transition_fn(state: PlanningState, plan: GWPlan) -> PlanningState`:**
  - Advances Gameweek by 1 (`state.gameweek + 1`) to satisfy `PlanningSearch` and `backtesting.simulator.simulate`.
  - Updates squad and remaining bank budget.
  - Accumulates and rolls Free Transfers according to official 2024/25+ & 2026/27 rules:
    - Managers can save up to 5 Free Transfers (`max_free_transfers = 5`).
    - Free Transfers are **not** lost when playing Wildcard or Free Hit.
  - Records used chips in `chips_used`.
  - Reverts squad and budget at the next Gameweek when `FreeHit` is active.
- **`generate_candidate_plans`:** Generates legal candidate actions (0-transfer / banked FT, 1-transfer moves) for beam search in `planning.search`.

---

## 6. Test Suite (`tests/test_fpl_*.py`)

31 tests covering all rules and CSP components:
- `tests/test_fpl_csp.py`: Map coloring CSP, AC-3 consistency, all-different, sum, count constraints, and multi-solution search.
- `tests/test_fpl_rules.py`: All 8 valid formations, invalid formations, squad budget/club limit checks, lineup captaincy, auto-subs formation preservation, captaincy resolution, and transfer hits.
- `tests/test_fpl_squad.py`: Squad properties, state tuple round-trip conversion, and CSP squad selection solver.
- `tests/test_fpl_lineup.py`: Formation CSP, optimal lineup solver maximizing expected points, captain/vice-captain assignment, and bench order.
- `tests/test_fpl_transfers.py`: Transfer validation, transition function Gameweek progression, budget updates, 5 FT cap banking, chip handling, Free Hit reversion, and `PlanningSearch` integration.

### Running Tests
```bash
# With uv / pytest
uv run pytest tests/test_fpl_* -v

# Or with standard Python unittest
python -m unittest discover -s tests -p "test_fpl_*.py" -v
```

