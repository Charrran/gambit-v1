# Changes

Baseline: tag `v1-baseline`. Every change is a separate commit. No story text, ending content, ending count, routes, Redis/session handling, WebSocket protocol or frontend code was changed. The LLM Director needed no logic change: it never writes game state (ANALYSIS.md §4).

Measured with `python -m sim.run_sim` (2,000 games per table) and `python -m sim.diagnose`. Full tables are in `reports/before/summary.md` and `reports/after/summary.md`, with charts in the same folders.

## Results against the definition of done

| Criterion | Before | After |
|---|---|---|
| All endings reachable through choices | 8 of 9 lanes reachable by search; **3 never reached** even by unanimous tables | **9 of 9** reachable; unanimous tables reach **every** lane 100% |
| Random tables: no ending above ~30% | `govardhan_consolidation` **61.3%** | top lane **21.2%** (`broken_house`); every lane **5.1–21.2%** |
| Random tables, by terminal node (5) | Govardhan **61.3%** | max **26.5%** (Raghava); Venkatadri lowest at 7.8% |
| Every ending appears occasionally | `pyrrhic_govardhan`, `saraswathi_betrayal`, `the_inheritance` at **0.0%** | all ≥ 5.1% |
| Shared direction reaches the matching ending | 6/9 lanes | **9/9 lanes at 100%** |
| One directed player among 3 random reaches their target | 0.0–85.5% (only high-supply lanes) | 22.5–61.8% for every lane (chance ≈ 11%) |
| Earlier chapters measurably matter | ch1 re-roll changes ending 40.8%; ch9 18.9% | ch1 **57.5%**, ch2 60.1%, ch4 47.4%, ch8 52.7%, ch9 39.7%; chapters 1–4 together 73.3%, 5–8 71.5% |
| Ending locked in early (leader at start of ch4 = final ending) | 61.7% | 28.4% |
| Disagreement drifts to the compromise "middle" | `venkatadri_compromise` 32.0% | 6.5% (winner is one of the pushed lanes in 82.3% of games) |
| Game runs end to end | **87% of games froze**, and `GAME_OVER` never reached clients | real uvicorn server + 4 WebSocket clients complete; `GAME_OVER` received by all 4 (see "End-to-end" below) |

## Changes

### 1. Fix interrogation-skip deadlock (`eb143d4`, `app/services/scene_engine.py`)
* **Problem:** ANALYSIS.md §6. `prepare_scene` recursed while holding the non-reentrant session lock, so every skipped interrogation froze the session until a player reconnected.
* **Change:** the recursive call reuses the lock it already holds (`_lock_held=True`, `nullcontext`). 8 lines.
* **Effect:** freeze rate 87% → 0%. Outcomes are byte-identical to baseline-plus-reconnect on 300 seeded games, so this is not a balance change.

### 2. Fix `GAME_OVER` payload serialisation (`82164c8`, `app/services/ending_engine.py`)
* **Problem:** ANALYSIS.md §7. `final_result` held `NewsHeadline` models, so `send_json` raised and no client received the ending.
* **Change:** store them as dicts (`model_dump()`). 2 lines.
* **Effect:** `GAME_OVER` is delivered. Found by the WebSocket equivalence test.

### 3. Balance: stop the choice ranker snowballing the leading lane (`e3134dd`, `app/design/content.py: choice_relevance_score`)
* **Problem:** DIAGNOSIS.md §2. Options feeding the current leader got +0.5 × lane points of relevance. With all lanes at 0, the leader defaulted to `govardhan_consolidation` (first dict key).
* **Change:** removed that boost. Visible choices now depend on authored priority and axis pressure only.
* **Effect, measured alone:** `govardhan_consolidation` 61.1% → 57.3% on random tables. On top of change 4 it still lowers it from 17.6% to 15.5%, so it was kept.

### 4. Balance: resolve the ending by choice pressure relative to the options offered (`a182dd3`)
Files: `content.py: lane_opportunity, resolve_lane`, `choice_resolver.py: record_lane_opportunity`, `schemas.py` (two fields), `state.py: start_game` (reset the two fields), `ending_engine.py` (pass the fields).

* **Problems:** DIAGNOSIS.md §1 (raw totals reward lanes with more authored points: 71 vs 13), §4 (sub-lanes can never beat parent lanes that share their choices), §5 (forced chapter-9 fallbacks hand compromise up to +4), §6.
* **Change:** at every resolved decision (spotlight, interrogation or poll winner), each lane accumulates:
  * *pressure*: the chosen option's points minus the mean of the offered options;
  * *spread*: the variance of the offered options.

  The ending is the lane with the highest `Σpressure / √Σspread`, i.e. how deliberately the table chose it given the chances it actually had, plus the existing authored axis bonuses (scaled by 1/3). Indifferent picks average to zero for every lane. A forced single option carries no pressure. A sub-lane wins when the table consistently prefers its options over the parent's. `lane_weights` is still accumulated and shown exactly as before.
