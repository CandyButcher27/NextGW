from dataclasses import dataclass, field
from typing import Set, Dict

@dataclass(frozen=True)
class PlanningState:
    """
    Represents the full state of an FPL team at a specific Gameweek.
    Frozen to ensure it can be used as a key in search algorithms (e.g. for memoization).
    """
    gameweek: int
    squad: Dict[str, str]  # PlayerID -> Position (e.g., "GK", "DEF", "MID", "FWD")
    budget: float
    free_transfers: int
    chips_used: Set[str] = field(default_factory=set)
    
    def __repr__(self):
        return f"State(GW={self.gameweek}, Budget={self.budget}, FT={self.free_transfers})"
