from typing import Dict, Any
from neomodel import adb
from app.models.graph import EpisodeNode
from app.services.state import state_manager


def _fallback_choice_id(node_id: str, props: Dict[str, Any]) -> str:
    role = str(props.get("required_role") or "choice").lower().replace(" ", "_")
    action = str(props.get("action_intent") or "option").lower()
    action = "".join(ch if ch.isalnum() else "_" for ch in action).strip("_")
    return f"{node_id}_{role}_{action[:24]}"


class NarrativeService:
    """
    Bridge service between the Neo4j Narrative Graph and the Redis Memory Bank.
    Handles graph traversal, choice filtering, and state updates.
    """
    async def get_current_beat(self, session_id: str, player_id: str) -> Dict[str, Any]:
        """
        Fetches the current narrative node and filters choices available to the player.
        """
        state = await state_manager.get_state(session_id)
        if not state:
            raise ValueError("Session not found")

        # 1. Fetch current node data from Neo4j
        # We use neomodel's nodes.get_or_none for simplicity
        node = await EpisodeNode.nodes.get_or_none(node_id=state.current_node)
        if not node:
            raise ValueError(f"Story beat {state.current_node} missing in database.")

        # 2. Fetch all choices (relationships) originating from this node using Cypher
        # This is more efficient for retrieving relationship properties in one go.
        query = """
        MATCH (n:EpisodeNode {node_id: $node_id})-[r:LEADS_TO]->(m:EpisodeNode)
        RETURN properties(r) as props, m.node_id as target_node_id
        """
        params = {"node_id": state.current_node}
        results, _ = await adb.cypher_query(query, params)

        player_role = state.active_players[player_id].role
        player_flags = set(state.active_players[player_id].flags)

        valid_choices = []
        for props, target_id in results:
            # Check if this choice belongs to the player's role
            if props.get('required_role') != player_role:
                continue
            
            # Check prerequisite flags
            req_flag = props.get('requires_flag')
            if req_flag and req_flag not in player_flags:
                continue

            valid_choices.append({
                "choice_id": props.get("choice_id") or _fallback_choice_id(state.current_node, props),
                "action_intent": props.get('action_intent'),
                "alignment_shift": props.get('alignment_shift'),
                "capital_shift": props.get('capital_shift', 0),
                "sets_flag": props.get('sets_flag'),
                "target_node_id": target_id
            })

        return {
            "type": "NARRATIVE_BEAT",
            "node_id": node.node_id,
            "premise": node.skeleton_premise,
            "is_terminal": node.is_terminal,
            "global_capital": state.global_capital,
            "options": valid_choices
        }

    async def process_decision(self, session_id: str, player_id: str, choice_id: str) -> Dict[str, Any]:
        """
        Applies a player's choice to the global and local state.
        Returns the updated global GameState.
        """
        # Re-fetch the current beat to validate the choice again (security/consistency)
        beat = await self.get_current_beat(session_id, player_id)
        
        selected_choice = next((c for c in beat["options"] if c["choice_id"] == choice_id), None)
        if not selected_choice:
            raise ValueError("Unauthorized or invalid choice selection.")

        # 1. Update Player Memory (Alignments and Flags)
        await state_manager.update_player_state(
            session_id,
            player_id,
            new_alignment=selected_choice["alignment_shift"],
            new_flag=selected_choice.get("sets_flag")
        )

        # 2. Update Global State (Capital and Node)
        state = await state_manager.get_state(session_id)
        state.global_capital += selected_choice["capital_shift"]
        state.current_node = selected_choice["target_node_id"]
        
        # Persist the global update back to Redis
        await state_manager.client.set(f"game:{session_id}", state.model_dump_json())

        return {
            "type": "DECISION_RESULT",
            "player_id": player_id,
            "choice_made": selected_choice["action_intent"],
            "new_state": state
        }

# Singleton instance
narrative_service = NarrativeService()
