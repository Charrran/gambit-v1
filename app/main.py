"""
Gambit Engine - main application and authoritative scene loop.

Major beats stay authored in Neo4j while player-facing choices are generated
inside the constraints of the current scene. Session state is cached in-process
to keep Redis usage low.
"""
import os
import uuid

import neomodel
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from neomodel.async_.node import NodeMeta
from pydantic import BaseModel

load_dotenv()
_uri = os.getenv("NEO4J_URI", "")
_user = os.getenv("NEO4J_USERNAME", "")
_pass = os.getenv("NEO4J_PASSWORD", "")
_host = _uri.split("://")[1] if "://" in _uri else _uri
neomodel.config.DATABASE_URL = f"neo4j://{_user}:{_pass}@{_host}"

from app.api.sockets import socket_manager
from app.core.config import settings
from app.core.database import init_neo4j_async
from app.design.content import (
    CHAPTER_ANCHORS,
    INTRO_CONTEXT,
    LANE_WEIGHTS,
    MASTER_BEATS,
    ROLES,
    STATE_AXES,
    chapter_for_node,
)
from app.models.graph import EpisodeNode
from app.models.schemas import HealthResponse
from app.services.choice_resolver import apply_choice
from app.services.ending_engine import ensure_finale
from app.services.scene_engine import prepare_scene
from app.services.state import state_manager

GROUP_NODE_TYPES = {"POLL"}

if not settings.neo4j_uri:
    raise ValueError("CRITICAL: NEO4J_URI is not set. Cannot start engine.")
if not settings.neo4j_username or not settings.neo4j_password:
    raise ValueError("CRITICAL: NEO4J_USERNAME or NEO4J_PASSWORD is missing.")
if not settings.groq_api_key:
    raise ValueError("CRITICAL: GROQ_API_KEY is missing. Narrative turns will fail.")
if not settings.gemini_api_key:
    raise ValueError("CRITICAL: GEMINI_API_KEY is missing. Canonical Summary will fail.")

app = FastAPI(title="Gambit: The Regent Rebellion Engine")


class JoinRequest(BaseModel):
    player_id: str


# ---------------------------------------------------------------------------
# Startup
# ---------------------------------------------------------------------------

@app.on_event("startup")
async def startup_event():
    try:
        await init_neo4j_async()
        if not hasattr(EpisodeNode, "DoesNotExist"):
            print("[WARN] Neomodel Registry Hydration missing. Triggering self-healing...")
            NodeMeta._setup_DoesNotExist(EpisodeNode)
        redis_host = settings.redis_url.split("@")[-1] if "@" in settings.redis_url else settings.redis_url
        print("\n[OK] Gambit Engine Online")
        print(f"[OK] Graph (Neo4j): {settings.neo4j_uri}")
        print(f"[OK] Cache (Redis write-through): {redis_host}\n")
    except Exception as exc:
        print(f"\n[X] STARTUP FAILURE: {exc}\n")
        raise


# ---------------------------------------------------------------------------
# REST routes
# ---------------------------------------------------------------------------

@app.get("/", response_model=HealthResponse)
async def health_check():
    return HealthResponse(status="Gambit Engine Online")


@app.get("/debug/db")
async def check_database():
    from neomodel import adb  # keep import local to avoid startup risk
    try:
        res, _ = await adb.cypher_query("MATCH (n:EpisodeNode) RETURN n.node_id ORDER BY n.node_id")
        node_ids = [row[0] for row in res]
        return {"status": "connected", "total_nodes": len(node_ids), "node_ids": node_ids}
    except Exception as exc:
        return {"status": "error", "message": str(exc), "tip": "Check NEO4J_URI in your .env file"}


@app.post("/lobby/create")
async def create_lobby():
    session_id = str(uuid.uuid4())[:8]
    state = await state_manager.create_lobby(session_id)
    return {"session_id": session_id, "state": state}


