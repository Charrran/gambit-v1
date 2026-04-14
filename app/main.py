"""
Gambit Engine - Main Application
Fully fail-proofed WebSocket narrative game loop.

Key Architectural Decisions:
- neomodel async (adb) is initialized at startup, NOT at module level
- The sync config.DATABASE_URL is set for health-check purposes only
- All graph queries use the async adb driver
- WebSocket loop errors are translated into structured client messages
"""
import os
import neomodel
from dotenv import load_dotenv

# ABSOLUTE ENTRYPOINT STABILIZATION:
# Manually load environment and set config BEFORE any other app modules are read.
load_dotenv()
_uri = os.getenv("NEO4J_URI", "")
_user = os.getenv("NEO4J_USERNAME", "")
_pass = os.getenv("NEO4J_PASSWORD", "")
_host = _uri.split("://")[1] if "://" in _uri else _uri
# Use a simple protocol for the registry engine to avoid SSL handshakes during metaclass construction
neomodel.config.DATABASE_URL = f"neo4j://{_user}:{_pass}@{_host}"

import uuid
import asyncio
from neomodel import adb
from neomodel.async_.node import NodeMeta  # For self-healing
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
from typing import Optional

from app.api.sockets import socket_manager
from app.services.state import state_manager
from app.services.ai_engine import ai_engine
from app.core.config import settings
from app.core.database import init_neo4j_async
from app.models.graph import EpisodeNode

# --------------------------------------------------------------------------
# Global: Fast-fail configuration check
# --------------------------------------------------------------------------
# Validate required settings immediately on load (not deferred)
if not settings.neo4j_uri:
    raise ValueError("CRITICAL: NEO4J_URI is not set. Cannot start engine.")
if not settings.neo4j_username or not settings.neo4j_password:
    raise ValueError("CRITICAL: NEO4J_USERNAME or NEO4J_PASSWORD is missing.")

# AI Layer Validation
if not settings.groq_api_key:
    raise ValueError("CRITICAL: GROQ_API_KEY is missing. Narrative turns will fail.")
if not settings.gemini_api_key:
    raise ValueError("CRITICAL: GEMINI_API_KEY is missing. Canonical Summary will fail.")



app = FastAPI(title="Gambit: The Regent Rebellion Engine")

class JoinRequest(BaseModel):
    player_id: str

# --------------------------------------------------------------------------
# Startup: Initialize async Neo4j driver
# --------------------------------------------------------------------------
@app.on_event("startup")
async def startup_event():
    """
    Initializes BOTH the sync and async neomodel drivers on startup.
    This is the correct way to set up neomodel for FastAPI.
    """
    try:
        # Initialize the async driver
        # We delegate connection URL construction to init_neo4j_async to enforce strict protocols
        await init_neo4j_async()
        
        # SELF-HEALING REGISTRY CHECK
        # Neomodel sometimes fails to hydrate DoesNotExist metadata in async contexts.
        # We explicitly force the metaclass setup if it's missing.
        is_setup = hasattr(EpisodeNode, "DoesNotExist")
        if not is_setup:
            print("[WARN] Neomodel Registry Hydration missing. Triggering self-healing...")
            NodeMeta._setup_DoesNotExist(EpisodeNode)
            is_setup = hasattr(EpisodeNode, "DoesNotExist")

        print(f"[SYS] Neomodel Registry Warm-Up: {'SUCCESS' if is_setup else 'FAILED'}")

        # 3. Log sanitized connection info
        if "@" in settings.redis_url:
            redis_host = settings.redis_url.split("@")[-1]
        else:
            redis_host = settings.redis_url

        print(f"\n[OK] Gambit Engine Online")
        print(f"[OK] Graph (Neo4j): {settings.neo4j_uri}")
        print(f"[OK] Cache (Redis): {redis_host}\n")

    except Exception as e:
        print(f"\n[X] STARTUP FAILURE: {e}\n")
        raise e  # Re-raise so the process exits if infra is unavailable

# --------------------------------------------------------------------------
# Routes
# --------------------------------------------------------------------------
@app.get("/")
async def health_check():
    return {"status": "Gambit Engine Online", "version": "2.0"}

