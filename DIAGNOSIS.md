# Diagnosis — why games collapse to one or two endings

All numbers come from the simulator (`sim/`), which runs the real `prepare_scene`/`apply_choice`/`ensure_finale` with the infrastructure stubbed. The logic measured is the pre-balance code: `v1-baseline` plus the deadlock and serialisation fixes, neither of which changes outcomes (see ANALYSIS.md §6–8). Reproduce with:

```
python -m sim.run_sim --label before --games 2000     # reports/before/summary.md + charts
python -m sim.diagnose --label before --games 1500    # reports/before/diagnosis.json
python -m sim.snowball 1000
```

## Headline

| Table type (2,000 games each) | Result |
|---|---|
| 4 random bots | `govardhan_consolidation` **61.3%**, `venkatadri_compromise` 17.9%, `raghava_restoration` 12.5%. **`pyrrhic_govardhan`, `saraswathi_betrayal` and `the_inheritance` occur 0.0% of the time.** |
| By terminal node | Govardhan 61.3%, Venkatadri 17.9%, Raghava 15.0%, Saraswathi 3.9%, Broken House 1.9% |
| All 4 bots push the same lane | 6 lanes hit 100%. `pyrrhic_govardhan` gives `govardhan_consolidation` 100% of the time, `saraswathi_betrayal` gives `broken_house` 100%, and `the_inheritance` gives `saraswathi_ascendancy` 75.5% / `venkatadri_compromise` 24.5%. **3 of 9 endings cannot be reached even by a unanimous table.** |
| 1 bot pushing, 3 random | Hit rate: Govardhan cons. 85.5%, Venkatadri 64.8%, Raghava rest. 48.6%, Patriarch 21.9%, Broken House 19.4%, Saraswathi asc. 16.8%, Sar. betrayal 0.8%, Pyrrhic 0.2%, Inheritance 0.0% |

This matches the playtest report of one or two endings. A random table is a coin flip weighted three-to-one toward Govardhan.

## Root causes, in order of impact

### 1. One lane has far more points on offer than the others (lane supply imbalance)

Total positive lane points authored on choices, counting only choices with no `requires` condition (the ones visible in a typical game):

| lane | unconditional points | all points |
|---|---|---|
| govardhan_consolidation | **31** | **71** |
| venkatadri_compromise | 22 | 46 |
| raghava_restoration | 18 | 44 |
| pyrrhic_govardhan | 9 | 21 |
| saraswathi_betrayal | 9 | 18 |
| patriarchs_last_roar | 8 | 44 |
| broken_house | 7 | 35 |
| saraswathi_ascendancy | 6 | 31 |
| the_inheritance | **1** | **13** |

Measured over 1,500 random games, players were *shown* 57,415 points of `govardhan_consolidation` against 4,592 of `the_inheritance` (12.5×). Govardhan also has 8 spotlight beats, and every poll has at least one +2 `govardhan_consolidation` option, often two (ch03 seal and majority; ch05 remove and governor). `resolve_lane` compares **raw** sums, so the lane with the most supply wins whenever nobody pushes hard against it. This is the "one scoring axis dominating the lane weights" hypothesis, and it is the main cause.

### 2. The choice ranker snowballs the leading lane, and starts with Govardhan in the lead

`choice_relevance_score` (`content.py:194`) adds `0.5 × lane points` toward the **current leading lane** when ranking which 3 choices to show. At game start every lane is 0, and `max()` returns the first dict key, `govardhan_consolidation`. So from the first beat, Govardhan-lane options get a free +1 relevance and are listed first. Whichever lane leads keeps being offered more often.

P(final ending = lane leading at the start of chapter *c*), random tables:

| ch2 | ch3 | ch4 | ch5 | ch6 | ch7 | ch8 | ch9 |
|---|---|---|---|---|---|---|---|
| 30.0% | 43.0% | 61.7% | 63.2% | 71.9% | 73.1% | 71.6% | 81.6% |

By the start of chapter 4, about one-third of the way through, the leader is already the eventual ending in 62% of games.

### 3. Poll ties go to the first-listed option, which is the leader's option

In `apply_choice` (`choice_resolver.py:133`), ties go to the earliest choice in `current_choices`. The ranker in §2 puts the leading lane's option first. Over 7,500 random polls, **22.8% ended in a tie** and the first-listed option won **41.4%** of all polls, against 33% for a neutral rule. Four voters split across three options, so ties are routine and quietly add to the snowball.

### 4. Sub-lanes are structurally dominated by their parent lane

