from __future__ import annotations

from typing import Any, Dict, List, Optional


ROLES = ["Raghava Rao", "Govardhan Naidu", "Saraswathi", "Venkatadri"]

INTRO_CONTEXT = (
    "Andhra Pradesh, August 1995. A party built around one mythic leader is beginning to discover that charisma, "
    "family, procedure, and private influence do not obey the same clock. The crisis will pass through the hotel, "
    "the residence, Raj Bhavan, and the public imagination, but its real battlefield is the question of who gets to "
    "inherit legitimacy when the founder is still alive."
)

STATE_AXES = {
    "institutional_control": 0,
    "public_mandate": 0,
    "family_cohesion": 0,
    "leader_stability": 0,
    "court_politics": 0,
    "elite_loyalty": 0,
    "betrayal_heat": 0,
    "media_spin": 0,
    "governor_patience": 0,
    "hotel_control": 0,
    "delhi_interest": 0,
    "saraswathi_influence": 0,
    "venkatadri_loyalty": 0,
    "govardhan_ruthlessness": 0,
    "raghava_paranoia": 0,
}

LANE_WEIGHTS = {
    "govardhan_consolidation": 0,
    "raghava_restoration": 0,
    "saraswathi_ascendancy": 0,
    "venkatadri_compromise": 0,
    "broken_house": 0,
    "pyrrhic_govardhan": 0,
    "patriarchs_last_roar": 0,
    "saraswathi_betrayal": 0,
    "the_inheritance": 0,
}

CHAPTER_ANCHORS: Dict[int, Dict[str, str]] = {
    1: {
        "title": "The Powder Keg",
        "historical_situation": "Saraswathi's influence grows; unease begins becoming political.",
        "register": "Still surface, deep current. Everything is polite. The danger is in what is not being said.",
        "power_map": "Raghava holds formal power. Govardhan holds institutional knowledge. Saraswathi holds proximity. Venkatadri holds observation.",
        "undercurrent": "Everyone already knows something is wrong. The pretense of normalcy is the tension.",
        "constraint": "No dramatic confrontations or raised voices. Choices should feel ordinary and consequential.",
    },
    2: {
        "title": "Warning at the Residence",
        "historical_situation": "Govardhan gathers MLAs and sends warning through senior leaders.",
        "register": "Controlled urgency. Politeness is cracking while still using the language of decorum.",
        "power_map": "Govardhan is building. Raghava is receiving. Saraswathi may accelerate or contain. Venkatadri watches.",
        "undercurrent": "The warning is not really about Saraswathi. Everyone knows it. Nobody says it.",
        "constraint": "No character is purely villainous. Every perspective must feel internally coherent.",
    },
    3: {
        "title": "The Hotel Fortress",
        "historical_situation": "MLAs consolidate inside the hotel camp.",
        "register": "Physical consolidation. The story moves from drawing rooms to a building with guards.",
        "power_map": "Govardhan controls the space. Raghava is outside it. Saraswathi frames its meaning. Venkatadri's absence is present.",
        "undercurrent": "The hotel is both stronghold and trap. Everyone inside knows this and nobody says it.",
        "constraint": "Make the hotel feel like a physical place with texture, temperature, and fatigue.",
    },
    4: {
        "title": "Venkatadri's Turn",
        "historical_situation": "Venkatadri becomes the decisive family-political hinge.",
        "register": "Everything slows down. The thriller breathes differently and becomes intimate.",
        "power_map": "Both camps need Venkatadri. He is most powerful here and least comfortable with that power.",
        "undercurrent": "This is about what kind of person Venkatadri is willing to be.",
        "constraint": "No option should feel easy or obviously correct.",
    },
    5: {
        "title": "The Night of Resolutions",
        "historical_situation": "Hotel resolutions formalize the rebellion.",
        "register": "Cold, procedural, efficient; underneath it, irreversible anxiety.",
        "power_map": "Govardhan commands the room. Venkatadri's position is resolved or suspended. Others follow.",
        "undercurrent": "They are doing this correctly. That is almost the worst part.",
        "constraint": "Let clean procedural choices be devastating without overexplaining them.",
    },
    6: {
        "title": "The Race to Raj Bhavan",
        "historical_situation": "Dissolution attempts, majority claims, and Governor pressure collide.",
        "register": "Speed. Time itself is now a variable.",
        "power_map": "Govardhan has procedure. Raghava has legitimacy. The Governor has the decision.",
        "undercurrent": "Everyone knows numbers decide it; theater only matters if it moves numbers.",
        "constraint": "No contemplative choices. Everything is urgent.",
    },
    7: {
        "title": "The Chappal Moment",
        "historical_situation": "Raghava's public humiliation becomes visual and legendary.",
        "register": "The story tears. Minimal framing; the situation carries the force.",
        "power_map": "Nobody has power in this chapter. That is the point.",
        "undercurrent": "The question is not what happens next, but what this moment means.",
        "constraint": "Do not resolve the emotion inside the chapter. Leave it unprocessed.",
    },
    8: {
        "title": "Deadlines and Headcounts",
        "historical_situation": "Governor deadlines, Delhi mediation, and final pressure narrow the field.",
        "register": "Exhaustion and urgency in the same breath. Tired people become honest and dangerous.",
        "power_map": "Govardhan is close. Raghava has one or two moves left. Saraswathi chooses her ending. Venkatadri may be the final variable.",
        "undercurrent": "Everyone can see the ending from here. Only the shape remains uncertain.",
        "constraint": "Spotlight beats should be short. Interrogations carry the chapter.",
    },
    9: {
        "title": "Resignation, Transfer, Reversal",
        "historical_situation": "Authority transfers, returns, fractures, or mutates.",
        "register": "Resolution. The thriller drops into relief, grief, ambiguity, or hollow victory.",
        "power_map": "Whoever the state machine put in front has the chair; history may judge differently.",
        "undercurrent": "It is over. For some that is relief. For others it begins a different problem.",
        "constraint": "Write as history, not as a game ending.",
    },
}


# ---------------------------------------------------------------------------
# Choice normalisation helpers
# ---------------------------------------------------------------------------

def normalize_choice(choice) -> Dict[str, Any]:
    """
    Accept either a legacy tuple (id, text, effects, lanes) or a new dict choice.
    Always return a canonical dict with all expected keys.
    """
    if isinstance(choice, (list, tuple)):
        cid, text, effects, lanes = choice[0], choice[1], choice[2] if len(choice) > 2 else {}, choice[3] if len(choice) > 3 else {}
        return {
            "id": cid,
            "text": text,
            "effects": effects,
            "lanes": lanes,
            "requires": [],
            "blocks": [],
            "priority": 5,
            "tags": [],
        }
    # already a dict – fill in missing keys with safe defaults
    d = dict(choice)
    d.setdefault("requires", [])
    d.setdefault("blocks", [])
    d.setdefault("priority", 5)
    d.setdefault("tags", [])
    d.setdefault("effects", {})
    d.setdefault("lanes", {})
    return d


def _eval_condition(cond: Dict[str, Any], state_axes: Dict[str, int], story_flags: List[str]) -> bool:
    """Evaluate a single requires/blocks condition."""
    if "flag" in cond:
        present = cond.get("present", True)
        return (cond["flag"] in story_flags) == present
    axis = cond.get("axis", "")
    op = cond.get("op", "==")
    value = int(cond.get("value", 0))
    actual = int(state_axes.get(axis, 0))
    if op == "<=":
        return actual <= value
    if op == ">=":
        return actual >= value
    if op == "<":
        return actual < value
    if op == ">":
        return actual > value
    if op == "!=":
        return actual != value
    return actual == value


def choice_conditions_match(
    choice: Dict[str, Any],
    state_axes: Dict[str, int],
    story_flags: Optional[List[str]] = None,
) -> bool:
    """
    Return True if all requires conditions pass AND no blocks condition passes.
    An empty requires list always passes.  A condition in blocks that matches blocks the choice.
    """
    flags = story_flags or []
    for cond in choice.get("requires", []):
        if not _eval_condition(cond, state_axes, flags):
            return False
    for cond in choice.get("blocks", []):
        if _eval_condition(cond, state_axes, flags):
            return False
    return True


def choice_relevance_score(
    choice: Dict[str, Any],
    state_axes: Dict[str, int],
    lane_weights: Dict[str, int],
    story_flags: Optional[List[str]] = None,
) -> float:
    """
    Score a choice by authored priority + how well its effects align with current
    dominant pressure in the state.  Higher = more relevant to show.
    """
    score = float(choice.get("priority", 5))
    # Boost for choices whose lane effects push the currently leading lane
    leading_lane = max(lane_weights, key=lambda k: lane_weights[k]) if lane_weights else None
    if leading_lane:
        score += float(choice.get("lanes", {}).get(leading_lane, 0)) * 0.5
    # Boost for choices that react to high-pressure axes
    for axis, val in state_axes.items():
        if abs(val) >= 4:
            score += abs(float(choice.get("effects", {}).get(axis, 0))) * 0.4
    return score


