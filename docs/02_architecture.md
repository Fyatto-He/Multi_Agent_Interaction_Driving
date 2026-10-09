# 02 — Architecture and decision log

Companion to [01_related_work_reuse.md](01_related_work_reuse.md). Each decision records
the alternatives, the evidence, the recommendation, and what would change it.
Status values: **decided** (by you, 2026-10-08), **open** (awaiting you),
**routine** (decided during implementation; cheap to reverse).

## Recommended first-experiment architecture

```
 scenario spec ──sample(seed)──▶ ScenarioInstance        per agent: route, spawn distance,
 (Python dataclass; optional                              initial speed, start delay,
  Scenic file as the sampler)                             task name, style
                                      │
                             ┌────────▼─────────┐
                             │  sim adapter      │  the ONLY module that imports metadrive
                             │  (MetaDrive MARL) │
                             └────────┬─────────┘
                                      │ WorldState  (plain data: poses, speeds, routes, contacts)
                 ┌────────────────────┼──────────────────────┐
                 ▼                    ▼                      ▼
        labeller                 policy_i                 recorder
  world facts → propositions     (WorldState,             every step: state, symbols,
  → one symbol per agent          own DFA state,          DFA states, actions → file
                 │                style_i) → action_i
                 ▼                    ▲
        task monitor  ────────────────┘
        per-agent DFA state
```

Three layers that never import each other's concerns:

| Layer | Answers | Lives in | Knows about |
|---|---|---|---|
| **World facts** | "what is true now?" | `dfadrive/world.py`, `labels.py` | geometry only |
| **Task state** | "how far along is agent *i*'s task?" | `dfadrive/tasks.py` | symbols only |
| **Policy decisions** | "what does agent *i* do?" | `dfadrive/controllers.py` now, a network later | world state + own DFA state + style |

Supporting modules: `scenario.py` (instances and samplers), `sim/metadrive_adapter.py`
(the only MetaDrive import), `env.py` (episode loop), `policy.py` (the policy interface
and the flat observation for networks), `recorder.py`, `metrics.py`.

This is the user's hypothesis (Scenic → MetaDrive → per-agent DFA → scripted → RL) with
one change: **Scenic samples the scenario but does not run it** (D1).

---

## D1 — Simulator / scenario stack — *decided: A*

| | A. MetaDrive MARL env + Scenic as *sampler* | B. MetaDrive MARL env, Python sampler only | C. Scenic drives MetaDrive (Town05) | D. SMARTS |
|---|---|---|---|---|
| RL API (per-agent obs/reward/done) | native | native | none; must be built on Scenic internals | native |
| Throughput measured (2 cars, headless, M1 Max) | ≈ 1750 steps/s, reset 0.02 s | same | ≈ 150 steps/s, new engine per episode | not measured |
| External policy can step the sim | yes | yes | no public step API in 3.1.1 | yes |
| Scenario description | `.scenic` file: `param` + `require` (sampling ≈ 3 ms, seed-deterministic, verified) | dataclass ranges + NumPy RNG | full Scenic: `conflictingManeuvers`, real maps, behaviours | Python "sstudio" |
| Road geometry Scenic can reason about | none (parameters are route-relative distances/speeds) | — | full OpenDRIVE network | — |
| Extra dependencies | `scenic` (pure-Python deps, coexists with MetaDrive in one venv, verified) | none | `scenic`, `sumolib`, map pair | SUMO |
| Project health | see 01 §3 | same | same | dormant since 2025-01 |

**Recommendation: A**, built so that B is the fallback with zero code change (the Scenic
file and the Python sampler produce the same `ScenarioInstance`).

Why not C, although it is the most "Scenic-native": the Scenic–MetaDrive interface makes
MetaDrive a single-agent env that Scenic steps itself. For scripted validation that is
fine; for RL it means writing our own multi-agent stepping layer on top of Scenic
internals, at a tenth of the speed, and giving up MetaDrive's multi-agent machinery.
That is the wrong trade for a project whose end goal is learned policies.

