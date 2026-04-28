"""
scene_engine.py – Scene preparation logic.

Responsibilities:
- Validate edge availability for the current state
- State-reactive choice filtering: filter by requires/blocks, score and select top 3
- Select spotlight role / player
- Build stance-variant spotlight payloads
- Orchestrate INTERROGATION (with trigger skip), POLL, and CHARACTERIZATION scene setup
- Return updated state (saved) after scene preparation
"""
from typing import Dict, List, Optional, Tuple

from app.design.content import (
    CHAPTER_ANCHORS,
    MASTER_BEATS,
    ROLES,
    beat_by_id,
    chapter_for_node,
    choice_conditions_match,
    choice_relevance_score,
    normalize_choice,
    pressure_tags,
)
from app.models.schemas import ChoiceView, GameState
from app.services.ai_engine import ai_engine
from app.services.graph_store import fetch_edges, fetch_node
from app.services.interrogation_engine import (
    build_interrogation_flavor,
    build_interrogation_payloads,
    choose_interrogation_pair,
    interrogation_should_fire,
)
from app.services.state import state_manager

GROUP_NODE_TYPES = {"POLL"}
ROLE_PRIORITY = ["Raghava Rao", "Govardhan Naidu", "Saraswathi", "Venkatadri"]


# ---------------------------------------------------------------------------
# Edge availability (graph-level guards — player count, capital, flags)
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
# State-reactive choice pool resolution
# ---------------------------------------------------------------------------

def _authored_choices_for_beat(beat: Optional[Dict]) -> List[Dict]:
    """Return normalized authored choices for a beat dict, or empty list."""
    if not beat:
        return []
    return [normalize_choice(c) for c in beat.get("choices", [])]


def _tag_diversity_penalty(choice: Dict, already_selected: List[Dict]) -> float:
    """Return a small penalty if this choice shares all tags with selected choices."""
    tags = set(choice.get("tags", []))
    if not tags:
        return 0.0
    for sel in already_selected:
        sel_tags = set(sel.get("tags", []))
        if sel_tags and tags and tags == sel_tags:
            return 0.8
    return 0.0


def select_reactive_choices(
    candidate_choices: List[Dict],
    state_axes: Dict[str, int],
    lane_weights: Dict[str, int],
    story_flags: List[str],
    target_count: int = 3,
) -> List[Dict]:
    """
    From a pool of normalized authored choices, return exactly *target_count*
    visible choices using the following pipeline:

    1. Filter out choices whose requires/blocks conditions do not match.
    2. If fewer than target_count survive, backfill with unconditional choices.
    3. Score the eligible set by priority + state relevance.
    4. Pick top-scoring choices while preferring tag diversity.
    """
    eligible = [c for c in candidate_choices if choice_conditions_match(c, state_axes, story_flags)]
    unconditional = [c for c in candidate_choices if not c.get("requires") and not c.get("blocks")]

    # Backfill so we always have target_count options
    if len(eligible) < target_count:
        for uc in unconditional:
            if uc not in eligible:
                eligible.append(uc)
            if len(eligible) >= target_count:
                break

    if len(eligible) <= target_count:
        return eligible[:target_count]

    # Score and pick top target_count with diversity preference
    scored = sorted(
        eligible,
        key=lambda c: choice_relevance_score(c, state_axes, lane_weights, story_flags),
        reverse=True,
    )
    selected: List[Dict] = []
    for c in scored:
        penalty = _tag_diversity_penalty(c, selected)
        adjusted = choice_relevance_score(c, state_axes, lane_weights, story_flags) - penalty
        if len(selected) < target_count:
            selected.append(c)
        elif adjusted > min(
            choice_relevance_score(s, state_axes, lane_weights, story_flags) for s in selected
        ):
            # Replace lowest scorer
            lowest_idx = min(
                range(len(selected)),
                key=lambda i: choice_relevance_score(selected[i], state_axes, lane_weights, story_flags),
            )
            selected[lowest_idx] = c

    return selected[:target_count]


