"""
graph_store.py - Neo4j graph access.

Responsibilities:
- Story graph: loaded from Neo4j once and served from memory (it is immutable
  between seeds, and each Aura round trip costs ~100 ms)
- Narration cache: LLM-written scene text stored on the graph and shared by
  every game and every server restart
- Playthroughs: each finished game is written back as a path through the
  Choice nodes, so real outcomes can be queried
- Fallback choice_id generation and design-payload lookup for graph choices
"""
import asyncio
import json
import zlib
from types import SimpleNamespace
from typing import Any, Dict, List, Optional

from neomodel import adb

from app.core.config import settings
from app.design.content import MASTER_BEATS, lane_standings, normalize_choice
from app.models.graph import EpisodeNode

EPISODE_ID = "EP_01_REGENT"


# ---------------------------------------------------------------------------
# Fallback / design helpers
# ---------------------------------------------------------------------------

def fallback_choice_id(node_id: str, props: Dict[str, object]) -> str:
    """Generate a deterministic choice_id when none is stored on the edge."""
    role = str(props.get("required_role") or "choice").lower().replace(" ", "_")
    action = str(props.get("action_intent") or "option").lower()
    action = "".join(ch if ch.isalnum() else "_" for ch in action).strip("_")
    return f"{node_id}_{role}_{action[:24]}"


_DESIGN_PAYLOADS: Optional[Dict[str, Dict[str, object]]] = None


def choice_design_payload(choice_id: str) -> Dict[str, object]:
    """Return the authored effects/lanes dict for a given choice_id."""
    global _DESIGN_PAYLOADS
    if _DESIGN_PAYLOADS is None:
        _DESIGN_PAYLOADS = {}
        for beat in MASTER_BEATS:
            for raw in beat.get("choices", []):
                choice = normalize_choice(raw)
                _DESIGN_PAYLOADS.setdefault(
                    choice["id"], {"effects": choice.get("effects", {}), "lanes": choice.get("lanes", {})}
                )
    return _DESIGN_PAYLOADS.get(choice_id, {"effects": {}, "lanes": {}})


# ---------------------------------------------------------------------------
# Story graph (read once, served from memory)
# ---------------------------------------------------------------------------

_graph: Optional[Dict[str, Dict[str, Any]]] = None
_narrations: Dict[str, List[Dict[str, Any]]] = {}
_pending_writes: set = set()


async def load_episode_graph(force: bool = False) -> Dict[str, Dict[str, Any]]:
    """Load every node, edge and cached narration of the episode in three queries."""
    global _graph
    if _graph is not None and not force:
        return _graph
    node_rows, _ = await adb.cypher_query(
        """
        MATCH (n:EpisodeNode {episode_id: $ep})
        RETURN n.node_id, n.node_type, coalesce(n.is_terminal, false), n.skeleton_premise, n.canonical_outcome
        """,
        {"ep": EPISODE_ID},
    )
    edge_rows, _ = await adb.cypher_query(
        """
        MATCH (n:EpisodeNode {episode_id: $ep})-[r:LEADS_TO]->(m:EpisodeNode)
        RETURN n.node_id, properties(r), m.node_id
        """,
        {"ep": EPISODE_ID},
    )
    narration_rows, _ = await adb.cypher_query(
        """
        MATCH (:EpisodeNode {episode_id: $ep})-[:NARRATED_AS]->(v:Narration)
        RETURN v.key, v.flavor, v.options_json ORDER BY v.key, v.variant
        """,
        {"ep": EPISODE_ID},
    )
    nodes = {
        node_id: SimpleNamespace(
            node_id=node_id,
            node_type=node_type or "STORY",
            is_terminal=bool(is_terminal),
            skeleton_premise=premise,
            canonical_outcome=outcome,
        )
        for node_id, node_type, is_terminal, premise, outcome in node_rows
    }
    edges: Dict[str, List[tuple]] = {}
    for source, props, target in edge_rows:
        edges.setdefault(source, []).append((dict(props), target))
    _narrations.clear()
    for key, flavor, options_json in narration_rows:
        _narrations.setdefault(key, []).append({"flavor_text": flavor, "options": json.loads(options_json)})
    loaded = {"nodes": nodes, "edges": edges}
    if nodes:  # never pin an unseeded (empty) graph in memory
        _graph = loaded
        print(
            f"[OK] Story graph cached: {len(nodes)} nodes, {sum(map(len, edges.values()))} choices, "
            f"{sum(map(len, _narrations.values()))} cached narrations"
        )
    return loaded