@app.get("/debug/db")
async def check_database():
    """
    Diagnostic: Verify Neo4j content without external tools.
    Lists every EpisodeNode ID currently in the database.
    """
    try:
        from neomodel import adb
        res, _ = await adb.cypher_query("MATCH (n:EpisodeNode) RETURN n.node_id")
        node_ids = [row[0] for row in res]
        return {
            "status": "connected",
            "total_nodes": len(node_ids),
            "node_ids": node_ids,
            "tip": "If total_nodes is 0, run: python seed_db.py"
        }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e),
            "tip": "Check NEO4J_URI in your .env file"
        }

@app.post("/lobby/create")
async def create_lobby():
    """Creates a new game session in Redis."""
    session_id = str(uuid.uuid4())[:8]
    state = await state_manager.create_lobby(session_id)
    return {"session_id": session_id, "state": state}

@app.post("/lobby/{session_id}/join")
async def join_lobby(session_id: str, request: JoinRequest):
    """Adds a player to an existing lobby."""
    try:
        updated_state = await state_manager.join_lobby(session_id, request.player_id)
        return updated_state
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/lobby/{session_id}/start")
async def start_game(session_id: str):
    """Assigns roles and activates the game session."""
    try:
        active_state = await state_manager.start_game(session_id)
        return active_state
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