def pressure_tags(
    state_axes: Dict[str, int],
    lane_weights: Dict[str, int],
    story_flags: Optional[List[str]] = None,
) -> List[str]:
    """
    Derive a short list of human-readable pressure descriptors from current state.
    This is passed to the LLM for framing only — it never controls mechanics.
    """
    tags = []
    flags = story_flags or []
    axes = state_axes or {}
    lanes = lane_weights or {}

    if axes.get("betrayal_heat", 0) >= 5:
        tags.append("BETRAYAL_PEAK")
    elif axes.get("betrayal_heat", 0) >= 3:
        tags.append("betrayal_rising")

    if axes.get("family_cohesion", 0) <= -4:
        tags.append("FAMILY_FRACTURED")
    elif axes.get("family_cohesion", 0) <= -2:
        tags.append("family_strained")

    if axes.get("public_mandate", 0) >= 6:
        tags.append("CROWD_BEHIND_RAGHAVA")
    elif axes.get("public_mandate", 0) >= 3:
        tags.append("public_sympathy_building")

    if axes.get("institutional_control", 0) >= 6:
        tags.append("MACHINE_MOVING")
    elif axes.get("institutional_control", 0) >= 3:
        tags.append("institutional_momentum")

    if axes.get("saraswathi_influence", 0) >= 5:
        tags.append("SARASWATHI_ASCENDANT")
    elif axes.get("saraswathi_influence", 0) >= 3:
        tags.append("saraswathi_visible")

    if axes.get("venkatadri_loyalty", 0) <= -2:
        tags.append("venkatadri_drifting")
    if "venkatadri_suspended" in flags:
        tags.append("venkatadri_suspended")
    if "venkatadri_independent_actor" in flags:
        tags.append("venkatadri_independent")

    if axes.get("govardhan_ruthlessness", 0) >= 4:
        tags.append("govardhan_relentless")

    if axes.get("leader_stability", 0) <= -3:
        tags.append("RAGHAVA_UNRAVELING")

    if axes.get("hotel_control", 0) >= 3:
        tags.append("hotel_locked_down")

    if axes.get("delhi_interest", 0) >= 2:
        tags.append("delhi_watching")

    leading = max(lanes, key=lambda k: lanes[k]) if lanes else None
    if leading and lanes.get(leading, 0) >= 4:
        tags.append(f"lane:{leading}")

    return tags


# ---------------------------------------------------------------------------
# Interrogation trigger evaluation
# ---------------------------------------------------------------------------

def interrogation_trigger_passes(
    interrogation_id: str,
    state_axes: Dict[str, int],
    story_flags: Optional[List[str]] = None,
) -> bool:
    """
    Return True if the interrogation should fire, False to skip it.
    Each entry in INTERROGATIONS may have a "trigger" list (OR-grouped dicts).
    If no "trigger" key, the interrogation always fires (permissive default).
    """
    definition = INTERROGATIONS.get(interrogation_id or "")
    if not definition:
        return True
    triggers = definition.get("trigger")
    if not triggers:
        return True
    flags = story_flags or []
    # Any single trigger dict matching is enough (OR semantics)
    for cond_group in triggers:
        # cond_group may be a single condition dict or a list of AND conditions
        if isinstance(cond_group, list):
            if all(_eval_condition(c, state_axes, flags) for c in cond_group):
                return True
        else:
            if _eval_condition(cond_group, state_axes, flags):
                return True
    return False


# ---------------------------------------------------------------------------
# MASTER_BEATS
# ---------------------------------------------------------------------------

