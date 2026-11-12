"""
Run Gambit tables of bots through the real game logic and write reports.

    python -m sim.run_sim --label before --games 2000

Table types
  random            4 random bots
  solo:<lane>       1 bot pushing <lane>, 3 random bots
  coordinated:<lane>  all 4 bots pushing <lane>
  disagreement      4 bots pushing 4 different lanes (sampled per game)
"""
from __future__ import annotations

import argparse
import asyncio
import json
import random
import time
from collections import Counter
from multiprocessing import Pool
from pathlib import Path
from typing import Dict, List

from sim.bots import LANES, directed_bot, random_bot
from sim.charts import bar_chart, heatmap

ROOT = Path(__file__).resolve().parent.parent
TERMINALS = ["ending_govardhan_consolidation", "ending_raghava_restoration", "ending_saraswathi_ascendancy",
             "ending_venkatadri_compromise", "ending_broken_house"]
PLAYERS = ["p0", "p1", "p2", "p3"]


def table_policies(table: str, seed: int):
    rng = random.Random(seed * 7919 + 17)
    if table == "random":
        return {p: random_bot(seed * 10 + i) for i, p in enumerate(PLAYERS)}, None
    kind, _, lane = table.partition(":")
    if kind == "solo":
        hero = rng.randrange(4)
        return {p: (directed_bot(lane, seed * 10 + i) if i == hero else random_bot(seed * 10 + i))
                for i, p in enumerate(PLAYERS)}, None
    if kind == "coordinated":
        return {p: directed_bot(lane, seed * 10 + i) for i, p in enumerate(PLAYERS)}, None
    if kind == "disagreement":
        lanes = rng.sample(LANES, 4)
        return {p: directed_bot(lanes[i], seed * 10 + i) for i, p in enumerate(PLAYERS)}, lanes
    raise ValueError(table)


def _play_chunk(args):
    table, seeds = args
    from sim.harness import play_game  # import inside worker

    async def go():
        rows = []
        for seed in seeds:
            policies, pushed = table_policies(table, seed)
            r = await play_game(policies, seed=seed, session_id=f"{table}:{seed}")
            rows.append({
                "seed": seed,
                "lane": r["resolved_lane"],
                "ending": r["ending_node"],
                "freezes": r["freezes"],
                "pushed": pushed,
                "roles": r["roles"],
            })
        return rows

    return asyncio.run(go())


def run_table(pool, table: str, games: int, seed0: int = 0) -> List[Dict]:
    seeds = list(range(seed0, seed0 + games))
    chunks = [(table, seeds[i:i + 50]) for i in range(0, games, 50)]
    rows = []
    for part in pool.imap_unordered(_play_chunk, chunks):
        rows.extend(part)
    return rows


def shares(rows, key, cats):
    c = Counter(r[key] for r in rows)
    n = max(1, len(rows))
    return {k: c.get(k, 0) / n for k in cats}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--label", required=True)
    ap.add_argument("--games", type=int, default=2000)
    ap.add_argument("--workers", type=int, default=12)
    args = ap.parse_args(argv)

    out_dir = ROOT / "reports" / args.label
    out_dir.mkdir(parents=True, exist_ok=True)
    tables = ["random", "disagreement"] + [f"solo:{l}" for l in LANES] + [f"coordinated:{l}" for l in LANES]
    t0 = time.time()
    results: Dict[str, Dict] = {}
    with Pool(args.workers) as pool:
        for table in tables:
            rows = run_table(pool, table, args.games)
            results[table] = {
                "games": len(rows),
                "lanes": shares(rows, "lane", LANES),
                "terminals": shares(rows, "ending", TERMINALS),
                "freeze_rate": sum(1 for r in rows if r["freezes"]) / len(rows),
            }
            if table == "disagreement":
                results[table]["winner_was_pushed"] = sum(1 for r in rows if r["lane"] in r["pushed"]) / len(rows)
            print(f"{table:34s} {time.time() - t0:7.1f}s  top={max(results[table]['lanes'].items(), key=lambda kv: kv[1])}", flush=True)

    (out_dir / "summary.json").write_text(json.dumps(results, indent=2))
    n = args.games
    tag = args.label
    (out_dir / "random_endings.svg").write_text(bar_chart(
        f"Random tables — ending lane share ({tag})", results["random"]["lanes"], f"{n} games, 4 random bots"), encoding="utf-8")
    (out_dir / "random_terminals.svg").write_text(bar_chart(
        f"Random tables — terminal node share ({tag})", results["random"]["terminals"], f"{n} games, 4 random bots"), encoding="utf-8")
    (out_dir / "disagreement_endings.svg").write_text(bar_chart(
        f"Disagreement tables — ending lane share ({tag})", results["disagreement"]["lanes"],
        f"{n} games, 4 bots pushing 4 different lanes"), encoding="utf-8")
    coord = {l: results[f"coordinated:{l}"]["lanes"] for l in LANES}
    solo = {l: results[f"solo:{l}"]["lanes"] for l in LANES}
    (out_dir / "coordinated_matrix.svg").write_text(heatmap(
        f"Coordinated tables — where 4 aligned players end up ({tag})", LANES, LANES, coord,
        f"{n} games per row; outlined diagonal = reached the lane the table pushed"), encoding="utf-8")
    (out_dir / "solo_matrix.svg").write_text(heatmap(
        f"One directed player + 3 random ({tag})", LANES, LANES, solo,
        f"{n} games per row; outlined diagonal = reached the pushed lane"), encoding="utf-8")

    lines = [f"# Simulation report: {tag}", "", f"{n} games per table.", "",
             "## Ending lane share by table", "",
             "| table | " + " | ".join(l.replace('_', ' ') for l in LANES) + " | freeze rate |",
             "|---|" + "---|" * (len(LANES) + 1)]
    for table in tables:
        r = results[table]
        lines.append(f"| {table} | " + " | ".join(f"{r['lanes'][l] * 100:.1f}%" for l in LANES)
                     + f" | {r['freeze_rate'] * 100:.0f}% |")
    lines += ["", "## Terminal node share by table", "",
              "| table | " + " | ".join(t.replace('ending_', '').replace('_', ' ') for t in TERMINALS) + " |",
              "|---|" + "---|" * len(TERMINALS)]
    for table in tables:
        r = results[table]
        lines.append(f"| {table} | " + " | ".join(f"{r['terminals'][t] * 100:.1f}%" for t in TERMINALS) + " |")
    lines += ["", f"Disagreement tables: winner was one of the 4 pushed lanes in "
              f"{results['disagreement']['winner_was_pushed'] * 100:.1f}% of games."]
    (out_dir / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"done in {time.time() - t0:.1f}s -> {out_dir}")


if __name__ == "__main__":
    main()