def _reactive_payloads_for_beat(
    beat: Optional[Dict],
    eligible_edges: List[Dict],
    state: GameState,
) -> List[Dict]:
    """
    Merge graph edges with authored choices, apply state-reactive filtering,
    and return a payload list suitable for passing to Groq / building ChoiceViews.

    The graph edge determines target_node_id.  The authored choice provides
    effects, lanes, requires, blocks, tags, priority.
    """
    authored = _authored_choices_for_beat(beat)

    # Build a lookup: authored choice_id -> authored dict
    authored_map = {c["id"]: c for c in authored}

    # Build a lookup: authored choice_id -> graph edge (for target)
    edge_map = {e["choice_id"]: e for e in eligible_edges}

    # The graph is the authority on which choice_ids exist.
    # Enrich edge payloads with authored metadata where available.
    enriched: List[Dict] = []
    for edge in eligible_edges:
        cid = edge.get("choice_id", "")
        authored_meta = authored_map.get(cid, {})
        enriched.append({
            **edge,
            "effects": authored_meta.get("effects", edge.get("effects", {})),
            "lanes": authored_meta.get("lanes", edge.get("lanes", {})),
            "requires": authored_meta.get("requires", []),
            "blocks": authored_meta.get("blocks", []),
            "priority": authored_meta.get("priority", 5),
            "tags": authored_meta.get("tags", []),
            "action_intent": authored_meta.get("text") or edge.get("action_intent", ""),
        })

    # For authored choices that are NOT yet seeded (new conditional ones), we
    # fall through to authored-only mode using graph's first available edge target.
    fallback_target = eligible_edges[0]["target_node_id"] if eligible_edges else "ending_broken_house"
    for ac in authored:
        if ac["id"] not in edge_map:
            enriched.append({
                "choice_id": ac["id"],
                "action_intent": ac["text"],
                "required_role": eligible_edges[0].get("required_role", "COUNCIL") if eligible_edges else "COUNCIL",
                "target_node_id": fallback_target,
                "capital_shift": 0,
                "alignment_shift": "DECISIVE",
                "sets_flag": None,
                "effects": ac.get("effects", {}),
                "lanes": ac.get("lanes", {}),
                "requires": ac.get("requires", []),
                "blocks": ac.get("blocks", []),
                "priority": ac.get("priority", 5),
                "tags": ac.get("tags", []),
                "advance_node": True,
            })

    state_axes = state.state_axes or {}
    lane_wts = state.lane_weights or {}
    story_flags = state.story_flags or []

    selected = select_reactive_choices(enriched, state_axes, lane_wts, story_flags, target_count=3)
    for payload in selected:
        payload["advance_node"] = True
    return selected


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


