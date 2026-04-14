import asyncio
import os

from dotenv import load_dotenv
from neomodel import adb

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


async def seed_rebellion_episode():
    print("[*] Clearing existing Episode 1 data...")
    await adb.cypher_query("MATCH (n:EpisodeNode {episode_id: 'EP_01_REGENT'}) DETACH DELETE n")

    print("[*] Seeding 'EP_01_REGENT' (15-node historical graph)...")

    n1 = await EpisodeNode(
        episode_id="EP_01_REGENT",
        node_id="regent_01_fractured_peace",
        node_type="CHARACTERIZATION",
        skeleton_premise="Chief Minister Raghava Rao has promoted Saraswathi to the functional head of the party. The senior leadership is in shock.",
        canonical_outcome="In 1995, NTR's decision to give Lakshmi Parvathi a greater role within the TDP was the primary catalyst for the internal revolt.",
    ).save()

    n2 = await EpisodeNode(
        episode_id="EP_01_REGENT",
        node_id="regent_02_hotel_lockdown",
        node_type="CHARACTERIZATION",
        skeleton_premise="Govardhan Naidu has countered by moving 144 MLAs to the Regent Hotel (Viceroy). The gates are locked.",
        canonical_outcome="Chandrababu Naidu sequestered the loyalists at the Viceroy Hotel in Hyderabad to prevent NTR from using his emotional charisma to sway them back.",
    ).save()

    n3 = await EpisodeNode(
        episode_id="EP_01_REGENT",
        node_id="regent_03_saraswathi_strike",
        node_type="CHARACTERIZATION",
        skeleton_premise="Saraswathi stands by Raghava Rao, urging him to dissolve the assembly and go to the people. The party legacy is at stake.",
        canonical_outcome="Lakshmi Parvathi advised NTR to dissolve the assembly, a move that only accelerated the defection of the remaining neutral MLAs to Naidu's camp.",
    ).save()

    n4 = await EpisodeNode(
        episode_id="EP_01_REGENT",
        node_id="regent_04_chaitanya_ratham",
        node_type="STORY",
        skeleton_premise="Raghava Rao arrives at the hotel gates in his famous 'Chaitanya Ratham' van. He demands entry to speak to his people.",
        canonical_outcome="NTR personally drove his Chaitanya Ratham to the Viceroy Hotel but was met with silence and closed gates, a visual symbol of his lost influence.",
    ).save()

    n5 = await EpisodeNode(
        episode_id="EP_01_REGENT",
        node_id="regent_05_haribabu_transport",
        node_type="STORY",
        skeleton_premise="Haribabu controls the logistics. Rumors say some MLAs want to return to Raghava Rao under cover of night.",
        canonical_outcome="Harikrishna, NTR's son, sided with Naidu and was instrumental in physically securing the MLAs and preventing NTR's agents from making contact.",
    ).save()

    n6 = await EpisodeNode(
        episode_id="EP_01_REGENT",
        node_id="regent_06_the_slipper_incident",
        node_type="STORY",
        skeleton_premise="Supporters clash at the hotel gates. Slippers are thrown at the convoy. The moral authority of the patriarch has cracked.",
        canonical_outcome="In one of the most painful moments of the coup, slippers were thrown at NTR's vehicle as it left the Viceroy hotel, marking a point of no return.",
    ).save()

    n7 = await EpisodeNode(
        episode_id="EP_01_REGENT",
        node_id="regent_07_governor_ultimatum",
        node_type="POLL",
        skeleton_premise="The Governor has called for proof of majority. Every faction must now commit their numbers publicly.",
        canonical_outcome="The Governor demanded a physical headcount at the Raj Bhavan to verify Naidu's claim of having the support of the majority of the TDP MLAs.",
    ).save()

    n8 = await EpisodeNode(
        episode_id="EP_01_REGENT",
        node_id="regent_08_the_speaker_hospital",
        node_type="STORY",
        skeleton_premise="The Speaker has been hospitalized. Without a ruling, the assembly is in a constitutional vacuum. Who will act first?",
        canonical_outcome="The Speaker's hospitalization was a tactical delay that allowed both sides to intensify their lobbying efforts in Delhi.",
    ).save()

    n9 = await EpisodeNode(
        episode_id="EP_01_REGENT",
        node_id="regent_09_delhi_lobby",
        node_type="STORY",
        skeleton_premise="The high command in Delhi is watching. National leaders are weighing in on the family drama versus institutional crisis.",
        canonical_outcome="National Front leaders attempted to mediate between NTR and Naidu, but the sheer number of MLAs supporting Naidu made his victory inevitable.",
    ).save()

    n10 = await EpisodeNode(
        episode_id="EP_01_REGENT",
        node_id="regent_10_the_midnight_call",
        node_type="INTERROGATION",
        skeleton_premise="A secret call is placed between Haribabu and Saraswathi. A final deal is proposed to save the family from public ruin.",
        canonical_outcome="Behind-the-scenes negotiations continued until the very last hour, but the trust deficit between Lakshmi Parvathi and NTR's children was total.",
    ).save()

    n11 = await EpisodeNode(
        episode_id="EP_01_REGENT",
        node_id="regent_11_the_last_supper",
        node_type="POLL",
        skeleton_premise="On the eve of the vote, the MLAs share a final meal inside the hotel. The air is thick with tension and the scale of the choice ahead.",
        canonical_outcome="The final night at the Viceroy Hotel saw intense bonding and pressure to ensure that no weak MLAs would flip during the secret ballot.",
    ).save()

    n12 = await EpisodeNode(
        episode_id="EP_01_REGENT",
        node_id="regent_12_the_floor_test",
        node_type="STORY",
        skeleton_premise="The Assembly bell rings. The division of the house begins. History is about to be written in numbers.",
        canonical_outcome="On September 1, 1995, Chandrababu Naidu was invited by the Governor to form the government after proving his majority on the floor of the house.",
    ).save()

    n13 = await EpisodeNode(
        episode_id="EP_01_REGENT",
        node_id="regent_13_cbn_victory",
        node_type="STORY",
        is_terminal=True,
        skeleton_premise="Govardhan Naidu is sworn in. A new era of administration begins, but the patriarch's shadow remains.",
        canonical_outcome="Chandrababu Naidu's takeover transformed the TDP into a modern, technocratic party, though it remained controversial for years.",
    ).save()

    n14 = await EpisodeNode(
        episode_id="EP_01_REGENT",
        node_id="regent_14_tragedy_ntr",
        node_type="STORY",
        is_terminal=True,
        skeleton_premise="Raghava Rao loses his chair and his party. He remains a beloved icon, but a broken leader.",
        canonical_outcome="NTR passed away just months after the coup, a tragic end for the man who had single-handedly broken Congress rule in Andhra Pradesh.",
    ).save()

    n15 = await EpisodeNode(
        episode_id="EP_01_REGENT",
        node_id="regent_15_terminal_anarchy",
        node_type="STORY",
        is_terminal=True,
        skeleton_premise="The Governor dissolves the assembly. Fresh elections are called amidst unprecedented chaos. No one wins this round.",
        canonical_outcome="The actual history avoided this outcome, but it was the greatest fear of the political class during the peak of the Viceroy crisis.",
    ).save()

    print("[*] Linking nodes with stable choice ids...")

    await _link(n1, n2, choice_id="regent_01_assert_control", action_intent="Publicly endorse Saraswathi as your successor.", required_role="Raghava Rao", alignment_shift="AUTHORITARIAN", capital_shift=10)
    await _link(n1, n2, choice_id="regent_01_sound_out_seniors", action_intent="Discreetly meet the seniors to hear their grievances.", required_role="Govardhan Naidu", alignment_shift="PRAGMATIC", capital_shift=5)

    await _link(n2, n3, choice_id="regent_02_cut_utilities", action_intent="Order the police to cut off power and water to the hotel.", required_role="Raghava Rao", alignment_shift="RUTHLESS", capital_shift=-10)
    await _link(n2, n3, choice_id="regent_02_open_to_press", action_intent="Bring the press inside to show the MLAs' unity.", required_role="Govardhan Naidu", alignment_shift="DEMOCRATIC", capital_shift=15)

    await _link(n3, n4, choice_id="regent_03_saraswathi_warns", action_intent="Warn that anyone who leaves will be expelled forever.", required_role="Saraswathi", alignment_shift="HARDLINE", capital_shift=5, min_players=3)
    await _link(n3, n4, choice_id="regent_03_raghava_rally", action_intent="Prepare the Chaitanya Ratham for a final rally.", required_role="Raghava Rao", alignment_shift="IDEALIST", capital_shift=10)

    await _link(n4, n5, choice_id="regent_04_breach_gates", action_intent="Attempt to breach the hotel gates personally.", required_role="Raghava Rao", alignment_shift="BRAVE", capital_shift=20)
    await _link(n4, n5, choice_id="regent_04_counter_mob", action_intent="Wait for Raghava Rao to arrive and block him with a crowd.", required_role="Haribabu", alignment_shift="PROTECTIVE", capital_shift=10, min_players=4)

    await _link(n5, n6, choice_id="regent_05_smuggle_defector", action_intent="Bribe the hotel staff to smuggle a defector out.", required_role="Haribabu", alignment_shift="SNEAKY", capital_shift=-5, min_players=4)
    await _link(n5, n6, choice_id="regent_05_public_warning", action_intent="Issue a public warning against family betrayal.", required_role="Raghava Rao", alignment_shift="PATRIARCHAL", capital_shift=5)

    await _link(n6, n7, choice_id="regent_06_call_headcount", action_intent="Ignore the provocation and call for a headcount.", required_role="Govardhan Naidu", alignment_shift="CALCULATED", capital_shift=15)
    await _link(n6, n7, choice_id="regent_06_demand_arrests", action_intent="Demand immediate arrests of the stone-pelters.", required_role="Saraswathi", alignment_shift="REACTIVE", capital_shift=-5, min_players=3)

    await _link(n7, n8, choice_id="regent_07_march_raj_bhavan", action_intent="March immediately to Raj Bhavan and force a public count.", required_role="COUNCIL", alignment_shift="CONSENSUS", capital_shift=20)
    await _link(n7, n8, choice_id="regent_07_hold_position", action_intent="Stay at the hotel and lock the MLAs down until dawn.", required_role="COUNCIL", alignment_shift="DISCIPLINED", capital_shift=10)

    await _link(n8, n9, choice_id="regent_08_verify_speaker", action_intent="Send a legal team to the hospital to verify the Speaker's condition.", required_role="Saraswathi", alignment_shift="LEGALISTIC", capital_shift=5, min_players=3)
    await _link(n8, n9, choice_id="regent_08_appeal_delhi", action_intent="Appeal directly to the Delhi high command.", required_role="Govardhan Naidu", alignment_shift="NATIONALIST", capital_shift=10)

    await _link(n9, n10, choice_id="regent_09_buy_deputy", action_intent="Offer a ministerial post to the Speaker's deputy.", required_role="Govardhan Naidu", alignment_shift="STRATEGIC", capital_shift=10)
    await _link(n9, n10, choice_id="regent_09_public_fast", action_intent="Threaten the Governor with a public fast.", required_role="Raghava Rao", alignment_shift="MARTYR", capital_shift=15)

    await _link(n10, n11, choice_id="regent_10_family_ceasefire", action_intent="Offer a face-saving family settlement before dawn.", required_role="Govardhan Naidu", alignment_shift="RECONCILIATORY", capital_shift=5)
    await _link(n10, n11, choice_id="regent_10_draw_red_lines", action_intent="Expose the other camp's motives and dare them to deny it publicly.", required_role="Saraswathi", alignment_shift="CONFRONTATIONAL", capital_shift=10, min_players=3)
    await _link(n10, n11, choice_id="regent_10_secure_hotel", action_intent="Tighten security around the loyalists and refuse private negotiation.", required_role="Haribabu", alignment_shift="PROTECTIVE", capital_shift=5, min_players=4)

    await _link(n11, n12, choice_id="regent_11_whip_vote", action_intent="Enforce absolute discipline before the vote begins.", required_role="COUNCIL", alignment_shift="DECISIVE", capital_shift=20)
    await _link(n11, n12, choice_id="regent_11_free_conscience", action_intent="Allow the undecided MLAs one last conscience vote.", required_role="COUNCIL", alignment_shift="RISKY", capital_shift=-10)

    await _link(n12, n13, choice_id="regent_12_naidu_victory", action_intent="Push the majority claim through with total confidence.", required_role="Govardhan Naidu", alignment_shift="TRIUMPHANT", capital_shift=25, min_capital=130)
    await _link(n12, n14, choice_id="regent_12_raghava_tragedy", action_intent="Stand on prestige alone even as the numbers collapse.", required_role="Raghava Rao", alignment_shift="MELANCHOLIC", capital_shift=-15, max_capital=85)
    await _link(n12, n15, choice_id="regent_12_governors_reset", action_intent="Let the constitutional crisis spiral into dissolution.", required_role="Govardhan Naidu", alignment_shift="CHAOTIC", capital_shift=0, min_capital=86, max_capital=129)

    print("[+] Historical 15-node graph successfully seeded.")


async def main():
    try:
        await configure_db_async()
        await seed_rebellion_episode()
        print("\n--- SEEDING COMPLETE ---")
        res, _ = await adb.cypher_query("MATCH (n:EpisodeNode) RETURN count(n)")
        print(f"Successfully verified {res[0][0]} nodes in Graph.")
    except Exception as exc:
        print(f"[!] Error: {exc}")
    finally:
        await adb.close_connection()


if __name__ == "__main__":
    asyncio.run(main())
