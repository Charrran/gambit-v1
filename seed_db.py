import asyncio
import os

from dotenv import load_dotenv
from neomodel import adb

from app.design.content import (
    CHAPTER_ANCHORS,
    INTERROGATIONS,
    LANE_WEIGHTS,
    MASTER_BEATS,
    STATE_AXES,
    TERMINAL_NODES,
    normalize_choice,
    terminal_for_lane,
)
from app.models.graph import EpisodeNode

load_dotenv()


async def configure_db_async():
    """Configure the async Neo4j connection used for seeding."""
    username = os.getenv("NEO4J_USERNAME")
    password = os.getenv("NEO4J_PASSWORD")
    uri = os.getenv("NEO4J_URI", "")
    host = uri.split("://")[1] if "://" in uri else uri
    await adb.set_connection(f"neo4j+ssc://{username}:{password}@{host}")
    print("[*] Async connection established to Neo4j.")


async def _link(source, target, **props):
    await source.leads_to.connect(target, props)


def _choice_required_role(beat, choice_id: str) -> str:
    if beat["type"] == "POLL":
        return "COUNCIL"
    return beat.get("role") or "COUNCIL"


async def seed_rebellion_episode():
    print("[*] Clearing existing Episode 1 data...")
    await adb.cypher_query("MATCH (n:EpisodeNode {episode_id: 'EP_01_REGENT'}) DETACH DELETE n")

    print("[*] Seeding Gambit master-design graph...")
    nodes = {}
    for beat in MASTER_BEATS:
        anchor = CHAPTER_ANCHORS[beat["chapter"]]
        nodes[beat["id"]] = await EpisodeNode(
            episode_id="EP_01_REGENT",
            node_id=beat["id"],
            node_type=beat["type"],
            skeleton_premise=beat["premise"],
            canonical_outcome=f"Chapter {beat['chapter']}: {anchor['historical_situation']}",
        ).save()

    for node_id, premise in TERMINAL_NODES:
        nodes[node_id] = await EpisodeNode(
            episode_id="EP_01_REGENT",
            node_id=node_id,
            node_type="STORY",
            is_terminal=True,
            skeleton_premise=premise,
            canonical_outcome="This is an alternate-history ending lane resolved from player state.",
        ).save()

    print("[*] Linking authored beats...")
    for index, beat in enumerate(MASTER_BEATS):
        source = nodes[beat["id"]]
        next_id = (
            MASTER_BEATS[index + 1]["id"]
            if index + 1 < len(MASTER_BEATS)
            else terminal_for_lane("broken_house")
        )
        target = nodes[next_id]

        if beat["type"] == "INTERROGATION":
            await _link(
                source,
                target,
                choice_id=f"{beat['id']}__continue",
                action_intent="Continue the authored confrontation.",
                required_role="COUNCIL",
                alignment_shift="INTERROGATION",
                capital_shift=0,
            )
            continue

        for raw_choice in beat.get("choices", []):
            choice = normalize_choice(raw_choice)
            await _link(
                source,
                target,
                choice_id=choice["id"],
                action_intent=choice["text"],
                required_role=_choice_required_role(beat, choice["id"]),
                alignment_shift="DECISIVE",
                capital_shift=0,
            )

    print("[+] Gambit master-design graph successfully seeded.")
    await seed_design_graph()


def design_graph_rows():
    """
    Project the authored mechanics (app/design/content.py) into graph rows:
    lanes, axes, flags, one Choice per option, and what each choice pushes,
    shifts, requires and sets. content.py stays the source of truth at runtime;
    this projection makes the design queryable and gives playthroughs
    something to attach to.
    """
    choices, pushes, shifts, requires, req_flags, sets_flags, triggers, trigger_flags = [], [], [], [], [], [], [], []

    def add(choice_id, node_id, kind, text, option, priority=5, tags=()):
        conds = option.get("requires") or []
        choices.append({
            "choice_id": choice_id, "node_id": node_id, "kind": kind, "text": text,
            "priority": priority, "tags": list(tags), "conditional": bool(conds),
        })
        for lane, points in (option.get("lanes") or {}).items():
            pushes.append({"choice_id": choice_id, "lane": lane, "points": points})
        for axis, delta in (option.get("effects") or {}).items():
            if delta:
                shifts.append({"choice_id": choice_id, "axis": axis, "delta": delta})
        for cond in conds:
            if "flag" in cond:
                req_flags.append({"choice_id": choice_id, "flag": cond["flag"], "present": cond.get("present", True)})
            else:
                requires.append({"choice_id": choice_id, "axis": cond["axis"], "op": cond["op"], "value": cond["value"]})
        for flag in option.get("flags") or []:
            sets_flags.append({"choice_id": choice_id, "flag": flag})

    for beat in MASTER_BEATS:
        if beat["type"] == "INTERROGATION":
            definition = INTERROGATIONS[beat["interrogation"]]
            for option in definition["options"]:
                add(f"{beat['id']}__{option['id'].lower()}", beat["id"], "interrogation", option["text"], option)
            for group, cond_group in enumerate(definition.get("trigger") or []):
                for cond in cond_group if isinstance(cond_group, list) else [cond_group]:
                    if "flag" in cond:
                        trigger_flags.append({"node_id": beat["id"], "flag": cond["flag"],
                                              "present": cond.get("present", True), "group": group})
                    else:
                        triggers.append({"node_id": beat["id"], "axis": cond["axis"], "op": cond["op"],
                                         "value": cond["value"], "group": group})
            continue
        kind = "poll" if beat["type"] == "POLL" else "spotlight"
        for raw in beat.get("choices", []):
            choice = normalize_choice(raw)
            add(choice["id"], beat["id"], kind, choice["text"], choice, choice["priority"], choice["tags"])

    lanes = [{"lane_id": lane, "terminal": terminal_for_lane(lane)} for lane in LANE_WEIGHTS]
    flags = sorted({r["flag"] for r in req_flags + sets_flags + trigger_flags})
    return {
        "lanes": lanes, "axes": list(STATE_AXES), "flags": flags, "choices": choices, "pushes": pushes,
        "shifts": shifts, "requires": requires, "req_flags": req_flags, "sets_flags": sets_flags,
        "triggers": triggers, "trigger_flags": trigger_flags,
    }


