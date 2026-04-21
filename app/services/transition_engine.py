"""
transition_engine.py – Deterministic chapter transition summaries.

Builds a structured transition context when the game moves from one chapter to
the next.  No LLM is used here; everything is assembled from authored anchors
and the concrete state diffs recorded by choice_resolver.

The output is stored in GameState.last_transition and forwarded to the frontend
inside NARRATIVE_BEAT payloads.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional


def _format_delta(val: int) -> str:
    return f"+{val}" if val > 0 else str(val)


def _leading_lanes(lane_changes: Dict[str, int], lane_weights: Dict[str, int], top_n: int = 2) -> List[str]:
    """Return the lane names whose running total is highest post-transition."""
    combined = {k: lane_weights.get(k, 0) + lane_changes.get(k, 0) for k in set(lane_changes) | set(lane_weights)}
    sorted_lanes = sorted(combined, key=lambda k: combined[k], reverse=True)
    return [lane for lane in sorted_lanes[:top_n] if combined.get(lane, 0) > 0]


def _describe_state_changes(state_changes: Dict[str, int]) -> str:
    """One short sentence describing which axes moved most."""
    if not state_changes:
        return ""
    significant = sorted(state_changes.items(), key=lambda kv: abs(kv[1]), reverse=True)[:3]
    parts = []
    for axis, delta in significant:
        human = axis.replace("_", " ")
        if delta > 0:
            parts.append(f"{human} rose by {delta}")
        else:
            parts.append(f"{human} fell by {abs(delta)}")
    return ", ".join(parts) + "."


def _pressure_sentence(leading_lanes: List[str]) -> str:
    lane_descriptions = {
        "govardhan_consolidation": "the institutional machine is moving toward Govardhan's succession",
        "raghava_restoration": "popular legitimacy is still pulling toward Raghava",
        "saraswathi_ascendancy": "Saraswathi's influence is becoming its own center of gravity",
        "venkatadri_compromise": "the hinge belongs to Venkatadri and neither camp controls it",
        "broken_house": "the fracture is becoming irreparable regardless of what individuals choose",
        "pyrrhic_govardhan": "Govardhan may win the chair but is beginning to look like the cost",
        "patriarchs_last_roar": "Raghava's defeat is shaping into the kind of loss that outlasts winners",
        "saraswathi_betrayal": "Saraswathi is accumulating a debt the story has not finished collecting",
        "the_inheritance": "the real succession question has quietly become about who comes after",
    }
    if not leading_lanes:
        return "No dominant lane has emerged yet."
    descriptions = [lane_descriptions.get(lane, lane.replace("_", " ")) for lane in leading_lanes]
    if len(descriptions) == 1:
        return f"The strongest current: {descriptions[0]}."
    return f"The strongest currents: {descriptions[0]}, while {descriptions[1]}."


def build_transition_summary(
    previous_node_id: str,
    next_node_id: str,
    chosen_edge: Dict[str, Any],
    state_changes: Dict[str, int],
    lane_changes: Dict[str, int],
    chapter_anchors: Dict[int, Dict[str, str]],
    current_lane_weights: Optional[Dict[str, int]] = None,
    from_chapter: Optional[int] = None,
    to_chapter: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Build a structured transition dict for consumption by the frontend and the
    Groq framing layer.  Everything here is deterministic.
    """
    lane_weights = current_lane_weights or {}
    fc = from_chapter or 0
    tc = to_chapter or 0

    from_anchor = chapter_anchors.get(fc, {})
    to_anchor = chapter_anchors.get(tc, {})

    chosen_text = chosen_edge.get("action_intent", "An unnamed choice was made.")
    state_change_sentence = _describe_state_changes(state_changes)
    leading = _leading_lanes(lane_changes, lane_weights)
    pressure_sentence = _pressure_sentence(leading)

    # Build 2–4 sentence narrative summary
    sentences: List[str] = []
    from_title = from_anchor.get("title", f"Chapter {fc}")
    to_title = to_anchor.get("title", f"Chapter {tc}")
    to_situation = to_anchor.get("historical_situation", "")
    to_constraint = to_anchor.get("undercurrent", "")

    if fc and tc and fc != tc:
        sentences.append(
            f"With \"{chosen_text.rstrip('.')}\" the turn in {from_title} closed."
        )
    else:
        sentences.append(f"The choice was: \"{chosen_text.rstrip('.')}\".")

    if state_change_sentence:
        sentences.append(state_change_sentence.capitalize())

    if to_situation:
        sentences.append(f"The story moves into {to_title}: {to_situation}")

    if pressure_sentence:
        sentences.append(pressure_sentence)

    if to_constraint and len(sentences) < 4:
        sentences.append(to_constraint)

    summary = " ".join(sentences[:4])

    return {
        "from_chapter": fc,
        "to_chapter": tc,
        "from_node": previous_node_id,
        "to_node": next_node_id,
        "chosen_text": chosen_text,
        "state_changes": state_changes,
        "lane_changes": lane_changes,
        "leading_lanes": leading,
        "summary": summary,
    }
