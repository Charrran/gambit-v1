"""
Where does a turn spend its time?  python -m sim.profile_turn [--real-redis]

Plays one random game through the real game logic with the LLM and graph stubbed,
counting state saves and timing them. With --real-redis the saves go to the
REDIS_URL in .env, which shows the network cost per decision.
"""
import argparse
import asyncio
import time
from pathlib import Path

from dotenv import dotenv_values

ap = argparse.ArgumentParser()
ap.add_argument("--real-redis", action="store_true")
ap.add_argument("--games", type=int, default=1)
args = ap.parse_args()

from sim.bots import random_bot  # noqa: E402
from sim.harness import install_offline_backends, play_game  # noqa: E402

install_offline_backends()
from app.services.state import state_manager  # noqa: E402

stats = {"sets": 0, "set_seconds": 0.0, "bytes": 0}


async def main():
    if args.real_redis:
        import redis.asyncio as redis

        url = dotenv_values(Path(__file__).resolve().parent.parent / ".env")["REDIS_URL"]
        client = redis.from_url(url, decode_responses=True)
        await client.ping()
    else:
        client = state_manager.client
    original_set = client.set

    async def timed_set(key, value, *a, **k):
        start = time.perf_counter()
        result = await original_set(key, value, *a, **k)
        stats["sets"] += 1
        stats["set_seconds"] += time.perf_counter() - start
        stats["bytes"] += len(value)
        return result

    client.set = timed_set
    state_manager.client = client
    start = time.perf_counter()
    decisions = 0
    for g in range(args.games):
        result = await play_game({f"p{i}": random_bot(g * 10 + i) for i in range(4)}, seed=g, session_id=f"PROFILE{g}",
                                 deadlock_timeout=60.0)
        decisions += sum(1 for h in result["history"] if h["role"] != "SYSTEM")
    total = time.perf_counter() - start
    if args.real_redis:
        for g in range(args.games):
            await client.delete(f"game:PROFILE{g}")
        await client.aclose()
    print(f"decisions: {decisions}   wall: {total:.2f}s   per decision: {total / decisions * 1000:.1f} ms")
    print(f"state saves: {stats['sets']} ({stats['sets'] / decisions:.1f} per decision), "
          f"{stats['set_seconds']:.2f}s in Redis ({stats['set_seconds'] / total * 100:.0f}% of wall), "
          f"avg payload {stats['bytes'] / max(1, stats['sets']) / 1024:.1f} KB")
    print(f"game logic only: {(total - stats['set_seconds']) / decisions * 1000:.2f} ms per decision")


asyncio.run(main())