async def seed_design_graph():
    """
    Write the design projection. Lane/Axis/Flag/Choice nodes are MERGEd (never
    deleted) so recorded playthroughs stay attached across reseeds; their
    mechanics relationships are rebuilt. Cached narrations are dropped because
    the text they were written for may have changed.
    """
    rows = design_graph_rows()
    ep = "EP_01_REGENT"
    run = adb.cypher_query
    print("[*] Projecting lanes, axes, flags and choice mechanics...")
    await run("MATCH (v:Narration {episode_id: $ep}) DETACH DELETE v", {"ep": ep})
    await run(
        "MATCH (c:Choice {episode_id: $ep})-[r:PUSHES|SHIFTS|REQUIRES|REQUIRES_FLAG|SETS_FLAG]->() DELETE r", {"ep": ep}
    )
    await run("MATCH (c:Choice {episode_id: $ep}) SET c.active = false", {"ep": ep})
    await run(
        """
        UNWIND $lanes AS row
        MERGE (l:Lane {lane_id: row.lane_id}) SET l.episode_id = $ep
        WITH l, row MATCH (t:EpisodeNode {node_id: row.terminal})
        MERGE (l)-[:RESOLVES_TO]->(t)
        """,
        {"lanes": rows["lanes"], "ep": ep},
    )
    await run("UNWIND $axes AS a MERGE (x:Axis {axis_id: a}) SET x.episode_id = $ep", {"axes": rows["axes"], "ep": ep})
    await run("UNWIND $flags AS f MERGE (x:Flag {flag_id: f}) SET x.episode_id = $ep", {"flags": rows["flags"], "ep": ep})
    await run(
        """
        UNWIND $rows AS row
        MERGE (c:Choice {choice_id: row.choice_id})
        SET c.episode_id = $ep, c.text = row.text, c.kind = row.kind, c.priority = row.priority,
            c.tags = row.tags, c.conditional = row.conditional, c.active = true
        WITH c, row MATCH (n:EpisodeNode {node_id: row.node_id})
        MERGE (n)-[:OFFERS]->(c)
        """,
        {"rows": rows["choices"], "ep": ep},
    )
    await run(
        "UNWIND $rows AS row MATCH (c:Choice {choice_id: row.choice_id}), (l:Lane {lane_id: row.lane}) "
        "MERGE (c)-[r:PUSHES]->(l) SET r.points = row.points",
        {"rows": rows["pushes"]},
    )
    await run(
        "UNWIND $rows AS row MATCH (c:Choice {choice_id: row.choice_id}), (a:Axis {axis_id: row.axis}) "
        "MERGE (c)-[r:SHIFTS]->(a) SET r.delta = row.delta",
        {"rows": rows["shifts"]},
    )
    await run(
        "UNWIND $rows AS row MATCH (c:Choice {choice_id: row.choice_id}), (a:Axis {axis_id: row.axis}) "
        "CREATE (c)-[:REQUIRES {op: row.op, value: row.value}]->(a)",
        {"rows": rows["requires"]},
    )
    await run(
        "UNWIND $rows AS row MATCH (c:Choice {choice_id: row.choice_id}), (f:Flag {flag_id: row.flag}) "
        "MERGE (c)-[r:REQUIRES_FLAG]->(f) SET r.present = row.present",
        {"rows": rows["req_flags"]},
    )
    await run(
        "UNWIND $rows AS row MATCH (c:Choice {choice_id: row.choice_id}), (f:Flag {flag_id: row.flag}) "
        "MERGE (c)-[:SETS_FLAG]->(f)",
        {"rows": rows["sets_flags"]},
    )
    await run(
        "UNWIND $rows AS row MATCH (n:EpisodeNode {node_id: row.node_id}), (a:Axis {axis_id: row.axis}) "
        "CREATE (n)-[:TRIGGERED_BY {op: row.op, value: row.value, group: row.group}]->(a)",
        {"rows": rows["triggers"]},
    )
    await run(
        "UNWIND $rows AS row MATCH (n:EpisodeNode {node_id: row.node_id}), (f:Flag {flag_id: row.flag}) "
        "CREATE (n)-[:TRIGGERED_BY_FLAG {present: row.present, group: row.group}]->(f)",
        {"rows": rows["trigger_flags"]},
    )
    print(
        f"[+] Design graph: {len(rows['lanes'])} lanes, {len(rows['axes'])} axes, {len(rows['flags'])} flags, "
        f"{len(rows['choices'])} choices, {len(rows['pushes'])} PUSHES, {len(rows['shifts'])} SHIFTS, "
        f"{len(rows['requires']) + len(rows['req_flags'])} requirements."
    )


async def main():
    try:
        await configure_db_async()
        await seed_rebellion_episode()
        print("\n--- SEEDING COMPLETE ---")
        res, _ = await adb.cypher_query("MATCH (n:EpisodeNode {episode_id: 'EP_01_REGENT'}) RETURN count(n)")
        print(f"Successfully verified {res[0][0]} nodes in Graph.")
    except Exception as exc:
        print(f"[!] Error: {exc}")
    finally:
        await adb.close_connection()


if __name__ == "__main__":
    asyncio.run(main())
