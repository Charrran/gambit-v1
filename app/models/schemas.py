from pydantic import BaseModel, Field, field_validator
from typing import Any, Dict, List, Optional

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

class ChoiceView(BaseModel):
    """
    A client-safe representation of a generated or authored choice.
    """
    choice_id: str
    text: str
    role: Optional[str] = None
    subtext: Optional[str] = None

class HealthResponse(BaseModel):
    status: str
    version: str = "2.1"

class NewsHeadline(BaseModel):
    id: str = Field(..., description="Stable short id.")
    dateline: str = Field(..., description="Fictional publication and edition.")
    headline: str = Field(..., description="In-world headline.")
    body: str = Field(..., description="One sentence description.")

    @field_validator("id", mode="before")
    @classmethod
    def coerce_id(cls, value):
        return str(value)

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

    # Advanced Mechanics Tracking
    session_history: List[Dict[str, str]] = Field(default_factory=list)
    votes: Dict[str, str] = Field(default_factory=dict)
    active_event: Optional[str] = None
    revision: int = 0
    current_scene_node: Optional[str] = None
    current_scene_type: Optional[str] = None
    current_scene_flavor: Optional[str] = None
    current_scene_role: Optional[str] = None
    current_scene_player: Optional[str] = None
    current_scene_round: int = 0
    current_scene_total_rounds: int = 0
    current_choices: List[ChoiceView] = Field(default_factory=list)
    current_choice_payloads: List[Dict[str, Any]] = Field(default_factory=list)
    current_interrogation_pair: Optional[Dict[str, str]] = None
    final_result: Optional[Dict[str, Any]] = None
    ended: bool = False
    last_aftermath: Optional[str] = None
    state_axes: Dict[str, int] = Field(default_factory=dict)
    lane_weights: Dict[str, int] = Field(default_factory=dict)
    story_flags: List[str] = Field(default_factory=list)
    spotlight_counts: Dict[str, int] = Field(default_factory=dict)
    resolved_lane: Optional[str] = None

    # State-reactive: chapter transition context sent with NARRATIVE_BEAT
    last_transition: Optional[Dict[str, Any]] = None
    trust_matrix: Dict[str, int] = Field(default_factory=dict)
    news_headlines: List[NewsHeadline] = Field(default_factory=list)
