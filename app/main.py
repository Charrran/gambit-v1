"""
Gambit Engine - main application and authoritative scene loop.

Major beats stay authored in Neo4j while player-facing choices are generated
inside the constraints of the current scene. Session state is cached in-process
to keep Redis usage low.
"""
import os
import random
import uuid
from collections import Counter
from typing import Dict, List, Optional, Tuple

import neomodel
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from neomodel import adb
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
    INTERROGATIONS,
    INTRO_CONTEXT,
    LANE_WEIGHTS,
    MASTER_BEATS,
    ROLES,
    STATE_AXES,
    beat_by_id,
    chapter_for_node,
    option_available,
    resolve_lane,
    terminal_for_lane,
)
from app.models.graph import EpisodeNode
from app.models.schemas import ChoiceView, HealthResponse
from app.services.ai_engine import ai_engine
from app.services.state import state_manager

ROLE_PRIORITY = ["Raghava Rao", "Govardhan Naidu", "Saraswathi", "Venkatadri"]
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


def _player_influence(profile) -> int:
    return (len(profile.alignments) * 3) + (len(profile.flags) * 2) + (2 if profile.primary_trait else 0)


def _derive_primary_trait(profile) -> None:
    if len(profile.alignments) >= 3:
        profile.primary_trait = Counter(profile.alignments).most_common(1)[0][0]


def _ensure_design_state(state) -> None:
    if not state.state_axes:
        state.state_axes = dict(STATE_AXES)
    else:
        for key, value in STATE_AXES.items():
            state.state_axes.setdefault(key, value)
    if not state.lane_weights:
        state.lane_weights = dict(LANE_WEIGHTS)
    else:
        for key, value in LANE_WEIGHTS.items():
            state.lane_weights.setdefault(key, value)
    if not state.spotlight_counts:
        state.spotlight_counts = {role: 0 for role in ROLES}
    else:
        for role in ROLES:
            state.spotlight_counts.setdefault(role, 0)


def _apply_axis_effects(state, effects: Dict[str, int] | None) -> None:
    _ensure_design_state(state)
    for key, delta in (effects or {}).items():
        state.state_axes[key] = int(state.state_axes.get(key, 0)) + int(delta)


def _apply_lane_effects(state, lanes: Dict[str, int] | None) -> None:
    _ensure_design_state(state)
    for key, delta in (lanes or {}).items():
        state.lane_weights[key] = int(state.lane_weights.get(key, 0)) + int(delta)


def _add_story_flags(state, flags: List[str] | None) -> None:
    for flag in flags or []:
        if flag not in state.story_flags:
            state.story_flags.append(flag)


def _edge_is_available(edge: Dict[str, object], state) -> bool:
    player_count = len(state.active_players)
    min_players = edge.get("min_players")
    max_players = edge.get("max_players")
    min_capital = edge.get("min_capital")
    max_capital = edge.get("max_capital")
    requires_flag = edge.get("requires_flag")

    if min_players is not None and player_count < min_players:
        return False
    if max_players is not None and player_count > max_players:
        return False
    if min_capital is not None and state.global_capital < min_capital:
        return False
    if max_capital is not None and state.global_capital > max_capital:
        return False
    if not requires_flag:
        return True

    all_flags = {flag for profile in state.active_players.values() for flag in profile.flags}
    return requires_flag in all_flags


def _fallback_choice_id(node_id: str, props: Dict[str, object]) -> str:
    role = str(props.get("required_role") or "choice").lower().replace(" ", "_")
    action = str(props.get("action_intent") or "option").lower()
    action = "".join(ch if ch.isalnum() else "_" for ch in action).strip("_")
    return f"{node_id}_{role}_{action[:24]}"


def _choice_design_payload(choice_id: str) -> Dict[str, object]:
    for beat in (beat for beat in MASTER_BEATS if beat.get("choices")):
        for raw in beat["choices"]:
            if raw[0] == choice_id:
                return {"effects": raw[2], "lanes": raw[3]}
    return {"effects": {}, "lanes": {}}


