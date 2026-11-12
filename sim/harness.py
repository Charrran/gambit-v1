"""
Offline harness for Gambit's game logic.

Runs the *production* scene/choice/finale code (app.services.scene_engine.prepare_scene,
app.services.choice_resolver.apply_choice, app.services.ending_engine.ensure_finale)
with only the infrastructure replaced:

* Redis   -> in-memory async key/value store (FakeRedis)
* Neo4j   -> FakeGraph built from MASTER_BEATS exactly the way seed_db.py builds the graph
* LLM     -> deterministic stubs that return authored text (never touch state)

Nothing in the game logic is reimplemented here, so any change to the logic is
picked up automatically by the simulator.
"""
from __future__ import annotations

import asyncio
import os
import random
import sys
from pathlib import Path
from types import SimpleNamespace
from typing import Callable, Dict, List, Optional

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Settings are validated at import time; offline runs only need placeholders.
for _key, _val in {
    "NEO4J_URI": "neo4j://offline:7687",
    "NEO4J_USERNAME": "offline",
    "NEO4J_PASSWORD": "offline",
    "REDIS_URL": "redis://offline:6379/0",
    "GROQ_API_KEY": "offline",
    "GEMINI_API_KEY": "offline",
}.items():
    os.environ.setdefault(_key, _val)

from app.design.content import (  # noqa: E402
    CHAPTER_ANCHORS,
    LANE_WEIGHTS,
    MASTER_BEATS,
    STATE_AXES,
    TERMINAL_NODES,
    normalize_choice,
    terminal_for_lane,
)
from app.models.schemas import NewsHeadline  # noqa: E402
from app.services import choice_resolver, ending_engine, scene_engine  # noqa: E402
from app.services import graph_store, live_intel  # noqa: E402
from app.services.ai_engine import EndingComparison, ai_engine  # noqa: E402
from app.services.graph_store import choice_design_payload  # noqa: E402
from app.services.state import state_manager  # noqa: E402

GROUP_NODE_TYPES = {"POLL"}


# ---------------------------------------------------------------------------
# Infrastructure fakes
# ---------------------------------------------------------------------------

class FakeRedis:
    def __init__(self):
        self.store: Dict[str, str] = {}

    async def get(self, key):
        return self.store.get(key)

    async def set(self, key, value):
        self.store[key] = value
        return True


