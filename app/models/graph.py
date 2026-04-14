import os
from neomodel import config
from dotenv import load_dotenv

# REDUNDANT INITIALIZATION: Ensures node classes are hydrated even if imported in isolation.
load_dotenv()
_uri = os.getenv("NEO4J_URI", "")
_user = os.getenv("NEO4J_USERNAME", "")
_pass = os.getenv("NEO4J_PASSWORD", "")
_host = _uri.split("://")[1] if "://" in _uri else _uri

# REGISTRY SETUP: We use a simplified protocol for the metadata engine
# to ensure the metaclass completes without protocol-parsing errors.
from neomodel import config
config.DATABASE_URL = f"neo4j://{_user}:{_pass}@{_host}"

from neomodel import (
    AsyncStructuredNode,
    AsyncStructuredRel,
    StringProperty,
    IntegerProperty,
    BooleanProperty,
    AsyncRelationshipTo
)

class PoliticalChoice(AsyncStructuredRel):
    """
    Represents a consequence-heavy choice connecting two story beats.
    Includes metadata for AI generation and game state logic.
    """
    action_intent = StringProperty(required=True)  # Prompt for AI MCQ generation
    required_role = StringProperty(required=True)  # E.g., "Raghava Rao", "Govardhan Naidu", "Saraswathi", "Haribabu"
    alignment_shift = StringProperty(required=True) # Direction of alignment change
    capital_shift = IntegerProperty(default=0)     # Economic/Political capital impact
    sets_flag = StringProperty()                   # Flag to activate in game state
    requires_flag = StringProperty()               # Prerequisite flag for choice availability

class EpisodeNode(AsyncStructuredNode):
    """
    A deterministic narrative node within a specific game episode.
    Supports different gameplay modes (Story, Characterization, Interrogation, Poll).
    """
    episode_id = StringProperty(required=True)
    node_id = StringProperty(unique_index=True, required=True)
    skeleton_premise = StringProperty(required=True)
    is_terminal = BooleanProperty(default=False)
    
    # NEW: Metadata for advanced gameplay phases
    node_type = StringProperty(default="STORY")  # STORY, CHARACTERIZATION, INTERROGATION, POLL
    canonical_outcome = StringProperty()         # The historical "fact" for this beat

    # Relationships
    leads_to = AsyncRelationshipTo('EpisodeNode', 'LEADS_TO', model=PoliticalChoice)
