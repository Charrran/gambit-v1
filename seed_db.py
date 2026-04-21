import asyncio
import os

from dotenv import load_dotenv
from neomodel import adb

from app.design.content import CHAPTER_ANCHORS, MASTER_BEATS, TERMINAL_NODES, normalize_choice, terminal_for_lane
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
