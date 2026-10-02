from dataclasses import dataclass, field
from typing import Set, Dict

@dataclass(frozen=True)
class PlanningState:
    """
    Represents the full state of an FPL team at a specific Gameweek.
    Frozen to ensure it can be used as a key in search algorithms. Squad is stored as a sorted tuple of (PlayerID, Position) for hashability.
    """
    gameweek: int
    squad: tuple  # PlayerID -> Position (e.g., "GK", "DEF", "MID", "FWD")
    budget: float
    free_transfers: int
    chips_used: frozenset = field(default_factory=frozenset)
    
    def __repr__(self):
        return f"State(GW={self.gameweek}, Budget={self.budget}, FT={self.free_transfers})"
