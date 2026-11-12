# Gambit — how choices become an ending

Baseline: git tag `v1-baseline` (commit `9236fd5`). All references are to that commit unless noted.

## 1. What counts as an "ending"

The brief says 8 endings. The code has two layers:

| Layer | Where | Count | What the player sees |
|---|---|---|---|
| **Resolved lane** | `LANE_WEIGHTS` in `app/design/content.py:33` and `resolve_lane()` in `content.py:806` | **9** | Drives the historian epilogue (`ai_engine.generate_historian_ending`), the canonical comparison, and the fallback ending title (`ending_engine.py:132` and `:179`) |
| **Terminal node** | `TERMINAL_NODES` in `content.py:590` and `terminal_for_lane()` in `content.py:824` | **5** | `ending.id` / `ending_node` in the `GAME_OVER` payload |

Nothing in the repo lists exactly 8 endings, so this work treats the **9 resolved lanes** as the endings and reports the 5 terminal nodes alongside. The number of lanes and nodes is unchanged. `terminal_for_lane` folds the lanes: `pyrrhic_govardhan` goes to the Govardhan node, `patriarchs_last_roar` to the Raghava node, and `saraswathi_betrayal` and `the_inheritance` to the Saraswathi node.

## 2. State

`GameState` (`app/models/schemas.py:39`) holds:

* `state_axes`: 15 integer axes, all starting at 0 (`STATE_AXES` in `content.py:15`).
* `lane_weights`: 9 integer lane scores, all starting at 0 (`LANE_WEIGHTS` in `content.py:33`).
* `story_flags`, `active_players[*].flags/alignments`, `global_capital`, and `session_history`.

The whole state is serialised to Redis on every save (`GameStateManager._persist` in `app/services/state.py:32`).

## 3. Flow of one game

The story is linear. Seeding builds one chain of nodes: `seed_db.py:60` links every beat only to the next beat, and every choice on a beat targets that same next node. **Choices never branch the graph.** They only:

1. add their `effects` to `state_axes` and their `lanes` to `lane_weights`, and
2. change which future choices are visible, through each choice's `requires`/`blocks` conditions and each interrogation's `trigger`.

There are 36 beats: 23 CHARACTERIZATION (8 Raghava, 8 Govardhan, 5 Saraswathi, 2 Venkatadri), 5 POLL, and 8 INTERROGATION.

| Step | Function | File |
|---|---|---|
| Driver: the sender task calls `prepare_scene`, then `ensure_finale`, whenever `current_scene_node != current_node` | `game_loop_websocket.sender_task` | `app/main.py:377` |
| Pick the acting role and player | `select_spotlight_role` | `app/services/scene_engine.py:222` |
| Skip an interrogation whose trigger fails | `interrogation_should_fire` → `interrogation_trigger_passes` | `interrogation_engine.py:31`, `content.py:285` |
| Build interrogation options | `build_interrogation_payloads` | `interrogation_engine.py:105` |
| Merge graph edges with authored effects and lanes | `_reactive_payloads_for_beat` | `scene_engine.py:145` |
| **Filter and rank the visible choices (3 max)** | `select_reactive_choices` → `choice_conditions_match`, `choice_relevance_score` | `scene_engine.py:90`, `content.py:175`, `content.py:194` |
| Receive a choice | `receiver_task` → `apply_choice` | `main.py:333`, `app/services/choice_resolver.py:99` |
| **Poll resolution** (plurality, ties go to the earliest-listed option) | inline in `apply_choice` | `choice_resolver.py:140-147` |
| **Apply effects** | `apply_axis_effects`, `apply_lane_effects`, `add_story_flags` | `choice_resolver.py:55-79` |
| **Ending selection** after the last beat (`gambit_ch09_verdict`) | `resolve_lane` → `terminal_for_lane` | `choice_resolver.py:221-223`, `content.py:806-833` |
| Finale payload (LLM text only) | `ensure_finale` | `app/services/ending_engine.py:92` |

### `resolve_lane` (content.py:806)

```text
weights = lane_weights
+3 broken_house            if family_cohesion <= -6 or betrayal_heat >= 9
+3 patriarchs_last_roar    if public_mandate >= 8 and leader_stability <= -2
+3 raghava_restoration     if public_mandate >= 8 and family_cohesion >= -2
+3 saraswathi_ascendancy   if saraswathi_influence >= 7 and court_politics >= 5
+3 govardhan_consolidation if institutional_control >= 8 and elite_loyalty >= 4
+2 venkatadri_compromise   if |venkatadri_loyalty| <= 1 and family_cohesion <= -2
winner = max by (weight, lane name)    # ties go to the alphabetically last lane
```

`pyrrhic_govardhan`, `saraswathi_betrayal` and `the_inheritance` get no bonus.

## 4. Where game logic is mixed into infrastructure code

| Location | What is mixed in |
|---|---|
| `scene_engine.prepare_scene` (`scene_engine.py:375`) | Holds the Redis session lock, reads Neo4j (`fetch_node`, `fetch_edges`), calls the LLM, **and** decides interrogation skips, spotlight role, and visible choices. It also re-enters itself while holding the lock (see §6). |
| `choice_resolver.apply_choice` (`choice_resolver.py:99`) | Holds the Redis lock, reads Neo4j, saves to Redis, calls the LLM (breakdown aftermath and headlines through `refresh_live_intel`), **and** contains the poll tally and tie-break, effect application, node advancement, and the final `resolve_lane` call. |
| `graph_store.fetch_edges` (`graph_store.py:58`) | A Neo4j query that also merges in authored `effects` and `lanes` from `content.py` through `choice_design_payload`. Choice mechanics come from `content.py`; Neo4j supplies only ids, roles and ordering. |
| `ending_engine.ensure_finale` (`ending_engine.py:92`) | The Redis lock and the LLM calls wrap the deterministic `resolve_lane`, and it also computes `_divergence_score`. |
| `state.GameStateManager.start_game` (`state.py:94`) | Role assignment (`random.shuffle`) sits inside the Redis manager. |
| `main.py` sender and receiver tasks | Only orchestration. No scoring lives here. |

