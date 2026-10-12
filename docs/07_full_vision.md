# 07 — Full vision, and the first three-car scene

**Decisions recorded here (2026-10-12).** Every car sees everything about every other car
(revises D4). With more than two cars, "the other" means any other car in a zone shared
with me (D5, option A). Learned policies keep controlling speed only.

**Outcome.**
- With full vision the scripted cars follow one shared schedule instead of guessing. Style
  then decides every open case cleanly, the standing-start collisions disappear, and a car
  whose task needs it to be first is let through. The systematic comparison, including
  three- and four-car scenes, is in [REPORT.md](../REPORT.md).
- The three-car scene works: the gap a yielding car accepts between two priority cars is
  5 s for a cautious style and 3 s for a middle or aggressive one.
- For the learned policy, full vision first made training fail, twice, for reasons that
  were weaknesses of the reward and of the action space rather than of full vision. Both
  are fixed. On the one pairing trained so far, full and world vision then perform the same.

Data: [results/vision/](results/vision/), [results/rl_vision/](results/rl_vision/).

## 1. What "full vision" means here

Each car's view (`AgentView`) now holds, for **every** car:

| What | Content | Was visible before |
|---|---|---|
| State | position, heading, speed, progress along its route, distance to the conflict zone | yes |
| Intent | its task automaton and the state that automaton is in | no |
| Style | its style number | no |
| Planned move | the acceleration it last commanded | no |

How much a policy uses is its own choice (`vision="full"` or `"world"`), so the two can
be compared on identical scenarios. The old world-only drivers still reproduce the
published tables exactly (540 episodes re-run, 0 differences).

**One point to confirm.** "Planned move" is implemented as *what the car is doing right
now* (its latest command) together with its task state and style, from which its next
decision follows. It is **not** a predicted trajectory several seconds ahead. If you
meant that, it is a further step: each car would have to publish a plan, or the others
would simulate its policy.

## 2. Scripted cars with full vision

`FullVisionController` replaces guessing by a **shared schedule**. Every car works out,
from the same information and with the same rules, who may enter the intersection when,
and holds back only if its own slot starts later than it would arrive:

1. cars are placed in order of priority, each at the earliest time that does not overlap
   the slot of a conflicting car placed before it, so cars whose paths do not cross can
   go at the same time;
2. priority: cars already in a zone or unable to stop; then cars whose task requires them
   to be first (nobody who can still stop may enter ahead of them); then by *claim* =
   free-running arrival time plus the time margin of the car's style; ties by agent id;
3. a car whose own task makes it wait holds no claim.

The priority order and the claim are my choices, not consequences of "full vision"; see §6.

Numbers below are from the paired comparison in [REPORT.md](../REPORT.md) (two cars,
10 seeds per style pair, the same instances for both visions).

| | world vision | full vision |
|---|---|---|
| **Precedence open (`CROSS:CROSS`): the more aggressive car goes first** | | |
| base scenario | 68% | 93% |
| `tie` | 82% | 100% |
| `crossing` | 82% | 100% |
| `standing_start` | 40% | 100% |
| **Both must go first, from a standing start** | | |
| collisions | 6 / 90 | 0 / 90 |
| **One must go first, the other is free (all four scenarios)** | | |
| both tasks accepted | 659 / 720 | 720 / 720 |
| **Total delay, precedence open** | | |
| base / tie / crossing / standing start | 5.3 / 9.1 / 7.9 / 6.9 s | 2.5 / 4.1 / 3.3 / 3.9 s |

Unchanged, as they should be: compatible pairs succeed every time, two cars that both
must go first produce exactly one winner, and in a tie between two such cars the winner
is still decided by position (48%), not by style. No collision in 1,800 two-car
full-vision episodes.

One consequence to be aware of: a cautious car gives way to an aggressive one unless it is
about 2 s ahead. In the base scenario a cautious A went first against an aggressive B in
none of 10 episodes, including those where A would have arrived up to 1.3 s earlier.

## 3. Three cars: the gap between two priority cars

`gap.scenic`: A1 and A2 go straight, `headway` seconds apart; B turns left across them and
holds `YIELD`. Under D5, B's automaton is satisfied once the first car has passed; whether
B then goes in front of A2 is left to style. A1 and A2 have style 0.5; 10 seeds per cell.

**Share of episodes in which B goes between A1 and A2**

| B's style | 2 s | 3 s | 4 s | 5 s | 6 s |
|---|---|---|---|---|---|
| *full vision* | | | | | |
| 0.1 cautious | 0% | 0% | 0% | 100% | 100% |
| 0.5 middle | 0% | 100% | 100% | 100% | 100% |
| 0.9 aggressive | 0% | 100% | 100% | 100% | 100% |
| *world vision* | | | | | |
| 0.1 cautious | 0% | 0% | 0% | 0% | 0% |
| 0.5 middle | 0% | 0% | 0% | 0% | 0% |
| 0.9 aggressive | 0% | 0% | 0% | 20% | 30% |

