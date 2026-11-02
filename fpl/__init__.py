"""NextGW FPL module: Official FPL rules and Constraint Satisfaction Problem (CSP) models."""

from .csp import (
    CSP,
    AllDifferentConstraint,
    BinaryConstraint,
    Constraint,
    CountConstraint,
    FunctionalConstraint,
    SumConstraint,
    UnaryConstraint,
    ac3,
    backtracking_search,
    first_unassigned_variable,
    forward_checking,
    lcv_heuristic,
    min_conflicts,
    mrv_heuristic,
    unordered_domain_values,
)
from .lineup import (
    Lineup,
    create_lineup_formation_csp,
    solve_optimal_lineup,
)
from .rules import (
    DEFAULT_CONFIG,
    FPLRulesConfig,
    auto_substitute,
    calculate_transfer_hits,
    get_valid_formations,
    is_valid_formation,
    resolve_captain,
    validate_chip,
    validate_lineup,
    validate_squad,
)
from .squad import (
    Player,
    Squad,
    create_squad_selection_csp,
    solve_squad,
)
from .transfers import (
    generate_candidate_plans,
    transition_fn,
    validate_transfers,
)

__all__ = [
    # Rules & Config
    "DEFAULT_CONFIG",
    "FPLRulesConfig",
    "is_valid_formation",
    "get_valid_formations",
    "validate_squad",
    "validate_lineup",
    "validate_chip",
    "auto_substitute",
    "resolve_captain",
    "calculate_transfer_hits",
    # CSP Core
    "CSP",
    "Constraint",
    "UnaryConstraint",
    "BinaryConstraint",
    "AllDifferentConstraint",
    "SumConstraint",
    "CountConstraint",
    "FunctionalConstraint",
    "ac3",
    "forward_checking",
    "mrv_heuristic",
    "lcv_heuristic",
    "first_unassigned_variable",
    "unordered_domain_values",
    "backtracking_search",
    "min_conflicts",
    # Squad
    "Player",
    "Squad",
    "create_squad_selection_csp",
    "solve_squad",
    # Lineup
    "Lineup",
    "create_lineup_formation_csp",
    "solve_optimal_lineup",
    # Transfers & State Transition
    "validate_transfers",
    "transition_fn",
    "generate_candidate_plans",
]

