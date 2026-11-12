"""
Play one full game against a running server with four real WebSocket clients.

    python -m sim.e2e_client [--port 8765] [--seed N]

Uses the same HTTP lobby routes and /ws/play protocol as gambit-frontend: each
client reacts only to the messages it receives (SPOTLIGHT_CHOICE /
INTERROGATION_CHOICE / POLL_REQUEST) and stops at GAME_OVER.
"""
import argparse
import asyncio
import json
import random
import time

import httpx
import websockets


PLAYERS = ["e2e_ana", "e2e_ben", "e2e_cy", "e2e_dev"]


async def player(base_ws, sid, pid, rng, log):
    acted = set()
    turns = 0
    async with websockets.connect(f"{base_ws}/ws/play/{sid}/{pid}", max_size=None) as ws:
        node = None
        while True:
            msg = json.loads(await asyncio.wait_for(ws.recv(), timeout=180))
            kind = msg.get("type")
            if kind == "ERROR":
                log.append((pid, "ERROR", msg.get("error")))
            if kind == "NARRATIVE_BEAT":
                node = msg.get("node_id")
            if kind in ("SPOTLIGHT_CHOICE", "INTERROGATION_CHOICE", "POLL_REQUEST"):
                if node in acted or not msg.get("options"):
                    continue
                acted.add(node)
                options = msg["options"]
                choice = rng.choice(options)["choice_id"]
                await ws.send(json.dumps({"choice_id": choice}))
                turns += 1
                log.append((pid, node, choice, options[[o["choice_id"] for o in options].index(choice)]["text"][:70]))
            if kind == "GAME_OVER":
                return msg, turns


async def main(port, seed):
    base = f"http://127.0.0.1:{port}"
    rng = random.Random(seed)
    async with httpx.AsyncClient(base_url=base, timeout=60) as http:
        sid = (await http.post("/lobby/create", json={"player_id": PLAYERS[0]})).json()["session_id"]
        for pid in PLAYERS[1:]:
            (await http.post(f"/lobby/{sid}/join", json={"player_id": pid})).raise_for_status()
        (await http.post(f"/lobby/{sid}/start")).raise_for_status()
        roles = (await http.get(f"/lobby/{sid}/state")).json()["active_players"]
    print(f"session {sid}: " + ", ".join(f"{p}={roles[p]['role']}" for p in PLAYERS), flush=True)
    log = []
    t0 = time.time()
    results = await asyncio.gather(*[
        player(f"ws://127.0.0.1:{port}", sid, pid, random.Random(rng.random()), log) for pid in PLAYERS
    ])
    elapsed = time.time() - t0
    finals = [r[0] for r in results]
    errors = [e for e in log if e[1] == "ERROR"]
    choices = [e for e in log if e[1] != "ERROR"]
    print(f"{len(choices)} choices submitted over WebSocket in {elapsed:.0f}s; {len(errors)} ERROR messages")
    for e in choices[:5]:
        print("  ", e)
    print("   ...")
    same = all(f.get("resolved_lane") == finals[0].get("resolved_lane") for f in finals)
    f = finals[0]
    print(f"GAME_OVER received by all 4 clients: {len(finals) == 4}, consistent: {same}")
    print(f"resolved_lane = {f.get('resolved_lane')}   ending_node = {f.get('ending_node')}")
    print(f"ending title (LLM) = {f.get('ending', {}).get('title')!r}   classification = {f.get('ending', {}).get('classification')}")
    print(f"historian ending (LLM): {(f.get('historian_ending') or '')[:300]!r}")
    print(f"lane_weights = {f.get('lane_weights')}")
    return 0 if (len(finals) == 4 and same and f.get("resolved_lane")) else 1


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8765)
    ap.add_argument("--seed", type=int, default=1)
    a = ap.parse_args()
    raise SystemExit(asyncio.run(main(a.port, a.seed)))
