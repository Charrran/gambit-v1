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
from app.services.state import state_manager


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
