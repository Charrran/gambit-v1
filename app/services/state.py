import random
import redis.asyncio as redis
from typing import Optional
from app.models.schemas import GameState, PlayerProfile
from app.core.config import settings

class GameStateManager:
    """
    Manager for episodic game state in Redis.
    Handles lobby logic, role shuffling, and persistent memory of player choices.
    """
    def __init__(self):
        self.redis_url = settings.redis_url
        # Ensure we use an async connection from the centralized settings
        self.client = redis.from_url(self.redis_url, decode_responses=True)

    async def create_lobby(self, session_id: str) -> GameState:
        """Initializes a new GameState in Redis with 'LOBBY' status."""
        state = GameState(session_id=session_id)
        await self.client.set(f"game:{session_id}", state.model_dump_json())
        return state

    async def get_state(self, session_id: str) -> Optional[GameState]:
        """Retrieves and hydrates the GameState from Redis."""
        raw_state = await self.client.get(f"game:{session_id}")
        if not raw_state:
            return None
        return GameState.model_validate_json(raw_state)

    async def join_lobby(self, session_id: str, player_id: str) -> GameState:
        """Adds a player to a lobby if capacity (4) allows."""
        state = await self.get_state(session_id)
        if not state:
            raise ValueError("Session not found")
        if state.status != "LOBBY":
            raise ValueError("Cannot join an active game")
        if len(state.active_players) >= 4:
            raise ValueError("Lobby is full")
        
        # Avoid duplicate joins
        if player_id not in state.active_players:
            state.active_players[player_id] = PlayerProfile(player_id=player_id)
            await self.client.set(f"game:{session_id}", state.model_dump_json())
        
        return state

    async def start_game(self, session_id: str) -> GameState:
        """Assigns roles, transitions state to 'ACTIVE', and sets the starting node."""
        state = await self.get_state(session_id)
        if not state:
            raise ValueError("Session not found")
        
        num_players = len(state.active_players)
        if num_players < 2:
            raise ValueError("Need at least 2 players to start")

        # Define roles based on player count
        roles = ["Raghava Rao", "Govardhan Naidu"] # Essential
        if num_players >= 3:
            roles.append("Saraswathi")
        if num_players == 4:
            roles.append("Haribabu")

        # Randomize role assignment
        random.shuffle(roles)
        player_ids = list(state.active_players.keys())
        for i, pid in enumerate(player_ids):
            state.active_players[pid].role = roles[i]

        # Transition game state
        state.status = "ACTIVE"
        state.current_node = "regent_01_fractured_peace"
        
        await self.client.set(f"game:{session_id}", state.model_dump_json())
        return state

    async def update_player_state(
        self, 
        session_id: str, 
        player_id: str, 
        new_alignment: str = None, 
        new_flag: str = None
    ) -> GameState:
        """Appends consequence data (alignments/flags) to a player's profile."""
        state = await self.get_state(session_id)
        if not state or player_id not in state.active_players:
            raise ValueError("Session or player not found")

        profile = state.active_players[player_id]
        if new_alignment:
            profile.alignments.append(new_alignment)
        if new_flag:
            profile.flags.append(new_flag)

        await self.client.set(f"game:{session_id}", state.model_dump_json())
        return state

# Global singleton for use in FastAPI routes
state_manager = GameStateManager()