def ensure_choice_payloads(
    payloads: List[Dict[str, object]],
    fallback_edges: List[Dict[str, object]],
    role: Optional[str],
    current_node_id: str,
) -> List[Dict[str, object]]:
    """Guarantee the client never receives an active turn with zero choices."""
    if payloads:
        return payloads

    target = fallback_edges[0]["target_node_id"] if fallback_edges else "ending_broken_house"
    base_role = role or (fallback_edges[0].get("required_role") if fallback_edges else "COUNCIL")
    return [
        {
            "choice_id": f"{current_node_id}__steady",
            "action_intent": "Hold the line and keep the room from committing too soon.",
            "required_role": base_role,
            "target_node_id": target,
            "capital_shift": 0,
            "alignment_shift": "CALCULATED",
            "sets_flag": "fallback_steady",
            "effects": {"leader_stability": 1},
            "lanes": {"venkatadri_compromise": 1},
            "advance_node": True,
        },
        {
            "choice_id": f"{current_node_id}__force",
            "action_intent": "Force a clear position before hesitation becomes the decision.",
            "required_role": base_role,
            "target_node_id": target,
            "capital_shift": 0,
            "alignment_shift": "DECISIVE",
            "sets_flag": "fallback_force",
            "effects": {"betrayal_heat": 1},
            "lanes": {"broken_house": 1},
            "advance_node": True,
        },
    ]


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

    Interrogation nodes whose trigger conditions are unmet are skipped
    automatically and the engine advances to the next beat.
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

        # ── Interrogation trigger check: skip if conditions not met ──────────
        if current_node.node_type == "INTERROGATION":
            if not interrogation_should_fire(state):
                # Advance silently to the next beat
                beat_ids = [beat["id"] for beat in master_beats]
                if state.current_node in beat_ids:
                    idx = beat_ids.index(state.current_node)
                    next_id = beat_ids[idx + 1] if idx + 1 < len(beat_ids) else "ending_broken_house"
                else:
                    next_id = "ending_broken_house"
                state.current_node = next_id
                state.current_scene_node = None
                # Save and recurse for next node
                await state_manager.save_state(state)
                return await prepare_scene(session_id, state_axes_defaults, lane_weights_defaults, master_beats)

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

        # Build current pressure tags for Groq framing
        current_pressure = pressure_tags(
            state.state_axes,
            state.lane_weights,
            state.story_flags,
        )
        transition_summary = (state.last_transition or {}).get("summary", "")

        beat = beat_by_id(state.current_node)

        if current_node.node_type == "INTERROGATION":
            pair = state.current_interrogation_pair or choose_interrogation_pair(state)
            interrogation_payloads = build_interrogation_payloads(
                pair, current_node, state, master_beats
            )
            interrogation_payloads = ensure_choice_payloads(
                interrogation_payloads,
                eligible_edges,
                pair.get("answering_role") or pair.get("target_role"),
                current_node.node_id,
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
            # Apply state-reactive filtering for poll choices
            reactive_payloads = _reactive_payloads_for_beat(beat, eligible_edges, state)
            reactive_payloads = ensure_choice_payloads(
                reactive_payloads,
                eligible_edges,
                "COUNCIL",
                current_node.node_id,
            )
            anchor = CHAPTER_ANCHORS.get(chapter_for_node(state.current_node), {})
            narrative = await ai_engine.generate_poll_turn(
                premise=current_node.skeleton_premise,
                db_choices=reactive_payloads,
                anchor=anchor,
                state_snapshot=state.state_axes,
                lane_weights=state.lane_weights,
                pressure_tags=current_pressure,
                transition_summary=transition_summary,
            )
            option_lookup = {option.choice_id: option for option in narrative.options}
            state.current_scene_role = "COUNCIL"
            state.current_scene_player = None
            state.current_scene_round = 1
            state.current_scene_total_rounds = 1
            state.current_scene_flavor = narrative.flavor_text
            state.current_choice_payloads = reactive_payloads
            state.current_choices = [
                ChoiceView(
                    choice_id=edge["choice_id"],
                    text=option_lookup.get(edge["choice_id"]).text
                    if option_lookup.get(edge["choice_id"])
                    else edge["action_intent"],
                    role=edge.get("required_role"),
                    subtext=option_lookup.get(edge["choice_id"]).subtext
                    if option_lookup.get(edge["choice_id"])
                    else None,
                )
                for edge in reactive_payloads
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

            # Apply state-reactive filtering to spotlight choices
            reactive_payloads = _reactive_payloads_for_beat(beat, spotlight_edges, state)
            if not reactive_payloads:
                reactive_payloads = build_spotlight_payloads(spotlight_edges, round_number)
            reactive_payloads = ensure_choice_payloads(
                reactive_payloads,
                spotlight_edges,
                spotlight_role,
                current_node.node_id,
            )

            player_profile = state.active_players[spotlight_player]
            anchor = CHAPTER_ANCHORS.get(chapter_for_node(state.current_node), {})
            narrative = await ai_engine.generate_spotlight_turn(
                premise=current_node.skeleton_premise,
                required_role=spotlight_role,
                db_choices=reactive_payloads,
                player_alignments=player_profile.alignments,
                anchor=anchor,
                state_snapshot=state.state_axes,
                compressed_history=state.session_history,
                pressure_tags=current_pressure,
                transition_summary=transition_summary,
            )
            option_lookup = {option.choice_id: option for option in narrative.options}
            state.current_scene_role = spotlight_role
            state.current_scene_player = spotlight_player
            state.current_scene_round = round_number
            state.current_scene_total_rounds = 1
            state.current_scene_flavor = narrative.flavor_text
            state.current_choice_payloads = reactive_payloads
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
                for payload in reactive_payloads
            ]

        return await state_manager.save_state(state)
