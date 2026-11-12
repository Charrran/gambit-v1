import asyncio
import random
import time
from typing import Dict, Optional

import redis.asyncio as redis

from app.core.config import settings
from app.design.content import LANE_WEIGHTS, ROLES, STATE_AXES
from app.models.schemas import GameState, PlayerProfile
from app.services.live_intel import build_trust_matrix, fallback_headlines


SESSION_TTL_SECONDS = 7 * 24 * 3600   # Redis keeps a session this long after its last save
IDLE_EVICT_SECONDS = 6 * 3600         # an untouched session leaves process memory (Redis still has it)


class GameStateManager:
    """
    Session state manager. The in-process copy is the live state; Redis is the
    durable copy, written behind the game:

    * save_state() updates memory, wakes the players' sockets and returns at once.
    * One background writer per session sends the newest snapshot to Redis. If
      several saves pile up only the latest is written, and a failed write is
      retried with backoff. A slow or flaky Redis therefore never delays or
      breaks a turn; the cost is that a process crash can lose the last
      fraction of a second of play.
    """

    def __init__(self):
        self.redis_url = settings.redis_url
        self.client = redis.from_url(self.redis_url, decode_responses=True)
        self._cache: Dict[str, GameState] = {}
        self._events: Dict[str, asyncio.Event] = {}
        self._locks: Dict[str, asyncio.Lock] = {}
        self._dirty: Dict[str, str] = {}
        self._writers: Dict[str, asyncio.Future] = {}
        self._touched: Dict[str, float] = {}

    def session_lock(self, session_id: str) -> asyncio.Lock:
        return self._locks.setdefault(session_id, asyncio.Lock())

    def _event_for(self, session_id: str) -> asyncio.Event:
        return self._events.setdefault(session_id, asyncio.Event())

    async def _persist(self, state: GameState) -> None:
        session_id = state.session_id
        self._cache[session_id] = state
        self._touched[session_id] = time.monotonic()
        # Snapshot now: the state object keeps being mutated by later turns.
        self._dirty[session_id] = state.model_dump_json()
        if session_id not in self._writers:
            writer = asyncio.ensure_future(self._write_behind(session_id))
            self._writers[session_id] = writer
            writer.add_done_callback(lambda _done, sid=session_id: self._writers.pop(sid, None))
        event = self._event_for(session_id)
        event.set()
        event.clear()

    async def _write_behind(self, session_id: str) -> None:
        backoff = 0.2
        while session_id in self._dirty:
            payload = self._dirty.pop(session_id)
            try:
                await self.client.set(f"game:{session_id}", payload, ex=SESSION_TTL_SECONDS)
                backoff = 0.2
            except Exception as exc:
                self._dirty.setdefault(session_id, payload)  # keep it unless a newer snapshot arrived
                print(f"[WARN] Redis save failed for {session_id}, retrying in {backoff:.1f}s: {exc}")
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, 5.0)

    async def flush(self, session_id: Optional[str] = None) -> None:
        """Wait until pending snapshots (one session, or all) have reached Redis."""
        writers = [self._writers.get(session_id)] if session_id else list(self._writers.values())
        for writer in writers:
            if writer is not None:
                await asyncio.shield(writer)

    def _evict_idle(self) -> None:
        """Drop long-idle sessions from process memory; they remain loadable from Redis."""
        cutoff = time.monotonic() - IDLE_EVICT_SECONDS
        for session_id in [sid for sid, seen in self._touched.items() if seen < cutoff]:
            if session_id in self._dirty or session_id in self._writers:
                continue
            for table in (self._cache, self._events, self._locks, self._touched):
                table.pop(session_id, None)


    async def save_state(self, state: GameState) -> GameState:
        state.revision += 1
        await self._persist(state)
        return state

    async def get_state(self, session_id: str, force_refresh: bool = False) -> Optional[GameState]:
        if not force_refresh and session_id in self._cache:
            return self._cache[session_id]

        raw_state = await self.client.get(f"game:{session_id}")
        if not raw_state:
            return None

        state = GameState.model_validate_json(raw_state)
        self._cache[session_id] = state
        return state

    async def wait_for_change(self, session_id: str, known_revision: int, timeout: float = 30.0) -> Optional[GameState]:
        current = await self.get_state(session_id)
        if current and current.revision != known_revision:
            return current

        event = self._event_for(session_id)
        try:
            await asyncio.wait_for(event.wait(), timeout=timeout)
        except asyncio.TimeoutError:
            return None
        return await self.get_state(session_id)

    async def create_lobby(self, session_id: str) -> GameState:
        self._evict_idle()
        state = GameState(session_id=session_id)
        state.state_axes = dict(STATE_AXES)
        state.lane_weights = dict(LANE_WEIGHTS)
        state.trust_matrix = build_trust_matrix(state.state_axes)
        state.news_headlines = fallback_headlines(state)
        state.spotlight_counts = {role: 0 for role in ROLES}
        await self._persist(state)
        return state

    async def join_lobby(self, session_id: str, player_id: str) -> GameState:
        async with self.session_lock(session_id):
            state = await self.get_state(session_id)
            if not state:
                raise ValueError("Session not found")
            if state.status != "LOBBY":
                raise ValueError("Cannot join an active game")
            if len(state.active_players) >= 4:
                raise ValueError("Lobby is full")

            if player_id not in state.active_players:
                state.active_players[player_id] = PlayerProfile(player_id=player_id)

            return await self.save_state(state)

    async def start_game(self, session_id: str) -> GameState:
        async with self.session_lock(session_id):
            state = await self.get_state(session_id)
            if not state:
                raise ValueError("Session not found")

            num_players = len(state.active_players)
            if num_players < 4:
                raise ValueError("Need all 4 roles to start this version of Gambit")

            roles = ["Raghava Rao", "Govardhan Naidu"]
            if num_players >= 3:
                roles.append("Saraswathi")
            if num_players == 4:
                roles.append("Venkatadri")

            random.shuffle(roles)
            for pid, role in zip(state.active_players.keys(), roles):
                state.active_players[pid].role = role

            state.status = "ACTIVE"
            state.current_node = "gambit_ch01_raghava"
            state.votes = {}
            state.active_event = None
            state.global_capital = 100
            state.session_history = []
            state.state_axes = dict(STATE_AXES)
            state.lane_weights = dict(LANE_WEIGHTS)
            state.headlines_chapter = None
            state.lane_pressure = {}
            state.lane_spread = {}
            state.story_flags = []
            state.spotlight_counts = {role: 0 for role in ROLES}
            state.resolved_lane = None
            state.current_scene_node = None
            state.current_scene_type = None
            state.current_scene_flavor = None
            state.current_scene_role = None
            state.current_scene_player = None
            state.current_scene_round = 0
            state.current_scene_total_rounds = 0
            state.current_choices = []
            state.current_choice_payloads = []
            state.current_interrogation_pair = None
            state.final_result = None
            state.ended = False
            state.last_aftermath = None
            state.last_transition = None
            state.trust_matrix = build_trust_matrix(state.state_axes)
            state.news_headlines = fallback_headlines(state)

            return await self.save_state(state)



state_manager = GameStateManager()
