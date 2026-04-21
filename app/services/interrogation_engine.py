"""
interrogation_engine.py – Interrogation scene logic.

Responsibilities:
- Look up a player by role
- Select instigator / target / answering triple from authored definitions or RNG fallback
- Build option payloads for an interrogation scene
- Build flavor text for the scene header
"""
import random
from typing import Dict, List, Optional

from app.design.content import INTERROGATIONS, beat_by_id, option_available
from app.models.schemas import GameState


def player_for_role(state: GameState, role: str) -> Optional[str]:
    """Return player_id whose assigned role matches *role*, or None."""
    return next(
        (pid for pid, profile in state.active_players.items() if profile.role == role),
        None,
    )


def choose_interrogation_pair(state: GameState) -> Dict[str, str]:
    """
    Derive the instigator / target / answering triple for the current node.

    If the beat has an authored interrogation definition, uses its participant
    roles so that instigator_role, target_role, and answering_role are all
    distinct and semantically meaningful.  Falls back to an RNG-seeded random
    pair where target == answering.
    """
    beat = beat_by_id(state.current_node)
    interrogation_id = beat.get("interrogation") if beat else None
    definition = INTERROGATIONS.get(interrogation_id or "")
    if definition:
        instigator_role = definition["participants"]["instigator_role"]
        target_role = definition["participants"]["target_role"]
        answering_role = definition["player_role"]
        return {
            "interrogation_id": interrogation_id,
            "instigator_player": player_for_role(state, instigator_role) or "",
            "instigator_role": instigator_role,
            "target_player": player_for_role(state, target_role) or "",
            "target_role": target_role,
            "answering_player": player_for_role(state, answering_role) or "",
            "answering_role": answering_role,
        }

    # Fallback: random pair, answering == target
    players = list(state.active_players.items())
    rng = random.Random(
        f"{state.session_id}:{state.current_node}:{state.global_capital}:{len(state.session_history)}"
    )
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


def next_node_after(current_node, master_beats: list) -> str:
    """Return the beat id that follows *current_node*, or a terminal fallback."""
    beat_ids = [beat["id"] for beat in master_beats]
    if current_node.node_id in beat_ids:
        index = beat_ids.index(current_node.node_id)
        if index + 1 < len(beat_ids):
            return beat_ids[index + 1]
    return "ending_broken_house"


def build_interrogation_payloads(
    pair: Dict[str, str],
    current_node,
    state: GameState,
    master_beats: list,
) -> List[Dict[str, object]]:
    """
    Build the list of choice payloads for an interrogation scene.

    Uses the authored option set when available; otherwise generates a single
    generic 'answer' payload.
    """
    definition = INTERROGATIONS.get(pair.get("interrogation_id") or "")
    target_node_id = next_node_after(current_node, master_beats)

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

    # Generic fallback payload
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


def build_interrogation_flavor(pair: Dict[str, str], current_node) -> str:
    """Return the flavor-text header string for an interrogation scene."""
    definition = INTERROGATIONS.get(pair.get("interrogation_id") or "")
    if not definition:
        return (
            f"{current_node.skeleton_premise} "
            f"{pair['instigator_role']} corners {pair['target_role']} in a tense private exchange."
        )
    return (
        f"{definition['setting']}\n\n"
        f"{definition['setup']}\n\n"
        f"{pair['instigator_role']}: \"{definition['opening']}\""
    )