@app.post("/lobby/{session_id}/join")
async def join_lobby(session_id: str, request: JoinRequest):
    try:
        return await state_manager.join_lobby(session_id, request.player_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.post("/lobby/{session_id}/start")
async def start_game(session_id: str):
    try:
        return await state_manager.start_game(session_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


# ---------------------------------------------------------------------------
# WebSocket payload helper
# ---------------------------------------------------------------------------

async def _send_scene_payload(websocket: WebSocket, state, player_id: str) -> None:
    if state.status != "ACTIVE":
        await websocket.send_json(
            {"type": "WAITING", "msg": "Waiting for all players to join and the host to start..."}
        )
        return

    if state.ended:
        await websocket.send_json(
            state.final_result or {"type": "GAME_OVER", "flavor": "The story ends here."}
        )
        return

    await websocket.send_json(
        {
            "type": "NARRATIVE_BEAT",
            "node_id": state.current_scene_node,
            "flavor": state.current_scene_flavor,
            "intro_context": INTRO_CONTEXT if state.current_scene_node == MASTER_BEATS[0]["id"] else None,
            "phase": state.current_scene_type,
            "spotlight_role": state.current_scene_role,
            "spotlight_player": state.current_scene_player,
            "interrogation_pair": state.current_interrogation_pair,
            "chapter": chapter_for_node(state.current_scene_node or state.current_node),
            "chapter_title": CHAPTER_ANCHORS.get(
                chapter_for_node(state.current_scene_node or state.current_node), {}
            ).get("title"),
            "state_axes": state.state_axes,
            "lane_weights": state.lane_weights,
            "aftermath": state.last_aftermath,
            "transition": state.last_transition,
        }
    )

    if state.current_scene_type in GROUP_NODE_TYPES:
        if player_id not in state.votes:
            await websocket.send_json(
                {
                    "type": "POLL_REQUEST" if state.current_scene_type == "POLL" else "INTERROGATION_REQUEST",
                    "options": [choice.model_dump() for choice in state.current_choices],
                    "msg": "Submit one choice to push the incident forward.",
                }
            )
        else:
            await websocket.send_json(
                {
                    "type": "WAITING",
                    "msg": f"Vote recorded. Waiting for others... ({len(state.votes)}/{len(state.active_players)})",
                }
            )
        return

    if player_id == state.current_scene_player:
        message_type = (
            "INTERROGATION_CHOICE" if state.current_scene_type == "INTERROGATION" else "SPOTLIGHT_CHOICE"
        )
        await websocket.send_json(
            {"type": message_type, "options": [choice.model_dump() for choice in state.current_choices]}
        )
    else:
        if state.current_scene_type == "INTERROGATION" and state.current_interrogation_pair:
            pair = state.current_interrogation_pair
            answering_role = pair.get("answering_role") or pair["target_role"]
            if answering_role == pair["instigator_role"]:
                msg = f"Waiting for {answering_role} to press {pair['target_role']}."
            else:
                msg = f"Waiting for {answering_role} to answer {pair['instigator_role']}."
        else:
            msg = f"Waiting for {state.current_scene_role} to act..."
        await websocket.send_json({"type": "WAITING", "msg": msg})


# ---------------------------------------------------------------------------
# WebSocket game loop
# ---------------------------------------------------------------------------

@app.websocket("/ws/play/{session_id}/{player_id}")
async def game_loop_websocket(websocket: WebSocket, session_id: str, player_id: str):
    await socket_manager.connect(websocket, session_id, player_id)
    last_revision = -1

    try:
        state = await state_manager.get_state(session_id)
        if not state or player_id not in state.active_players:
            await websocket.send_json(
                {
                    "type": "ERROR",
                    "error": f"Player '{player_id}' is not registered in session '{session_id}'.",
                    "action": "Join the lobby before opening the WebSocket.",
                }
            )
            await websocket.close()
            return

        while True:
            state = await state_manager.get_state(session_id)
            if not state:
                await websocket.send_json({"type": "ERROR", "error": "Session not found."})
                break

            if state.status == "ACTIVE" and not state.ended:
                state = await prepare_scene(session_id, STATE_AXES, LANE_WEIGHTS, MASTER_BEATS)
                state = await state_manager.get_state(session_id)
                if state and state.current_node:
                    from app.services.graph_store import fetch_node  # local import avoids top-level
                    current_node = await fetch_node(state.current_node)
                    if current_node.is_terminal:
                        state = await ensure_finale(session_id)

            state = await state_manager.get_state(session_id)
            if not state:
                break

            if state.revision != last_revision:
                await _send_scene_payload(websocket, state, player_id)
                last_revision = state.revision

            if state.ended:
                break

            if state.status != "ACTIVE":
                state = await state_manager.wait_for_change(session_id, last_revision)
                if state:
                    last_revision = state.revision - 1
                continue

            if state.current_scene_type in GROUP_NODE_TYPES:
                if player_id in state.votes:
                    state = await state_manager.wait_for_change(session_id, last_revision)
                    if state:
                        last_revision = state.revision - 1
                    continue
                client_msg = await websocket.receive_json()
                choice_id = str(client_msg.get("choice_id") or client_msg.get("edge_id") or "")
            elif player_id == state.current_scene_player:
                client_msg = await websocket.receive_json()
                choice_id = str(client_msg.get("choice_id") or client_msg.get("edge_id") or "")
            else:
                state = await state_manager.wait_for_change(session_id, last_revision)
                if state:
                    last_revision = state.revision - 1
                continue

            if client_msg.get("type") == "READY":
                continue
            if not choice_id:
                await websocket.send_json({"type": "ERROR", "error": "No choice_id was provided."})
                continue

            try:
                await apply_choice(session_id, player_id, choice_id, STATE_AXES, LANE_WEIGHTS)
            except ValueError as exc:
                await websocket.send_json({"type": "ERROR", "error": str(exc)})

    except WebSocketDisconnect:
        print(f"[WS] Player '{player_id}' disconnected from session '{session_id}'")
    except Exception as exc:
        print(f"[X] Unhandled error in game loop for '{player_id}': {type(exc).__name__}: {exc}")
        await websocket.send_json({"type": "FATAL_ERROR", "error": str(exc)})
    finally:
        socket_manager.disconnect(session_id, player_id)
