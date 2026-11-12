"""
Equivalence tests: the offline simulator reproduces the real game.

1. FakeGraph == the graph seed_db.py writes to Neo4j (seed_db run against a recorder).
2. Choice sequences recorded from the simulator, replayed through the real FastAPI
   lobby routes and /ws/play WebSocket loop, give exactly the same final state.
3. (opt-in, GAMBIT_CHECK_BASELINE=1) the simulator reproduces the outcomes recorded
   from the pre-balance logic. Expected to pass only on the pre-balance commits.

Run:  python -m unittest tests.test_equivalence -v
"""
import asyncio
import json
import os
import unittest
from pathlib import Path

from sim.harness import FakeGraph, install_offline_backends, play_game
from sim.replay import replay_over_websocket, replay_policies

FIXTURES = Path(__file__).resolve().parent / "fixtures"
RECORDINGS = json.loads((FIXTURES / "recorded_sequences.json").read_text(encoding="utf-8"))


def _sim_replay(rec):
    players = list(rec["roles"])
    policies, remaining = replay_policies(rec["steps"], players)
    result = asyncio.run(play_game(policies, seed=0, session_id=f"replay-{rec['name']}",
                                   role_order=[rec["roles"][p] for p in players]))
    assert not remaining, f"{len(remaining)} recorded steps were not consumed"
    return result


class SeededGraphMatchesFakeGraph(unittest.TestCase):
    def test_seed_db_output_equals_fake_graph(self):
        import seed_db

        nodes, edges = {}, []

        class RecNode:
            def __init__(self, **props):
                self.props = props
                self.leads_to = self

            async def save(self):
                nodes[self.props["node_id"]] = self
                return self

        async def connect(self, target, props):  # RecNode doubles as its own leads_to manager
            edges.append((self.props["node_id"], target.props["node_id"], props))

        RecNode.connect = connect

        class NoDb:
            async def cypher_query(self, *a, **k):
                return [], None

        orig = seed_db.EpisodeNode, seed_db.adb
        seed_db.EpisodeNode, seed_db.adb = RecNode, NoDb()
        try:
            seed_db.print = lambda *a, **k: None
            asyncio.run(seed_db.seed_rebellion_episode())
        finally:
            seed_db.EpisodeNode, seed_db.adb = orig

        fake = FakeGraph()
        self.assertEqual(set(nodes), set(fake.nodes))
        for node_id, rec in nodes.items():
            fn = fake.nodes[node_id]
            self.assertEqual(rec.props.get("node_type", "STORY"), fn.node_type, node_id)
            self.assertEqual(rec.props.get("is_terminal", False), fn.is_terminal, node_id)
            self.assertEqual(rec.props["skeleton_premise"], fn.skeleton_premise, node_id)
            self.assertEqual(rec.props["canonical_outcome"], fn.canonical_outcome, node_id)
        seeded = sorted((s, t, p["choice_id"], p["required_role"], p["action_intent"]) for s, t, p in edges)
        faked = sorted((s, t, p["choice_id"], p["required_role"], p["action_intent"])
                       for s, lst in fake.edges.items() for p, t in lst)
        self.assertEqual(seeded, faked)


class SimulatorMatchesWebSocketServer(unittest.TestCase):
    """
    Sequences are recorded fresh from the simulator on the *current* logic (choice
    visibility changes with balance work, so frozen sequences cannot always be
    replayed), then replayed through the real HTTP + WebSocket server.
    """

    @classmethod
    def setUpClass(cls):
        install_offline_backends()

    def test_fresh_sequences(self):
        from sim.record_sequences import TABLES
        from sim.run_sim import table_policies

        for table, seed in TABLES:
            with self.subTest(f"{table}#{seed}"):
                steps = []
                policies, _ = table_policies(table, seed)
                sim = asyncio.run(play_game(policies, seed=seed, session_id=f"rec-{table}-{seed}", record=steps))
                ws = replay_over_websocket(steps, sim["roles"])
                for key in ("resolved_lane", "ending_node", "state_axes", "lane_weights", "story_flags"):
                    self.assertEqual(sim[key], ws[key], f"{table}#{seed}: {key}")
                self.assertIsNotNone(ws["ws_game_over"], "GAME_OVER never reached the client")
                self.assertEqual(ws["ws_game_over"]["resolved_lane"], sim["resolved_lane"])
                self.assertEqual(ws["ws_game_over"]["ending_node"], sim["ending_node"])


@unittest.skipUnless(os.environ.get("GAMBIT_CHECK_BASELINE") == "1", "baseline outcomes only hold before balance changes")
class SimulatorMatchesRecordedBaseline(unittest.TestCase):
    def test_recorded_outcomes(self):
        for rec in RECORDINGS:
            with self.subTest(rec["name"]):
                sim = _sim_replay(rec)
                for key, expected in rec["outcome"].items():
                    self.assertEqual(sim[key], expected, f"{rec['name']}: {key}")


if __name__ == "__main__":
    unittest.main()