What A costs: in a parameters-only Scenic file, Scenic adds readability and constraint
handling ("arrival times within 1.5 s") but not its road-network reasoning. For *one*
scenario that is a modest gain, which is why B is a legitimate choice too.

**What would change this.** (i) We need scenarios on real road networks or many
intersection topologies → move toward C, or export MetaDrive's map to OpenDRIVE so
Scenic's driving domain can see it. (ii) Scenic gains a Gymnasium/PettingZoo stepping
interface → C becomes attractive. (iii) We want falsification/adversarial scenario search
(VerifAI) → Scenic moves from optional to central.

## D2 — First per-agent task semantics — *decided: goal + precedence family, one symbol by priority*

Full definition with transition tables: [03_tasks.md](03_tasks.md). Summary:

- Scenario: unprotected left turn. **A** goes straight west→east; **B** comes from the
  east and turns left across A's lane. One **conflict zone** = overlap of the two lane
  corridors, computed from route geometry.
- Four world facts per agent: `crashed`, `at_goal`, `own_in_cz`, `other_in_cz`.
- Collapsed to **one of six symbols** per step by a fixed priority
  (`crash > goal > both | own | other | none`), so the DFAs are over a 6-symbol alphabet
  and stay compatible with the ACC-MARL toolchain (≤ 10 tokens).
- A family of three goal-type DFAs over that alphabet: `CROSS` (reach goal, never
  crash), `YIELD` (CROSS, and do not enter the zone until the other has cleared it),
  `GO_FIRST` (CROSS, and enter the zone before the other does).
- Episode outcome per agent is three-valued: accepted / rejected / unfinished (timeout).

Alternatives: (a) one progress-only DFA for both agents, precedence left entirely to
style; (b) truth-assignment alphabet (2^AP) with Boolean guards, as in reward machines;
(c) rule-monitor DFAs (right-of-way compliance) instead of goal DFAs.

## D3 — Aggressive vs. conservative — *decided: one scalar*

One scalar `style ∈ [0, 1]` per agent (0 conservative, 1 aggressive), **never read by the
labeller or the DFA**. It maps monotonically to a few interpretable controller
parameters (cruise speed, acceleration limit, comfortable braking, and the time margin
required before committing to the conflict zone). A learned policy later receives the
same scalar as an observation feature.

Alternatives: (a) two scalars (pace and risk); (b) three discrete presets; (c) a
reward-mixing angle in the style of social value orientation (CoPO), which only exists
for learned policies.

Implemented values (`dfadrive/style.py`), linear in `style`:

