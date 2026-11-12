"""
Bot policies for the Gambit simulator.

A policy is called with (state, player_id, role, payloads) and returns one of the
visible choice_ids.  Bots only see what a player sees (the offered choices and the
public lane/axis panels the frontend already shows); they never read hidden code.
"""
from __future__ import annotations

import random
from typing import Dict, List

LANES = [
    "govardhan_consolidation",
    "raghava_restoration",
    "saraswathi_ascendancy",
    "venkatadri_compromise",
    "broken_house",
    "pyrrhic_govardhan",
    "patriarchs_last_roar",
    "saraswathi_betrayal",
    "the_inheritance",
]

# What a player "pushing toward" an outcome would want the visible state to do.
# Derived from the lane descriptions in transition_engine._pressure_sentence and the
# themed tags in content.py. Lane points shown on each choice dominate; axis intent
# is a light tie-breaker so bots also chase the conditional choices that unlock.
AXIS_INTENT: Dict[str, Dict[str, float]] = {
    "govardhan_consolidation": {"institutional_control": 1, "elite_loyalty": 1},
    "pyrrhic_govardhan": {"govardhan_ruthlessness": 1, "institutional_control": 0.5, "betrayal_heat": 0.5},
    "raghava_restoration": {"public_mandate": 1, "leader_stability": 1, "family_cohesion": 0.5},
    "patriarchs_last_roar": {"public_mandate": 1, "leader_stability": -0.5, "betrayal_heat": 0.5},
    "saraswathi_ascendancy": {"saraswathi_influence": 1, "court_politics": 1},
    "saraswathi_betrayal": {"betrayal_heat": 1, "saraswathi_influence": -0.5, "court_politics": 0.5},
    "the_inheritance": {"saraswathi_influence": 1, "family_cohesion": 0.5, "leader_stability": 0.5},
    "venkatadri_compromise": {"court_politics": 0.5, "family_cohesion": 0.5, "betrayal_heat": -0.5},
    "broken_house": {"betrayal_heat": 1, "family_cohesion": -1},
}


def random_bot(seed: int):
    rng = random.Random(seed)

    def policy(state, player_id, role, payloads: List[Dict]) -> str:
        return rng.choice(payloads)["choice_id"]

    policy.kind = "random"
    return policy


def directed_score(payload: Dict, lane: str) -> float:
    lanes = payload.get("lanes") or {}
    effects = payload.get("effects") or {}
    score = 3.0 * lanes.get(lane, 0)
    score -= 0.5 * sum(v for k, v in lanes.items() if k != lane and v > 0)
    for axis, weight in AXIS_INTENT[lane].items():
        score += 0.3 * weight * effects.get(axis, 0)
    return score


def directed_bot(lane: str, seed: int):
    """Always picks the visible choice that best pushes `lane` (ties broken randomly)."""
    rng = random.Random(seed)

    def policy(state, player_id, role, payloads: List[Dict]) -> str:
        scored = [(directed_score(p, lane), rng.random(), p["choice_id"]) for p in payloads]
        return max(scored)[2]

    policy.kind = f"push:{lane}"
    return policy