The pure pieces are already free of I/O: `content.py` (conditions, relevance score, `resolve_lane`, `terminal_for_lane`), `select_reactive_choices`, `_reactive_payloads_for_beat`, `build_interrogation_payloads`, and `apply_*_effects`.

### Does the LLM Director change game state?

No. `ai_engine` output is used only for text: flavor, rewritten option text, headlines, aftermath, historian ending, and title. `_reconcile_options` (`ai_engine.py:419`) keeps the authored `choice_id`s, and poll ordering comes from the payload list, not from the LLM. Effects and lanes always come from `content.py`. The LLM *sees* the leading lane (`ai_engine.py:169`) but cannot move it. LLM failures fall back to authored text. **No LLM change was needed.**

## 5. Approach for running the logic offline (step 2)

**Chosen: run the existing code with the infrastructure stubbed** (`sim/harness.py`), not extraction.

Why: the logic that decides endings is not just `resolve_lane` and the effect adders. Visible choices (`select_reactive_choices`), interrogation skips, the poll tally and tie-break, and node advancement all live inside the two async functions that also own the Redis lock, the Neo4j reads and the LLM calls. Pulling them out would mean restructuring `prepare_scene` and `apply_choice`, which is more than "scoring and ending-selection code". So, per the brief, the simulator calls the real `prepare_scene`, `apply_choice` and `ensure_finale`, with:

* Redis replaced by an in-memory async key/value store (`FakeRedis`). The real `GameStateManager` still runs, including its locks and cache.
* Neo4j replaced by `FakeGraph`, built exactly the way `seed_db.py` builds the graph. It reuses the real `choice_design_payload` post-processing.
* The LLM replaced by stubs that return authored text, the same as the production fallback path.

Any change to game logic is therefore picked up by the simulator automatically, with no second implementation to keep in sync. Equivalence with the server is checked by `tests/test_equivalence.py`, which replays recorded choice sequences through the real FastAPI WebSocket endpoint and through the simulator and compares the results. A snapshot of the live Neo4j graph is also compared against `FakeGraph`.

## 6. Bug found while building the harness: interrogation-skip deadlock

`prepare_scene` skips an interrogation whose trigger fails by recursing into `prepare_scene` **inside** `async with state_manager.session_lock(...)` (`scene_engine.py:390-416`). `asyncio.Lock` is not reentrant, so the inner call waits forever and the session freezes for every player, because `apply_choice` needs the same lock. The state has already moved to the next beat when this happens. In production, play resumes only when a player's socket disconnects: that cancels the stuck sender task and releases the lock, and the next `prepare_scene` continues from the advanced node.

With random bots, **87% of baseline games freeze at least once** (2,000 simulated games; see `reports/before/summary.md`, column "freeze rate"). Playtest tables that did not reconnect never reached an ending, so the endings reported from playtests come from a biased subset of games. The harness emulates the reconnect: it cancels the stuck call and retries. That gives the same state outcome as production, so the "before" numbers reflect baseline game logic. The deadlock is fixed separately; see `CHANGES.md`.

## 7. Second bug: the ending never reached clients

`ensure_finale` put `NewsHeadline` pydantic objects into `final_result["aftermath_headlines"]` (`ending_engine.py:133` and `:193`). Redis serialisation handles them, but the in-process cache keeps the objects, so `websocket.send_json(state.final_result)` (`main.py:228`) raised `TypeError`. The sender task died and no player received `GAME_OVER`. This was found by the WebSocket equivalence test and fixed by dumping the models to dicts.

## 8. Equivalence evidence (before any balance change)

`tests/test_equivalence.py`:

* **Graph.** The live Neo4j Aura instance and the Upstash Redis instance in `.env` no longer resolve in DNS (checked 2026-11-12), so a live snapshot was not possible. Instead, the real `seed_db.seed_rebellion_episode()` is run against a recording stand-in for `EpisodeNode`/`adb`. Every node (type, terminal flag, premise, canonical outcome) and every edge (source, target, choice id, role, intent) it would write equals `FakeGraph`.
* **Server vs simulator.** 16 recorded choice sequences (`tests/fixtures/recorded_sequences.json`: 6 random, 6 coordinated, 2 disagreement, 2 solo; 44–51 choices each) are replayed through the real FastAPI lobby routes and the `/ws/play` WebSocket loop with four connected players. The final `state_axes`, `lane_weights`, `story_flags`, resolved lane and ending node are identical to the simulator's, and `GAME_OVER` is received by a client.
* **Baseline outcomes.** With `GAMBIT_CHECK_BASELINE=1`, the simulator reproduces the outcomes recorded from the pre-balance logic. This passed on commit `eb143d4` plus the serialisation fix. It is opt-in because balance changes intentionally change outcomes.

The deadlock fix was also checked game-by-game: 300 seeded random games produced byte-identical histories and outcomes before and after it.
