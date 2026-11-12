"""
Tests for the Neo4j-backed features and the LLM router (no services needed).

Run:  python -m unittest tests.test_graph_and_llm -v
"""
import asyncio
import unittest
from collections import Counter

from sim.bots import directed_bot, random_bot
from sim.harness import RECORDED_PLAYTHROUGHS, FakeGraph, install_offline_backends, play_game

PLAYERS = ["p0", "p1", "p2", "p3"]


class DesignGraphProjection(unittest.TestCase):
    """seed_db.design_graph_rows() must mirror app/design/content.py exactly."""

    @classmethod
    def setUpClass(cls):
        install_offline_backends()
        import seed_db

        cls.rows = seed_db.design_graph_rows()

    def test_lane_points_match_content(self):
        from app.design.content import INTERROGATIONS, MASTER_BEATS, normalize_choice

        expected = Counter()
        for beat in MASTER_BEATS:
            for raw in beat.get("choices", []):
                expected.update(normalize_choice(raw)["lanes"])
        for definition in INTERROGATIONS.values():
            for option in definition["options"]:
                expected.update(option.get("lanes", {}))
        projected = Counter()
        for row in self.rows["pushes"]:
            projected[row["lane"]] += row["points"]
        self.assertEqual(dict(projected), dict(expected))

    def test_every_playable_choice_is_a_choice_node(self):
        ids = {row["choice_id"] for row in self.rows["choices"]}
        self.assertEqual(len(ids), len(self.rows["choices"]), "duplicate choice ids")
        graph = FakeGraph()
        for edges in graph.edges.values():
            for props, _ in edges:
                if not props["choice_id"].endswith("__continue"):
                    self.assertIn(props["choice_id"], ids)

    def test_every_lane_resolves_to_a_terminal(self):
        from app.design.content import LANE_WEIGHTS, TERMINAL_NODES

        terminals = {node_id for node_id, _ in TERMINAL_NODES}
        self.assertEqual({row["lane_id"] for row in self.rows["lanes"]}, set(LANE_WEIGHTS))
        for row in self.rows["lanes"]:
            self.assertIn(row["terminal"], terminals)

    def test_recorded_playthrough_attaches_to_choice_nodes(self):
        ids = {row["choice_id"] for row in self.rows["choices"]}
        result = asyncio.run(play_game({p: random_bot(50 + i) for i, p in enumerate(PLAYERS)}, seed=4242,
                                       session_id="graph-test"))
        recorded = RECORDED_PLAYTHROUGHS[-1]
        self.assertEqual(recorded["session_id"], "graph-test")
        self.assertEqual(recorded["resolved_lane"], result["resolved_lane"])
        decisions = [h for h in result["history"] if h["role"] != "SYSTEM"]
        self.assertEqual(len(recorded["choice_ids"]), len(decisions))
        self.assertTrue(set(recorded["choice_ids"]) <= ids, set(recorded["choice_ids"]) - ids)


class NarrationCache(unittest.TestCase):
    """Once enough variants are stored for a situation, the LLM is not called again."""

    def test_repeat_games_stop_calling_the_llm(self):
        install_offline_backends()
        from app.core.config import settings
        from app.services import graph_store
        from app.services.ai_engine import GeneratedOption, TurnNarrative, ai_engine

        calls = Counter()

        def fake(kind):
            async def generate(premise, *args, db_choices=None, **kwargs):
                db_choices = db_choices if db_choices is not None else args[-1]
                calls[kind] += 1
                return TurnNarrative(
                    flavor_text=f"LLM v{calls[kind]}",
                    options=[GeneratedOption(choice_id=c["choice_id"], text="llm " + c["action_intent"]) for c in db_choices],
                )
            return generate

        originals = ai_engine.generate_spotlight_turn, ai_engine.generate_poll_turn
        ai_engine.generate_spotlight_turn, ai_engine.generate_poll_turn = fake("spotlight"), fake("poll")
        graph_store._narrations.clear()
        try:
            per_game, outcomes = [], []
            for game in range(settings.narration_variants + 1):
                before = sum(calls.values())
                policies = {p: directed_bot("raghava_restoration", 7 + i) for i, p in enumerate(PLAYERS)}
                result = asyncio.run(play_game(policies, seed=99, session_id=f"cache-{game}",
                                               role_order=["Raghava Rao", "Govardhan Naidu", "Saraswathi", "Venkatadri"]))
                per_game.append(sum(calls.values()) - before)
                outcomes.append((result["resolved_lane"], result["lane_weights"], result["state_axes"]))
        finally:
            ai_engine.generate_spotlight_turn, ai_engine.generate_poll_turn = originals
            graph_store._narrations.clear()
        self.assertGreater(per_game[0], 20)
        self.assertEqual(per_game[-1], 0, f"LLM calls per game: {per_game}")
        self.assertTrue(all(o == outcomes[0] for o in outcomes), "narration must not change mechanics")


class RouterFailsFast(unittest.TestCase):
    def test_rate_limited_route_is_skipped_until_cooldown_ends(self):
        from app.services.llm_router import LLMRouter, LLMUnavailable

        router = LLMRouter()
        attempts = []

        async def call(route, prompt, system, json_mode, max_tokens, timeout):
            attempts.append(route)
            if route[0] == "groq":
                router._cool(route, 60.0, "test")
                raise LLMUnavailable("429")
            return '{"ok": true}'

        router._call = call
        routes = "groq:a,gemini:b"

        async def go():
            first = await router.text(routes, "x")
            second = await router.text(routes, "x")
            return first, second

        import app.services.llm_router as module
        module.print = lambda *a, **k: None
        self.assertEqual(asyncio.run(go()), ('{"ok": true}', '{"ok": true}'))
        self.assertEqual(attempts, [("groq", "a"), ("gemini", "b"), ("gemini", "b")])

    def test_all_routes_down_raises_immediately(self):
        from app.services.llm_router import LLMRouter, LLMUnavailable

        router = LLMRouter()

        async def call(*args, **kwargs):
            raise LLMUnavailable("down")

        router._call = call
        with self.assertRaises(LLMUnavailable):
            asyncio.run(router.text("groq:a,gemini:b", "x"))


if __name__ == "__main__":
    unittest.main()