Every choice that feeds `pyrrhic_govardhan` through ruthless play also feeds `govardhan_consolidation` equally or more. Examples: `ch01_govardhan_accelerate` (+2/+1), `ch03_govardhan_intimidate_waverers` (+2/+1), `ch05_govardhan_total_control` (+2/+2), `ch08_govardhan_isolate_last_holdouts` (+2/+1). Likewise `saraswathi_betrayal` choices also feed `broken_house` or `govardhan_consolidation`, and `the_inheritance` choices feed `saraswathi_ascendancy` more (`ch02_saraswathi_own_faction` +2/+1, `ch07_saraswathi_claim_moment` +2/+1, `ch08_saraswathi_inheritance_claim` +3/+2). None of these three lanes has a bonus in `resolve_lane`.

Reachability, by beam search (width 60, all four players cooperating, maximising the target's winning margin; `reports/before/diagnosis.json`):

| lane | reachable? | best winning margin | how |
|---|---|---|---|
| govardhan_consolidation | yes | +28 | |
| venkatadri_compromise | yes | +24 | |
| raghava_restoration | yes | +20 | |
| broken_house | yes | +16 | |
| saraswathi_ascendancy | yes | +13 | |
| patriarchs_last_roar | yes | +10 | |
| saraswathi_betrayal | yes, narrowly | +6 | only by avoiding most betrayal-flavoured choices that also feed `broken_house` |
| pyrrhic_govardhan | yes, narrowly | +4 | only if Govardhan plays *soft* (media, soften, optics, manage) and avoids every ruthless choice; the opposite of what the lane means |
| **the_inheritance** | **no** | −3 | best path ends in `venkatadri_compromise` |

So the coordinated failures are not bad luck. The thematic way to reach these endings is mechanically the wrong way.

### 5. Disagreement drifts to the compromise lane (four-player averaging)

When the four players push four different lanes, the "middle" lane `venkatadri_compromise` wins **32.0%** (17.9% with random tables), and in 20.3% of games the winner is a lane *nobody* pushed. Two reasons:

* Many soft or hedging options carry `venkatadri_compromise` points.
* All three unconditional fallbacks in chapter 9 pay `venkatadri_compromise`: `ch09_raghava_yield` +1, `ch09_govardhan_halt` +1, `ch09_poll_family_compromise` +2. A table that has not hit the high thresholds is handed up to +4 compromise at the very end.

A single directed player among three random ones can steer only the high-supply lanes (§1 table). For the six lower-supply lanes, three random players dilute one player's intent below 25% (`pyrrhic_govardhan`, `saraswathi_betrayal` and `the_inheritance` ≈0%).

### 6. Thresholds and tie-break in `resolve_lane`

* The +3 bonuses need axes ≥ 7–8 (`public_mandate`, `institutional_control`, `saraswathi_influence`). These are reachable but mostly reward lanes that are already high-supply.
* The final tie-break is alphabetical (`max(..., key=(weight, name))`), which would favour `venkatadri_compromise`/`the_inheritance`. In practice it rarely decides: the runner-up is within 1 point in 14.8% of random games, and exact ties are rarer still.
* Final-verdict poll offers: 3 options in 78.5% of games, 2 in 16.3%, 1 in 5.1%. When only one option qualifies, the vote is forced (always `family_compromise` → compromise).

## Hypotheses from the brief, checked

| Hypothesis | Verdict |
|---|---|
| The final chapter overpowers earlier choices | **No.** Counterfactual influence: re-rolling only one chapter's random choices changes the ending in **ch1 40.8%, ch2 43.0%, ch3 30.7%, ch4 28.9%, ch5 21.7%, ch6 21.7%, ch7 14.2%, ch8 22.2%, ch9 18.9%** of games. Chapters 1–4 together: 53.6%; 5–8: 35.9%. Early chapters matter *most*, through the snowball (§2). Chapter 9's influence is real but small, and it pushes toward compromise (§5). |
| Four players' choices average out toward the middle | **Partly.** True for disagreeing tables (§5, compromise 32%). With random tables, the collapse goes to the *high-supply* lane, not the middle. |
| Unreachable ending thresholds | **Yes, for 1 lane outright (`the_inheritance`), and in practice for 2 more** (`pyrrhic_govardhan`, `saraswathi_betrayal`), because of the sub-lane coupling (§4). |
| One scoring axis dominates the lane weights | **Yes. This is the main cause** (§1), amplified by §2 and §3. |

## The LLM Director

The LLM never writes game state: effects, lanes, flags, poll tallies and `resolve_lane` are all deterministic (ANALYSIS.md §4). It sees the leading lane only as framing text. No change needed.

## Bugs found on the way (not balance, fixed first)

* **Interrogation-skip deadlock**: 87% of random games froze until a player reconnected (ANALYSIS.md §6).
* **`GAME_OVER` never delivered**: the finale payload was not JSON-serialisable over the socket (ANALYSIS.md §7).
