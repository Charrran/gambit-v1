"""
Record and replay choice sequences.

* `replay_policy` turns a recorded list of choice_ids back into bot policies for the
  simulator (direct service calls).
* `replay_over_websocket` drives the real FastAPI app (app.main) through its HTTP lobby
  routes and the /ws/play WebSocket game loop with four connected players, using the
  same offline Redis/Neo4j/LLM stubs. Used by the equivalence tests.
"""
from __future__ import annotations

import time
from typing import Dict, List

from sim.harness import install_offline_backends


class ReplayMismatch(AssertionError):
    pass


def replay_policies(steps: List[Dict[str, str]], players: List[str]):
    queue = list(steps)

    def make(pid):
        def policy(state, player_id, role, payloads):
            if not queue:
                raise ReplayMismatch("recording exhausted")
            step = queue.pop(0)
            offered = [p["choice_id"] for p in payloads]
            if step["player"] != player_id or step["choice_id"] not in offered:
                raise ReplayMismatch(f"expected {step}, got player {player_id} offered {offered}")
            return step["choice_id"]

        return policy

    return {pid: make(pid) for pid in players}, queue


def replay_over_websocket(steps: List[Dict[str, str]], roles: Dict[str, str], timeout: float = 20.0) -> Dict:
    install_offline_backends()
    import app.main as main
    from fastapi.testclient import TestClient
    from app.services.state import state_manager

    async def _no_neo4j():
        return None

    main.init_neo4j_async = _no_neo4j
    import builtins

    # Silence per-request debug logging but keep the server's error lines visible.
    main.print = lambda *a, **k: None if str(a[0] if a else "").startswith("[DEBUG]") else builtins.print(*a, **k)

    players = list(roles)
    with TestClient(main.app) as client:
        sid = client.post("/lobby/create", json={"player_id": players[0]}).json()["session_id"]
        for pid in players[1:]:
            assert client.post(f"/lobby/{sid}/join", json={"player_id": pid}).status_code == 200
        assert client.post(f"/lobby/{sid}/start").status_code == 200
        state = state_manager._cache[sid]
        for pid, role in roles.items():
            state.active_players[pid].role = role

        sockets = {}
        try:
            for pid in players:
                ws = client.websocket_connect(f"/ws/play/{sid}/{pid}")
                sockets[pid] = ws.__enter__()

            def wait_for(pred):
                deadline = time.time() + timeout
                while time.time() < deadline:
                    st = state_manager._cache.get(sid)
                    if st is not None and pred(st):
                        return st
                    time.sleep(0.002)
                raise TimeoutError("server did not reach expected state")

            def scene_ready(st):
                return st.ended or (
                    st.current_scene_node == st.current_node and bool(st.current_choices)
                )

            for step in steps:
                st = wait_for(scene_ready)
                if st.ended:
                    raise ReplayMismatch(f"game ended before step {step}")
                offered = [c.choice_id for c in st.current_choices]
                if step["node"] != st.current_node or step["choice_id"] not in offered:
                    raise ReplayMismatch(f"server at {st.current_node} offered {offered}, recording has {step}")
                revision = st.revision
                sockets[step["player"]].send_json({"choice_id": step["choice_id"]})
                wait_for(lambda s: s.revision != revision)

            st = wait_for(lambda s: s.ended and s.final_result)
            # The GAME_OVER payload must actually reach a client over the socket.
            game_over = None
            for _ in range(500):
                msg = sockets[players[0]].receive_json()
                if msg.get("type") == "GAME_OVER":
                    game_over = msg
                    break
            return {
                "resolved_lane": st.resolved_lane,
                "ending_node": st.final_result.get("ending_node"),
                "state_axes": dict(st.state_axes),
                "lane_weights": dict(st.lane_weights),
                "story_flags": list(st.story_flags),
                "ws_game_over": game_over,
            }
        finally:
            for ws in sockets.values():
                try:
                    ws.__exit__(None, None, None)
                except Exception:
                    pass
            state_manager._cache.pop(sid, None)