MASTER_BEATS: List[Dict[str, Any]] = [
    {"id": "gambit_ch01_raghava", "chapter": 1, "type": "CHARACTERIZATION", "role": "Raghava Rao",
     "premise": "Saraswathi's role in public appearances has grown. Senior leaders are asking questions they are not fully asking.",
     "choices": [
        ("ch01_raghava_elevate", "Formalize Saraswathi's visibility and dare the party to object.", {"saraswathi_influence": 2, "court_politics": 1, "leader_stability": -1}, {"saraswathi_ascendancy": 1}),
        ("ch01_raghava_reassure", "Quietly reassure seniors that affection has not replaced structure.", {"elite_loyalty": 1, "leader_stability": 1, "saraswathi_influence": -1}, {"raghava_restoration": 1}),
        ("ch01_raghava_challenge", "Ask who has been whispering and make the unease answerable.", {"betrayal_heat": 1, "raghava_paranoia": 1, "public_mandate": 1}, {"broken_house": 1}),
        {"id": "ch01_raghava_withdraw", "text": "Withdraw from public appearances and make the party come to you.", "effects": {"leader_stability": -1, "public_mandate": -1, "raghava_paranoia": 1}, "lanes": {"patriarchs_last_roar": 1}, "requires": [{"axis": "family_cohesion", "op": "<=", "value": -1}], "tags": ["withdrawal", "family"]},
        {"id": "ch01_raghava_confront_saraswathi", "text": "Ask Saraswathi directly whether she intends to use this for herself.", "effects": {"saraswathi_influence": -1, "betrayal_heat": 2, "leader_stability": 1}, "lanes": {"saraswathi_betrayal": 1}, "requires": [{"axis": "saraswathi_influence", "op": ">=", "value": 2}], "tags": ["confrontation", "family"], "priority": 7},
    ]},
    {"id": "gambit_ch01_govardhan", "chapter": 1, "type": "CHARACTERIZATION", "role": "Govardhan Naidu",
     "premise": "Govardhan hears the same worry from three sources, each with a different agenda.",
     "choices": [
        ("ch01_govardhan_test", "Test the gossip through district calls without revealing concern.", {"elite_loyalty": 1, "institutional_control": 1}, {"govardhan_consolidation": 1}),
        ("ch01_govardhan_wait", "Hold back and watch who repeats the rumor unprompted.", {"court_politics": 1, "govardhan_ruthlessness": -1}, {"venkatadri_compromise": 1}),
        ("ch01_govardhan_camp", "Begin listing reliable MLAs before anyone knows there is a list.", {"institutional_control": 2, "betrayal_heat": 1, "govardhan_ruthlessness": 1}, {"govardhan_consolidation": 2}),
        {"id": "ch01_govardhan_family_channel", "text": "Reach Venkatadri first and read the family's real position before moving.", "effects": {"venkatadri_loyalty": 1, "court_politics": 1}, "lanes": {"venkatadri_compromise": 1}, "requires": [{"axis": "venkatadri_loyalty", "op": ">=", "value": 0}], "tags": ["family", "calculation"]},
        {"id": "ch01_govardhan_accelerate", "text": "Accelerate the count and build numbers before the situation becomes visible.", "effects": {"institutional_control": 3, "govardhan_ruthlessness": 2, "betrayal_heat": 2}, "lanes": {"govardhan_consolidation": 3, "pyrrhic_govardhan": 1}, "requires": [{"axis": "govardhan_ruthlessness", "op": ">=", "value": 1}], "priority": 8, "tags": ["escalation", "institutional"]},
    ]},
    {"id": "gambit_ch01_venkatadri", "chapter": 1, "type": "CHARACTERIZATION", "role": "Venkatadri",
     "premise": "Family discomfort has not become public, but Venkatadri can feel people changing their tone around Raghava.",
     "choices": [
        ("ch01_venkatadri_calm", "Calm the family privately before suspicion learns to organize.", {"family_cohesion": 2, "venkatadri_loyalty": 1}, {"raghava_restoration": 1}),
        ("ch01_venkatadri_warn", "Warn Raghava that people close to him are becoming afraid.", {"leader_stability": -1, "raghava_paranoia": 1, "family_cohesion": 1}, {"broken_house": 1}),
        ("ch01_venkatadri_observe", "Say nothing yet and learn who moves when nobody is pushed.", {"court_politics": 1, "venkatadri_loyalty": -1}, {"venkatadri_compromise": 2}),
        {"id": "ch01_venkatadri_distance", "text": "Begin creating distance from both camps before the crisis forces a side.", "effects": {"venkatadri_loyalty": -2, "family_cohesion": -1, "court_politics": 2}, "lanes": {"venkatadri_compromise": 3}, "requires": [{"axis": "venkatadri_loyalty", "op": "<=", "value": 0}], "tags": ["neutrality", "calculation"], "priority": 7},
        {"id": "ch01_venkatadri_back_govardhan_quietly", "text": "Signal to Govardhan quietly that the family is not a wall against him.", "effects": {"venkatadri_loyalty": -1, "institutional_control": 1, "betrayal_heat": 1}, "lanes": {"govardhan_consolidation": 1}, "requires": [{"axis": "betrayal_heat", "op": ">=", "value": 2}], "tags": ["betrayal", "family"], "priority": 6},
    ]},
    {"id": "gambit_ch02_govardhan", "chapter": 2, "type": "CHARACTERIZATION", "role": "Govardhan Naidu",
     "premise": "The warning can still look like concern, but only if Govardhan decides not to make it a threat.",
     "choices": [
        ("ch02_govardhan_negotiate", "Send a final warning through seniors and leave room for dignity.", {"elite_loyalty": 1, "betrayal_heat": -1}, {"venkatadri_compromise": 1}),
        ("ch02_govardhan_threaten", "Make clear that the numbers are already moving.", {"institutional_control": 2, "govardhan_ruthlessness": 1, "betrayal_heat": 1}, {"govardhan_consolidation": 2}),
        ("ch02_govardhan_quiet", "Consolidate quietly while others believe mediation is still possible.", {"institutional_control": 1, "court_politics": 1}, {"pyrrhic_govardhan": 1}),
        {"id": "ch02_govardhan_go_public", "text": "Break cover and make the warning public before Raghava can dismiss it.", "effects": {"betrayal_heat": 3, "media_spin": 2, "elite_loyalty": -1}, "lanes": {"govardhan_consolidation": 2, "broken_house": 1}, "requires": [{"axis": "betrayal_heat", "op": ">=", "value": 3}], "priority": 8, "tags": ["escalation", "public", "media"]},
        {"id": "ch02_govardhan_procedural_lock", "text": "Lock in documentary proof of majority before any response can arrive.", "effects": {"institutional_control": 3, "governor_patience": 1}, "lanes": {"govardhan_consolidation": 3}, "requires": [{"axis": "institutional_control", "op": ">=", "value": 3}], "priority": 9, "tags": ["institutional", "procedure"]},
    ]},
    {"id": "gambit_ch02_raghava", "chapter": 2, "type": "CHARACTERIZATION", "role": "Raghava Rao",
     "premise": "Senior leaders carry a warning into the residence. It arrives dressed as respect.",
     "choices": [
        ("ch02_raghava_listen", "Listen fully and ask what fear has made them brave.", {"leader_stability": 1, "elite_loyalty": 1, "raghava_paranoia": -1}, {"raghava_restoration": 2}),
        ("ch02_raghava_dismiss", "Treat the warning as insolence and force loyalty into the open.", {"leader_stability": -1, "betrayal_heat": 2, "public_mandate": 1}, {"broken_house": 1}),
        ("ch02_raghava_private", "Ask Venkatadri to verify who is truly wavering.", {"family_cohesion": 1, "venkatadri_loyalty": 1}, {"venkatadri_compromise": 1}),
        {"id": "ch02_raghava_massive_public", "text": "Call a mass public meeting the next day and dare the party to stay home.", "effects": {"public_mandate": 3, "betrayal_heat": 1, "media_spin": 2}, "lanes": {"raghava_restoration": 2, "patriarchs_last_roar": 1}, "requires": [{"axis": "public_mandate", "op": ">=", "value": 2}], "priority": 8, "tags": ["public", "escalation", "mass_appeal"]},
        {"id": "ch02_raghava_saraswathi_shield", "text": "Place Saraswathi visibly at his side to make the warning about family loyalty.", "effects": {"saraswathi_influence": 2, "betrayal_heat": 2, "family_cohesion": -1}, "lanes": {"saraswathi_ascendancy": 1, "broken_house": 1}, "requires": [{"axis": "saraswathi_influence", "op": ">=", "value": 2}], "priority": 7, "tags": ["family", "confrontation"]},
    ]},
    {"id": "gambit_ch02_saraswathi", "chapter": 2, "type": "CHARACTERIZATION", "role": "Saraswathi",
     "premise": "Saraswathi can cool the room or turn the warning into proof of betrayal.",
     "choices": [
        ("ch02_saraswathi_cool", "Tell Raghava the warning is fear, not yet treason.", {"leader_stability": 1, "saraswathi_influence": 1, "betrayal_heat": -1}, {"raghava_restoration": 1}),
        ("ch02_saraswathi_radicalize", "Frame the warning as proof that softness invites replacement.", {"saraswathi_influence": 2, "raghava_paranoia": 1, "betrayal_heat": 1}, {"saraswathi_betrayal": 1}),
        ("ch02_saraswathi_record", "Start tracking who entered, who spoke, and who avoided her eyes.", {"court_politics": 2, "saraswathi_influence": 1}, {"saraswathi_ascendancy": 1}),
        {"id": "ch02_saraswathi_own_faction", "text": "Begin building contacts independent of Raghava's standing approval.", "effects": {"saraswathi_influence": 3, "court_politics": 2, "family_cohesion": -1}, "lanes": {"saraswathi_ascendancy": 2, "the_inheritance": 1}, "requires": [{"axis": "saraswathi_influence", "op": ">=", "value": 3}], "priority": 9, "tags": ["ascendancy", "calculation"]},
        {"id": "ch02_saraswathi_isolate_govardhan", "text": "Feed Raghava specific intelligence that names Govardhan as the center.", "effects": {"betrayal_heat": 3, "raghava_paranoia": 2, "govardhan_ruthlessness": 1}, "lanes": {"broken_house": 1, "saraswathi_betrayal": 1}, "requires": [{"axis": "betrayal_heat", "op": ">=", "value": 2}], "priority": 7, "tags": ["betrayal", "manipulation"]},
    ]},
    {"id": "gambit_ch02_interrogation_gov_saraswathi", "chapter": 2, "type": "INTERROGATION",
     "interrogation": "govardhan_vs_saraswathi",
     "premise": "Govardhan chooses a private anteroom and asks the question nobody wants witnessed."},
    {"id": "gambit_ch02_poll", "chapter": 2, "type": "POLL",
     "premise": "The rebel camp must decide whether the warning becomes negotiation, escalation, or cover.",
     "choices": [
        ("ch02_poll_final_warning", "Send one final warning.", {"elite_loyalty": 1, "betrayal_heat": -1}, {"venkatadri_compromise": 1}),
        ("ch02_poll_secure_location", "Move straight to a secure location.", {"hotel_control": 2, "institutional_control": 1}, {"govardhan_consolidation": 2}),
        ("ch02_poll_mediation", "Seek mediated compromise.", {"family_cohesion": 1, "governor_patience": 1}, {"raghava_restoration": 1}),
        ("ch02_poll_split_strategy", "Split public reassurance from private consolidation.", {"court_politics": 1, "institutional_control": 1}, {"pyrrhic_govardhan": 1}),
        {"id": "ch02_poll_burn_bridges", "text": "Cut all back-channel communication and make the split irreversible.", "effects": {"betrayal_heat": 3, "institutional_control": 2, "family_cohesion": -2}, "lanes": {"govardhan_consolidation": 2, "broken_house": 2}, "requires": [{"axis": "betrayal_heat", "op": ">=", "value": 4}], "priority": 9, "tags": ["escalation", "rupture"]},
    ]},
    {"id": "gambit_ch03_govardhan", "chapter": 3, "type": "CHARACTERIZATION", "role": "Govardhan Naidu",
     "premise": "The MLAs are inside the hotel. Control is now physical before it is constitutional.",
     "choices": [
        ("ch03_govardhan_seal", "Seal the camp and make access a privilege.", {"hotel_control": 2, "institutional_control": 1, "betrayal_heat": 1}, {"govardhan_consolidation": 2}),
        ("ch03_govardhan_media", "Let cameras see discipline before rumor defines captivity.", {"media_spin": 2, "public_mandate": -1}, {"pyrrhic_govardhan": 1}),
        ("ch03_govardhan_numbers", "Rush documentary proof of majority before emotion reaches the gates.", {"institutional_control": 2, "governor_patience": 1}, {"govardhan_consolidation": 2}),
        {"id": "ch03_govardhan_intimidate_waverers", "text": "Privately threaten wavering MLAs before they can communicate outside.", "effects": {"institutional_control": 2, "govardhan_ruthlessness": 2, "betrayal_heat": 2}, "lanes": {"govardhan_consolidation": 2, "pyrrhic_govardhan": 1}, "requires": [{"axis": "govardhan_ruthlessness", "op": ">=", "value": 2}], "priority": 8, "tags": ["intimidation", "institution"]},
        {"id": "ch03_govardhan_saraswathi_alliance", "text": "Give Saraswathi a formal role inside the hotel operation in exchange for her contacts.", "effects": {"saraswathi_influence": 2, "court_politics": 2, "hotel_control": 1}, "lanes": {"saraswathi_ascendancy": 1, "govardhan_consolidation": 1}, "requires": [{"axis": "saraswathi_influence", "op": ">=", "value": 3}], "priority": 7, "tags": ["alliance", "saraswathi"]},
    ]},
    {"id": "gambit_ch03_raghava", "chapter": 3, "type": "CHARACTERIZATION", "role": "Raghava Rao",
     "premise": "Raghava is outside the hotel system now. Persuasion, shame, and legality each pull him in a different direction.",
     "choices": [
        ("ch03_raghava_persuade", "Call wavering MLAs by name and make absence feel personal.", {"public_mandate": 2, "leader_stability": 1}, {"raghava_restoration": 2}),
        ("ch03_raghava_shame", "Denounce the hotel as betrayal wearing discipline.", {"betrayal_heat": 2, "public_mandate": 1}, {"patriarchs_last_roar": 1}),
        ("ch03_raghava_legal", "Prepare a legal challenge before confronting the gates.", {"institutional_control": -1, "governor_patience": 1}, {"raghava_restoration": 1}),
        {"id": "ch03_raghava_mass_rally", "text": "Stage a spontaneous mass rally outside the hotel gates and let the crowd speak.", "effects": {"public_mandate": 3, "media_spin": 2, "betrayal_heat": 1}, "lanes": {"raghava_restoration": 2, "patriarchs_last_roar": 2}, "requires": [{"axis": "public_mandate", "op": ">=", "value": 4}], "priority": 9, "tags": ["mass_appeal", "public", "media"]},
        {"id": "ch03_raghava_venkatadri_plea", "text": "Send word to Venkatadri that the family will be blamed if the hotel holds.", "effects": {"family_cohesion": -1, "venkatadri_loyalty": 1}, "lanes": {"venkatadri_compromise": 1}, "requires": [{"axis": "venkatadri_loyalty", "op": ">=", "value": -1}], "tags": ["family", "pressure"]},
    ]},
    {"id": "gambit_ch03_saraswathi", "chapter": 3, "type": "CHARACTERIZATION", "role": "Saraswathi",
     "premise": "Saraswathi knows the hotel can be framed as captivity, treason, or constitutional crisis.",
     "choices": [
        ("ch03_saraswathi_captivity", "Call the hotel a cage built for elected men.", {"media_spin": 2, "saraswathi_influence": 1}, {"saraswathi_ascendancy": 1}),
        ("ch03_saraswathi_betrayal", "Tell Raghava this is no longer dissent but family-backed betrayal.", {"betrayal_heat": 2, "raghava_paranoia": 1}, {"broken_house": 1}),
        ("ch03_saraswathi_legal", "Push the constitutional illegitimacy of locked-away MLAs.", {"governor_patience": -1, "institutional_control": -1}, {"raghava_restoration": 1}),
        {"id": "ch03_saraswathi_parallel_power", "text": "Start a parallel counter-camp outside the hotel to demonstrate majority is contested.", "effects": {"saraswathi_influence": 3, "public_mandate": 2, "court_politics": 2}, "lanes": {"saraswathi_ascendancy": 2, "raghava_restoration": 1}, "requires": [{"axis": "saraswathi_influence", "op": ">=", "value": 4}], "priority": 9, "tags": ["ascendancy", "public"]},
        {"id": "ch03_saraswathi_break_family", "text": "Publicly state that the family did not sanction the hotel and cannot endorse it.", "effects": {"family_cohesion": -3, "betrayal_heat": 2, "media_spin": 2}, "lanes": {"broken_house": 2, "saraswathi_betrayal": 1}, "requires": [{"axis": "family_cohesion", "op": "<=", "value": -2}], "priority": 8, "tags": ["rupture", "family", "media"]},
    ]},
    {"id": "gambit_ch03_poll", "chapter": 3, "type": "POLL",
     "premise": "Inside the hotel, the camp chooses how visibly to behave.",
     "choices": [
        ("ch03_poll_seal", "Seal the camp and deny access.", {"hotel_control": 2, "betrayal_heat": 1}, {"govardhan_consolidation": 2}),
        ("ch03_poll_media", "Let selected media inside.", {"media_spin": 2, "elite_loyalty": 1}, {"pyrrhic_govardhan": 1}),
        ("ch03_poll_majority", "Rush proof of majority.", {"institutional_control": 2, "governor_patience": 1}, {"govardhan_consolidation": 2}),
        ("ch03_poll_openness", "Perform openness while maintaining control.", {"court_politics": 2, "hotel_control": 1}, {"saraswathi_betrayal": 1}),
        {"id": "ch03_poll_intimidate", "text": "Physically bar any attempt to reach wavering MLAs from outside.", "effects": {"hotel_control": 3, "govardhan_ruthlessness": 1, "betrayal_heat": 2}, "lanes": {"govardhan_consolidation": 2, "broken_house": 1}, "requires": [{"axis": "hotel_control", "op": ">=", "value": 2}], "priority": 8, "tags": ["intimidation", "hotel"]},
    ]},
    {"id": "gambit_ch04_interrogation_saraswathi_venkatadri", "chapter": 4, "type": "INTERROGATION",
     "interrogation": "saraswathi_vs_venkatadri",
     "premise": "Saraswathi reaches Venkatadri before the others can turn his hesitation into a verdict."},
    {"id": "gambit_ch04_venkatadri", "chapter": 4, "type": "CHARACTERIZATION", "role": "Venkatadri",
     "premise": "Venkatadri has heard enough to understand that neutrality is becoming a choice with consequences.",
     "choices": [
        ("ch04_venkatadri_family", "Protect family legitimacy even if the party calls it weakness.", {"family_cohesion": 2, "venkatadri_loyalty": 1}, {"raghava_restoration": 1}),
        ("ch04_venkatadri_party", "Accept that the institution may need saving from its founder.", {"institutional_control": 1, "venkatadri_loyalty": -1}, {"govardhan_consolidation": 1}),
        ("ch04_venkatadri_middle", "Refuse both camps until someone offers a future that can survive the morning.", {"venkatadri_loyalty": 0, "family_cohesion": -1}, {"venkatadri_compromise": 2}),
        {"id": "ch04_venkatadri_demand_price", "text": "Tell both camps his support has a price that neither has offered yet.", "effects": {"court_politics": 3, "venkatadri_loyalty": 0}, "lanes": {"venkatadri_compromise": 3}, "requires": [{"axis": "court_politics", "op": ">=", "value": 2}], "priority": 8, "tags": ["calculation", "neutrality"]},
        {"id": "ch04_venkatadri_condemn_govardhan", "text": "Break publicly with the hotel camp and call it what it is without naming Govardhan.", "effects": {"family_cohesion": 1, "betrayal_heat": 1, "venkatadri_loyalty": 2}, "lanes": {"raghava_restoration": 2, "patriarchs_last_roar": 1}, "requires": [{"axis": "family_cohesion", "op": "<=", "value": -3}], "priority": 9, "tags": ["rupture", "family", "public"]},
    ]},
    {"id": "gambit_ch04_interrogation_raghava_venkatadri", "chapter": 4, "type": "INTERROGATION",
     "interrogation": "raghava_vs_venkatadri",
     "premise": "Raghava asks Venkatadri to sit down like family, not like a visitor."},
    {"id": "gambit_ch04_raghava", "chapter": 4, "type": "CHARACTERIZATION", "role": "Raghava Rao",
     "premise": "Raghava tries to retain family legitimacy before numbers make the wound permanent.",
     "choices": [
        ("ch04_raghava_mercy", "Ask for mercy instead of loyalty.", {"public_mandate": 1, "leader_stability": -1, "family_cohesion": -1}, {"patriarchs_last_roar": 1}),
        ("ch04_raghava_history", "Frame the fracture as history judging the family.", {"public_mandate": 2, "family_cohesion": -2}, {"raghava_restoration": 1}),
        ("ch04_raghava_bless", "Offer a conditional blessing if they stop humiliating the house.", {"family_cohesion": 1, "betrayal_heat": -1}, {"venkatadri_compromise": 1}),
        {"id": "ch04_raghava_legacy_weapon", "text": "Invoke every sacrifice made to build this party and dare them to erase it.", "effects": {"public_mandate": 3, "betrayal_heat": 1, "leader_stability": -1}, "lanes": {"patriarchs_last_roar": 3}, "requires": [{"axis": "public_mandate", "op": ">=", "value": 4}], "priority": 9, "tags": ["mass_appeal", "legacy", "escalation"]},
        {"id": "ch04_raghava_unravel", "text": "Stop pretending this is a party crisis. Say it is a family betrayal and nothing less.", "effects": {"leader_stability": -2, "family_cohesion": -3, "public_mandate": 2}, "lanes": {"broken_house": 2, "patriarchs_last_roar": 1}, "requires": [{"axis": "leader_stability", "op": "<=", "value": -2}, {"axis": "betrayal_heat", "op": ">=", "value": 3}], "priority": 8, "tags": ["rupture", "family", "grievance"]},
    ]},
    {"id": "gambit_ch04_govardhan", "chapter": 4, "type": "CHARACTERIZATION", "role": "Govardhan Naidu",
     "premise": "Govardhan can turn family fracture into legislative certainty, but every visible family break has a price.",
     "choices": [
        ("ch04_govardhan_use_family", "Make Venkatadri's distance from Raghava politically visible.", {"institutional_control": 2, "family_cohesion": -2}, {"govardhan_consolidation": 2}),
        ("ch04_govardhan_soften", "Avoid using family wounds and keep the argument institutional.", {"elite_loyalty": 1, "betrayal_heat": -1}, {"pyrrhic_govardhan": 1}),
        ("ch04_govardhan_compromise", "Offer Venkatadri a role in the transition he cannot easily refuse.", {"venkatadri_loyalty": -1, "court_politics": 1}, {"venkatadri_compromise": 1}),
        {"id": "ch04_govardhan_lock_numbers", "text": "Treat the majority as already achieved and start acting like the successor.", "effects": {"institutional_control": 3, "govardhan_ruthlessness": 1, "elite_loyalty": 1}, "lanes": {"govardhan_consolidation": 3}, "requires": [{"axis": "institutional_control", "op": ">=", "value": 5}], "priority": 9, "tags": ["institutional", "procedure"]},
        {"id": "ch04_govardhan_expose_saraswathi", "text": "Let the camp know Saraswathi has been running her own channel. A controlled leak.", "effects": {"saraswathi_influence": -2, "court_politics": 2, "betrayal_heat": 2}, "lanes": {"saraswathi_betrayal": 2, "govardhan_consolidation": 1}, "requires": [{"axis": "saraswathi_influence", "op": ">=", "value": 4}], "priority": 8, "tags": ["betrayal", "saraswathi", "manipulation"]},
    ]},
    {"id": "gambit_ch05_govardhan", "chapter": 5, "type": "CHARACTERIZATION", "role": "Govardhan Naidu",
     "premise": "The resolutions are drafted. The rebellion needs to look cleaner than it feels.",
     "choices": [
        ("ch05_govardhan_clean", "Make the transition procedurally immaculate.", {"institutional_control": 2, "elite_loyalty": 1}, {"govardhan_consolidation": 2}),
        ("ch05_govardhan_aggressive", "Remove Raghava immediately and absorb the moral blast.", {"institutional_control": 2, "betrayal_heat": 2}, {"pyrrhic_govardhan": 2}),
        ("ch05_govardhan_reconcile", "Leave one formal path for Raghava to step down with dignity.", {"family_cohesion": 1, "betrayal_heat": -1}, {"venkatadri_compromise": 1}),
        {"id": "ch05_govardhan_total_control", "text": "Treat the resolution as a unilateral fact and remove all options for negotiation.", "effects": {"institutional_control": 4, "govardhan_ruthlessness": 2, "betrayal_heat": 3}, "lanes": {"govardhan_consolidation": 3, "pyrrhic_govardhan": 2}, "requires": [{"axis": "govardhan_ruthlessness", "op": ">=", "value": 3}, {"axis": "institutional_control", "op": ">=", "value": 5}], "priority": 10, "tags": ["escalation", "institutional", "relentless"]},
        {"id": "ch05_govardhan_venkatadri_endorsement", "text": "Delay finalization until Venkatadri publicly endorses. The optics matter more than the hours.", "effects": {"elite_loyalty": 2, "betrayal_heat": -1, "venkatadri_loyalty": -2}, "lanes": {"govardhan_consolidation": 2, "venkatadri_compromise": 1}, "requires": [{"flag": "venkatadri_endorses_govardhan", "present": True}], "priority": 8, "tags": ["procedure", "endorsement"]},
    ]},
    {"id": "gambit_ch05_interrogation_venkatadri_govardhan", "chapter": 5, "type": "INTERROGATION",
     "interrogation": "venkatadri_vs_govardhan",
     "premise": "The resolutions wait on the table. Venkatadri asks whether the party is being saved or the man who built it destroyed."},
    {"id": "gambit_ch05_poll", "chapter": 5, "type": "POLL",
     "premise": "The hotel camp must formalize rebellion as removal, rescue, compromise, or immediate claim.",
     "choices": [
        ("ch05_poll_remove", "Remove Raghava immediately.", {"institutional_control": 2, "betrayal_heat": 2}, {"govardhan_consolidation": 2}),
        ("ch05_poll_anti_saraswathi", "Frame it as anti-Saraswathi, not anti-Raghava.", {"family_cohesion": -1, "saraswathi_influence": -1}, {"saraswathi_betrayal": 2}),
        ("ch05_poll_reconcile", "Leave one path open for reconciliation.", {"family_cohesion": 1, "elite_loyalty": 1}, {"venkatadri_compromise": 2}),
        ("ch05_poll_governor", "Push the Governor tonight without hesitation.", {"institutional_control": 2, "governor_patience": -1}, {"govardhan_consolidation": 2}),
        {"id": "ch05_poll_venkatadri_ultimatum", "text": "Issue an internal ultimatum: Venkatadri joins or is named an enemy of the transition.", "effects": {"venkatadri_loyalty": -3, "betrayal_heat": 2, "institutional_control": 1}, "lanes": {"broken_house": 2, "govardhan_consolidation": 1}, "requires": [{"axis": "venkatadri_loyalty", "op": "<=", "value": -1}], "priority": 9, "tags": ["rupture", "ultimatum"]},
    ]},
    {"id": "gambit_ch06_raghava", "chapter": 6, "type": "CHARACTERIZATION", "role": "Raghava Rao",
     "premise": "Overnight, legal response, emotional appeal, and retaliation all demand speed.",
     "choices": [
        ("ch06_raghava_legal", "Challenge the majority claim before it hardens.", {"institutional_control": -1, "governor_patience": 1}, {"raghava_restoration": 1}),
        ("ch06_raghava_emotional", "Go public before procedure makes emotion irrelevant.", {"public_mandate": 2, "media_spin": 1}, {"patriarchs_last_roar": 1}),
        ("ch06_raghava_retaliate", "Move against ministers who have crossed the line.", {"leader_stability": -1, "betrayal_heat": 2}, {"broken_house": 1}),
        {"id": "ch06_raghava_governor_appeal", "text": "Go directly to Raj Bhavan and ask the Governor to recognize the constitutional crisis.", "effects": {"governor_patience": 2, "institutional_control": -1, "public_mandate": 1}, "lanes": {"raghava_restoration": 2}, "requires": [{"axis": "governor_patience", "op": ">=", "value": 1}], "priority": 8, "tags": ["constitutional", "governor"]},
        {"id": "ch06_raghava_last_walk", "text": "Walk to the hotel gates with supporters and let what happens happen.", "effects": {"public_mandate": 3, "betrayal_heat": 1, "leader_stability": -1}, "lanes": {"patriarchs_last_roar": 3}, "requires": [{"axis": "public_mandate", "op": ">=", "value": 5}], "priority": 10, "tags": ["mass_appeal", "confrontation", "sacrifice"]},
    ]},
    {"id": "gambit_ch06_govardhan", "chapter": 6, "type": "CHARACTERIZATION", "role": "Govardhan Naidu",
     "premise": "Govardhan must present majority as fact before Raghava can turn it into sacrilege.",
     "choices": [
        ("ch06_govardhan_numbers", "Present the numbers to Raj Bhavan as settled reality.", {"institutional_control": 2, "governor_patience": 1}, {"govardhan_consolidation": 2}),
        ("ch06_govardhan_optics", "Pair the numbers with senior faces and family distance.", {"elite_loyalty": 1, "family_cohesion": -1}, {"pyrrhic_govardhan": 1}),
        ("ch06_govardhan_speed", "Move faster than outrage can coordinate.", {"institutional_control": 1, "govardhan_ruthlessness": 1}, {"govardhan_consolidation": 1}),
        {"id": "ch06_govardhan_delhi_brief", "text": "Brief Delhi before presenting to the Governor so the center cannot be surprised.", "effects": {"delhi_interest": 2, "governor_patience": 1, "institutional_control": 1}, "lanes": {"govardhan_consolidation": 2}, "requires": [{"axis": "delhi_interest", "op": ">=", "value": 1}], "priority": 7, "tags": ["delhi", "institutional"]},
        {"id": "ch06_govardhan_suppress_saraswathi", "text": "Quietly sideline Saraswathi's parallel moves before she complicates the Governor meeting.", "effects": {"saraswathi_influence": -2, "court_politics": 1, "elite_loyalty": 1}, "lanes": {"govardhan_consolidation": 2, "saraswathi_betrayal": 1}, "requires": [{"axis": "saraswathi_influence", "op": ">=", "value": 5}], "priority": 9, "tags": ["saraswathi", "suppression"]},
    ]},
    {"id": "gambit_ch06_interrogation_raghava_govardhan", "chapter": 6, "type": "INTERROGATION",
     "interrogation": "raghava_vs_govardhan",
     "premise": "A threshold space puts Raghava and Govardhan alone together before Raj Bhavan decides."},
    {"id": "gambit_ch07_raghava", "chapter": 7, "type": "CHARACTERIZATION", "role": "Raghava Rao",
     "premise": "At the hotel gates, security blocks Raghava. The humiliation becomes visible before anyone can interpret it.",
     "choices": [
        ("ch07_raghava_stand", "Stand still until the insult has nowhere to hide.", {"public_mandate": 3, "leader_stability": -1}, {"patriarchs_last_roar": 3}),
        ("ch07_raghava_leave", "Leave without giving them the satisfaction of spectacle.", {"leader_stability": 1, "public_mandate": 1}, {"raghava_restoration": 1}),
        ("ch07_raghava_bless_crowd", "Turn toward the crowd, not the gates, and absorb the wound publicly.", {"public_mandate": 3, "betrayal_heat": 1}, {"raghava_restoration": 2}),
        {"id": "ch07_raghava_remove_footwear", "text": "Remove footwear at the gates in a gesture that needs no words.", "effects": {"public_mandate": 4, "betrayal_heat": 2, "leader_stability": -2}, "lanes": {"patriarchs_last_roar": 4}, "requires": [{"axis": "public_mandate", "op": ">=", "value": 5}], "priority": 10, "tags": ["sacrifice", "mass_appeal", "symbol"]},
        {"id": "ch07_raghava_collapse", "text": "Sit on the ground at the hotel entrance and refuse to move until morning.", "effects": {"public_mandate": 3, "leader_stability": -3, "media_spin": 3}, "lanes": {"patriarchs_last_roar": 3, "broken_house": 1}, "requires": [{"axis": "leader_stability", "op": "<=", "value": -2}], "priority": 9, "tags": ["grievance", "symbol", "media"]},
    ]},
    {"id": "gambit_ch07_saraswathi", "chapter": 7, "type": "CHARACTERIZATION", "role": "Saraswathi",
     "premise": "Saraswathi must decide whether this humiliation becomes outrage, weapon, or wound.",
     "choices": [
        ("ch07_saraswathi_outrage", "Make the shame a charge against every silent insider.", {"media_spin": 2, "betrayal_heat": 2}, {"saraswathi_betrayal": 1}),
        ("ch07_saraswathi_dignity", "Protect Raghava from being reduced to the image.", {"leader_stability": 1, "saraswathi_influence": 1}, {"raghava_restoration": 1}),
        ("ch07_saraswathi_weaponize", "Let the image travel before anyone can soften it.", {"public_mandate": 2, "court_politics": 1}, {"saraswathi_ascendancy": 1}),
        {"id": "ch07_saraswathi_claim_moment", "text": "Step into the media moment as the only person who never abandoned him.", "effects": {"saraswathi_influence": 3, "public_mandate": 2, "court_politics": 2}, "lanes": {"saraswathi_ascendancy": 2, "the_inheritance": 1}, "requires": [{"axis": "saraswathi_influence", "op": ">=", "value": 5}], "priority": 10, "tags": ["ascendancy", "media", "inheritance"]},
        {"id": "ch07_saraswathi_family_fracture", "text": "State that the family cannot absorb this and that the party must answer for what was done.", "effects": {"family_cohesion": -3, "betrayal_heat": 2, "media_spin": 2}, "lanes": {"broken_house": 2, "saraswathi_betrayal": 1}, "requires": [{"axis": "family_cohesion", "op": "<=", "value": -3}], "priority": 9, "tags": ["rupture", "family", "media"]},
    ]},
    {"id": "gambit_ch07_interrogation_venkatadri_saraswathi", "chapter": 7, "type": "INTERROGATION",
     "interrogation": "venkatadri_vs_saraswathi",
     "premise": "If blame needs a focal point, Venkatadri is the only one who can say it to Saraswathi's face."},
    {"id": "gambit_ch08_govardhan", "chapter": 8, "type": "CHARACTERIZATION", "role": "Govardhan Naidu",
     "premise": "Deadlines and headcounts are close enough that even certainty has started to look tired.",
     "choices": [
        ("ch08_govardhan_force", "Force immediate headcount before fatigue creates sympathy.", {"institutional_control": 2, "governor_patience": -1}, {"govardhan_consolidation": 2}),
        ("ch08_govardhan_manage", "Manage numbers quietly and let procedure look inevitable.", {"elite_loyalty": 1, "institutional_control": 1}, {"pyrrhic_govardhan": 1}),
        ("ch08_govardhan_bargain", "Reopen one private bargain to prevent a public fracture.", {"family_cohesion": 1, "betrayal_heat": -1}, {"venkatadri_compromise": 1}),
        {"id": "ch08_govardhan_exhaustion_move", "text": "Use the exhaustion in the room to push a procedurally unobjectionable final vote.", "effects": {"institutional_control": 3, "govardhan_ruthlessness": 1, "elite_loyalty": 2}, "lanes": {"govardhan_consolidation": 3}, "requires": [{"axis": "institutional_control", "op": ">=", "value": 6}], "priority": 9, "tags": ["procedure", "institutional"]},
        {"id": "ch08_govardhan_isolate_last_holdouts", "text": "Name the two or three holdouts in the room and apply targeted private pressure.", "effects": {"govardhan_ruthlessness": 2, "betrayal_heat": 1, "institutional_control": 1}, "lanes": {"govardhan_consolidation": 2, "pyrrhic_govardhan": 1}, "requires": [{"axis": "govardhan_ruthlessness", "op": ">=", "value": 4}], "priority": 8, "tags": ["intimidation", "relentless"]},
    ]},
    {"id": "gambit_ch08_raghava", "chapter": 8, "type": "CHARACTERIZATION", "role": "Raghava Rao",
     "premise": "Raghava can fight in public, fight institutionally, or attempt one last private bargain.",
     "choices": [
        ("ch08_raghava_public", "Take the last fight to the people.", {"public_mandate": 2, "leader_stability": -1}, {"patriarchs_last_roar": 2}),
        ("ch08_raghava_institution", "Contest the deadlines through constitutional pressure.", {"governor_patience": -1, "institutional_control": -1}, {"raghava_restoration": 1}),
        ("ch08_raghava_bargain", "Ask for a private settlement before the headcount freezes history.", {"family_cohesion": 1, "betrayal_heat": -1}, {"venkatadri_compromise": 1}),
        {"id": "ch08_raghava_final_address", "text": "Give one final televised address and hand the burden of judgment to the voters.", "effects": {"public_mandate": 4, "media_spin": 2, "leader_stability": -1}, "lanes": {"patriarchs_last_roar": 3, "raghava_restoration": 1}, "requires": [{"axis": "public_mandate", "op": ">=", "value": 6}], "priority": 10, "tags": ["mass_appeal", "media", "legacy"]},
        {"id": "ch08_raghava_resign_with_conditions", "text": "Offer to resign if and only if the family's role in the party is guaranteed in writing.", "effects": {"family_cohesion": 2, "betrayal_heat": -2, "leader_stability": 1}, "lanes": {"venkatadri_compromise": 2, "raghava_restoration": 1}, "requires": [{"axis": "leader_stability", "op": "<=", "value": -3}, {"axis": "family_cohesion", "op": ">=", "value": -1}], "priority": 8, "tags": ["negotiation", "family"]},
    ]},
    {"id": "gambit_ch08_interrogation_saraswathi_raghava", "chapter": 8, "type": "INTERROGATION",
     "interrogation": "saraswathi_vs_raghava",
     "premise": "In the private rooms, Raghava finally asks Saraswathi what she is."},
    {"id": "gambit_ch08_saraswathi", "chapter": 8, "type": "CHARACTERIZATION", "role": "Saraswathi",
     "premise": "Saraswathi can remain loyal, become opportunistic, or prepare for an inheritance nobody has named.",
     "choices": [
        ("ch08_saraswathi_loyal", "Stay with Raghava even if it burns every bridge.", {"saraswathi_influence": 2, "leader_stability": 1, "family_cohesion": -1}, {"the_inheritance": 1}),
        ("ch08_saraswathi_opportunist", "Prepare channels for life after his authority collapses.", {"court_politics": 2, "betrayal_heat": 1}, {"saraswathi_ascendancy": 2}),
        ("ch08_saraswathi_betrayal", "Trade access for survival before the door closes.", {"saraswathi_influence": -1, "betrayal_heat": 2}, {"saraswathi_betrayal": 2}),
        {"id": "ch08_saraswathi_inheritance_claim", "text": "Make a direct move to position herself as the only viable future for the party.", "effects": {"saraswathi_influence": 4, "court_politics": 3, "family_cohesion": -1}, "lanes": {"saraswathi_ascendancy": 3, "the_inheritance": 2}, "requires": [{"axis": "saraswathi_influence", "op": ">=", "value": 6}], "priority": 10, "tags": ["ascendancy", "inheritance", "ambition"]},
        {"id": "ch08_saraswathi_protect_raghava", "text": "Physically refuse to leave Raghava's side until the crisis is resolved.", "effects": {"leader_stability": 2, "saraswathi_influence": 1, "betrayal_heat": -1}, "lanes": {"raghava_restoration": 2, "the_inheritance": 1}, "requires": [{"flag": "inheritance_unlocked", "present": True}], "priority": 9, "tags": ["loyalty", "family"]},
    ]},
    {"id": "gambit_ch08_interrogation_govardhan_venkatadri", "chapter": 8, "type": "INTERROGATION",
     "interrogation": "govardhan_vs_venkatadri",
     "premise": "If Venkatadri remains suspended, Govardhan comes to him. That reversal says enough."},
    {"id": "gambit_ch08_poll", "chapter": 8, "type": "POLL",
     "premise": "The camp chooses the final posture before authority transfers or breaks.",
     "choices": [
        ("ch08_poll_headcount", "Force immediate headcount.", {"institutional_control": 2, "governor_patience": -1}, {"govardhan_consolidation": 2}),
        ("ch08_poll_boycott", "Boycott and delegitimize the process.", {"public_mandate": 1, "institutional_control": -2}, {"broken_house": 2}),
        ("ch08_poll_delhi", "Seek Delhi intervention.", {"delhi_interest": 2, "governor_patience": 1}, {"venkatadri_compromise": 1}),
        ("ch08_poll_compromise", "Reopen private compromise.", {"family_cohesion": 2, "betrayal_heat": -1}, {"venkatadri_compromise": 2}),
        {"id": "ch08_poll_final_rupture", "text": "Demand formal dissolution of any rival faction before tomorrow's deadline.", "effects": {"betrayal_heat": 3, "institutional_control": 2, "family_cohesion": -3}, "lanes": {"govardhan_consolidation": 2, "broken_house": 3}, "requires": [{"axis": "betrayal_heat", "op": ">=", "value": 6}], "priority": 9, "tags": ["rupture", "ultimatum"]},
    ]},
    {"id": "gambit_ch09_raghava", "chapter": 9, "type": "CHARACTERIZATION", "role": "Raghava Rao",
     "premise": "Raghava receives the final shape of the crisis: chair, loss, restoration, fracture, or something stranger.",
     "choices": [
        ("ch09_raghava_claim", "Claim the mandate one final time.", {"public_mandate": 1, "leader_stability": 1}, {"raghava_restoration": 2}),
        ("ch09_raghava_release", "Release the chair without releasing the story.", {"family_cohesion": 1, "betrayal_heat": -1}, {"patriarchs_last_roar": 1}),
        ("ch09_raghava_burn", "Refuse legitimacy to any successor born from this week.", {"betrayal_heat": 2, "family_cohesion": -2}, {"broken_house": 2}),
        {"id": "ch09_raghava_forgive_record", "text": "Issue a public statement of forgiveness that makes every opponent look small.", "effects": {"public_mandate": 3, "leader_stability": 2, "betrayal_heat": -2}, "lanes": {"raghava_restoration": 3, "patriarchs_last_roar": 1}, "requires": [{"axis": "public_mandate", "op": ">=", "value": 7}], "priority": 10, "tags": ["legacy", "mass_appeal", "symbol"]},
        {"id": "ch09_raghava_saraswathi_successor", "text": "Name Saraswathi explicitly as the person who must carry what he built.", "effects": {"saraswathi_influence": 3, "family_cohesion": 1, "leader_stability": 1}, "lanes": {"the_inheritance": 3, "saraswathi_ascendancy": 1}, "requires": [{"flag": "inheritance_unlocked", "present": True}], "priority": 9, "tags": ["inheritance", "succession"]},
    ]},
    {"id": "gambit_ch09_govardhan", "chapter": 9, "type": "CHARACTERIZATION", "role": "Govardhan Naidu",
     "premise": "Govardhan can stabilize power, inherit a wound, or discover that procedure won less than he thought.",
     "choices": [
        ("ch09_govardhan_stabilize", "Accept power and immediately stabilize the institution.", {"institutional_control": 2, "elite_loyalty": 1}, {"govardhan_consolidation": 2}),
        ("ch09_govardhan_acknowledge", "Acknowledge Raghava's place while taking the chair.", {"public_mandate": 1, "betrayal_heat": -1}, {"pyrrhic_govardhan": 1}),
        ("ch09_govardhan_share", "Offer a compromise structure before victory curdles.", {"family_cohesion": 1, "elite_loyalty": -1}, {"venkatadri_compromise": 2}),
        {"id": "ch09_govardhan_total_victory", "text": "Accept power without ceremony and begin governance immediately.", "effects": {"institutional_control": 3, "elite_loyalty": 2, "govardhan_ruthlessness": 1}, "lanes": {"govardhan_consolidation": 4}, "requires": [{"axis": "institutional_control", "op": ">=", "value": 8}], "priority": 10, "tags": ["procedure", "total_control"]},
        {"id": "ch09_govardhan_pyrrhic_speech", "text": "Acknowledge the cost publicly. Let the victory look like what it was.", "effects": {"public_mandate": 2, "betrayal_heat": -1, "govardhan_ruthlessness": -1}, "lanes": {"pyrrhic_govardhan": 3}, "requires": [{"axis": "govardhan_ruthlessness", "op": ">=", "value": 4}], "priority": 8, "tags": ["acknowledgement", "media"]},
    ]},
]