async def _fetch_node(node_id: str):
    results, _ = await adb.cypher_query(
        "MATCH (n:EpisodeNode {node_id: $node_id}) RETURN n",
        {"node_id": node_id},
    )
    if not results:
        raise EpisodeNode.DoesNotExist(f"Node '{node_id}' not found")
    return EpisodeNode.inflate(results[0][0])


async def _fetch_edges(node_id: str) -> List[Dict[str, object]]:
    results, _ = await adb.cypher_query(
        """
        MATCH (n:EpisodeNode {node_id: $node_id})-[r:LEADS_TO]->(m:EpisodeNode)
        RETURN properties(r) as props, m.node_id as target_node_id
        """,
        {"node_id": node_id},
    )
    edges: List[Dict[str, object]] = []
    for props, target_node_id in results:
        choice_id = props.get("choice_id") or _fallback_choice_id(node_id, props)
        design_payload = _choice_design_payload(choice_id)
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


def _select_spotlight_role(eligible_edges: List[Dict[str, object]], state) -> Tuple[Optional[str], Optional[str]]:
    _ensure_design_state(state)
    best: Optional[Tuple[int, int, int, int, str, str]] = None
    for edge_index, edge in enumerate(eligible_edges):
        role = edge["required_role"]
        player_id = next((pid for pid, profile in state.active_players.items() if profile.role == role), None)
        if not player_id:
            continue

        influence = _player_influence(state.active_players[player_id])
        spotlight_debt = -int(state.spotlight_counts.get(role, 0))
        priority = ROLE_PRIORITY.index(role) if role in ROLE_PRIORITY else len(ROLE_PRIORITY)
        candidate = (spotlight_debt, influence, -priority, -edge_index, role, player_id)
        if best is None or candidate > best:
            best = candidate

    if best is None:
        return None, None

    return best[4], best[5]


def _stance_variants(round_number: int) -> List[Tuple[str, str, int, Optional[str], Optional[str]]]:
    if round_number == 1:
        return [
            ("press", "Escalate and seize the initiative immediately.", 10, "ASSERTIVE", None),
            ("maneuver", "Play a calculated middle move and test the room first.", 5, "CALCULATED", None),
            ("concede", "Soften the tone, buy time, and preserve leverage.", -5, "CONCILIATORY", None),
        ]
    return [
        ("deceive", "Hide your real hand and push a misleading line.", 0, "DECEPTIVE", "double_bluff"),
        ("deflect", "Redirect pressure onto the rival camp without overcommitting.", 5, "DEFENSIVE", None),
        ("commit", "Commit publicly and force the next beat to react to you.", 10, "DECISIVE", None),
    ]


def _build_spotlight_payloads(edges: List[Dict[str, object]], round_number: int) -> List[Dict[str, object]]:
    payloads: List[Dict[str, object]] = []

    for edge in edges:
        payloads.append(
            {
                "choice_id": edge["choice_id"],
                "action_intent": edge["action_intent"],
                "required_role": edge.get("required_role"),
                "target_node_id": edge["target_node_id"],
                "capital_shift": int(edge.get("capital_shift") or 0),
                "alignment_shift": edge.get("alignment_shift"),
                "sets_flag": edge.get("sets_flag"),
                "effects": edge.get("effects", {}),
                "lanes": edge.get("lanes", {}),
                "advance_node": False,
            }
        )

    primary = edges[0]
    for stance_id, directive, capital_delta, alignment, flag in _stance_variants(round_number):
        if len(payloads) >= 3:
            break
        payloads.append(
            {
                "choice_id": f"{primary['choice_id']}__{stance_id}_r{round_number}",
                "action_intent": f"{primary['action_intent']} Then {directive}",
                "required_role": primary.get("required_role"),
                "target_node_id": primary["target_node_id"],
                "capital_shift": int(primary.get("capital_shift") or 0) + capital_delta,
                "alignment_shift": alignment,
                "sets_flag": flag,
                "effects": primary.get("effects", {}),
                "lanes": primary.get("lanes", {}),
                "advance_node": False,
            }
        )

    for payload in payloads:
        payload["advance_node"] = True

    return payloads[:3]


def _player_for_role(state, role: str) -> Optional[str]:
    return next((pid for pid, profile in state.active_players.items() if profile.role == role), None)


