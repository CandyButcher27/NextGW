"""Constraint Satisfaction Problem (CSP) framework and FPL CSP models.

Implements standard AI CSP representations, arc consistency (AC-3), backtracking search
with MRV (Minimum Remaining Values), Degree heuristic, LCV (Least Constraining Value),
forward checking, and local search (Min-Conflicts), alongside specialized CSP formulations
for FPL squad selection and formation lineup.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections import defaultdict
from collections.abc import Callable, Sequence
import copy
import random
from typing import Any, Generic, TypeVar

T = TypeVar("T")


class Constraint(ABC):
    """Abstract base class for all constraints in a CSP."""

    def __init__(self, variables: Sequence[str]) -> None:
        self.variables: tuple[str, ...] = tuple(variables)

    @abstractmethod
    def is_satisfied(self, assignment: dict[str, Any]) -> bool:
        """Return True if the assignment satisfies this constraint.

        If some variables in the constraint's scope are not yet assigned,
        the constraint should return True (partial assignments are optimistic).
        """
        ...


class UnaryConstraint(Constraint):
    """A constraint on a single variable."""

    def __init__(self, var: str, predicate: Callable[[Any], bool]) -> None:
        super().__init__([var])
        self.var: str = var
        self.predicate: Callable[[Any], bool] = predicate

    def is_satisfied(self, assignment: dict[str, Any]) -> bool:
        if self.var not in assignment:
            return True
        return self.predicate(assignment[self.var])


class BinaryConstraint(Constraint):
    """A constraint between two variables."""

    def __init__(self, var1: str, var2: str, predicate: Callable[[Any, Any], bool]) -> None:
        super().__init__([var1, var2])
        self.var1: str = var1
        self.var2: str = var2
        self.predicate: Callable[[Any, Any], bool] = predicate

    def is_satisfied(self, assignment: dict[str, Any]) -> bool:
        if self.var1 not in assignment or self.var2 not in assignment:
            return True
        return self.predicate(assignment[self.var1], assignment[self.var2])


class AllDifferentConstraint(Constraint):
    """Ensures all assigned variables in the scope have unique values."""

    def __init__(self, variables: Sequence[str]) -> None:
        super().__init__(variables)

    def is_satisfied(self, assignment: dict[str, Any]) -> bool:
        assigned_vals = [assignment[v] for v in self.variables if v in assignment]
        return len(assigned_vals) == len(set(assigned_vals))


class SumConstraint(Constraint):
    """Ensures the sum of values (or a mapped property) does not exceed max_sum."""

    def __init__(
        self,
        variables: Sequence[str],
        max_sum: float,
        value_fn: Callable[[Any], float] | None = None,
        exact: bool = False,
    ) -> None:
        super().__init__(variables)
        self.max_sum: float = max_sum
        self.value_fn: Callable[[Any], float] = value_fn or (lambda x: float(x))
        self.exact: bool = exact

    def is_satisfied(self, assignment: dict[str, Any]) -> bool:
        current_sum = sum(self.value_fn(assignment[v]) for v in self.variables if v in assignment)
        if self.exact:
            # If all assigned, must equal max_sum; if partially assigned, must not exceed max_sum
            all_assigned = all(v in assignment for v in self.variables)
            if all_assigned:
                return abs(current_sum - self.max_sum) < 1e-6
            return current_sum <= self.max_sum + 1e-6
        return current_sum <= self.max_sum + 1e-6


class CountConstraint(Constraint):
    """Ensures the count of variables satisfying a predicate falls within [min_count, max_count]."""

    def __init__(
        self,
        variables: Sequence[str],
        predicate: Callable[[Any], bool],
        min_count: int,
        max_count: int,
    ) -> None:
        super().__init__(variables)
        self.predicate: Callable[[Any], bool] = predicate
        self.min_count: int = min_count
        self.max_count: int = max_count

    def is_satisfied(self, assignment: dict[str, Any]) -> bool:
        assigned = [assignment[v] for v in self.variables if v in assignment]
        count = sum(1 for val in assigned if self.predicate(val))
        if count > self.max_count:
            return False
        # If all variables in scope are assigned, verify lower bound
        if len(assigned) == len(self.variables):
            return count >= self.min_count
        # Even if all unassigned variables matched the predicate, could we reach min_count?
        unassigned_count = len(self.variables) - len(assigned)
        return (count + unassigned_count) >= self.min_count


class FunctionalConstraint(Constraint):
    """Arbitrary callable constraint over a scope of variables."""

    def __init__(self, variables: Sequence[str], predicate: Callable[[dict[str, Any]], bool]) -> None:
        super().__init__(variables)
        self.predicate: Callable[[dict[str, Any]], bool] = predicate

    def is_satisfied(self, assignment: dict[str, Any]) -> bool:
        return self.predicate(assignment)


class CSP:
    """Representation of a Constraint Satisfaction Problem."""

    def __init__(
        self,
        variables: Sequence[str] | None = None,
        domains: dict[str, list[Any]] | None = None,
    ) -> None:
        self.variables: list[str] = list(variables) if variables else []
        self.domains: dict[str, list[Any]] = {
            v: list(domains[v]) for v in self.variables
        } if domains else {}
        self.constraints: list[Constraint] = []
        self.var_constraints: dict[str, list[Constraint]] = defaultdict(list)
        self.neighbors: dict[str, set[str]] = defaultdict(set)

    def add_variable(self, var: str, domain: Sequence[Any]) -> None:
        """Add a variable with its initial domain."""
        if var not in self.variables:
            self.variables.append(var)
        self.domains[var] = list(domain)

    def add_constraint(self, constraint: Constraint) -> None:
        """Register a constraint in the CSP and update variable adjacency."""
        self.constraints.append(constraint)
        for var in constraint.variables:
            self.var_constraints[var].append(constraint)
            for other in constraint.variables:
                if var != other:
                    self.neighbors[var].add(other)

    def is_consistent(self, var: str, val: Any, assignment: dict[str, Any]) -> bool:
        """Check if assigning val to var satisfies all relevant constraints."""
        assignment[var] = val
        consistent = True
        for constraint in self.var_constraints[var]:
            if not constraint.is_satisfied(assignment):
                consistent = False
                break
        del assignment[var]
        return consistent

    def is_complete(self, assignment: dict[str, Any]) -> bool:
        """Check if all variables have been assigned consistently."""
        if len(assignment) != len(self.variables):
            return False
        return all(c.is_satisfied(assignment) for c in self.constraints)

    def nconflicts(self, var: str, val: Any, assignment: dict[str, Any]) -> int:
        """Count the number of constraints violated by assigning var = val."""
        assignment[var] = val
        conflicts = sum(1 for c in self.var_constraints[var] if not c.is_satisfied(assignment))
        del assignment[var]
        return conflicts


# --- Variable and Value Selection Heuristics ---

def mrv_heuristic(csp: CSP, assignment: dict[str, Any]) -> str:
    """Minimum Remaining Values (MRV) heuristic with Degree Heuristic tie-breaking."""
    unassigned = [v for v in csp.variables if v not in assignment]
    
    def key_fn(var: str) -> tuple[int, int]:
        # Count legal values in domain given current assignment
        legal_count = sum(1 for val in csp.domains[var] if csp.is_consistent(var, val, assignment))
        # Degree heuristic: number of unassigned neighbors (negated for max)
        unassigned_neighbors = sum(1 for n in csp.neighbors[var] if n not in assignment)
        return (legal_count, -unassigned_neighbors)

    return min(unassigned, key=key_fn)


def first_unassigned_variable(csp: CSP, assignment: dict[str, Any]) -> str:
    """Select the first unassigned variable in canonical order."""
    for v in csp.variables:
        if v not in assignment:
            return v
    raise ValueError("All variables are assigned.")


def lcv_heuristic(csp: CSP, var: str, assignment: dict[str, Any]) -> list[Any]:
    """Least Constraining Value (LCV) heuristic.

    Sorts values by how few options they rule out for neighboring variables.
    """
    def count_conflicts(val: Any) -> int:
        assignment[var] = val
        conflicts = 0
        for neighbor in csp.neighbors[var]:
            if neighbor not in assignment:
                for n_val in csp.domains[neighbor]:
                    if not csp.is_consistent(neighbor, n_val, assignment):
                        conflicts += 1
        del assignment[var]
        return conflicts

    return sorted(csp.domains[var], key=count_conflicts)


def unordered_domain_values(csp: CSP, var: str, assignment: dict[str, Any]) -> list[Any]:
    """Return domain values in their original order."""
    return list(csp.domains[var])


# --- Inference: AC-3 and Forward Checking ---

def ac3(csp: CSP, queue: list[tuple[str, str]] | None = None) -> bool:
    """Arc Consistency Algorithm #3 (AC-3).

    Enforces arc consistency across all binary constraints in the CSP.
    Returns False if an empty domain is detected (inconsistency), True otherwise.
    """
    if queue is None:
        queue = [
            (xi, xj)
            for xi in csp.variables
            for xj in csp.neighbors[xi]
        ]

    while queue:
        xi, xj = queue.pop(0)
        if _revise(csp, xi, xj):
            if len(csp.domains[xi]) == 0:
                return False
            for xk in csp.neighbors[xi]:
                if xk != xj:
                    queue.append((xk, xi))
    return True


def _revise(csp: CSP, xi: str, xj: str) -> bool:
    """Revise domain of xi to satisfy arc consistency with xj."""
    revised = False
    to_remove = []
    
    # Binary constraints between xi and xj
    relevant_constraints = [
        c for c in csp.var_constraints[xi]
        if xj in c.variables and len(c.variables) == 2
    ]
    if not relevant_constraints:
        return False

    for x in csp.domains[xi]:
        # Check if there exists some y in D(xj) satisfying all constraints between xi and xj
        satisfiable = False
        for y in csp.domains[xj]:
            test_assignment = {xi: x, xj: y}
            if all(c.is_satisfied(test_assignment) for c in relevant_constraints):
                satisfiable = True
                break
        if not satisfiable:
            to_remove.append(x)
            revised = True

    for val in to_remove:
        csp.domains[xi].remove(val)
    return revised


def forward_checking(
    csp: CSP,
    var: str,
    val: Any,
    assignment: dict[str, Any],
    removals: list[tuple[str, Any]],
) -> bool:
    """Forward checking: prune inconsistent values from domains of unassigned neighbors."""
    for neighbor in csp.neighbors[var]:
        if neighbor not in assignment:
            for n_val in list(csp.domains[neighbor]):
                if not csp.is_consistent(neighbor, n_val, assignment):
                    csp.domains[neighbor].remove(n_val)
                    removals.append((neighbor, n_val))
            if not csp.domains[neighbor]:
                return False
    return True


# --- Solvers ---

def backtracking_search(
    csp: CSP,
    select_unassigned_variable: Callable[[CSP, dict[str, Any]], str] = mrv_heuristic,
    order_domain_values: Callable[[CSP, str, dict[str, Any]], list[Any]] = lcv_heuristic,
    inference: Callable[[CSP, str, Any, dict[str, Any], list[tuple[str, Any]]], bool] | None = forward_checking,
    find_all: bool = False,
    max_solutions: int | None = None,
) -> dict[str, Any] | list[dict[str, Any]] | None:
    """Backtracking search with configurable variable ordering, value ordering, and inference.

    Parameters
    ----------
    csp : CSP
        The constraint satisfaction problem to solve.
    select_unassigned_variable : callable
        Heuristic for variable selection (defaults to MRV).
    order_domain_values : callable
        Heuristic for value ordering (defaults to LCV).
    inference : callable or None
        Inference routine (defaults to forward_checking; pass None for simple backtracking).
    find_all : bool
        If True, returns a list of all solutions found (up to max_solutions).
    max_solutions : int or None
        Maximum solutions to find if find_all is True.

    Returns
    -------
    dict or list of dict or None
        Consistent assignment map(s) or None if no solution exists.
    """
    solutions: list[dict[str, Any]] = []

    def backtrack(assignment: dict[str, Any]) -> dict[str, Any] | None:
        if len(assignment) == len(csp.variables):
            if find_all:
                solutions.append(dict(assignment))
                if max_solutions and len(solutions) >= max_solutions:
                    return assignment
                return None
            return assignment

        var = select_unassigned_variable(csp, assignment)
        for val in order_domain_values(csp, var, assignment):
            if csp.is_consistent(var, val, assignment):
                assignment[var] = val
                removals: list[tuple[str, Any]] = []
                
                inferences_ok = True
                if inference is not None:
                    inferences_ok = inference(csp, var, val, assignment, removals)

                if inferences_ok:
                    result = backtrack(assignment)
                    if result is not None and not find_all:
                        return result

                # Undo inferences and assignment
                for rem_var, rem_val in removals:
                    csp.domains[rem_var].append(rem_val)
                del assignment[var]

        return None

    res = backtrack({})
    if find_all:
        return solutions
    return res


def min_conflicts(csp: CSP, max_steps: int = 1000) -> dict[str, Any] | None:
    """Min-Conflicts local search algorithm for CSPs."""
    # Start with a random initial complete assignment
    current: dict[str, Any] = {}
    for var in csp.variables:
        current[var] = random.choice(csp.domains[var])

    for _ in range(max_steps):
        conflicted = [
            var for var in csp.variables
            if any(not c.is_satisfied(current) for c in csp.var_constraints[var])
        ]
        if not conflicted:
            return current

        var = random.choice(conflicted)
        # Pick value that minimizes conflicts
        best_val = min(csp.domains[var], key=lambda val: csp.nconflicts(var, val, current))
        current[var] = best_val

    return None