class FakeGraph:
    """Mirror of the graph seed_db.py writes to Neo4j."""

    def __init__(self):
        self.nodes: Dict[str, SimpleNamespace] = {}
        self.edges: Dict[str, List[Dict[str, object]]] = {}
        for beat in MASTER_BEATS:
            anchor = CHAPTER_ANCHORS[beat["chapter"]]
            self.nodes[beat["id"]] = SimpleNamespace(
                node_id=beat["id"],
                node_type=beat["type"],
                skeleton_premise=beat["premise"],
                canonical_outcome=f"Chapter {beat['chapter']}: {anchor['historical_situation']}",
                is_terminal=False,
            )
        for node_id, premise in TERMINAL_NODES:
            self.nodes[node_id] = SimpleNamespace(
                node_id=node_id,
                node_type="STORY",
                skeleton_premise=premise,
                canonical_outcome="This is an alternate-history ending lane resolved from player state.",
                is_terminal=True,
            )
        for index, beat in enumerate(MASTER_BEATS):
            next_id = (
                MASTER_BEATS[index + 1]["id"]
                if index + 1 < len(MASTER_BEATS)
                else terminal_for_lane("broken_house")
            )
            props_list = []
            if beat["type"] == "INTERROGATION":
                props_list.append(
                    {
                        "choice_id": f"{beat['id']}__continue",
                        "action_intent": "Continue the authored confrontation.",
                        "required_role": "COUNCIL",
                        "alignment_shift": "INTERROGATION",
                        "capital_shift": 0,
                    }
                )
            else:
                for raw in beat.get("choices", []):
                    choice = normalize_choice(raw)
                    props_list.append(
                        {
                            "choice_id": choice["id"],
                            "action_intent": choice["text"],
                            "required_role": "COUNCIL" if beat["type"] == "POLL" else (beat.get("role") or "COUNCIL"),
                            "alignment_shift": "DECISIVE",
                            "capital_shift": 0,
                        }
                    )
            self.edges[beat["id"]] = [(props, next_id) for props in props_list]

    async def fetch_node(self, node_id: str):
        if node_id not in self.nodes:
            raise KeyError(f"Node '{node_id}' not found")
        return self.nodes[node_id]

    async def fetch_edges(self, node_id: str):
        """Same post-processing as graph_store.fetch_edges, minus the Cypher call."""
        edges = []
        for props, target_node_id in self.edges.get(node_id, []):
            choice_id = props.get("choice_id")
            design_payload = choice_design_payload(choice_id)
            edges.append(
                {
                    "choice_id": choice_id,
                    "action_intent": props.get("action_intent", "Make a strategic choice"),
                    "required_role": props.get("required_role"),
                    "alignment_shift": props.get("alignment_shift"),
                    "capital_shift": props.get("capital_shift", 0),
                    "sets_flag": props.get("sets_flag"),
                    "requires_flag": props.get("requires_flag"),
                    "min_capital": props.get("min_capital"),
                    "max_capital": props.get("max_capital"),
                    "min_players": props.get("min_players"),
                    "max_players": props.get("max_players"),
                    "option_group": props.get("option_group", "DEFAULT"),
                    "target_node_id": target_node_id,
                    "effects": design_payload["effects"],
                    "lanes": design_payload["lanes"],
                }
            )
        return sorted(edges, key=lambda edge: edge["choice_id"] or "")


def _install_llm_stubs() -> None:
    """Deterministic AI Director: authored text only, no state access."""

    async def spotlight(premise, required_role, db_choices, **_):
        return ai_engine._build_fallback_turn(premise, required_role, db_choices)

    async def poll(premise, db_choices, **_):
        return ai_engine._build_fallback_turn(premise, "COUNCIL", db_choices)

    async def comparison(session_history, global_capital, resolved_lane="", final_state_snapshot=None):
        return EndingComparison(
            player_summary=f"The run resolved into {resolved_lane.replace('_', ' ')}.",
            canonical_summary="Canonical baseline.",
            divergence_analysis="Offline simulation.",
            final_score=resolved_lane.replace("_", " ").title(),
        )

    async def historian(resolved_lane, final_state_snapshot, all_flags, pivotal_decisions):
        return f"Offline historian ending for {resolved_lane}."

    async def headlines(**_):
        raise RuntimeError("offline")  # live_intel falls back to deterministic headlines

    async def aftermath(**_):
        return "Offline aftermath."

    ai_engine.generate_spotlight_turn = spotlight
    ai_engine.generate_poll_turn = poll
    ai_engine.generate_canonical_comparison = comparison
    ai_engine.generate_historian_ending = historian
    ai_engine.generate_news_headlines = headlines
    ai_engine.generate_breakdown_aftermath = aftermath


_INSTALLED: Optional[FakeGraph] = None


def install_offline_backends() -> FakeGraph:
    """Patch Redis/Neo4j/LLM access points. Idempotent."""
    global _INSTALLED
    if _INSTALLED is not None:
        return _INSTALLED
    graph = FakeGraph()
    state_manager.client = FakeRedis()
    for module in (scene_engine, choice_resolver, ending_engine, graph_store):
        if hasattr(module, "fetch_node"):
            module.fetch_node = graph.fetch_node
        if hasattr(module, "fetch_edges"):
            module.fetch_edges = graph.fetch_edges
    _install_llm_stubs()
    # live_intel prints a warning on every headline fallback; keep sim output clean.
    live_intel.print = lambda *a, **k: None  # type: ignore[attr-defined]
    _INSTALLED = graph
    return graph