All three tasks accepted in 300 of 300 episodes, no collision.

- **With full vision the accepted gap depends on style**: 5 s for a cautious car, 3 s for a
  middle or aggressive one.
- **With world vision the gap almost never opens.** A1 cannot know that B will yield, so
  it hesitates (2.8 s of delay on average, against 0.1 s with full vision), and A2 closes
  up behind it.
- When B takes the gap, A2 pays for it: A2's mean delay rises from 0.9 s to 2.2 s, while
  B's falls from 8.8 s to 4.8 s.

What was needed: conflict zones per pair of cars, a following rule so A2 does not run into
A1, and metrics for more than two cars. The task automata and the alphabet did not change.
**Learned policies do not handle three cars yet** (the network input describes one other car).

## 4. Learned policy with full vision

Same pairing as before (A crosses, B yields), same seed, 1 M steps, with 11 more inputs:
the other car's task state, style and latest command.

**Two failures first, and what they revealed.**

| Attempt | Result | Cause | Fix |
|---|---|---|---|
| Full vision, reward as in 05 (log not kept) | Both roles 0% accepted: every car stops and stays stopped | The shaping term paid a small positive amount on every step spent standing still. "Everyone stops" was a stable solution; the world-vision run had escaped it by luck of initialisation | Shaping is now the plain difference of the potential: standing still pays exactly nothing |
| Full vision, corrected shaping | Crossing 99%, yielding 3%: the yielder parks 25 m back and never restarts | The policy's output was an acceleration. Having learned to brake, it commanded braking on about 86% of steps even when free to go, and a stopped car needs a run of positive commands to move | The output is now a **target speed**. Any target above zero starts the car |

Neither is specific to full vision; it happened to be the run that fell in. Both are
changes to choices I had made inside D4, and are listed in 02.

**After both fixes**, 180 held-out scenarios per row (20 seeds × 9 style pairs):

| Policy | Scenario | Both tasks accepted | Collisions | Free-road speed at style 0.1 / 0.5 / 0.9 |
|---|---|---|---|---|
| world vision | base | 180 / 180 | 0 | 6.2 / 8.2 / 10.0 m/s |
| world vision | early yielder | 180 / 180 | 0 | 6.2 / 8.2 / 10.2 |
| full vision | base | 180 / 180 | 0 | 6.3 / 8.3 / 10.2 |
| full vision | early yielder | 180 / 180 | 0 | 6.3 / 8.3 / 10.2 |

Targets are 6.5 / 8.5 / 10.5 m/s. The aggressive-yielder failure of 05 §5 (4 of 60) does
not occur in either policy now. The smallest gap between one car leaving the zone and the
next entering is still short: as little as 0.2 s on the base scenario, for both policies.

**Full vision makes no visible difference on this pairing**, and none was expected: the
tasks already fix who goes first, so knowing the other's intent adds nothing. Where it
should matter is where intent is ambiguous from motion alone (both free, or one free and
one that must lead). That needs training on all pairings and has not been done.

## 5. Status of earlier documents

- 04 and 06 §2 describe the world-vision scripted controller; they remain correct and
  reproducible with `--controller task`.
- 05 describes the first learned policies, which used acceleration outputs and the old
  shaping. Its numbers stand as a record; its reward section is superseded by §4 here.
- New default for learned policies: full vision, target-speed output, corrected shaping.

## 6. Choices I made that you did not decide

| Choice | Why | Alternative |
|---|---|---|
| A car that must be first has priority over one that is free | Seeing intent is only useful if it is used | Selfish: ignore the other's need. Then full vision would change predictions only |
| Priority by claim = arrival time + style margin | One number that everyone can compute, in which style counts directly | Pure arrival time (style acts only through speed); or search for the order with the least total delay |
| Strict priority when placing cars in the schedule | Simple and the same for everyone | It is not optimal: in 7% of four-car instances it does worse than world vision |
| "Planned move" = latest command | The only plan a reactive policy has | Published multi-second plans; see §1 |
| Target-speed output for learned policies | Removes the parked-car trap | Keep acceleration output and penalise saturated commands |
| Shaping without discount | Removes the stand-still solution | Keep exact potential-based shaping and add a real progress reward |

## 7. Next steps

1. Train on all nine pairings, world and full vision side by side, several seeds. This is
   the experiment that can show what full vision is worth to a learned policy.
2. Extend the learned policy's input to several other cars, then train on `gap`.
3. Further two-car probes from 06 §4: late challenger, offset sweep, opponent swap.
