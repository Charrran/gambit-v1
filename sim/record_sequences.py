"""
Record choice sequences (and the outcomes the game logic produced for them) to
tests/fixtures/recorded_sequences.json.

    python -m sim.record_sequences

Recorded once at the pre-balance logic (v1-baseline + deadlock fix), so the
`outcome` blocks document baseline behaviour.
"""
import asyncio
import json
from pathlib import Path

from sim.harness import play_game
from sim.run_sim import table_policies

ROOT = Path(__file__).resolve().parent.parent
TABLES = (
    [("random", s) for s in range(6)]
    + [("coordinated:govardhan_consolidation", 1), ("coordinated:raghava_restoration", 2),
       ("coordinated:saraswathi_ascendancy", 3), ("coordinated:broken_house", 4),
       ("coordinated:patriarchs_last_roar", 5), ("coordinated:venkatadri_compromise", 6)]
    + [("disagreement", 11), ("disagreement", 12), ("solo:the_inheritance", 13), ("solo:saraswathi_betrayal", 14)]
)


async def main():
    recordings = []
    for table, seed in TABLES:
        steps = []
        policies, _ = table_policies(table, seed)
        r = await play_game(policies, seed=seed, record=steps)
        recordings.append({
            "name": f"{table}#{seed}",
            "roles": r["roles"],
            "steps": steps,
            "outcome": {
                "resolved_lane": r["resolved_lane"],
                "ending_node": r["ending_node"],
                "state_axes": r["state_axes"],
                "lane_weights": r["lane_weights"],
                "story_flags": r["story_flags"],
            },
        })
    out = ROOT / "tests" / "fixtures" / "recorded_sequences.json"
    out.write_text(json.dumps(recordings, indent=1), encoding="utf-8")
    print(f"{len(recordings)} sequences -> {out}")
    for rec in recordings:
        print(f"  {rec['name']:42s} {len(rec['steps']):3d} steps -> {rec['outcome']['resolved_lane']}")


if __name__ == "__main__":
    asyncio.run(main())
