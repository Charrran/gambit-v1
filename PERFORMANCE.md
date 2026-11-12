# Speed, free tiers and the graph

How Gambit stays fast on free tiers, and what Neo4j is used for. Measured on 2026-11-12 against Groq, Gemini, Upstash Redis and Neo4j Aura free tiers.

## Results

| | Before | After |
|---|---|---|
| Text for one turn | 15–47 s once the Groq limit was hit | 0.7–1.2 s from the LLM; instant from the graph cache |
| Full game, 4 bots clicking instantly, live stack | 911 s | 98 s, 24 s and 66 s (three consecutive games) |
| LLM calls for a cold game | ~75 (one per turn, one per headline refresh, epilogue) | ~47 (turns, 9 headline refreshes, epilogue) |
| LLM calls once a table's situations are cached | ~75 | ~11 (headlines and epilogue only) |
| Neo4j queries per turn | 3–4 (~100 ms each) | 0 |
| Behaviour when a provider is rate limited | waited and retried | next provider at once, then authored text |

## Free-tier limits this is built around

| Route | Limit | Latency | Used for |
|---|---|---|---|
| Groq `qwen/qwen3.8-27b` | 8,000 tokens/min, 1,000 requests/day | ~0.6 s | first choice for per-turn text (~960 tokens per turn, so ~8 turns/min) |
| Gemini `gemini-3.1-flash-lite` | 15 requests/min | ~2 s | first choice for headlines, aftermath, epilogue; second for turns |
| Groq `openai/gpt-oss-20b` | its own 8,000 tokens/min, 1,000 requests/day | 1–2 s | third route; asked for low reasoning effort |

Each Groq model has its own quota, so routing across models adds capacity. Routes are settings, not code:

```
LLM_TURN_ROUTES=groq:qwen/qwen3.8-27b,gemini:gemini-3.1-flash-lite,groq:openai/gpt-oss-20b
LLM_TEXT_ROUTES=gemini:gemini-3.1-flash-lite,groq:openai/gpt-oss-20b,groq:qwen/qwen3.8-27b
NARRATION_VARIANTS=2
```

## How the AI Director is routed (`app/services/llm_router.py`)

* Every call tries its routes in order, **once each**, with a 10–12 s timeout and no hidden retries.
* A 429, 5xx, 404 or timeout puts that route on **cooldown** (the provider's `retry-after` when given), and later calls skip it until it recovers.
* If every route is down, the authored text is used immediately. The game never waits on a rate limit.
* Prompts send only the axes that have moved and the last four decisions.
* LLM headlines are written once per chapter (9 per game), not after every decision (36).
* The two epilogue texts are written concurrently.
* `GET /stats/llm` shows which routes served text, tokens used on Groq, and how much narration is cached.

The LLM still only writes words. Effects, lanes, votes and the ending are deterministic.

## What Neo4j does

```
(:EpisodeNode)-[:LEADS_TO {choice_id, ...}]->(:EpisodeNode)     story spine (unchanged)
(:EpisodeNode)-[:OFFERS]->(:Choice)                             every option, including interrogation options
(:Choice)-[:PUSHES {points}]->(:Lane)-[:RESOLVES_TO]->(:EpisodeNode)   lane points and which ending screen a lane uses
(:Choice)-[:SHIFTS {delta}]->(:Axis)                            state effects
(:Choice)-[:REQUIRES {op, value}]->(:Axis)                      unlock conditions
(:Choice)-[:SETS_FLAG]->(:Flag)<-[:REQUIRES_FLAG]-(:Choice)     flag chains
(:EpisodeNode)-[:TRIGGERED_BY {op, value, group}]->(:Axis)      interrogation triggers
(:EpisodeNode)-[:NARRATED_AS]->(:Narration {key, variant})      LLM text cache
(:Playthrough)-[:CHOSE {step, role}]->(:Choice)                 finished games
(:Playthrough)-[:ENDED_IN]->(:Lane)
```

1. **Story graph in memory.** The episode is read once (three queries) and served from memory. It only changes when `seed_db.py` runs, so restart the server after reseeding.
2. **Narration cache.** A scene "situation" is the beat, the acting role, the exact choices on offer and the leading lane. The first tables to reach a situation get fresh LLM text, which is stored on the graph. Once `NARRATION_VARIANTS` versions exist, every later table is served from the graph with no LLM call; which version a table sees is fixed by its session id. The cache survives restarts, is shared by all games, and is cleared on reseed. If the LLM is unavailable and only one version exists, that version is used before falling back to authored text.
3. **Design model.** `seed_db.py` projects the mechanics from `app/design/content.py` into the graph. `content.py` remains the source of truth at runtime; a test checks the projection matches it. Lane, Axis, Flag and Choice nodes are merged, never deleted, so playthroughs stay attached across reseeds.
4. **Playthroughs.** Each finished game is written back as a path through the Choice nodes. `GET /stats/endings` and `GET /stats/lanes/{lane}/choices` read them, which gives the real-player ending distribution to compare with `reports/after/`.

### Useful queries

Lane points on offer, all and unconditional (the supply table in DIAGNOSIS.md):
```cypher
MATCH (c:Choice {active: true})-[p:PUSHES]->(l:Lane) WHERE p.points > 0
RETURN l.lane_id, sum(p.points) AS all, sum(CASE WHEN c.conditional THEN 0 ELSE p.points END) AS open
ORDER BY all DESC
```
Flag chains (which choice unlocks which):
```cypher
MATCH (c:Choice)-[:SETS_FLAG]->(f:Flag)<-[:REQUIRES_FLAG]-(d:Choice) RETURN c.choice_id, f.flag_id, d.choice_id
```
Real ending distribution:
```cypher
MATCH (p:Playthrough)-[:ENDED_IN]->(l:Lane) RETURN l.lane_id, count(p) ORDER BY count(p) DESC
```
Most common opening three decisions of games that ended in a lane:
```cypher
MATCH (p:Playthrough {resolved_lane: 'broken_house'})-[r:CHOSE]->(c:Choice) WHERE r.step < 3
WITH p, r, c ORDER BY r.step
WITH p, collect(c.choice_id) AS opening RETURN opening, count(*) ORDER BY count(*) DESC LIMIT 10
```

The flag-chain query found a real bug: the fifth, conditional option of two interrogations could never be offered (0 of 8,082 simulated scenes), which also made `inheritance_unlocked` and the choice it unlocks unreachable. Fixed in `interrogation_engine.py`.

## Capacity and limits

* **Concurrent tables.** Fresh text capacity is roughly 8 turns/min (qwen) + 15/min (Gemini) + the third route. A human table plays about 2–3 scenes a minute, so several tables can get fresh text at once, and cached situations cost nothing.
* **Daily caps.** Each Groq model allows 1,000 requests/day. A cold game uses about 47 LLM calls, falling toward 11 as the cache fills.
* **Cached text is shared.** Two tables in the same situation can see the same wording (one of `NARRATION_VARIANTS`). Cached text is not personalised to a table's earlier decisions. Raise `NARRATION_VARIANTS` for more variety at the cost of more LLM calls.
* **One worker.** The graph cache, session state and locks are per process.
* **Aura free tier** allows 200,000 nodes and 400,000 relationships. A playthrough adds 1 node and about 50 relationships.
