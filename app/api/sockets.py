from typing import Dict, Any
from fastapi import WebSocket

class ConnectionManager:
    """
    Manages real-time WebSocket communication for multiplayer lobbies.
    Supports both session-wide broadcasting and targeted spotlight dispatching.
    """
    def __init__(self):
        # session_id -> {player_id: WebSocket}
        self.active_sessions: Dict[str, Dict[str, WebSocket]] = {}

    async def connect(self, websocket: WebSocket, session_id: str, player_id: str):
        """Accepts the connection and adds the player to the session map."""
        await websocket.accept()
        if session_id not in self.active_sessions:
            self.active_sessions[session_id] = {}
        self.active_sessions[session_id][player_id] = websocket

    def disconnect(self, session_id: str, player_id: str):
        """Removes the player from the active session map."""
        if session_id in self.active_sessions:
            if player_id in self.active_sessions[session_id]:
                del self.active_sessions[session_id][player_id]
            if not self.active_sessions[session_id]:
                del self.active_sessions[session_id]

    async def broadcast_to_session(self, session_id: str, message: Dict[str, Any]):
        """
        Sends narrative flavor text or global state updates to all players in the session.
        """
        if session_id in self.active_sessions:
            for ws in self.active_sessions[session_id].values():
                try:
                    await ws.send_json(message)
                except Exception:
                    # In production, we'd handle dead connections here
                    pass

    async def send_personal_state(self, session_id: str, player_id: str, message: Dict[str, Any]):
        """
        Sends the specific interactive choices (Spotlight state) to a target player.
        """
        if session_id in self.active_sessions:
            ws = self.active_sessions[session_id].get(player_id)
            if ws:
                try:
                    await ws.send_json(message)
                except Exception:
                    pass

# Master singleton instance
socket_manager = ConnectionManager()