# --------------------------------------------------------------------------
# WebSocket Game Loop
# --------------------------------------------------------------------------
@app.websocket("/ws/play/{session_id}/{player_id}")
async def game_loop_websocket(websocket: WebSocket, session_id: str, player_id: str):
    """
    The Gambit Narrative Engine WebSocket Loop.

    Architecture: Leader-Follower pattern.
    - The 'Spotlight' (Leader) player triggers the AI Director and submits choices.
    - All other players (Followers) receive broadcasts and wait for the state to advance.
    - All state is persisted in Redis so reconnecting clients sync instantly.
    """
    await socket_manager.connect(websocket, session_id, player_id)
    print(f"[WS] Player '{player_id}' connected to session '{session_id}'")

    # Tracks which node has already had AI generated to prevent redundant API calls
    last_ai_node: Optional[str] = None
    chosen_edge_id: Optional[str] = None

    try:
        while True:
            # Reset choice for each iteration
            chosen_edge_id = None
            # ----------------------------------------------------------------
            # Step 1: Load Redis State
            # ----------------------------------------------------------------
            state = await state_manager.get_state(session_id)
            if not state:
                await websocket.send_json({
                    "type": "ERROR",
                    "error": f"Session '{session_id}' not found in Redis.",
                    "action": "Create a new lobby via POST /lobby/create"
                })
                await websocket.close()
                break

            if state.status != "ACTIVE":
                await websocket.send_json({
                    "type": "WAITING",
                    "msg": "Waiting for all players to join and the host to start..."
                })
                await asyncio.sleep(2)
                continue

            # ----------------------------------------------------------------
            # Step 2: Load Current Narrative Node from Neo4j
            # ----------------------------------------------------------------
            try:
                from neomodel import adb
                res, _ = await adb.cypher_query(f"MATCH (n:EpisodeNode {{node_id: '{state.current_node}'}}) RETURN n")
                if not res:
                    raise EpisodeNode.DoesNotExist("Node not found")
                current_node = EpisodeNode.inflate(res[0][0])
            except EpisodeNode.DoesNotExist:
                error_msg = (
                    f"Node '{state.current_node}' not found in Neo4j. "
                    f"This means the database is out of sync with the game state. "
                    f"Fix: run 'python seed_db.py' then create a new lobby."
                )
                print(f"[X] {error_msg}")
                await websocket.send_json({
                    "type": "FATAL_ERROR",
                    "error": error_msg
                })
                await websocket.close()
                break
            except Exception as e:
                import traceback
                traceback.print_exc()
                print(f"[X] Neo4j connection error: {e}")
                await websocket.send_json({
                    "type": "FATAL_ERROR",
                    "error": "Lost connection to the narrative database. Retrying in 3s...",
                    "detail": str(e)
                })
                await asyncio.sleep(3)
                continue  # Retry - don't break, might be transient

            # ----------------------------------------------------------------
            # Step 3: Terminal Node (Gemini Canonical Finale)
            # ----------------------------------------------------------------
            if current_node.is_terminal:
                # Add the terminal node to history before closing
                state.session_history.append({
                    "node": current_node.node_id,
                    "role": "SYSTEM",
                    "choice": "THE END"
                })
                
                # Signal to everyone that history is being processed
                await socket_manager.broadcast_to_session(session_id, {
                    "type": "PROCESSING_FINALE",
                    "msg": "The AI Historian (Gemini) is analyzing your performance against history..."
                })

                try:
                    comparison = await ai_engine.generate_canonical_comparison(
                        session_history=state.session_history,
                        global_capital=state.global_capital
                    )
                    
                    await socket_manager.broadcast_to_session(session_id, {
                        "type": "GAME_OVER",
                        "comparison": comparison.model_dump()
                    })
                except Exception as e:
                    print(f"[!] Finale Generation Failed: {e}")
                    await socket_manager.broadcast_to_session(session_id, {
                        "type": "GAME_OVER",
                        "flavor": "The story ends here. (AI Historian Offline)"
                    })
                
                print(f"[OK] Session '{session_id}' reached terminal node: {state.current_node}")
                break

            # ----------------------------------------------------------------
            # Step 4: Discover Available Paths (Cypher Hardened)
            # ----------------------------------------------------------------
            available_edges = []
            try:
                from neomodel import adb
                # We fetch relationship properties, the stable elementId, and destination node_id
                query = f"""
                MATCH (n:EpisodeNode {{node_id: '{state.current_node}'}})-[r:LEADS_TO]->(m:EpisodeNode)
                RETURN r, elementId(r), m.node_id
                """
                res, _ = await adb.cypher_query(query)
                for row in res:
                    rel_data = row[0]   # Properties dictionary
                    edge_id = row[1]    # Stable database ID
                    target_id = row[2]  # Destination node identifier
                    
                    available_edges.append({
                        "edge_id": edge_id,
                        "action_intent": rel_data.get("action_intent", "Make a strategic choice"),
                        "required_role": rel_data.get("required_role"),
                        "alignment_shift": rel_data.get("alignment_shift"),
                        "capital_shift": rel_data.get("capital_shift", 0),
                        "sets_flag": rel_data.get("sets_flag"),
                        "target_node_id": target_id
                    })
            except Exception as e:
                print(f"[X] Hardened path traversal failed at node '{state.current_node}': {e}")
                await asyncio.sleep(2)
                continue  # Retry on next loop iteration

            if not available_edges:
                print(f"[!] Dead-end node with no outgoing edges: '{state.current_node}'")
                await websocket.send_json({
                    "type": "EPILOGUE",
                    "flavor": "The story has reached an unexpected end. This node has no paths forward."
                })
                break

            # ----------------------------------------------------------------
            # Step 5: Determine Spotlight (Leader)
            # ----------------------------------------------------------------
            required_role = available_edges[0]["required_role"]
            spotlight_player_id = next(
                (pid for pid, prof in state.active_players.items() if prof.role == required_role),
                None
            )

            # ----------------------------------------------------------------
            # Step 6: Mode-Based Interaction Loop
            # ----------------------------------------------------------------
            
            # Use Node Type to branch logic
            node_type = getattr(current_node, "node_type", "STORY")
            
            if node_type in ["STORY", "CHARACTERIZATION"]:
                if player_id == spotlight_player_id:
                    # Only generate AI narrative once per node
                    if state.current_node != last_ai_node:
                        try:
                            # Fetch the player's current profile for trait context
                            player_profile = state.active_players[player_id]
                            
                            narrative = await ai_engine.generate_spotlight_turn(
                                premise=current_node.skeleton_premise,
                                required_role=required_role,
                                db_choices=available_edges,
                                player_alignments=player_profile.alignments
                            )

                            # Broadcast narrative context to everyone
                            await socket_manager.broadcast_to_session(session_id, {
                                "type": "NARRATIVE_BEAT",
                                "flavor": narrative.flavor_text,
                                "spotlight_role": required_role,
                                "spotlight_player": spotlight_player_id,
                                "phase": node_type
                            })

                            # Send choices ONLY to spotlight
                            await websocket.send_json({
                                "type": "SPOTLIGHT_CHOICE",
                                "options": [opt.model_dump() for opt in narrative.options]
                            })

                            last_ai_node = state.current_node
                        except Exception as ai_err:
                            print(f"[!] AI Director failed: {ai_err}")
                            await websocket.send_json({"type": "WARNING", "msg": "Narrative Engine Lagging. Retrying..."})
                            await asyncio.sleep(3)
                            continue

                    # Wait for input
                    try:
                        client_msg = await websocket.receive_json()
                    except Exception: break
                    
                    chosen_edge_id = str(client_msg.get("edge_id") or client_msg.get("choice_id", ""))
                else:
                    # Follower Path: Passive sleep
                    await asyncio.sleep(2)
                    continue

            elif node_type == "POLL":
                # Everyone is in the spotlight for a Poll
                if player_id not in state.votes:
                    await websocket.send_json({
                        "type": "POLL_REQUEST",
                        "options": [{"id": e["edge_id"], "text": e["action_intent"]} for e in available_edges],
                        "msg": "GLOBAL VOTE REQUIRED. The majority will decide the path."
                    })
                    
                    try:
                        client_msg = await websocket.receive_json()
                        vote_id = client_msg.get("choice_id") or client_msg.get("edge_id")
                        if vote_id:
                            state.votes[player_id] = vote_id
                            await state_manager.client.set(f"game:{session_id}", state.model_dump_json())
                    except Exception: break
                
                # Check if all votes are in
                if len(state.votes) < len(state.active_players):
                    await websocket.send_json({"type": "WAITING", "msg": f"Waiting for votes... ({len(state.votes)}/{len(state.active_players)})"})
                    await asyncio.sleep(2)
                    continue
                else:
                    # Resolve Poll
                    vote_counts = {}
                    for vid in state.votes.values():
                        vote_counts[vid] = vote_counts.get(vid, 0) + 1
                    
                    # Sort to find majority
                    winner_id = max(vote_counts, key=vote_counts.get)
                    chosen_edge_id = winner_id
                    # Clear votes for next session
                    state.votes = {}

            elif node_type == "INTERROGATION":
                # Special PvP Mode (Automatic)
                # Ensure we only announce the start once
                if state.active_event != state.current_node:
                    print(f"[INTERROGATION] Triggered at {state.current_node}")
                    await socket_manager.broadcast_to_session(session_id, {
                        "type": "INTERROGATION_START",
                        "msg": f"CONFRONTATION: {required_role} is being interrogated!"
                    })
                    state.active_event = state.current_node
                    await state_manager.client.set(f"game:{session_id}", state.model_dump_json())
                
                # Fallback to Poll mechanism for the prototype
                node_type = "POLL" 
                continue # Re-run loop as POLL 

            else:
                # Default safety
                await asyncio.sleep(2)
                continue


            # ----------------------------------------------------------------
            # Step 7: Resolve Choice & Apply Consequences
            # ----------------------------------------------------------------
            if not chosen_edge_id or chosen_edge_id == "None":
                continue

            chosen_edge = next(
                (edge for edge in available_edges if edge["edge_id"] == chosen_edge_id),
                None
            )

            if not chosen_edge:
                await websocket.send_json({
                    "type": "ERROR",
                    "error": f"Choice ID '{chosen_edge_id}' did not match any available paths."
                })
                continue

            # Add to Session History for Gemini Finale
            state.session_history.append({
                "node": state.current_node,
                "role": required_role,
                "choice": chosen_edge["action_intent"]
            })

            # Apply consequences
            profile = state.active_players[player_id]
            alignment = chosen_edge["alignment_shift"]
            if alignment:
                profile.alignments.append(alignment)
                # AUTO-TRAIT CALCULATION: After 3 alignments, set a primary trait
                if len(profile.alignments) >= 3 and not profile.primary_trait:
                    from collections import Counter
                    most_common = Counter(profile.alignments).most_common(1)[0][0]
                    profile.primary_trait = most_common
                    print(f"[TRAIT] Player {player_id} is now '{profile.primary_trait}'")

            flag = chosen_edge["sets_flag"]
            if flag: profile.flags.append(flag)

            capital_delta = chosen_edge.get("capital_shift", 0) or 0
            state.global_capital += capital_delta

            # Advance Node
            next_node_id = chosen_edge["target_node_id"]
            state.current_node = next_node_id
            
            # CLEANUP: Prepare for next node
            state.active_event = None
            state.votes = {}

            # Save to Redis
            await state_manager.client.set(f"game:{session_id}", state.model_dump_json())
            print(f"[OK] Session '{session_id}' advanced: '{state.current_node}'")

            # Broadcast turn resolution
            await socket_manager.broadcast_to_session(session_id, {
                "type": "TURN_RESOLVED",
                "resolved_by": player_id,
                "role": required_role,
                "next_node": next_node_id,
                "msg": f"{required_role} has acted. The story flows..."
            })

    except WebSocketDisconnect:
        print(f"[WS] Player '{player_id}' disconnected from session '{session_id}'")
    except Exception as e:
        print(f"[X] Unhandled error in game loop for '{player_id}': {type(e).__name__}: {e}")
    finally:
        socket_manager.disconnect(session_id, player_id)