* **Backward compatibility:** sessions saved before this change have `lane_pressure = None` and keep the v1 raw-total rule. Checked: 0/20,000 random states differ from the v1 function, and a regression test covers it.
* **Effect, measured alone after change 3:** random top lane 57.3% → 20.8%, smallest lane 0% → 5.0%. Unanimous tables 6/9 → 9/9. Compromise share in disagreement tables 31.3% → 5.9%.

### Tried and dropped
* **Static normalisation by authored lane supply** (divide by total, or by gated-discounted, authored points). Reached 9/9 for coordinated tables, but over-rewarded lanes whose points sit on unconditional choices: `broken_house` reached 30–37% and `saraswathi_betrayal` 17.5%, while gated lanes fell to 1%. Replaced by change 4, which uses what each table was *actually* offered.
* **Poll tie-break to the least-spotlighted voter** instead of first-listed (DIAGNOSIS.md §3). No measurable effect once change 3 was in: `govardhan_consolidation` 57.3% → 57.0%, within noise. Reverted to keep the change set minimal. The first-listed tie-break remains (ties in 22.7% of polls), but list order no longer follows the leading lane.

## Known side effects and limits

* **Leading lane shown to players and the LLM (fixed in a follow-up):** the frontend never renders `lane_weights`, but the fallback "likely path" headline (always used on the ending screen), the transition summaries, the LLM prompts and the `lane:X` pressure tag picked the leader from raw totals, so the ending screen could name a different lane than the one reached. They now all use `content.lane_standings()`, the same scores `resolve_lane` maximises. `tests/test_balance_regression.py::VisibleLeaderMatchesEnding` covers this.
* **`_divergence_score`** (ending classification) now also uses `lane_standings()` (fixed in the same follow-up).
* **Bot model:** the random/directed bots pick from visible options only. Real players read LLM-rewritten option text, so human distributions will differ somewhat. The pressure rule itself is player-model independent.
* **Old search margins:** the beam-search "margin" figures in `reports/after/diagnosis.json` (and its `final_margin_hist`/`runner_up_within_1`) are computed on raw lane totals and do not apply to the new rule. Only the `reachable` flags (actual `resolved_lane`) are meaningful after the change.

## Tests

* `tests/test_equivalence.py`:
  * `seed_db` output equals the simulator's graph.
  * Sequences recorded from the simulator, replayed through the real HTTP + `/ws/play` loop, give identical final state and a delivered `GAME_OVER`.
  * Opt-in (`GAMBIT_CHECK_BASELINE=1`): the simulator reproduces the 16 outcomes recorded on the pre-balance logic.
* `tests/test_balance_regression.py` (≈35 s) fails if:
  * any lane takes > 32% of random games, or any lane drops below 1.5%;
  * any terminal node takes > 35%;
  * a unanimous table reaches its lane < 90% of the time;
  * re-rolling chapters 1–4 changes < 30% of endings;
  * old sessions stop resolving with the v1 rule.

  Verified to fail with 6 failures and 2 errors against the pre-balance commit.

```
python -m unittest tests.test_equivalence tests.test_balance_regression -v
```

## End-to-end

`python -m sim.e2e_server --offline-llm` with `python -m sim.e2e_client` runs the real `uvicorn` app with the real FastAPI routes and WebSocket loop, and four independent WebSocket clients over TCP that react only to server messages, as the frontend does. Result: 47 choices, 0 errors, `GAME_OVER` received by all four clients with a consistent `resolved_lane`.

Not covered, because it needs new infrastructure or keys (deferred at your request):

* **Neo4j/Redis:** the hosted Aura and Upstash instances in `.env` no longer resolve in DNS, so both ran as in-process stand-ins. The real `redis.asyncio` network client and the Cypher queries were therefore not exercised. Re-seed a new Neo4j with `python seed_db.py`; the graph shape is unchanged.
* **LLM Director:** the model IDs hardcoded in `app/services/ai_engine.py` are retired: Groq `llama-3.1-8b-instant` returns 404 and Gemini `gemini-2.0-flash` reports "no longer available". Every LLM call therefore falls back to authored text, in production too. The fallbacks work, so the game completes. `sim/e2e_server.py --groq-model … --gemini-model …` can override the IDs for a run without editing app code.
* **Local TLS:** AVG Web/Mail Shield re-signs HTTPS on this machine, so Python (`certifi`) rejects every LLM call. `sim/e2e_server.py --os-trust-store` also trusts the Windows certificate store.
