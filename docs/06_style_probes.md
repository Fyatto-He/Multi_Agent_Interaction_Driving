# 06 — Style probes: scenarios where driving style has to show

**Why.** In the base scenario the two cars start at unrelated speeds and up to 2 s apart,
so most episodes are decided by who happens to be ahead. Style only matters when the
situation is genuinely contested. These probes remove the head start so that the task
and the style are the only things left to decide the outcome.

**Status.** Three two-car probes are implemented and run (§1–§3) with the world-vision
drivers. Cases that need a third car are brainstormed (§4); the first one (§5) has since
been decided and built, and the same probes have been re-run with full vision:
[07_full_vision.md](07_full_vision.md).

Data: [results/probes/](results/probes/), [results/rl_style_fix/](results/rl_style_fix/).

## 1. The probes

Each is one Scenic file in `dfadrive/scenarios/`. In `tie` and `crossing` every car
starts at the cruise speed of its own style, so the "arrival offset" is what would
happen if both simply kept driving.

| Probe | Situation | What it isolates |
|---|---|---|
| `tie` | Unprotected left turn; both would reach the conflict zone within 0.3 s of each other | Precedence with no head start |
| `crossing` | Right-angle crossing (A west→east, B south→north), same tie | The same, without the left turn's asymmetry |
| `standing_start` | Both at rest 9–12 m before the zone, like an all-way stop | Negotiation with no momentum at all |
| early yielder (`tie` with `--arrival-offset -1.5`) | The car that must yield would arrive 1.5 s *before* the car with priority | Task against style: the task says wait, the style says go |

```bash
.venv/bin/python scripts/run_matrix.py --name probe_tie --scenario tie \
    --tasks CROSS:CROSS GO_FIRST:GO_FIRST CROSS:YIELD YIELD:CROSS --styles 0.1 0.5 0.9 --seeds 10
.venv/bin/python scripts/eval_policy.py runs/rl/style_fix/model.zip --scenario tie --arrival-offset -1.5 \
    --tasks CROSS:YIELD --styles 0.1 0.5 0.9 --seeds 20 --out eval_early_yielder
```

## 2. Scripted controller on the probes

10 seeds per cell, 360 episodes per probe; the base scenario (20 seeds, from 04) for
comparison. With 10 seeds a single cell is uncertain by about ±15 points.

**Task leaves precedence open (`CROSS:CROSS`): share of episodes in which A enters first.**
Rows are A's style, columns B's style (0.1 / 0.5 / 0.9).

| A's style | base scenario | `tie` | `crossing` | `standing_start` |
|---|---|---|---|---|
| 0.1 | 60 / 55 / 10 | 60 / 40 / 10 | 60 / 40 / 10 | 50 / 100 / 0 |
| 0.5 | 50 / 60 / 15 | 80 / 70 / 30 | 80 / 60 / 30 | 0 / 50 / 80 |
| 0.9 | 85 / 75 / 65 | 100 / 90 / 70 | 100 / 90 / 70 | 100 / 20 / 50 |
| *more aggressive car goes first* | *72%* | *82%* | *82%* | *40%* |

**Both must go first (`GO_FIRST:GO_FIRST`).**

| | base scenario | `tie` | `crossing` | `standing_start` |
|---|---|---|---|---|
| More aggressive car wins | 82% | 48% | 48% | 97% |
| Collisions | 0 / 180 | 0 / 90 | 0 / 90 | **6 / 90** |

**Task fixes precedence (`CROSS:YIELD`, `YIELD:CROSS`).** In every probe, at every style
pair: both tasks accepted in 100% of episodes, the order is the one the task prescribes,
and no collision.

What the probes add to the picture from 04:

1. **In a tie, style orders precedence cleanly.** The `tie` and `crossing` tables rise
   along every row and fall along every column, where the base scenario's did not
   separate styles 0.1 and 0.5. The earlier "mid-range styles are not separated" was a
   property of the base scenario (unrelated start speeds and timing), not of the style
   scalar.
2. **The left turn's geometry was not the reason for the result.** `crossing` gives almost
   the same table as `tie`.
3. **A contest is decided by position, not by temperament.** When both cars must go first
   and arrive together at their own cruise speeds, the more aggressive one wins only 48%
   of the time: whoever is a fraction of a second ahead takes it. In the base scenario
   the aggressive car won 82% of the time only because it accelerates into the lead.
4. **From a standing start the scripted controller breaks down.** With precedence open,
   the order is erratic (40%, with cells at 0% and 100% side by side). With both cars
   told to go first it produces the first collisions of the task-reading controller
   (6 of 90): by the controller's rule each sees a stationary opponent as far away in
   time, so both commit and they meet in the zone (read from the rule, not traced episode
   by episode). This is a controller limit, and a useful one to have on record,
   because it is the situation a learned policy would have to do better in.