TERMINAL_NODES = [
    ("ending_govardhan_consolidation", "Govardhan is sworn in and stabilizes power through numbers, procedure, and exhausted acceptance."),
    ("ending_raghava_restoration", "Raghava reclaims authority through emotional legitimacy, late reversal, or symbolic defiance."),
    ("ending_saraswathi_ascendancy", "Saraswathi moves from influence to open power and becomes the true inheritor of the crisis."),
    ("ending_venkatadri_compromise", "Both main camps lose enough legitimacy that Venkatadri becomes the acceptable successor."),
    ("ending_broken_house", "No one fully wins. Party, family, and legitimacy fracture beyond repair."),
]


def condition(axis: str, op: str, value: int) -> Dict[str, Any]:
    return {"axis": axis, "op": op, "value": value}


INTERROGATIONS: Dict[str, Dict[str, Any]] = {
    "govardhan_vs_saraswathi": {
        "chapter": 2,
        "participants": {"instigator_role": "Govardhan Naidu", "target_role": "Saraswathi"},
        "player_role": "Saraswathi",
        "theme": "Accusation, legitimacy, insider versus outsider.",
        "setting": "A private anteroom. No audience. Govardhan chose that deliberately.",
        "setup": "Govardhan has managed elections, broken alliances, rebuilt them, and never needed permission. Now Saraswathi has Raghava's ear in a way nobody else does, and he is not here because he is angry. He is here because he has decided.",
        "opening": "I've spent thirty years making sure this party doesn't embarrass itself. I'm not going to stop now.",
        "aftermath": "Neither of them mentions it afterward. That is the most revealing thing about both of them.",
        # Fires if Saraswathi has become visible OR Govardhan is already moving
        "trigger": [
            {"axis": "saraswathi_influence", "op": ">=", "value": 1},
            {"axis": "govardhan_ruthlessness", "op": ">=", "value": 1},
        ],
        "options": [
            {"id": "A", "text": "Thirty years. And in thirty years you never once asked him what he actually needed. I did.", "effects": {"govardhan_ruthlessness": 1, "saraswathi_influence": 2, "betrayal_heat": 1}, "lanes": {"saraswathi_ascendancy": 1}, "flags": ["saraswathi_reverses_govardhan"]},
            {"id": "B", "text": "Ask him directly. Walk into that room now, if you are brave enough to hear the answer.", "effects": {"raghava_paranoia": -1, "court_politics": 2, "venkatadri_loyalty": 1}, "lanes": {"saraswathi_ascendancy": 1}},
            {"id": "C", "text": "Govardhan-garu, we both want him to survive this. I am willing to do what it requires.", "effects": {"elite_loyalty": 1, "govardhan_ruthlessness": -1, "court_politics": 1}, "lanes": {"pyrrhic_govardhan": 1, "saraswathi_ascendancy": 1}, "flags": ["govardhan_saraswathi_parallel"]},
            {"id": "D", "text": "He is unraveling. I am still in that room with him while it happens. Where are you?", "requires": [condition("leader_stability", "<=", -3)], "effects": {"leader_stability": -2, "family_cohesion": -1, "saraswathi_influence": 3}, "lanes": {"saraswathi_ascendancy": 3}, "flags": ["breakdown", "raghava_unraveling_named"]},
        ],
    },
    "raghava_vs_venkatadri": {
        "chapter": 4,
        "participants": {"instigator_role": "Raghava Rao", "target_role": "Venkatadri"},
        "player_role": "Raghava Rao",
        "theme": "Blood, betrayal, and the grief of being failed by someone you raised.",
        "setting": "Raghava's residence, late. The staff have been asked to leave.",
        "setup": "Raghava has faced political enemies his entire career, but Venkatadri is not a political enemy. He is family, and Raghava has no playbook for this.",
        "opening": "Sit down. Not like a visitor. Sit down like you used to.",
        "aftermath": "Venkatadri's silence is the loudest thing in the room.",
        # Fires if family bond is already strained OR Venkatadri is wavering
        "trigger": [
            {"axis": "family_cohesion", "op": "<=", "value": -1},
            {"axis": "venkatadri_loyalty", "op": "<=", "value": 0},
        ],
        "options": [
            {"id": "A", "text": "Tell me it wasn't you. Not the hotel or the numbers. Just tell me it wasn't you.", "effects": {"family_cohesion": -2, "leader_stability": -1, "betrayal_heat": 2, "public_mandate": 1}, "lanes": {"patriarchs_last_roar": 1}},
            {"id": "B", "text": "I built something bigger than me. I did not know it would be used against me from this chair.", "effects": {"public_mandate": 2, "leader_stability": 1, "family_cohesion": -3}, "lanes": {"raghava_restoration": 1}},
            {"id": "C", "text": "Your mother would have known what to do. I relied on that more than I ever told her.", "effects": {"betrayal_heat": 0, "venkatadri_loyalty": 0}, "lanes": {"venkatadri_compromise": 1}, "flags": ["venkatadri_volatile"]},
            {"id": "D", "text": "Then go. If you have decided, go. Do not sit here and make me watch you choose it.", "requires": [condition("leader_stability", "<=", -3), condition("family_cohesion", "<=", -3)], "effects": {"leader_stability": -3, "public_mandate": 2}, "lanes": {"patriarchs_last_roar": 3}, "flags": ["breakdown", "patriarchs_last_roar_unlocked"]},
        ],
    },
    "saraswathi_vs_venkatadri": {
        "chapter": 4,
        "participants": {"instigator_role": "Saraswathi", "target_role": "Venkatadri"},
        "player_role": "Venkatadri",
        "theme": "Seduction of certainty and the price of hesitation.",
        "setting": "A casual crossing of paths that both know was engineered.",
        "setup": "Saraswathi sees Venkatadri's carefulness as an asset instead of a flaw. That is why this conversation is dangerous.",
        "opening": "You've been very careful. For a very long time. I've always wondered what that costs.",
        "aftermath": "She stays after he leaves, sitting exactly where he sat, replaying the shape of what happened.",
        # Fires if family is already fractured OR Saraswathi is visible enough to reach him
        "trigger": [
            {"axis": "family_cohesion", "op": "<=", "value": -3},
            {"axis": "saraswathi_influence", "op": ">=", "value": 2},
        ],
        "options": [
            {"id": "A", "text": "Careful is what keeps families together. You might not know that yet.", "effects": {"saraswathi_influence": -1, "venkatadri_loyalty": 1, "court_politics": 1}, "lanes": {"raghava_restoration": 1}},
            {"id": "B", "text": "What do you need from me specifically? Not the party answer. Not the family answer.", "effects": {"saraswathi_influence": 0, "venkatadri_loyalty": 0}, "lanes": {"venkatadri_compromise": 3}, "flags": ["venkatadri_independent_actor"]},
            {"id": "C", "text": "My father-in-law built this with his hands. I have not forgotten that.", "effects": {"family_cohesion": 1, "raghava_paranoia": -1, "saraswathi_influence": 1}, "lanes": {"raghava_restoration": 1}},
            {"id": "D", "text": "You came to me before Govardhan did. I noticed that. I have not decided what it means.", "effects": {"court_politics": 2, "govardhan_ruthlessness": 1}, "lanes": {"venkatadri_compromise": 2}, "flags": ["venkatadri_suspended"]},
            {"id": "E", "text": "I am tired of everyone needing me to be the answer to their particular problem.", "requires": [condition("family_cohesion", "<=", -3), condition("betrayal_heat", ">=", 3)], "effects": {"venkatadri_loyalty": -3, "saraswathi_influence": 2}, "lanes": {"broken_house": 3}, "flags": ["breakdown", "venkatadri_unaligned"]},
        ],
    },
    "venkatadri_vs_govardhan": {
        "chapter": 5,
        "participants": {"instigator_role": "Venkatadri", "target_role": "Govardhan Naidu"},
        "player_role": "Venkatadri",
        "theme": "Conscience versus necessity.",
        "setting": "The hotel, late night. The resolutions have been drafted.",
        "setup": "Govardhan has the numbers, the Governor's patience, and the legal architecture. What he lacks is Venkatadri standing beside him when it becomes public.",
        "opening": "The party survives this. I need you to know that is what this is about. Not him. Not me. The institution.",
        "aftermath": "The papers get signed or they do not. This is still the conversation they both remember years later.",
        # Conditional: fires only if Venkatadri is truly suspended or loyalty is near-zero, and Govardhan has the machine moving
        "trigger": [
            [{"flag": "venkatadri_suspended", "present": True}, {"axis": "institutional_control", "op": ">=", "value": 3}],
            [{"axis": "venkatadri_loyalty", "op": "<=", "value": 1}, {"axis": "venkatadri_loyalty", "op": ">=", "value": -1}, {"axis": "institutional_control", "op": ">=", "value": 3}],
        ],
        "options": [
            {"id": "A", "text": "When you are the institution, will you remember tonight differently than I will?", "effects": {"govardhan_ruthlessness": 1, "institutional_control": 1, "betrayal_heat": 2}, "lanes": {"pyrrhic_govardhan": 1}},
            {"id": "B", "text": "I will stand with you tonight. But I speak to him first when this is truly over.", "effects": {"venkatadri_loyalty": -2, "institutional_control": 2, "elite_loyalty": 1, "family_cohesion": -1}, "lanes": {"govardhan_consolidation": 2, "venkatadri_compromise": 1}, "flags": ["venkatadri_endorses_govardhan"]},
            {"id": "C", "text": "History from inside mostly looks like a corridor you cannot turn around in.", "effects": {"venkatadri_loyalty": 0}, "lanes": {"broken_house": 1, "venkatadri_compromise": 2}, "flags": ["venkatadri_suspended"]},
            {"id": "D", "text": "He called me tonight. He did not ask me to stop you. He asked if I was okay.", "requires": [condition("family_cohesion", "<=", -3)], "effects": {"leader_stability": 2, "family_cohesion": 1}, "lanes": {"patriarchs_last_roar": 3}, "flags": ["breakdown", "raghava_human_moment"]},
        ],
    },
    "raghava_vs_govardhan": {
        "chapter": 6,
        "participants": {"instigator_role": "Raghava Rao", "target_role": "Govardhan Naidu"},
        "player_role": "Raghava Rao",
        "theme": "Betrayal, succession, and a relationship becoming historical fact.",
        "setting": "A corridor or threshold neither chose.",
        "setup": "Raghava has been betrayed before. What he did not know is that it feels different when the person doing it genuinely believes he is right.",
        "opening": "I made you. I chose you, when there were others. I want to understand why that did not matter.",
        "aftermath": "Govardhan says something before leaving. The game does not render it. This scene belongs to Raghava.",
        # Always fires — core confrontation of ch06
        "trigger": [{"axis": "betrayal_heat", "op": ">=", "value": 1}],
        "options": [
            {"id": "A", "text": "Tell me what I did that made this feel necessary to you.", "effects": {"leader_stability": 2, "public_mandate": 1, "betrayal_heat": -1}, "lanes": {"raghava_restoration": 3}},
            {"id": "B", "text": "You will win. And you will spend your life explaining why the explanation sounds like this.", "effects": {"public_mandate": 3, "elite_loyalty": -1, "govardhan_ruthlessness": 1}, "lanes": {"patriarchs_last_roar": 2}},
            {"id": "C", "text": "Walk away from it tonight. I am not asking you to lose. I am asking you to stop.", "effects": {"family_cohesion": 1, "betrayal_heat": 2}, "lanes": {"broken_house": 1}, "flags": ["last_point_of_change"]},
            {"id": "D", "text": "Was it always this? If you sat across from me all those years knowing, what does that make me?", "requires": [condition("leader_stability", "<=", -3), condition("raghava_paranoia", ">=", 2)], "effects": {"leader_stability": -2, "raghava_paranoia": 2, "public_mandate": 3}, "lanes": {"patriarchs_last_roar": 3}, "flags": ["breakdown", "betrayal_turns_inward"]},
        ],
    },
    "saraswathi_vs_raghava": {
        "chapter": 8,
        "participants": {"instigator_role": "Saraswathi", "target_role": "Raghava Rao"},
        "player_role": "Saraswathi",
        "theme": "Dependence, intimacy, and the power of the person who stayed.",
        "setting": "The back of the residence, in a private room outside the public crisis.",
        "setup": "By Chapter 8 most things have been stripped away. What remains, visibly and stubbornly, is Saraswathi.",
        "opening": "Everyone has told me what you are. I never asked you.",
        "aftermath": "He does not ask her to leave. That is the answer.",
        # Always fires in ch08 — central to Saraswathi arc
        "trigger": [{"axis": "saraswathi_influence", "op": ">=", "value": 1}],
        "options": [
            {"id": "A", "text": "I am the person who is still here. Decide what that means tonight.", "effects": {"saraswathi_influence": 2, "leader_stability": 1, "court_politics": 2}, "lanes": {"saraswathi_ascendancy": 3}},
            {"id": "B", "text": "I am the only person in this building who never needed anything from you.", "effects": {"leader_stability": 2, "raghava_paranoia": -2, "betrayal_heat": -1}, "lanes": {"raghava_restoration": 2}},
            {"id": "C", "text": "Do you trust me because you decided to, or because you cannot afford not to anymore?", "effects": {"leader_stability": 1, "family_cohesion": -1}, "lanes": {"the_inheritance": 1}},
            {"id": "D", "text": "I am what this party made necessary and then refused to name.", "effects": {"saraswathi_influence": 3, "court_politics": 2, "betrayal_heat": 2}, "lanes": {"saraswathi_ascendancy": 3, "saraswathi_betrayal": 2}},
            {"id": "E", "text": "I do not know how to leave. I have never had a plan for what I do if this ends.", "requires": [condition("saraswathi_influence", ">=", 5), condition("leader_stability", "<=", -3)], "effects": {"leader_stability": 3, "raghava_paranoia": -3, "family_cohesion": -2}, "lanes": {"the_inheritance": 4}, "flags": ["breakdown", "inheritance_unlocked"]},
        ],
    },
    "govardhan_vs_venkatadri": {
        "chapter": 8,
        "participants": {"instigator_role": "Govardhan Naidu", "target_role": "Venkatadri"},
        "player_role": "Govardhan Naidu",
        "theme": "The pressure of history and the loneliness of the man who has to ask.",
        "setting": "A neutral hotel room. Govardhan comes to Venkatadri this time.",
        "setup": "Govardhan is not a man who asks. He engineers reality until asking is unnecessary. He is here because the gap has Venkatadri's name.",
        "opening": "I've never asked you for anything directly. I'm asking now.",
        "aftermath": "Govardhan thanks him before leaving. Formally. Correctly.",
        # Conditional: Venkatadri must still be undecided (suspended or loyalty near-zero)
        "trigger": [
            [{"flag": "venkatadri_suspended", "present": True}],
            [{"axis": "venkatadri_loyalty", "op": "<=", "value": 0}, {"axis": "venkatadri_loyalty", "op": ">=", "value": -2}],
        ],
        "options": [
            {"id": "A", "text": "Stand with me publicly tomorrow. After that your conscience can do what it requires.", "effects": {"institutional_control": 2, "elite_loyalty": 2, "venkatadri_loyalty": -2}, "lanes": {"govardhan_consolidation": 2}, "flags": ["venkatadri_reluctant_endorsement"]},
            {"id": "B", "text": "After tonight waiting becomes its own answer. I am telling you how the situation works.", "effects": {"betrayal_heat": 2, "govardhan_ruthlessness": 1}, "lanes": {"broken_house": 1}},
            {"id": "C", "text": "Twenty years from now, I need you able to say you were part of the institution surviving.", "effects": {"elite_loyalty": 1, "venkatadri_loyalty": -1}, "lanes": {"venkatadri_compromise": 1}},
            {"id": "D", "text": "I am tired of being the person who has to close things.", "requires": [condition("govardhan_ruthlessness", ">=", 4), condition("betrayal_heat", ">=", 5)], "effects": {"govardhan_ruthlessness": -1, "venkatadri_loyalty": -2}, "lanes": {"pyrrhic_govardhan": 3}, "flags": ["breakdown", "govardhan_crack"]},
        ],
    },
    "venkatadri_vs_saraswathi": {
        "chapter": 7,
        "participants": {"instigator_role": "Venkatadri", "target_role": "Saraswathi"},
        "player_role": "Venkatadri",
        "theme": "Counter-accusation, moral ambiguity, two people pulling the same thread.",
        "setting": "A hallway or doorway. It happens because they are in the same space at the wrong moment.",
        "setup": "Venkatadri has watched Saraswathi be blamed for things she did not do and avoided naming the things she did do. She sees the same doubleness in him.",
        "opening": "I never thought you were exactly the cause. I also never thought you were exactly innocent.",
        "aftermath": "She watches him walk away, unused to being the one left watching.",
        # Conditional: family must be already fractured OR Saraswathi must be exposed
        "trigger": [
            {"axis": "family_cohesion", "op": "<=", "value": -3},
            {"flag": "saraswathi_reverses_govardhan", "present": True},
        ],
        "options": [
            {"id": "A", "text": "Tell me one thing you did because it was right. Not strategic. Just right.", "effects": {"saraswathi_influence": -1, "court_politics": -1, "family_cohesion": 1}, "lanes": {"venkatadri_compromise": 1}},
            {"id": "B", "text": "Tell me what this family looks like from outside it.", "effects": {"saraswathi_influence": 1, "betrayal_heat": -1}, "lanes": {"venkatadri_compromise": 2}},
            {"id": "C", "text": "You defended him when nobody else would. Whatever else is true, I saw that.", "effects": {"betrayal_heat": -2, "family_cohesion": 2}, "lanes": {"raghava_restoration": 1}},
            {"id": "D", "text": "There is no true thing. There is just what happened, and none of us will agree on what that was.", "requires": [condition("family_cohesion", "<=", -5)], "effects": {"betrayal_heat": -1}, "lanes": {"broken_house": 1}, "flags": ["breakdown", "historian_complete_register"]},
        ],
    },
}