def _choose_interrogation_pair(state, current_node=None) -> Dict[str, str]:
    beat = beat_by_id(state.current_node)
    interrogation_id = beat.get("interrogation") if beat else None
    definition = INTERROGATIONS.get(interrogation_id or "")
    if definition:
        instigator_role = definition["participants"]["instigator_role"]
        target_role = definition["participants"]["target_role"]
        answering_role = definition["player_role"]
        return {
            "interrogation_id": interrogation_id,
            "instigator_player": _player_for_role(state, instigator_role) or "",
            "instigator_role": instigator_role,
            "target_player": _player_for_role(state, target_role) or "",
            "target_role": target_role,
            "answering_player": _player_for_role(state, answering_role) or "",
            "answering_role": answering_role,
        }

    players = list(state.active_players.items())
    rng = random.Random(f"{state.session_id}:{state.current_node}:{state.global_capital}:{len(state.session_history)}")
    anchor_player_id, anchor_profile = rng.choice(players)
    opponents = [(pid, profile) for pid, profile in players if pid != anchor_player_id]
    target_player_id, target_profile = rng.choice(opponents)
    return {
        "interrogation_id": "",
        "instigator_player": anchor_player_id,
        "instigator_role": anchor_profile.role or "Unknown",
        "target_player": target_player_id,
        "target_role": target_profile.role or "Unknown",
        "answering_player": target_player_id,
        "answering_role": target_profile.role or "Unknown",
    }


def _next_node_after(current_node) -> str:
    beat_ids = [beat["id"] for beat in MASTER_BEATS]
    if current_node.node_id in beat_ids:
        index = beat_ids.index(current_node.node_id)
        if index + 1 < len(beat_ids):
            return beat_ids[index + 1]
    return "ending_broken_house"


def _build_interrogation_payloads(pair: Dict[str, str], current_node, state) -> List[Dict[str, object]]:
    definition = INTERROGATIONS.get(pair.get("interrogation_id") or "")
    target_node_id = _next_node_after(current_node)
    if definition:
        payloads = []
        for option in definition["options"]:
            if not option_available(option, state.state_axes):
                continue
            choice_id = f"{current_node.node_id}__{option['id'].lower()}"
            flags = list(option.get("flags", []))
            flags.append(f"interrogation_{pair['interrogation_id']}_{option['id'].lower()}")
            payloads.append(
                {
                    "choice_id": choice_id,
                    "action_intent": option["text"],
                    "required_role": definition["player_role"],
                    "target_node_id": target_node_id,
                    "capital_shift": 0,
                    "alignment_shift": "BREAKDOWN" if "breakdown" in flags else "INTERROGATION",
                    "sets_flag": flags[0] if flags else None,
                    "story_flags": flags,
                    "effects": option.get("effects", {}),
                    "lanes": option.get("lanes", {}),
                    "advance_node": True,
                }
            )
        return payloads[:4]

    target_role = pair["target_role"]
    return [
        {
            "choice_id": f"{current_node.node_id}__answer",
            "action_intent": f"{target_role} answers the accusation and accepts the cost.",
            "required_role": target_role,
            "target_node_id": target_node_id,
            "capital_shift": 0,
            "alignment_shift": "INTERROGATION",
            "sets_flag": "interrogation_answer",
            "story_flags": ["interrogation_answer"],
            "effects": {"betrayal_heat": 1},
            "lanes": {"broken_house": 1},
            "advance_node": True,
        },
    ]


def _interrogation_flavor(pair: Dict[str, str], current_node) -> str:
    definition = INTERROGATIONS.get(pair.get("interrogation_id") or "")
    if not definition:
        return f"{current_node.skeleton_premise} {pair['instigator_role']} corners {pair['target_role']} in a tense private exchange."
    return (
        f"{definition['setting']}\n\n"
        f"{definition['setup']}\n\n"
        f"{pair['instigator_role']}: \"{definition['opening']}\""
    )


