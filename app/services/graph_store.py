"""
graph_store.py – Neo4j graph access helpers.

Responsibilities:
- Fetch EpisodeNode by node_id
- Fetch outgoing LEADS_TO edges for a node
- Fallback choice_id generation
- Design-payload lookup for graph choices
"""
from typing import Dict, List

from neomodel import adb

from app.design.content import MASTER_BEATS
from app.models.graph import EpisodeNode


# ---------------------------------------------------------------------------
# Fallback / design helpers
# ---------------------------------------------------------------------------

def fallback_choice_id(node_id: str, props: Dict[str, object]) -> str:
    """Generate a deterministic choice_id when none is stored on the edge."""
    role = str(props.get("required_role") or "choice").lower().replace(" ", "_")
    action = str(props.get("action_intent") or "option").lower()
    action = "".join(ch if ch.isalnum() else "_" for ch in action).strip("_")
    return f"{node_id}_{role}_{action[:24]}"


def choice_design_payload(choice_id: str) -> Dict[str, object]:
    """Return the authored effects/lanes dict for a given choice_id."""
    for beat in (beat for beat in MASTER_BEATS if beat.get("choices")):
        for raw in beat["choices"]:
            if raw[0] == choice_id:
                return {"effects": raw[2], "lanes": raw[3]}
    return {"effects": {}, "lanes": {}}


# ---------------------------------------------------------------------------
# Neo4j queries
# ---------------------------------------------------------------------------

async def fetch_node(node_id: str) -> EpisodeNode:
    """Fetch a single EpisodeNode by its node_id. Raises DoesNotExist if missing."""
    results, _ = await adb.cypher_query(
        "MATCH (n:EpisodeNode {node_id: $node_id}) RETURN n",
        {"node_id": node_id},
    )
    if not results:
        raise EpisodeNode.DoesNotExist(f"Node '{node_id}' not found")
    return EpisodeNode.inflate(results[0][0])


async def fetch_edges(node_id: str) -> List[Dict[str, object]]:
    """Fetch all LEADS_TO edges from a node, enriched with design payloads."""
    results, _ = await adb.cypher_query(
        """
        MATCH (n:EpisodeNode {node_id: $node_id})-[r:LEADS_TO]->(m:EpisodeNode)
        RETURN properties(r) as props, m.node_id as target_node_id
        """,
        {"node_id": node_id},
    )
    edges: List[Dict[str, object]] = []
    for props, target_node_id in results:
        choice_id = props.get("choice_id") or fallback_choice_id(node_id, props)
        design_payload = choice_design_payload(choice_id)
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