# ---------------------------------------------------------------------------
# Helper lookups
# ---------------------------------------------------------------------------

def beat_by_id(node_id: str) -> Optional[Dict[str, Any]]:
    return next((beat for beat in MASTER_BEATS if beat["id"] == node_id), None)


def chapter_for_node(node_id: str) -> int:
    beat = beat_by_id(node_id)
    if beat:
        return int(beat["chapter"])
    if node_id.startswith("ending_"):
        return 9
    return 1


def op_matches(actual: int, op: str, expected: int) -> bool:
    if op == "<=":
        return actual <= expected
    if op == ">=":
        return actual >= expected
    if op == "<":
        return actual < expected
    if op == ">":
        return actual > expected
    if op == "==":
        return actual == expected
    return False


def option_available(option: Dict[str, Any], state_axes: Dict[str, int]) -> bool:
    return all(op_matches(int(state_axes.get(rule["axis"], 0)), rule["op"], int(rule["value"])) for rule in option.get("requires", []))


def resolve_lane(lane_weights: Dict[str, int], state_axes: Dict[str, int]) -> str:
    weights = dict(LANE_WEIGHTS)
    weights.update(lane_weights or {})
    if state_axes.get("family_cohesion", 0) <= -6 or state_axes.get("betrayal_heat", 0) >= 9:
        weights["broken_house"] += 3
    if state_axes.get("public_mandate", 0) >= 8 and state_axes.get("leader_stability", 0) <= -2:
        weights["patriarchs_last_roar"] += 3
    if state_axes.get("saraswathi_influence", 0) >= 7 and state_axes.get("court_politics", 0) >= 5:
        weights["saraswathi_ascendancy"] += 3
    if state_axes.get("institutional_control", 0) >= 8 and state_axes.get("elite_loyalty", 0) >= 4:
        weights["govardhan_consolidation"] += 3
    if abs(state_axes.get("venkatadri_loyalty", 0)) <= 1 and state_axes.get("family_cohesion", 0) <= -2:
        weights["venkatadri_compromise"] += 2
    return max(weights, key=lambda lane: (weights[lane], lane))


def terminal_for_lane(lane: str) -> str:
    if lane in {"govardhan_consolidation", "pyrrhic_govardhan"}:
        return "ending_govardhan_consolidation"
    if lane in {"raghava_restoration", "patriarchs_last_roar"}:
        return "ending_raghava_restoration"
    if lane in {"saraswathi_ascendancy", "saraswathi_betrayal", "the_inheritance"}:
        return "ending_saraswathi_ascendancy"
    if lane == "venkatadri_compromise":
        return "ending_venkatadri_compromise"
    return "ending_broken_house"