async def _ensure_finale(session_id: str):
    async with state_manager.session_lock(session_id):
        state = await state_manager.get_state(session_id)
        if not state:
            return None
        if state.ended and state.final_result:
            return state

        current_node = await _fetch_node(state.current_node)
        if not current_node.is_terminal:
            return state

        if not state.session_history or state.session_history[-1]["node"] != current_node.node_id:
            state.session_history.append({"node": current_node.node_id, "role": "SYSTEM", "choice": "THE END"})

        try:
            if not state.resolved_lane:
                state.resolved_lane = resolve_lane(state.lane_weights, state.state_axes)
            historian_text = await ai_engine.generate_historian_ending(
                resolved_lane=state.resolved_lane,
                final_state_snapshot=state.state_axes,
                all_flags=state.story_flags,
                pivotal_decisions=state.session_history,
            )
            comparison = await ai_engine.generate_canonical_comparison(
                session_history=state.session_history,
                global_capital=state.global_capital,
                resolved_lane=state.resolved_lane,
                final_state_snapshot=state.state_axes,
            )
            state.final_result = {
                "type": "GAME_OVER",
                "ending_node": current_node.node_id,
                "resolved_lane": state.resolved_lane,
                "historian_ending": historian_text,
                "comparison": comparison.model_dump(),
                "canonical_ending": comparison.canonical_summary,
                "divergence_analysis": comparison.divergence_analysis,
                "state_axes": state.state_axes,
                "lane_weights": state.lane_weights,
            }
        except Exception as exc:
            print(f"[!] Finale Generation Failed: {exc}")
            state.final_result = {
                "type": "GAME_OVER",
                "ending_node": current_node.node_id,
                "flavor": current_node.skeleton_premise,
                "historical_note": current_node.canonical_outcome,
            }

        state.ended = True
        return await state_manager.save_state(state)


async def _prepare_scene(session_id: str):
    async with state_manager.session_lock(session_id):
        state = await state_manager.get_state(session_id)
        if not state or state.status != "ACTIVE" or state.ended:
            return state
        _ensure_design_state(state)
        if state.current_scene_node == state.current_node and state.current_choices:
            return state

        current_node = await _fetch_node(state.current_node)
        if current_node.is_terminal:
            return state

        all_edges = await _fetch_edges(state.current_node)
        eligible_edges = [edge for edge in all_edges if _edge_is_available(edge, state)]
        if not eligible_edges:
            raise ValueError(f"No valid choices available for node '{state.current_node}'")

        state.current_scene_node = state.current_node
        state.current_scene_type = current_node.node_type
        state.current_scene_flavor = current_node.skeleton_premise
        state.current_choices = []
        state.current_choice_payloads = []
        state.active_event = None

        if current_node.node_type == "INTERROGATION":
            pair = state.current_interrogation_pair or _choose_interrogation_pair(state, current_node)
            interrogation_payloads = _build_interrogation_payloads(pair, current_node, state)
            state.current_interrogation_pair = pair
            state.current_scene_role = pair.get("answering_role") or pair["target_role"]
            state.current_scene_player = pair.get("answering_player") or pair["target_player"]
            state.current_scene_round = 1
            state.current_scene_total_rounds = 1
            state.current_scene_flavor = _interrogation_flavor(pair, current_node)
            state.current_choice_payloads = interrogation_payloads
            state.current_choices = [
                ChoiceView(choice_id=payload["choice_id"], text=payload["action_intent"], role=state.current_scene_role)
                for payload in interrogation_payloads
            ]
        elif current_node.node_type in GROUP_NODE_TYPES:
            anchor = CHAPTER_ANCHORS.get(chapter_for_node(state.current_node), {})
            narrative = await ai_engine.generate_poll_turn(
                premise=current_node.skeleton_premise,
                db_choices=eligible_edges,
                anchor=anchor,
                state_snapshot=state.state_axes,
                lane_weights=state.lane_weights,
            )
            option_lookup = {option.choice_id: option for option in narrative.options}
            state.current_scene_role = "COUNCIL"
            state.current_scene_player = None
            state.current_scene_round = 1
            state.current_scene_total_rounds = 1
            state.current_scene_flavor = narrative.flavor_text
            state.current_choice_payloads = eligible_edges
            state.current_choices = [
                ChoiceView(
                    choice_id=edge["choice_id"],
                    text=option_lookup.get(edge["choice_id"]).text if option_lookup.get(edge["choice_id"]) else edge["action_intent"],
                    role=edge["required_role"],
                    subtext=option_lookup.get(edge["choice_id"]).subtext if option_lookup.get(edge["choice_id"]) else None,
                )
                for edge in eligible_edges
            ]
        else:
            spotlight_role = state.current_scene_role
            spotlight_player = state.current_scene_player
            round_number = state.current_scene_round or 1

            if not spotlight_role or not spotlight_player:
                spotlight_role, spotlight_player = _select_spotlight_role(eligible_edges, state)
                round_number = 1

            if not spotlight_role or not spotlight_player:
                raise ValueError(f"No eligible acting role found for node '{state.current_node}'")

            spotlight_edges = [edge for edge in eligible_edges if edge["required_role"] == spotlight_role]
            if not spotlight_edges:
                spotlight_role, spotlight_player = _select_spotlight_role(eligible_edges, state)
                spotlight_edges = [edge for edge in eligible_edges if edge["required_role"] == spotlight_role]

            spotlight_payloads = _build_spotlight_payloads(spotlight_edges, round_number)
            player_profile = state.active_players[spotlight_player]
            narrative = await ai_engine.generate_spotlight_turn(
                premise=current_node.skeleton_premise,
                required_role=spotlight_role,
                db_choices=spotlight_payloads,
                player_alignments=player_profile.alignments,
                anchor=CHAPTER_ANCHORS.get(chapter_for_node(state.current_node), {}),
                state_snapshot=state.state_axes,
                compressed_history=state.session_history,
            )
            option_lookup = {option.choice_id: option for option in narrative.options}
            state.current_scene_role = spotlight_role
            state.current_scene_player = spotlight_player
            state.current_scene_round = round_number
            state.current_scene_total_rounds = 1
            state.current_scene_flavor = narrative.flavor_text
            state.current_choice_payloads = spotlight_payloads
            state.current_choices = [
                ChoiceView(
                    choice_id=payload["choice_id"],
                    text=option_lookup.get(payload["choice_id"]).text if option_lookup.get(payload["choice_id"]) else payload["action_intent"],
                    role=spotlight_role,
                    subtext=option_lookup.get(payload["choice_id"]).subtext if option_lookup.get(payload["choice_id"]) else None,
                )
                for payload in spotlight_payloads
            ]

        return await state_manager.save_state(state)