async def fetch_node(node_id: str):
    """Return a story node by node_id. Raises DoesNotExist if missing."""
    graph = await load_episode_graph()
    node = graph["nodes"].get(node_id)
    if node is None:
        raise EpisodeNode.DoesNotExist(f"Node '{node_id}' not found")
    return node


def _edge_payloads(node_id: str, raw_edges: List[tuple]) -> List[Dict[str, object]]:
    edges: List[Dict[str, object]] = []
    for props, target_node_id in raw_edges:
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


async def fetch_edges(node_id: str) -> List[Dict[str, object]]:
    """Return all LEADS_TO edges from a node, enriched with design payloads."""
    graph = await load_episode_graph()
    prepared = graph.setdefault("prepared", {})
    if node_id not in prepared:
        prepared[node_id] = _edge_payloads(node_id, graph["edges"].get(node_id, []))
    return [dict(edge) for edge in prepared[node_id]]  # callers may annotate their copy


# ---------------------------------------------------------------------------
# Narration cache (LLM text stored on the graph)
# ---------------------------------------------------------------------------

def narration_key(node_id: str, role: str, choice_ids: List[str], pressure_tags: List[str]) -> str:
    """
    A scene "situation": the beat, who acts, exactly which choices are on offer
    (these already encode the state that unlocked them) and the leading lane.
    """
    lane = next((tag for tag in pressure_tags or [] if tag.startswith("lane:")), "lane:none")
    return f"{node_id}|{role}|{','.join(sorted(choice_ids))}|{lane}"


def narration_lookup(key: str, session_id: str, allow_partial: bool = False) -> Optional[Dict[str, Any]]:
    """
    Return a cached narration for this situation. Until `narration_variants`
    versions exist the LLM keeps writing new ones (allow_partial=False returns
    None); after that every table is served from the graph and no LLM is called.
    Which variant a table gets is fixed by its session id.
    """
    variants = _narrations.get(key) or []
    if not variants or (len(variants) < settings.narration_variants and not allow_partial):
        return None
    return variants[zlib.crc32(f"{session_id}|{key}".encode()) % len(variants)]


def narration_store(node_id: str, key: str, flavor_text: str, options: List[Dict[str, str]]) -> None:
    """Add a freshly generated narration to memory now and to Neo4j in the background."""
    variants = _narrations.setdefault(key, [])
    if len(variants) >= settings.narration_variants:
        return
    variants.append({"flavor_text": flavor_text, "options": options})
    task = asyncio.ensure_future(_write_narration(node_id, key, len(variants) - 1, flavor_text, options))
    _pending_writes.add(task)
    task.add_done_callback(_pending_writes.discard)


async def _write_narration(node_id: str, key: str, variant: int, flavor_text: str, options: List[Dict[str, str]]) -> None:
    try:
        await adb.cypher_query(
            """
            MATCH (n:EpisodeNode {node_id: $node_id})
            MERGE (n)-[:NARRATED_AS]->(v:Narration {key: $key, variant: $variant})
            SET v.episode_id = $ep, v.flavor = $flavor, v.options_json = $options, v.created_at = datetime()
            """,
            {
                "node_id": node_id,
                "key": key,
                "variant": variant,
                "ep": EPISODE_ID,
                "flavor": flavor_text,
                "options": json.dumps(options, ensure_ascii=False),
            },
        )
    except Exception as exc:  # the cache is an optimisation; never fail a turn over it
        print(f"[WARN] Narration cache write failed: {exc}")