# ---------------------------------------------------------------------------
# Game driver
# ---------------------------------------------------------------------------

# A policy receives (state, player_id, role, payloads) and returns a choice_id.
Policy = Callable[[object, str, str, List[Dict[str, object]]], str]


async def _forget(session_id: str) -> None:
    state_manager._cache.pop(session_id, None)
    state_manager._locks.pop(session_id, None)
    state_manager._events.pop(session_id, None)
    state_manager.client.store.pop(f"game:{session_id}", None)


async def play_game(
    policies: Dict[str, Policy],
    seed: int,
    session_id: Optional[str] = None,
    record: Optional[List[Dict[str, str]]] = None,
    role_order: Optional[List[str]] = None,
    deadlock_timeout: float = 0.02,
) -> Dict[str, object]:
    """
    Play one full game.

    policies: player_id -> policy (exactly 4 players).
    seed: seeds the global RNG used by start_game's role shuffle.
    role_order: optional explicit role per player (bypasses the shuffle result).
    record: if given, every submitted choice is appended as {node, player, role, choice_id}.

    Baseline (v1) prepare_scene deadlocks when it skips an interrogation (it recurses
    while holding the non-reentrant session lock). In production the stuck sender task
    is cancelled when a player reconnects, which releases the lock with current_node
    already advanced. We emulate exactly that: cancel after `deadlock_timeout` and
    retry. `freezes` in the result counts how often this happened.
    """
    install_offline_backends()
    session_id = session_id or f"SIM{seed}"
    await _forget(session_id)
    random.seed(seed)
    player_ids = list(policies)
    await state_manager.create_lobby(session_id)
    for pid in player_ids:
        await state_manager.join_lobby(session_id, pid)
    state = await state_manager.start_game(session_id)
    if role_order:
        for pid, role in zip(player_ids, role_order):
            state.active_players[pid].role = role

    trajectory: List[Dict[str, object]] = []
    freezes = 0
    for _ in range(200):
        state = await state_manager.get_state(session_id)
        if state.ended:
            break
        if state.current_scene_node != state.current_node:
            try:
                state = await asyncio.wait_for(
                    scene_engine.prepare_scene(session_id, STATE_AXES, LANE_WEIGHTS, MASTER_BEATS),
                    deadlock_timeout,
                )
            except asyncio.TimeoutError:
                freezes += 1
                continue
            state = await ending_engine.ensure_finale(session_id) or state
            if state.ended:
                break
        payloads = list(state.current_choice_payloads)
        node = state.current_node
        snapshot = (dict(state.state_axes), dict(state.lane_weights))
        if state.current_scene_type in GROUP_NODE_TYPES:
            actors = list(player_ids)
        else:
            actors = [state.current_scene_player]
        for pid in actors:
            role = state.active_players[pid].role
            choice_id = policies[pid](state, pid, role, payloads)
            if record is not None:
                record.append({"node": node, "player": pid, "role": role, "choice_id": choice_id})
            state = await choice_resolver.apply_choice(session_id, pid, choice_id, STATE_AXES, LANE_WEIGHTS)
        trajectory.append({"node": node, "before": snapshot})
    else:
        raise RuntimeError("Game did not terminate")

    result = {
        "seed": seed,
        "freezes": freezes,
        "resolved_lane": state.resolved_lane,
        "ending_node": (state.final_result or {}).get("ending_node"),
        "state_axes": dict(state.state_axes),
        "lane_weights": dict(state.lane_weights),
        "story_flags": list(state.story_flags),
        "history": list(state.session_history),
        "roles": {pid: p.role for pid, p in state.active_players.items()},
        "trajectory": trajectory,
    }
    await _forget(session_id)
    return result


def run(coro):
    return asyncio.run(coro)