async def _resolve_group_actor(state, edge: Dict[str, object]) -> Optional[str]:
    role = edge.get("required_role")
    if not role:
        return None
    return next((pid for pid, profile in state.active_players.items() if profile.role == role), None)


async def _apply_choice(session_id: str, player_id: str, choice_id: str):
    async with state_manager.session_lock(session_id):
        state = await state_manager.get_state(session_id)
        if not state:
            raise ValueError("Session not found")
        if state.ended:
            return await state_manager.save_state(state)
        if state.current_scene_node != state.current_node:
            raise ValueError("Scene is out of date. Wait for the next update.")

        current_node = await _fetch_node(state.current_node)
        edge_map = {edge["choice_id"]: edge for edge in state.current_choice_payloads}
        chosen_edge = edge_map.get(choice_id)
        if not chosen_edge:
            raise ValueError(f"Choice '{choice_id}' is not valid for this scene.")

        acting_player_id = player_id

        if current_node.node_type in GROUP_NODE_TYPES:
            if player_id in state.votes:
                raise ValueError("Vote already submitted for this scene.")
            state.votes[player_id] = choice_id
            await state_manager.save_state(state)
            if len(state.votes) < len(state.active_players):
                return state

            ordered_choice_ids = [choice.choice_id for choice in state.current_choices]
            winner = max(
                ordered_choice_ids,
                key=lambda cid: (sum(vote == cid for vote in state.votes.values()), -ordered_choice_ids.index(cid)),
            )
            chosen_edge = edge_map[winner]
            acting_player_id = await _resolve_group_actor(state, chosen_edge) or player_id
        elif state.current_scene_player != player_id:
            raise ValueError("Only the spotlight player can submit this choice.")

        state.session_history.append(
            {
                "node": state.current_node,
                "role": state.current_scene_role or chosen_edge["required_role"] or "COUNCIL",
                "choice": chosen_edge["action_intent"],
            }
        )
        _apply_axis_effects(state, chosen_edge.get("effects"))
        _apply_lane_effects(state, chosen_edge.get("lanes"))
        _add_story_flags(state, chosen_edge.get("story_flags"))
        if "breakdown" in (chosen_edge.get("story_flags") or []):
            state.last_aftermath = await ai_engine.generate_breakdown_aftermath(
                character_name=state.current_scene_role or chosen_edge.get("required_role") or "Unknown",
                breakdown_option_text=chosen_edge["action_intent"],
                relevant_state_flags=state.state_axes,
                scene_participants=state.current_interrogation_pair or {},
                relationship_flags=state.story_flags,
            )
        else:
            state.last_aftermath = None

        if acting_player_id in state.active_players:
            profile = state.active_players[acting_player_id]
            alignment = chosen_edge.get("alignment_shift")
            if alignment:
                profile.alignments.append(alignment)
                _derive_primary_trait(profile)

            flag = chosen_edge.get("sets_flag")
            if flag and flag not in profile.flags:
                profile.flags.append(flag)
            if flag:
                _add_story_flags(state, [flag])

        state.global_capital += int(chosen_edge.get("capital_shift") or 0)
        if state.current_scene_role in ROLES and state.current_scene_type not in GROUP_NODE_TYPES:
            state.spotlight_counts[state.current_scene_role] = int(state.spotlight_counts.get(state.current_scene_role, 0)) + 1
        state.votes = {}
        state.active_event = None
        state.current_scene_node = None
        state.current_scene_flavor = None
        state.current_choices = []
        state.current_choice_payloads = []

        if not chosen_edge.get("advance_node") and current_node.node_type not in GROUP_NODE_TYPES:
            state.current_scene_round += 1
            return await state_manager.save_state(state)

        if state.current_node == MASTER_BEATS[-1]["id"]:
            state.resolved_lane = resolve_lane(state.lane_weights, state.state_axes)
            state.current_node = terminal_for_lane(state.resolved_lane)
        else:
            state.current_node = chosen_edge["target_node_id"]
        state.current_scene_type = None
        state.current_scene_role = None
        state.current_scene_player = None
        state.current_scene_round = 0
        state.current_scene_total_rounds = 0
        state.current_interrogation_pair = None

        return await state_manager.save_state(state)