5. **When the task fixes the order, style never overrides it**, in any probe.

## 3. Learned policy on the probes

Only `CROSS:YIELD`, the one pairing it was trained on (policy `style_fix`, see 05 §5).

| Probe | Both tasks accepted | Collisions | Where it fails |
|---|---|---|---|
| base scenario | 266 / 270 | 1 | all 4 in one cell: A cautious (0.1), B aggressive (0.9) |
| `tie` | 270 / 270 | 0 | — |
| early yielder | 176 / 180 | 0 | all 4 with B aggressive (0.9); none with B at 0.1 or 0.5 |

The learned yielder is sound in a tie and unsound in one specific situation: **an
aggressive car that must yield and would arrive well before the car it must yield to.**
It enters about 1 s after the other leaves on average (0.6–1.0 s median, against 2.4–2.6 s
for the scripted controller), and in roughly 1 case in 15 it enters while the other is
still inside. The scripted controller, where the task rule is absolute, never does.

This is the clearest evidence so far of the thing the project is about: in a learned
policy, intent and style are traded off against each other, and at the aggressive end
the style can win. Whether more training, more seeds or a larger rejection penalty
removes it is open.

## 4. Brainstorm: situations worth probing

Grouped by what they need. "Reveals" is what a difference between styles would look like.

**Possible today (two cars, existing tasks)**

| Case | Tasks | Reveals |
|---|---|---|
| Tie (done) | `CROSS:CROSS` | who claims an unclaimed right of way |
| Contest (done) | `GO_FIRST:GO_FIRST` | whether the loser backs off cleanly or forces it |
| Early yielder (done) | `CROSS:YIELD` | whether style can override the task |
| Standing start (done) | any | hesitation, double starts, deadlock |
| Late challenger | `CROSS:GO_FIRST`, GO_FIRST car 1–2 s behind | whether a lost cause is abandoned safely or chased |
| Double courtesy | `YIELD:YIELD` | how long two cautious cars wait; today always a deadlock by construction |
| Mismatched pair sweep | `CROSS:CROSS`, offset swept −2…2 s | the offset at which the more aggressive car stops giving way: a "style exchange rate" in seconds |
| Opponent swap | learned vs. scripted, or learned vs. blind | whether a learned policy relies on its partner behaving like itself |

**Needs a third car**

| Case | Setup | Reveals |
|---|---|---|
| **Gap between two priority cars** | A1 and A2 straight, a few seconds apart; B turns left and must yield | whether B takes the gap between them (aggressive) or waits for both (cautious). The classic gap-acceptance test |
| Three-way arrival | three cars from three arms at once | cyclic waiting: each yields to the next |
| Impatient follower | a cautious yielder with an aggressive car queued behind it | pressure from behind; needs car following |
| Blocked zone | a car stops inside the zone | waiting forever versus going around; needs a new fact |

**Needs new task vocabulary**

| Case | Why |
|---|---|
| Right-of-way rule as a monitor | "priority car approaching" is a distance threshold, i.e. a new fact |
| Merge into the same exit lane | the conflict is a shared lane, not a zone to cross |

## 5. Proposal for the first three-car case — *decided 2026-10-12: option A; built, see 07 §3*

**Case.** Gap between two priority cars: A1 and A2 go straight in the same lane, B turns
left across them and holds `YIELD`.

**Why this one.** It is the standard situation in which driving style is defined in the
traffic literature (the gap a driver accepts), it uses the existing intersection, and it
needs no new symbol.

**The decision.** With more than two cars, what does "the other" in `other_in_cz` mean?

| Option | Meaning | Consequence |
|---|---|---|
| **A. Any other car (recommended)** | `other_in_cz` is true when any other car is in a zone shared with me | Alphabet and all three DFAs unchanged; still fits the pretrained encoder. `YIELD` then means "wait until the first car has passed". After that the agent holds plain `CROSS`, and whether it goes between A1 and A2 is left to **style**. That is exactly the comparison wanted. |
| B. One symbol per opponent | `other1`, `other2`, … | `YIELD` can say "yield to both". Alphabet grows with the number of cars and DFAs must be rewritten per traffic situation. |
| C. One DFA per opponent | each agent runs a `YIELD` monitor against each priority car | "Yield to both" without a bigger alphabet, but an agent now has several task states, which changes the policy input. |

Under A, "yield to both" is not expressible; if you want the *task* to demand it, that
needs B or C.

**What it costs to build (any option).** Support for more than two agents in the
geometry, labels, recorder and metrics; a following rule so A2 does not run into A1;
and a learned-policy observation that handles more than one other car. Roughly the size
of the reward work in 05.
