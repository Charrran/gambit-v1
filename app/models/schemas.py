from pydantic import BaseModel, Field
from typing import List, Optional, Dict

class PlayerProfile(BaseModel):
    """
    Profile for a specific player in a game session.
    Tracks assigned role, moral/political alignments, and world flags.
    """
    player_id: str
    role: Optional[str] = None
    alignments: List[str] = Field(default_factory=list)
    primary_trait: Optional[str] = None
    flags: List[str] = Field(default_factory=list)

class GameState(BaseModel):
    """
    Global state for a specific game session (The Memory Bank).
    Tracks current narrative position, global resources, and player distribution.
    """
    session_id: str
    current_node: str = "regent_01_fractured_peace"
    global_capital: int = 100
    active_players: Dict[str, PlayerProfile] = Field(default_factory=dict)
    status: str = "LOBBY"  # Valid statuses: "LOBBY", "ACTIVE"
    
    # NEW: Advanced Mechanics Tracking
    session_history: List[Dict[str, str]] = Field(default_factory=list) # List of {"node": node_id, "role": role, "choice": choice_text}
    votes: Dict[str, str] = Field(default_factory=dict) # Dict[player_id, choice_id] for polling and interrogations
    active_event: Optional[str] = None # Tracks the node_id of a currently active special event (Confrontation, etc)