async def _send_scene_payload(websocket: WebSocket, state, player_id: str) -> None:
    if state.status != "ACTIVE":
        await websocket.send_json({"type": "WAITING", "msg": "Waiting for all players to join and the host to start..."})
        return

    if state.ended:
        await websocket.send_json(state.final_result or {"type": "GAME_OVER", "flavor": "The story ends here."})
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
            "chapter_title": CHAPTER_ANCHORS.get(chapter_for_node(state.current_scene_node or state.current_node), {}).get("title"),
            "state_axes": state.state_axes,
            "lane_weights": state.lane_weights,
            "aftermath": state.last_aftermath,
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
        message_type = "INTERROGATION_CHOICE" if state.current_scene_type == "INTERROGATION" else "SPOTLIGHT_CHOICE"
        await websocket.send_json({"type": message_type, "options": [choice.model_dump() for choice in state.current_choices]})
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


@app.get("/", response_model=HealthResponse)
async def health_check():
    return HealthResponse(status="Gambit Engine Online")


@app.get("/debug/db")
async def check_database():
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
                state = await _prepare_scene(session_id)
                state = await state_manager.get_state(session_id)
                if state and state.current_node:
                    current_node = await _fetch_node(state.current_node)
                    if current_node.is_terminal:
                        state = await _ensure_finale(session_id)

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
                await _apply_choice(session_id, player_id, choice_id)
            except ValueError as exc:
                await websocket.send_json({"type": "ERROR", "error": str(exc)})

    except WebSocketDisconnect:
        print(f"[WS] Player '{player_id}' disconnected from session '{session_id}'")
    except Exception as exc:
        print(f"[X] Unhandled error in game loop for '{player_id}': {type(exc).__name__}: {exc}")
        await websocket.send_json({"type": "FATAL_ERROR", "error": str(exc)})
    finally:
        socket_manager.disconnect(session_id, player_id)
