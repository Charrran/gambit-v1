"""
Diagnostics for ending balance.

    python -m sim.diagnose --label before

1. Reachability: beam search over choice sequences (all 4 players cooperating) for
   each lane; reports whether the lane can win and the best winning margin.
2. Chapter influence: keyed-random counterfactuals. A game is replayed with the
   random draws of ONE chapter re-rolled; influence = P(ending changes).
3. Four-player effects: poll tie frequency / tie-break winners, final-verdict option
   counts, final lane margins, and how often resolve_lane's tie-break decides.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import random
from collections import Counter, defaultdict
from multiprocessing import Pool
from pathlib import Path
from typing import Dict, List

from sim.bots import LANES

ROOT = Path(__file__).resolve().parent.parent
PLAYERS = ["p0", "p1", "p2", "p3"]


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def lane_margin(lane_weights: Dict[str, int], axes: Dict[str, int], lane: str) -> int:
    """Smallest extra weight `lane` would need to win (<=0 means it already wins by -m)."""
    from app.design.content import resolve_lane

    for k in range(-40, 41):
        w = dict(lane_weights)
        w[lane] = w.get(lane, 0) + k
        if resolve_lane(w, axes) == lane:
            return k
    return 99


def keyed_policy(seed: int, salts: Dict[int, int], log: List | None = None):
    from app.design.content import chapter_for_node

    def policy(state, pid, role, payloads):
        node = state.current_node
        salt = salts.get(chapter_for_node(node), 0)
        idx = random.Random(f"{seed}:{node}:{pid}:{salt}").randrange(len(payloads))
        if log is not None:
            log.append({"node": node, "type": state.current_scene_type, "pid": pid,
                        "offered": [p["choice_id"] for p in payloads], "pick": payloads[idx]["choice_id"]})
        return payloads[idx]["choice_id"]

    return policy


# ---------------------------------------------------------------------------
# 1. reachability (beam search)
# ---------------------------------------------------------------------------

async def _advance(state, choice_id: str):
    """Apply one decision (all voters agree on polls) to a cloned state and prepare the next scene."""
    from app.design.content import LANE_WEIGHTS, MASTER_BEATS, STATE_AXES
    from app.services import choice_resolver, ending_engine, scene_engine
    from app.services.state import state_manager

    clone = state.model_copy(deep=True)
    clone.session_id = f"beam{random.random()}"
    state_manager._cache[clone.session_id] = clone
    sid = clone.session_id
    actors = PLAYERS if clone.current_scene_type == "POLL" else [clone.current_scene_player]
    for pid in actors:
        await choice_resolver.apply_choice(sid, pid, choice_id, STATE_AXES, LANE_WEIGHTS)
    st = await state_manager.get_state(sid)
    if st.current_scene_node != st.current_node and not st.ended:
        await scene_engine.prepare_scene(sid, STATE_AXES, LANE_WEIGHTS, MASTER_BEATS)
        await ending_engine.ensure_finale(sid)
    st = await state_manager.get_state(sid)
    state_manager._cache.pop(sid, None)
    state_manager._locks.pop(sid, None)
    state_manager._events.pop(sid, None)
    state_manager.client.store.pop(f"game:{sid}", None)
    return st


async def beam_search(lane: str, width: int = 60, seed: int = 0):
    from sim.harness import install_offline_backends
    from app.design.content import LANE_WEIGHTS, MASTER_BEATS, STATE_AXES
    from app.services import scene_engine
    from app.services.state import state_manager

    install_offline_backends()
    random.seed(seed)
    sid = f"beamroot{lane}"
    await state_manager.create_lobby(sid)
    for pid in PLAYERS:
        await state_manager.join_lobby(sid, pid)
    await state_manager.start_game(sid)
    root = await scene_engine.prepare_scene(sid, STATE_AXES, LANE_WEIGHTS, MASTER_BEATS)

    def score(st):
        return -lane_margin(st.lane_weights, st.state_axes, lane)

    beam = [(score(root), root, [])]
    finished = []
    for _ in range(80):
        if not beam:
            break
        children = []
        for _, st, path in beam:
            for p in st.current_choice_payloads:
                child = await _advance(st, p["choice_id"])
                cpath = path + [p["choice_id"]]
                if child.ended:
                    finished.append((child.resolved_lane == lane, score(child), child, cpath))
                else:
                    children.append((score(child), child, cpath))
        seen, beam = set(), []
        for item in sorted(children, key=lambda x: (x[0], random.random()), reverse=True):
            st = item[1]
            key = (st.current_node, tuple(sorted(st.state_axes.items())), tuple(sorted(st.lane_weights.items())),
                   tuple(sorted(st.story_flags)))
            if key in seen:
                continue
            seen.add(key)
            beam.append(item)
            if len(beam) >= width:
                break
    finished.sort(key=lambda x: (x[0], x[1]), reverse=True)
    best = finished[0]
    return {
        "lane": lane,
        "reachable": bool(best[0]),
        "best_resolved": best[2].resolved_lane,
        "best_margin": best[1],
        "path_len": len(best[3]),
        "path": best[3],
        "final_lane_weights": best[2].lane_weights,
    }


def _beam_worker(lane):
    return asyncio.run(beam_search(lane))


# ---------------------------------------------------------------------------
# 2 & 3. random-play statistics
# ---------------------------------------------------------------------------

def _influence_worker(args):
    seeds, chapters = args
    from sim.harness import play_game
    from app.design.content import resolve_lane

    async def go():
        rows = []
        for seed in seeds:
            log: List = []
            base = await play_game({p: keyed_policy(seed, {}, log) for p in PLAYERS}, seed=seed)
            row = {"seed": seed, "base": base["resolved_lane"], "base_ending": base["ending_node"],
                   "margin": None, "tie_decided": False, "log": log, "perturbed": {}}
            lw, ax = base["lane_weights"], base["state_axes"]
            # runner-up margin: how much the winner would need to lose to be overtaken
            row["margin"] = min(lane_margin(lw, ax, l) for l in LANES if l != base["resolved_lane"])
            row["tie_decided"] = row["margin"] <= 1
            for label, chs in chapters.items():
                salts = {c: 1 for c in chs}
                r = await play_game({p: keyed_policy(seed, salts) for p in PLAYERS}, seed=seed)
                row["perturbed"][label] = r["resolved_lane"]
            rows.append(row)
        return rows

    return asyncio.run(go())


def poll_stats(rows):
    ties = Counter()
    first_wins = Counter()
    n_polls = 0
    verdict_options = Counter()
    from app.design.content import beat_by_id
    for row in rows:
        by_node = defaultdict(list)
        for e in row["log"]:
            if e["type"] == "POLL":
                by_node[e["node"]].append(e)
        for node, votes in by_node.items():
            n_polls += 1
            offered = votes[0]["offered"]
            if node == "gambit_ch09_verdict":
                verdict_options[len(offered)] += 1
            counts = Counter(v["pick"] for v in votes)
            top = max(counts.values())
            leaders = [c for c in offered if counts.get(c, 0) == top]
            if len(leaders) > 1:
                ties["tie"] += 1
                if leaders[0] == offered[0]:
                    first_wins["tie_won_by_first_listed"] += 1
            winner = leaders[0]
            if winner == offered[0]:
                first_wins["first_listed_won"] += 1
    return {
        "polls": n_polls,
        "tie_rate": ties["tie"] / max(1, n_polls),
        "first_listed_win_rate": first_wins["first_listed_won"] / max(1, n_polls),
        "verdict_option_counts": dict(verdict_options),
    }


def leading_lane_bias(rows):
    """How often the first-listed option on a poll pushes govardhan_consolidation."""
    from app.design.content import MASTER_BEATS, normalize_choice
    lanes_of = {}
    for b in MASTER_BEATS:
        for c in b.get("choices", []):
            c = normalize_choice(c)
            lanes_of[c["id"]] = c["lanes"]
    shown = Counter()
    total = 0
    for row in rows:
        seen_nodes = set()
        for e in row["log"]:
            if e["node"] in seen_nodes:
                continue
            seen_nodes.add(e["node"])
            for cid in e["offered"]:
                for lane, v in lanes_of.get(cid, {}).items():
                    if v > 0:
                        shown[lane] += v
            total += 1
    return {lane: shown[lane] for lane in LANES}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--label", required=True)
    ap.add_argument("--games", type=int, default=1500)
    ap.add_argument("--workers", type=int, default=12)
    ap.add_argument("--skip-beam", action="store_true")
    args = ap.parse_args(argv)
    out_dir = ROOT / "reports" / args.label
    out_dir.mkdir(parents=True, exist_ok=True)

    chapters = {f"ch{c}": [c] for c in range(1, 10)}
    chapters["ch1-4"] = [1, 2, 3, 4]
    chapters["ch5-8"] = [5, 6, 7, 8]
    chapters["ch1-8"] = list(range(1, 9))
    seeds = list(range(100000, 100000 + args.games))
    chunks = [(seeds[i:i + 25], chapters) for i in range(0, len(seeds), 25)]
    with Pool(args.workers) as pool:
        beam = [] if args.skip_beam else pool.map(_beam_worker, LANES)
        rows = [r for part in pool.imap_unordered(_influence_worker, chunks) for r in part]

    influence = {label: sum(1 for r in rows if r["perturbed"][label] != r["base"]) / len(rows) for label in chapters}
    margins = Counter(min(r["margin"], 6) for r in rows)
    report = {
        "games": len(rows),
        "base_distribution": {l: sum(1 for r in rows if r["base"] == l) / len(rows) for l in LANES},
        "chapter_influence": influence,
        "final_margin_hist": {str(k): v / len(rows) for k, v in sorted(margins.items())},
        "runner_up_within_1": sum(1 for r in rows if r["tie_decided"]) / len(rows),
        "poll_stats": poll_stats(rows),
        "lane_points_shown": leading_lane_bias(rows),
        "reachability": [{k: v for k, v in b.items() if k != "path"} | {"path": b["path"]} for b in beam],
    }
    name = "diagnosis.json"
    if args.skip_beam and (out_dir / name).exists():
        old = json.loads((out_dir / name).read_text())
        report["reachability"] = old.get("reachability", [])
    (out_dir / name).write_text(json.dumps(report, indent=1))
    print(json.dumps({k: v for k, v in report.items() if k != "reachability"}, indent=1))
    for b in beam:
        print(f"{b['lane']:26s} reachable={b['reachable']!s:5s} best={b['best_resolved']:26s} margin={b['best_margin']}")


if __name__ == "__main__":
    main()