| | conservative (0) | aggressive (1) |
|---|---|---|
| cruise speed | 6 m/s | 11 m/s |
| acceleration limit | 1.5 m/s² | 2.9 m/s² (the simulated car's maximum; the 3.5 first proposed is not reachable) |
| comfortable braking | 2.0 m/s² | 4.5 m/s² |
| time margin to commit | 3.0 s | 0.5 s |

**What would change this.** The validation run shows the scalar orders who goes first
only at the extremes (see 04 §4). If mid-range styles need to be distinguishable, split
into pace and risk (alternative a).

## D4 — First RL formulation — *open*

Preliminary view, so it can be challenged early: **parameter-shared independent PPO**,
continuous actions, observation = full world state in the ego frame ⊕ own DFA state ⊕
style, **per-agent** reward (not team-`min`), PyTorch.

- It is what ACC-MARL uses, minus the JAX loop that MetaDrive cannot support.
- Under full observability each agent's value function already sees the joint state, so
  MAPPO's centralised critic adds little at n = 2; and MAPPO presumes a shared reward,
  which our mixed-motive tasks do not have.
- Throughput is CPU-bound (physics), so the RTX 4080 Super is not the bottleneck;
  vectorise over processes. MetaDrive allows one engine per process, so vectorising
  means subprocesses.

Alternatives: (a) MAPPO with a centralised critic that also sees the other agent's task
and style; (b) ACC-MARL's layout in full, i.e. every agent observes all agents' DFAs
through RAD embeddings; (c) single-agent PPO against the scripted controller as a fixed
opponent, as a first sanity step before self-play.

Open sub-questions that belong to this decision:
1. Does an agent observe the other's task and style (ACC-MARL: yes for tasks), or only
   the world state (what the scripted controllers get)?
2. Reward: sparse accept/reject only, or plus potential-based shaping on
   `TaskMonitor.remaining` (ACC-MARL's choice), plus what collision/comfort terms.
3. How style enters the objective. As an observation alone it has no effect; it needs a
   style-dependent reward term or imitation of the scripted controller.

## Routine decisions

| Topic | Choice | Evidence | Would change if |
|---|---|---|---|
| Python | **3.11** | Highest version PyPI MetaDrive 0.4.3 accepts (`<3.12`); satisfies Scenic 3.1.1 (≥3.8), `dfax`/`rad-embeddings` (≥3.10), `jaxmarl` (≥3.11); wheels for Panda3D exist on macOS arm64 and Linux x86-64 | MetaDrive publishes a release supporting 3.12+ |
| MetaDrive version | `main` @ `85e5dad`, installed from the commit archive | Scenic docs: PyPI 0.4.3 has a "vehicles may not come to a complete stop" issue fixed on `main`; yielding needs a full stop. A commit pin is as reproducible as a tag | a 0.4.4+ release |
| DFA library | `dfa` 4.7.1 | Base type of the ACC-MARL toolchain; pure Python | — |
| Map | MetaDrive procedural 4-way intersection, 1 lane per direction | Simplest geometry with a genuine crossing conflict; route lanes and lengths are available from the lane graph | need multi-lane or signalised junctions |
| Time step | 0.1 s decision, 0.02 s physics (MetaDrive default) | Same as Scenic's MetaDrive default; enough for 10 m/s approach speeds | faster dynamics |
| Stop logic, gap acceptance | hand-written in `controllers.py` (~120 lines) | MetaDrive's `IDMPolicy` handles only a leader in the same lane and needs engine internals; ours is a pure function of the policy view | we need a stronger scripted opponent |
| Environment location | venv in `~/.venvs/dfa-drive`, symlinked as `.venv` | `~/Desktop` is Drive-synced; a 1 GB venv would be uploaded and native libraries can misload | project moves off the Desktop |
| RL framework family | PyTorch (when we get there) | Env is not JAX-jittable; CUDA PyTorch works on both Linux and Windows, JAX-on-GPU does not on native Windows | env replaced by a JAX simulator |

## Uncertainties I am not resolving silently

- **OS of the RTX 4080 Super machine** is unknown. Everything chosen runs on Linux and
  Windows; if we later use `rad-embeddings` on GPU, native Windows would need WSL2.
- **MetaDrive is slow-moving** (last push 2025-08). It works today with NumPy 2.4 and
  Gymnasium 1.4 on Python 3.11, but we own the pin.
- **The ITSC 2026 reward-machine paper** could not be found; it may bear on D2.
- **Labels about another agent** (needed for `YIELD`/`GO_FIRST`) are outside what
  ACC-MARL evaluated; whether RAD embeddings remain informative there is an open question.
- **`rad-embeddings` needs old JAX.** With current JAX its import fails inside
  `distrax`/TensorFlow Probability; it works with `jax==0.4.38 flax==0.10.4 chex==0.1.90`
  (the versions ACC-MARL pins). Checked 2026-10-08 in a separate venv: all three task
  DFAs embed with the shipped weights, and `YIELD` after the other has cleared embeds
  identically to `CROSS`, as it should. It is not a dependency of this repository yet.
- **Replay is bit-exact only from a fresh simulator.** A reused MetaDrive engine carries
  about 1e-6 m of physics state between episodes. `make_env(exact=True)` rebuilds it
  every episode, but each rebuild leaks about 4 MB and slows the process, so it is for
  replaying single episodes. Sweeps reuse one engine; a sweep is still reproducible as a
  whole (same command, same order: byte-identical CSV, checked on two 40-episode runs).
- **One MetaDrive engine per process.** Parallel environments must be subprocesses.
