"""
choice_resolver.py – Choice application logic.

Responsibilities:
- Apply a player's choice (spotlight or poll) to the game state
- Resolve poll votes and elect the winner
- Mutate state axes, lane weights, story flags, spotlight counts
- Advance to the next node or terminal node
"""
from collections import Counter
from typing import Dict, List, Optional

from app.design.content import MASTER_BEATS, ROLES, resolve_lane, terminal_for_lane
from app.models.schemas import GameState
from app.services.ai_engine import ai_engine
from app.services.graph_store import fetch_node
from app.services.state import state_manager

GROUP_NODE_TYPES = {"POLL"}


# ---------------------------------------------------------------------------
# Pure state-mutation helpers
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


def apply_axis_effects(state: GameState, effects: Optional[Dict[str, int]]) -> None:
    for key, delta in (effects or {}).items():
        state.state_axes[key] = int(state.state_axes.get(key, 0)) + int(delta)


def apply_lane_effects(state: GameState, lanes: Optional[Dict[str, int]]) -> None:
    for key, delta in (lanes or {}).items():
        state.lane_weights[key] = int(state.lane_weights.get(key, 0)) + int(delta)


def add_story_flags(state: GameState, flags: Optional[List[str]]) -> None:
    for flag in flags or []:
        if flag not in state.story_flags:
            state.story_flags.append(flag)


def derive_primary_trait(profile) -> None:
    if len(profile.alignments) >= 3:
        profile.primary_trait = Counter(profile.alignments).most_common(1)[0][0]


async def _resolve_group_actor(state: GameState, edge: Dict[str, object]) -> Optional[str]:
    role = edge.get("required_role")
    if not role:
        return None
    return next(
        (pid for pid, profile in state.active_players.items() if profile.role == role), None
    )


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

async def apply_choice(
    session_id: str,
    player_id: str,
    choice_id: str,
    state_axes_defaults: dict,
    lane_weights_defaults: dict,
) -> GameState:
    """
    Apply a player's choice to the session state.

    For GROUP nodes this records a vote and resolves once all players have voted.
    For SPOTLIGHT nodes only the current scene player may submit.
    Returns the saved state.
    """
    async with state_manager.session_lock(session_id):
        state = await state_manager.get_state(session_id)
        if not state:
            raise ValueError("Session not found")
        if state.ended:
            return await state_manager.save_state(state)
        if state.current_scene_node != state.current_node:
            raise ValueError("Scene is out of date. Wait for the next update.")

        _ensure_design_state(state, state_axes_defaults, lane_weights_defaults)

        current_node = await fetch_node(state.current_node)
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
                key=lambda cid: (
                    sum(vote == cid for vote in state.votes.values()),
                    -ordered_choice_ids.index(cid),
                ),
            )
            chosen_edge = edge_map[winner]
            acting_player_id = await _resolve_group_actor(state, chosen_edge) or player_id
        elif state.current_scene_player != player_id:
            raise ValueError("Only the spotlight player can submit this choice.")

        # Record history
        state.session_history.append(
            {
                "node": state.current_node,
                "role": state.current_scene_role or chosen_edge["required_role"] or "COUNCIL",
                "choice": chosen_edge["action_intent"],
            }
        )

        # Apply effects
        apply_axis_effects(state, chosen_edge.get("effects"))
        apply_lane_effects(state, chosen_edge.get("lanes"))
        add_story_flags(state, chosen_edge.get("story_flags"))

        # Breakdown aftermath
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

        # Update acting player profile
        if acting_player_id in state.active_players:
            profile = state.active_players[acting_player_id]
            alignment = chosen_edge.get("alignment_shift")
            if alignment:
                profile.alignments.append(alignment)
                derive_primary_trait(profile)

            flag = chosen_edge.get("sets_flag")
            if flag and flag not in profile.flags:
                profile.flags.append(flag)
            if flag:
                add_story_flags(state, [flag])

        state.global_capital += int(chosen_edge.get("capital_shift") or 0)

        # Update spotlight count for non-group scenes
        if state.current_scene_role in ROLES and state.current_scene_type not in GROUP_NODE_TYPES:
            state.spotlight_counts[state.current_scene_role] = (
                int(state.spotlight_counts.get(state.current_scene_role, 0)) + 1
            )

        # Clear scene
        state.votes = {}
        state.active_event = None
        state.current_scene_node = None
        state.current_scene_flavor = None
        state.current_choices = []
        state.current_choice_payloads = []

        # If advance_node is False and not a group node, just increment round
        if not chosen_edge.get("advance_node") and current_node.node_type not in GROUP_NODE_TYPES:
            state.current_scene_round += 1
            return await state_manager.save_state(state)

        # Advance to next node
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
