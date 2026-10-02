from dataclasses import dataclass
from typing import Optional, List, Tuple

@dataclass(frozen=True)
class Action:
    """Base class for all planning actions."""
    pass

@dataclass(frozen=True)
class TransferAction(Action):
    """Action to transfer one player out and another in."""
    player_out: str
    player_in: str

@dataclass(frozen=True)
class LineupAction(Action):
    """Action to set the starting XI and captain for the GW."""
    starting_xi: List[str]
    captain: str
    vice_captain: str

@dataclass(frozen=True)
class ChipAction(Action):
    """Action to activate a specific chip."""
    chip_name: str  # e.g., "Wildcard", "FreeHit", "BenchBoost", "TripleCaptain"

@dataclass(frozen=True)
class NoOpAction(Action):
    """Action for when no changes are made."""
    pass

@dataclass(frozen=True)
class GWPlan:
    """A complete set of decisions for a single Gameweek."""
    transfers: List[TransferAction]
    lineup: LineupAction
    chip: Optional[ChipAction] = None
