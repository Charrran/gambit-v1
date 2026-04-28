from __future__ import annotations

from typing import Any, Dict, List

from app.design.content import CHAPTER_ANCHORS, chapter_for_node
from app.services.ai_engine import ai_engine
from app.models.schemas import NewsHeadline


ROLE_KEYS = {
    "Raghava Rao": "raghava_rao",
    "Govardhan Naidu": "govardhan_naidu",
    "Saraswathi": "saraswathi",
    "Venkatadri": "venkatadri",
}

CHAPTER_DATES = {
    1: "12 August 1995",
    2: "13 August 1995",
    3: "14 August 1995",
    4: "15 August 1995",
    5: "16 August 1995",
    6: "17 August 1995",
    7: "18 August 1995",
    8: "19 August 1995",
    9: "September 1995",
}

PUBLICATIONS = [
    "Empire Bay Courier",
    "Deccan Wire Service",
    "The Political Observer",
]


def clamp(value: int, low: int = 0, high: int = 100) -> int:
    return max(low, min(high, int(value)))


def build_trust_matrix(state_axes: Dict[str, int] | None) -> Dict[str, int]:
    """
    Convert authored state-axis consequences into pairwise relationship pressure.
    The frontend renders this as trust, but the source of truth remains the
    graph-driven metrics changed by Neo4j choices.
    """
    axes = state_axes or {}
    betrayal = axes.get("betrayal_heat", 0)
    family = axes.get("family_cohesion", 0)
    leader = axes.get("leader_stability", 0)
    institution = axes.get("institutional_control", 0)
    elite = axes.get("elite_loyalty", 0)
    court = axes.get("court_politics", 0)
    saras = axes.get("saraswathi_influence", 0)
    venkat = axes.get("venkatadri_loyalty", 0)
    gov = axes.get("govardhan_ruthlessness", 0)
    paranoia = axes.get("raghava_paranoia", 0)

    return {
        "raghava_rao-govardhan_naidu": clamp(55 + family * 2 - betrayal * 4 - institution * 2 + elite),
        "raghava_rao-saraswathi": clamp(58 + saras * 3 + leader * 2 - paranoia * 4 - betrayal),
        "raghava_rao-venkatadri": clamp(62 + family * 5 + venkat * 4 + leader - betrayal * 2),
        "govardhan_naidu-saraswathi": clamp(46 + court * 2 - saras * 2 - gov * 3 - betrayal),
        "govardhan_naidu-venkatadri": clamp(50 + institution * 2 + elite * 2 - abs(venkat) * 3 - betrayal * 2),
        "saraswathi-venkatadri": clamp(52 + family * 2 + court - abs(saras) - betrayal + venkat * 2),
    }


def fallback_headlines(state: Any) -> List[NewsHeadline]:
    axes = state.state_axes or {}
    lane_weights = state.lane_weights or {}
    leading_lane = max(lane_weights, key=lambda lane: lane_weights[lane]) if lane_weights else "broken_house"
    chapter = chapter_for_node(state.current_scene_node or state.current_node)
    chapter_title = CHAPTER_ANCHORS.get(chapter, {}).get("title", "The Crisis")
    in_world_date = CHAPTER_DATES.get(chapter, "August 1995")

    if axes.get("betrayal_heat", 0) >= 5:
        lead = ("Private Warnings Become Open Fracture", "Senior figures are no longer treating the dispute as a family matter.")
    elif axes.get("institutional_control", 0) >= 5:
        lead = ("Hotel Camp Tightens Its Procedural Grip", "Documents, headcounts, and corridor discipline now matter more than speeches.")
    elif axes.get("public_mandate", 0) >= 5:
        lead = ("Crowds Reframe the Leadership Question", "Public sympathy is complicating every calculation inside the party machinery.")
    elif axes.get("saraswathi_influence", 0) >= 5:
        lead = ("Saraswathi's Shadow Falls Across Negotiations", "Those outside the inner circle are beginning to name what they previously implied.")
    else:
        lead = (f"{chapter_title} Enters a Narrower Phase", "The faction is moving carefully, but the range of acceptable outcomes is shrinking.")

    return [
        NewsHeadline(
            id="lead",
            dateline=f"Empire Bay Courier · {in_world_date}",
            headline=lead[0],
            body=lead[1],
        ),
        NewsHeadline(
            id="lane",
            dateline=f"Deccan Wire Service · {in_world_date}",
            headline=leading_lane.replace("_", " ").title(),
            body="Internal numbers suggest this path is becoming the most likely interpretation of the crisis.",
        ),
        NewsHeadline(
            id="room",
            dateline=f"The Political Observer · {in_world_date}",
            headline="Closed Rooms Now Carry Public Consequences",
            body="Each private exchange is changing how loyalty, legitimacy, and family obligation are understood outside the suite.",
        ),
    ]


def normalize_headlines(items: List[Any], state: Any) -> List[NewsHeadline]:
    chapter = chapter_for_node(state.current_scene_node or state.current_node)
    in_world_date = CHAPTER_DATES.get(chapter, "August 1995")
    normalized = []
    for index, item in enumerate((items or [])[:3]):
        data = item.model_dump() if hasattr(item, "model_dump") else dict(item)
        publication = PUBLICATIONS[index % len(PUBLICATIONS)]
        normalized.append(
            NewsHeadline(
                id=data.get("id") or f"headline_{index + 1}",
                dateline=f"{publication} · {in_world_date}",
                headline=data.get("headline") or "Crisis Enters New Phase",
                body=data.get("body") or "Party observers say the balance of pressure has shifted again.",
            )
        )
    return normalized or fallback_headlines(state)


async def refresh_live_intel(state: Any) -> Any:
    state.trust_matrix = build_trust_matrix(state.state_axes)
    try:
        chapter = chapter_for_node(state.current_node)
        state.news_headlines = normalize_headlines(await ai_engine.generate_news_headlines(
            current_node=state.current_node,
            chapter_title=CHAPTER_ANCHORS.get(chapter, {}).get("title", ""),
            in_world_date=CHAPTER_DATES.get(chapter, "August 1995"),
            state_axes=state.state_axes,
            lane_weights=state.lane_weights,
            story_flags=state.story_flags,
            recent_history=state.session_history[-6:],
        ), state)
    except Exception as exc:
        print(f"[WARN] Headline generation failed for {state.session_id}:{state.current_node}: {exc}")
        state.news_headlines = fallback_headlines(state)
    return state


def role_key(role_name: str | None) -> str:
    return ROLE_KEYS.get(role_name or "", (role_name or "saraswathi").lower().replace(" ", "_"))
