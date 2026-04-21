"""
scene_engine.py – Scene preparation logic.

Responsibilities:
- Validate edge availability for the current state
- Select spotlight role / player
- Build stance-variant spotlight payloads
- Orchestrate INTERROGATION, POLL, and CHARACTERIZATION scene setup
- Return updated state (saved) after scene preparation
"""
from typing import Dict, List, Optional, Tuple

from app.design.content import (
    CHAPTER_ANCHORS,
    ROLES,
    chapter_for_node,
)
from app.models.schemas import ChoiceView, GameState
from app.services.ai_engine import ai_engine
from app.services.graph_store import fetch_edges, fetch_node
from app.services.interrogation_engine import (
    build_interrogation_flavor,
    build_interrogation_payloads,
    choose_interrogation_pair,
)
from app.services.state import state_manager

GROUP_NODE_TYPES = {"POLL"}
ROLE_PRIORITY = ["Raghava Rao", "Govardhan Naidu", "Saraswathi", "Venkatadri"]


# ---------------------------------------------------------------------------
# Edge availability
# ---------------------------------------------------------------------------

def edge_is_available(edge: Dict[str, object], state: GameState) -> bool:
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


# ---------------------------------------------------------------------------
# Spotlight helpers
# ---------------------------------------------------------------------------

def _player_influence(profile) -> int:
    return (len(profile.alignments) * 3) + (len(profile.flags) * 2) + (2 if profile.primary_trait else 0)


def select_spotlight_role(
    eligible_edges: List[Dict[str, object]], state: GameState
) -> Tuple[Optional[str], Optional[str]]:
    """Return (role, player_id) for the next spotlight actor."""
    best: Optional[Tuple[int, int, int, int, str, str]] = None
    for edge_index, edge in enumerate(eligible_edges):
        role = edge["required_role"]
        player_id = next(
            (pid for pid, profile in state.active_players.items() if profile.role == role),
            None,
        )
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


def build_spotlight_payloads(
    edges: List[Dict[str, object]], round_number: int
) -> List[Dict[str, object]]:
    """Build three spotlight choice payloads (original edge + stance variants)."""
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


# ---------------------------------------------------------------------------
# Design-state initialisation (guard for missing defaults)
# ---------------------------------------------------------------------------

def _ensure_design_state(state: GameState, state_axes_defaults, lane_weights_defaults) -> None:
    if not state.state_axes:
        state.state_axes = dict(state_axes_defaults)
    else:
        for key, value in state_axes_defaults.items():
            state.state_axes.setdefault(key, value)
    if not state.lane_weights:
        state.lane_weights = dict(lane_weights_defaults)
    else:
        for key, value in lane_weights_defaults.items():
            state.lane_weights.setdefault(key, value)
    if not state.spotlight_counts:
        state.spotlight_counts = {role: 0 for role in ROLES}
    else:
        for role in ROLES:
            state.spotlight_counts.setdefault(role, 0)


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

async def prepare_scene(
    session_id: str,
    state_axes_defaults: dict,
    lane_weights_defaults: dict,
    master_beats: list,
) -> GameState:
    """
    Prepare the current scene for a session.

    Idempotent: if scene is already prepared for the current node, returns
    state unchanged.  Saves and returns the mutated state on a fresh prep.
    """
    async with state_manager.session_lock(session_id):
        state = await state_manager.get_state(session_id)
        if not state or state.status != "ACTIVE" or state.ended:
            return state
        _ensure_design_state(state, state_axes_defaults, lane_weights_defaults)
        if state.current_scene_node == state.current_node and state.current_choices:
            return state

        current_node = await fetch_node(state.current_node)
        if current_node.is_terminal:
            return state

        all_edges = await fetch_edges(state.current_node)
        eligible_edges = [edge for edge in all_edges if edge_is_available(edge, state)]
        if not eligible_edges:
            raise ValueError(f"No valid choices available for node '{state.current_node}'")

        state.current_scene_node = state.current_node
        state.current_scene_type = current_node.node_type
        state.current_scene_flavor = current_node.skeleton_premise
        state.current_choices = []
        state.current_choice_payloads = []
        state.active_event = None

        if current_node.node_type == "INTERROGATION":
            pair = state.current_interrogation_pair or choose_interrogation_pair(state)
            interrogation_payloads = build_interrogation_payloads(
                pair, current_node, state, master_beats
            )
            state.current_interrogation_pair = pair
            state.current_scene_role = pair.get("answering_role") or pair["target_role"]
            state.current_scene_player = pair.get("answering_player") or pair["target_player"]
            state.current_scene_round = 1
            state.current_scene_total_rounds = 1
            state.current_scene_flavor = build_interrogation_flavor(pair, current_node)
            state.current_choice_payloads = interrogation_payloads
            state.current_choices = [
                ChoiceView(
                    choice_id=payload["choice_id"],
                    text=payload["action_intent"],
                    role=state.current_scene_role,
                )
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
                    text=option_lookup.get(edge["choice_id"]).text
                    if option_lookup.get(edge["choice_id"])
                    else edge["action_intent"],
                    role=edge["required_role"],
                    subtext=option_lookup.get(edge["choice_id"]).subtext
                    if option_lookup.get(edge["choice_id"])
                    else None,
                )
                for edge in eligible_edges
            ]

        else:  # CHARACTERIZATION / default spotlight
            spotlight_role = state.current_scene_role
            spotlight_player = state.current_scene_player
            round_number = state.current_scene_round or 1

            if not spotlight_role or not spotlight_player:
                spotlight_role, spotlight_player = select_spotlight_role(eligible_edges, state)
                round_number = 1

            if not spotlight_role or not spotlight_player:
                raise ValueError(
                    f"No eligible acting role found for node '{state.current_node}'"
                )

            spotlight_edges = [
                edge for edge in eligible_edges if edge["required_role"] == spotlight_role
            ]
            if not spotlight_edges:
                spotlight_role, spotlight_player = select_spotlight_role(eligible_edges, state)
                spotlight_edges = [
                    edge for edge in eligible_edges if edge["required_role"] == spotlight_role
                ]

            spotlight_payloads = build_spotlight_payloads(spotlight_edges, round_number)
            player_profile = state.active_players[spotlight_player]
            anchor = CHAPTER_ANCHORS.get(chapter_for_node(state.current_node), {})
            narrative = await ai_engine.generate_spotlight_turn(
                premise=current_node.skeleton_premise,
                required_role=spotlight_role,
                db_choices=spotlight_payloads,
                player_alignments=player_profile.alignments,
                anchor=anchor,
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
                    text=option_lookup.get(payload["choice_id"]).text
                    if option_lookup.get(payload["choice_id"])
                    else payload["action_intent"],
                    role=spotlight_role,
                    subtext=option_lookup.get(payload["choice_id"]).subtext
                    if option_lookup.get(payload["choice_id"])
                    else None,
                )
                for payload in spotlight_payloads
            ]

        return await state_manager.save_state(state)
