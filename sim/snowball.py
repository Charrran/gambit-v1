"""How early is the ending decided? P(final lane == leading lane at the start of chapter c)."""
import asyncio
import sys
from collections import Counter

from sim.bots import random_bot
from sim.harness import play_game
from app.design.content import chapter_for_node


async def main(n):
    hits = Counter()
    for s in range(n):
        r = await play_game({f"p{i}": random_bot(s * 10 + i) for i in range(4)}, seed=50000 + s)
        seen = set()
        for step in r["trajectory"]:
            ch = chapter_for_node(step["node"])
            if ch in seen:
                continue
            seen.add(ch)
            lanes = step["before"][1]
            if any(lanes.values()):
                lead = max(lanes, key=lambda k: (lanes[k], k))
                hits[ch] += lead == r["resolved_lane"]
    for ch in sorted(hits):
        print(f"start of ch{ch}: leader == final ending in {hits[ch] / n * 100:.1f}% of games")


if __name__ == "__main__":
    asyncio.run(main(int(sys.argv[1]) if len(sys.argv) > 1 else 1000))
