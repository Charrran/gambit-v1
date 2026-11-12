"""
Balance regression tests: fail if the ending distribution collapses again.

Runs the real game logic through the offline harness (sim/harness.py). Seeds are
fixed, so results are deterministic; thresholds leave headroom over the measured
values in CHANGES.md so legitimate content tweaks don't trip them, but a return
to one dominant ending will.

Run:  python -m unittest tests.test_balance_regression -v
"""
import asyncio
import random
import unittest
from collections import Counter

from sim.bots import LANES, directed_bot, random_bot
from sim.diagnose import keyed_policy
from sim.harness import install_offline_backends, play_game

PLAYERS = ["p0", "p1", "p2", "p3"]
TERMINALS = ["ending_govardhan_consolidation", "ending_raghava_restoration", "ending_saraswathi_ascendancy",
             "ending_venkatadri_compromise", "ending_broken_house"]


def _run(coro):
    return asyncio.run(coro)


async def _random_games(n, seed0=900000):
    rows = []
    for s in range(seed0, seed0 + n):
        r = await play_game({p: random_bot(s * 10 + i) for i, p in enumerate(PLAYERS)}, seed=s)
        rows.append((r["resolved_lane"], r["ending_node"]))
    return rows


class RandomTablesDoNotCollapse(unittest.TestCase):
    """Measured after the fix: top lane ~21%, smallest lane ~5%, top terminal ~28%."""

    @classmethod
    def setUpClass(cls):
        install_offline_backends()
        cls.rows = _run(_random_games(800))

    def test_no_lane_dominates(self):
        shares = Counter(lane for lane, _ in self.rows)
        top_lane, top = shares.most_common(1)[0]
        self.assertLessEqual(top / len(self.rows), 0.32, f"{top_lane} won {top}/{len(self.rows)} random games")

    def test_every_lane_appears(self):
        shares = Counter(lane for lane, _ in self.rows)
        for lane in LANES:
            self.assertGreaterEqual(shares[lane] / len(self.rows), 0.015, f"{lane} is (nearly) unreachable for random tables")

    def test_no_terminal_dominates(self):
        shares = Counter(node for _, node in self.rows)
        for node in TERMINALS:
            self.assertLessEqual(shares[node] / len(self.rows), 0.35, f"{node} dominates")
            self.assertGreater(shares[node], 0, f"{node} never reached")


class CoordinatedTablesReachTheirEnding(unittest.TestCase):
    """A table that all pushes one lane reaches it (measured: 100% for all 9)."""

    @classmethod
    def setUpClass(cls):
        install_offline_backends()

    def test_each_lane(self):
        async def go():
            out = {}
            for lane in LANES:
                hits = 0
                for s in range(30):
                    r = await play_game({p: directed_bot(lane, s * 10 + i) for i, p in enumerate(PLAYERS)}, seed=7000 + s)
                    hits += r["resolved_lane"] == lane
                out[lane] = hits / 30
            return out

        for lane, rate in _run(go()).items():
            with self.subTest(lane):
                self.assertGreaterEqual(rate, 0.9, f"unanimous table pushing {lane} reached it only {rate:.0%}")


class EarlyChoicesMatter(unittest.TestCase):
    """Re-rolling only chapters 1-4 must change a meaningful share of endings."""

    @classmethod
    def setUpClass(cls):
        install_offline_backends()

    def test_early_chapters_influence(self):
        async def go():
            changed = 0
            n = 200
            for s in range(n):
                seed = 300000 + s
                base = await play_game({p: keyed_policy(seed, {}) for p in PLAYERS}, seed=seed)
                alt = await play_game({p: keyed_policy(seed, {1: 1, 2: 1, 3: 1, 4: 1}) for p in PLAYERS}, seed=seed)
                changed += base["resolved_lane"] != alt["resolved_lane"]
            return changed / n

        self.assertGreaterEqual(_run(go()), 0.3)


class VisibleLeaderMatchesEnding(unittest.TestCase):
    """Headlines/transitions/LLM hints name the leading lane from lane_standings(); it must be the real ending."""

    @classmethod
    def setUpClass(cls):
        install_offline_backends()

    def test_final_headline_names_the_resolved_lane(self):
        async def go():
            out = []
            for s in range(60):
                r = await play_game({p: random_bot(s * 10 + i) for i, p in enumerate(PLAYERS)}, seed=440000 + s)
                out.append(r)
            return out

        for r in _run(go()):
            lane_headline = next(h for h in r["final_result"]["aftermath_headlines"] if h["id"] == "lane")
            self.assertEqual(lane_headline["headline"], r["resolved_lane"].replace("_", " ").title(), f"seed {r['seed']}")


class LaneOpportunityScoring(unittest.TestCase):
    def test_forced_choice_carries_no_pressure(self):
        from app.design.content import lane_opportunity

        only = {"lanes": {"venkatadri_compromise": 2}}
        pressure, spread = lane_opportunity([only], only)
        self.assertEqual(pressure, {})
        self.assertEqual(spread, {})

    def test_indifferent_choice_has_zero_expected_pressure(self):
        from app.design.content import lane_opportunity

        offered = [{"lanes": {"govardhan_consolidation": 2}}, {"lanes": {"the_inheritance": 1}}, {"lanes": {}}]
        totals = Counter()
        for chosen in offered:
            pressure, _ = lane_opportunity(offered, chosen)
            totals.update(pressure)
        for lane, val in totals.items():
            self.assertAlmostEqual(val, 0.0, places=9, msg=lane)

    def test_legacy_sessions_keep_v1_rule(self):
        """Sessions saved before lane_pressure existed resolve exactly as v1 did."""
        from app.design.content import LANE_WEIGHTS, STATE_AXES, resolve_lane

        def v1_resolve_lane(lane_weights, state_axes):  # verbatim from v1-baseline content.py
            weights = dict(LANE_WEIGHTS)
            weights.update(lane_weights or {})
            if state_axes.get("family_cohesion", 0) <= -6 or state_axes.get("betrayal_heat", 0) >= 9:
                weights["broken_house"] += 3
            if state_axes.get("public_mandate", 0) >= 8 and state_axes.get("leader_stability", 0) <= -2:
                weights["patriarchs_last_roar"] += 3
            if state_axes.get("public_mandate", 0) >= 8 and state_axes.get("family_cohesion", 0) >= -2:
                weights["raghava_restoration"] += 3
            if state_axes.get("saraswathi_influence", 0) >= 7 and state_axes.get("court_politics", 0) >= 5:
                weights["saraswathi_ascendancy"] += 3
            if state_axes.get("institutional_control", 0) >= 8 and state_axes.get("elite_loyalty", 0) >= 4:
                weights["govardhan_consolidation"] += 3
            if abs(state_axes.get("venkatadri_loyalty", 0)) <= 1 and state_axes.get("family_cohesion", 0) <= -2:
                weights["venkatadri_compromise"] += 2
            return max(weights, key=lambda lane: (weights[lane], lane))

        rng = random.Random(1)
        for _ in range(5000):
            lw = {k: rng.randint(-3, 15) for k in LANE_WEIGHTS}
            ax = {k: rng.randint(-10, 12) for k in STATE_AXES}
            self.assertEqual(resolve_lane(lw, ax), v1_resolve_lane(lw, ax))


if __name__ == "__main__":
    unittest.main()