# ---------------------------------------------------------------------------
# Playthroughs (finished games written back to the graph)
# ---------------------------------------------------------------------------

async def record_playthrough(state) -> None:
    """
    Store a finished game as (:Playthrough)-[:CHOSE {step}]->(:Choice) plus
    (:Playthrough)-[:ENDED_IN]->(:Lane). Best effort: the ending never depends on it.
    """
    decisions = [
        {"step": step, "choice_id": item["choice_id"], "role": item.get("role", "")}
        for step, item in enumerate(state.session_history or [])
        if item.get("choice_id")
    ]
    try:
        await asyncio.wait_for(
            adb.cypher_query(
                """
                MERGE (p:Playthrough {session_id: $sid})
                SET p.episode_id = $ep, p.ended_at = datetime(), p.resolved_lane = $lane,
                    p.ending_node = $ending, p.decision_count = $count,
                    p.lane_scores = $scores, p.state_axes = $axes
                WITH p
                OPTIONAL MATCH (l:Lane {lane_id: $lane})
                FOREACH (_ IN CASE WHEN l IS NULL THEN [] ELSE [1] END | MERGE (p)-[:ENDED_IN]->(l))
                WITH p
                UNWIND $decisions AS d
                MATCH (c:Choice {choice_id: d.choice_id})
                MERGE (p)-[r:CHOSE {step: d.step}]->(c)
                SET r.role = d.role
                """,
                {
                    "sid": state.session_id,
                    "ep": EPISODE_ID,
                    "lane": state.resolved_lane,
                    "ending": (state.final_result or {}).get("ending_node"),
                    "count": len(decisions),
                    "scores": json.dumps(lane_standings(state)),
                    "axes": json.dumps(state.state_axes or {}),
                    "decisions": decisions,
                },
            ),
            timeout=8.0,
        )
    except Exception as exc:
        print(f"[WARN] Playthrough not recorded for {state.session_id}: {exc}")


async def ending_stats() -> Dict[str, Any]:
    """How real games have ended."""
    rows, _ = await adb.cypher_query(
        """
        MATCH (l:Lane {episode_id: $ep})
        OPTIONAL MATCH (l)<-[:ENDED_IN]-(p:Playthrough)
        OPTIONAL MATCH (l)-[:RESOLVES_TO]->(t:EpisodeNode)
        RETURN l.lane_id, t.node_id, count(p) AS games ORDER BY games DESC, l.lane_id
        """,
        {"ep": EPISODE_ID},
    )
    total = sum(row[2] for row in rows)
    return {
        "games": total,
        "endings": [
            {"lane": lane, "ending_node": node, "games": games, "share": round(games / total, 3) if total else 0.0}
            for lane, node, games in rows
        ],
    }


async def lane_signature_choices(lane: str, limit: int = 15) -> List[Dict[str, Any]]:
    """Choices that most often appear in games ending in `lane`, relative to how often they are picked at all."""
    rows, _ = await adb.cypher_query(
        """
        MATCH (c:Choice)<-[:CHOSE]-(p:Playthrough)
        WITH c, count(p) AS picked, sum(CASE WHEN p.resolved_lane = $lane THEN 1 ELSE 0 END) AS in_lane
        WHERE in_lane > 0
        RETURN c.choice_id, c.text, picked, in_lane, toFloat(in_lane) / picked AS share
        ORDER BY share DESC, in_lane DESC LIMIT $limit
        """,
        {"lane": lane, "limit": limit},
    )
    return [
        {"choice_id": cid, "text": text, "times_picked": picked, "games_ending_here": in_lane, "share": round(share, 3)}
        for cid, text, picked, in_lane, share in rows
    ]
