"""
ending_engine.py – Finale detection and ending generation.

Responsibilities:
- Detect a terminal node and trigger finale resolution
- Call resolve_lane to compute the winning lane
- Call ai_engine for historian ending and canonical comparison
- Build final_result payload with graceful fallback
"""
from app.design.content import resolve_lane
from app.services.ai_engine import ai_engine
from app.services.graph_store import fetch_node
from app.services.live_intel import fallback_headlines, role_key
from app.services.state import state_manager


def _classification(divergence: int) -> str:
    if divergence <= 24:
        return "Canonical"
    if divergence <= 49:
        return "Near-Canonical"
    if divergence <= 74:
        return "Divergent"
    return "Rupture"


def _divergence_score(state) -> int:
    axes = state.state_axes or {}
    lanes = state.lane_weights or {}
    score = 30
    score += min(25, abs(axes.get("family_cohesion", 0)) * 4)
    score += min(20, axes.get("betrayal_heat", 0) * 3)
    score += min(15, abs(axes.get("leader_stability", 0)) * 2)
    if state.resolved_lane and state.resolved_lane != "govardhan_consolidation":
        score += 15
    if lanes:
        score += min(10, max(lanes.values()))
    return max(0, min(100, score))


def _role_verdicts(state):
    axes = state.state_axes or {}
    verdicts = []
    for player_id, profile in state.active_players.items():
        role = profile.role or "Unknown"
        outcome = "Survived"
        if role == "Raghava Rao" and axes.get("leader_stability", 0) <= -4:
            outcome = "Fell"
        elif role == "Govardhan Naidu" and axes.get("govardhan_ruthlessness", 0) >= 5:
            outcome = "Compromised"
        elif role == "Saraswathi" and axes.get("saraswathi_influence", 0) >= 6:
            outcome = "Survived"
        elif role == "Venkatadri" and abs(axes.get("venkatadri_loyalty", 0)) <= 1:
            outcome = "Compromised"
        if "breakdown" in profile.flags or "BREAKDOWN" in profile.alignments:
            outcome = "Compromised"

        verdicts.append(
            {
                "roleKey": role_key(role),
                "name": role,
                "analogue": {
                    "Raghava Rao": "Patriarch · Mass Leader",
                    "Govardhan Naidu": "Strategist · Institutional Operator",
                    "Saraswathi": "Influence Center · Queenmaker",
                    "Venkatadri": "Family Hinge · Moral Witness",
                }.get(role, "Player"),
                "outcome": outcome,
                "outcomeDetail": f"{role} ended the crisis shaped by {', '.join((profile.alignments or ['unreadable'])[-3:])}.",
                "secretAchieved": bool(profile.primary_trait or profile.alignments),
                "secretLabel": profile.primary_trait or "Survive the crisis with agency",
                "playerName": player_id,
            }
        )
    return verdicts


def _key_moments(state):
    moments = []
    for idx, item in enumerate((state.session_history or [])[-6:], start=1):
        moments.append(
            {
                "round": idx,
                "decision": item.get("choice", "A private decision changed the room."),
                "impact": "high" if idx >= max(1, len((state.session_history or [])[-6:]) - 2) else "medium",
                "label": "Pivotal" if idx >= max(1, len((state.session_history or [])[-6:]) - 2) else "Pressure",
            }
        )
    return moments


async def ensure_finale(session_id: str):
    """
    If the current node is terminal, generate the ending and mark the session ended.

    Idempotent: returns early if already ended.  Returns the (possibly updated) state.
    """
    async with state_manager.session_lock(session_id):
        state = await state_manager.get_state(session_id)
        if not state:
            return None
        if state.ended and state.final_result:
            return state

        current_node = await fetch_node(state.current_node)
        if not current_node.is_terminal:
            return state

        # Append terminal node to session history if not already there
        if not state.session_history or state.session_history[-1]["node"] != current_node.node_id:
            state.session_history.append(
                {"node": current_node.node_id, "role": "SYSTEM", "choice": "THE END"}
            )

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
            divergence = _divergence_score(state)
            title = comparison.final_score or state.resolved_lane.replace("_", " ").title()
            headlines = fallback_headlines(state)
            state.final_result = {
                "type": "GAME_OVER",
                "phase": "EPILOGUE",
                "ending_node": current_node.node_id,
                "resolved_lane": state.resolved_lane,
                "historian_ending": historian_text,
                "comparison": comparison.model_dump(),
                "canonical_ending": comparison.canonical_summary,
                "divergence_analysis": comparison.divergence_analysis,
                "state_axes": state.state_axes,
                "lane_weights": state.lane_weights,
                "ending": {
                    "id": current_node.node_id,
                    "title": title,
                    "classification": _classification(divergence),
                    "divergenceScore": divergence,
                    "episodeTitle": "Episode I - The Regent Rebellion",
                    "location": "Empire Bay Hotel, Suite 412",
                    "date": "August 1995",
                },
                "narration_beats": [
                    {"type": "environment", "text": comparison.player_summary},
                    {"type": "environment", "text": historian_text},
                    {"type": "environment", "text": comparison.divergence_analysis},
                ],
                "canonical": {
                    "title": "The Canonical Record",
                    "summary": comparison.canonical_summary,
                    "verdict": comparison.divergence_analysis,
                },
                "verdicts": _role_verdicts(state),
                "aftermath_headlines": headlines,
                "key_moments": _key_moments(state),
            }
        except Exception as exc:
            print(f"[!] Finale Generation Failed: {exc}")
            divergence = _divergence_score(state)
            state.final_result = {
                "type": "GAME_OVER",
                "phase": "EPILOGUE",
                "ending_node": current_node.node_id,
                "flavor": current_node.skeleton_premise,
                "historical_note": current_node.canonical_outcome,
                "ending": {
                    "id": current_node.node_id,
                    "title": state.resolved_lane.replace("_", " ").title() if state.resolved_lane else "Altered Verdict",
                    "classification": _classification(divergence),
                    "divergenceScore": divergence,
                    "episodeTitle": "Episode I - The Regent Rebellion",
                    "location": "Empire Bay Hotel, Suite 412",
                    "date": "August 1995",
                },
                "narration_beats": [{"type": "environment", "text": current_node.skeleton_premise}],
                "canonical": {
                    "title": "The Canonical Record",
                    "summary": current_node.canonical_outcome or "The canonical crisis resolved through institutional consolidation.",
                    "verdict": "The session departed from the expected record in the distribution of loyalty and authority.",
                },
                "verdicts": _role_verdicts(state),
                "aftermath_headlines": fallback_headlines(state),
                "key_moments": _key_moments(state),
            }

        state.ended = True
        return await state_manager.save_state(state)
