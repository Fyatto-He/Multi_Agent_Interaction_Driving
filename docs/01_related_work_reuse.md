# 01 — Related work: research / reuse matrix

Scope: what each nearby work actually does, and what we can take from it for
*multi-agent driving with one task automaton per vehicle*. Not a survey.

**How this was produced (2026-10-08).** Papers read from arXiv / ar5iv; code read from
shallow clones of the public repositories at the commits listed in
[§5](#5-sources-and-versions). Statements tagged *(code)* were checked in the source;
statements tagged *(paper)* come from the paper text only. Nothing here was run except
where a measurement is quoted.

Our setting, for comparison: 2+ vehicles, **continuous** control, full/shared world state,
each vehicle has its **own** DFA, tasks are **not** purely cooperative (two cars that both
want the conflict zone), plus a behaviour-**style** variable that is not part of the task.

---

## 1. Learning methods

| | **ACC-MARL** (Yalcinkaya et al., ICML 2026) | **DGRM** (Hu et al., 2021/2024) | **LTL2Action** (Vaezipoor et al., ICML 2021) | **DeepLTL** (Jackermeier & Abate, ICLR 2025) |
|---|---|---|---|---|
| **Problem actually solved** | One shared policy that makes a *team* satisfy a tuple of DFAs given at run time; plus test-time task assignment using the learned value function | Scaling a *fixed* multi-agent task with sparse/non-Markovian reward by decentralising over an interaction graph | Single agent follows *unseen* LTL instructions | Single agent satisfies *unseen* LTL, incl. infinite-horizon (ω-regular) and safety-aware |
| **Task representation** | DFA per agent over a token alphabet, one symbol per step; kept *minimised*; progress = "advance then minimise" (the task state **is** the residual DFA) *(code: `DFAWrapper.step_env`)* | Reward machine per agent (states, propositions, transition + reward output) | LTL formula, rewritten each step by *progression* | LTL → limit-deterministic Büchi automaton (Rabinizer 4), abstracted to **reach–avoid sequences** of truth-assignment sets |
| **Global or per-agent** | Per-agent DFAs, **team** objective: reward 1 only if *all* DFAs accept (`min` over agents) *(code)*; some agents get trivial DFAs ("helpers") | Per-agent RMs; global reward = mean of local rewards | n/a (single agent) | n/a (single agent) |
| **What an agent observes** | Full state from its own viewpoint + its agent id + **all agents' DFAs** (own first, others by id) *(code: `move_to_front`)* | Policy: own state + own RM state only. Critic: states/RM states/actions of κ-hop neighbours | Env observation + current (progressed) formula | Env observation + current reach–avoid sequence |
| **How the automaton enters the policy** | Residual DFA → graph → **frozen pretrained GATv2 encoder** (RAD embedding, 32-d per agent) → concat with obs/id features → MLP | Product state (s, u): table index, or network input in the deep variant (encoding not specified) | Formula AST → R-GCN (or GRU/LSTM over tokens) → concat with obs features; encoder pretrainable env-free ("LTLBootcamp") | Assignment sets → set network (DeepSets-style) → GRU over the sequence → concat; path through the automaton chosen by the value function |
| **Learning algorithm** | IPPO with **parameter sharing**, PureJaxRL/JaxMARL style; whole loop incl. env is `jax.jit`-ed *(code: `train_policy.py`, `ppo.py`)*; potential-based shaping on own-DFA acceptance | Actor–critic with truncated (κ-hop) Q; tabular and deep variants; separate parameters per agent | PPO (`torch_ac`) | PPO (`torch_ac`) + curriculum over sequences |
| **Control** | Discrete (5 moves, grid `TokenEnv`) | Discrete (continuous listed as future work) | Discrete (LetterWorld, MiniGrid) **and continuous** (ZoneEnv / Safety Gym) | Discrete **and continuous** (ZoneEnv / Safety-Gymnasium, FlatWorld) |
| **Multiple / unseen tasks** | **Yes.** Trained on sampled "RAD" DFAs ≤ 5 states; tested on Reach, Reach-Avoid, and ≤ 10-state DFAs | **No.** RM fixed and known | **Yes** (deeper/unseen formulas) | **Yes** (zero-shot, finite and infinite horizon) |
| **Public code** | Yes, MIT: `rad-dfa/acc-marl` + helper libs (§2) | None found | Yes, MIT, but Python 3.6 / gym 0.17 / dgl 0.4.3 / Spot 2.9 | Yes, MIT, Python 3.10 / PyTorch 2.2; needs Java 11 for Rabinizer |

**Traffic Rule Compliant Autonomous Driving Using Reward Machines and RL (ITSC 2026).**
*Not accessible.* Three web searches and an arXiv API query (`"reward machines" AND
"traffic rule"`) on 2026-10-08 found no paper or preprint with this title, and no code.
The nearest hits are different papers (Yan et al., arXiv 2606.14609, reward machines for
highway driving; the Krasowski/Althoff temporal-logic traffic-rule line) and should not be
mistaken for it. **Action:** if you have the PDF, drop it in `docs/papers/` and this row
gets filled in. It matters because it is presumably the closest prior on *rules as
automata in driving*, i.e. the "rule monitor" reading of a DFA that we deliberately are
not starting with (see `02_architecture.md`, D2).

---

## 2. ACC-MARL helper libraries — the part most worth reusing

All MIT, all on PyPI, all require Python ≥ 3.10, all JAX-based except `dfa`.

| Library | What it is *(code)* | Verdict for us |
|---|---|---|
| [`dfa`](https://github.com/mvcisback/dfa) 4.7.1 | Pure-Python DFA: hashable states, `transition`, `label`, `advance`, `minimize`, `find_word`, `dict2dfa`/`dfa2dict`, `min_distance_to_accept_by_state`, counterexample search | **Use now.** It is the base type the rest of the toolchain converts from. No JAX needed. |
| [`dfax`](https://github.com/rad-dfa/dfax) 0.1.19 | JAX DFA as fixed-size arrays (`transitions[state, symbol]`, `labels`); `advance`, `minimize`, Boolean ops, `to_graph()`; samplers `Reach`, `ReachAvoid`, `RAD`; `dfa2dfax`/`dfax2dfa` | **Use later**, when we sample task distributions or feed the RAD encoder. Our DFAs convert losslessly as long as the alphabet is ≤ 10 single symbols. |
| [`rad-embeddings`](https://github.com/rad-dfa/rad-embeddings) 0.2.10 | GATv2 DFA encoder + **shipped pretrained weights** for (≤10 states, 10 tokens) and (≤10 states, 5 tokens); trained env-free on a DFA bisimulation game; `Encoder()(dfa)` accepts `dfa.DFA` directly | **Use later** as a frozen featuriser: DFA → 32-d vector, computed on CPU, fed to any (PyTorch) policy. Avoids training a task encoder ourselves. Checked 2026-10-08: our three DFAs embed with the shipped weights, but the package only imports with `jax==0.4.38 flax==0.10.4 chex==0.1.90` (ACC-MARL's pins), not with current JAX. |
| [`dfa-gym`](https://github.com/rad-dfa/dfa-gym) 0.2.18 | `DFAWrapper` (per-agent DFAs around a multi-agent env: `label_f(state)` → symbol → advance → reward/done) and the grid `TokenEnv` | **Copy the pattern, not the code.** The wrapper is hard-wired to jittable JAX envs and to team reward. |
| [`acc-marl`](https://github.com/rad-dfa/acc-marl) | IPPO training script, actor–critic network, configs | **Read, don't run.** The loop requires a JAX-jittable env (`jax.jit(make_train(...))`); MetaDrive (Panda3D/Bullet) is not. The network layout (id ⊕ obs ⊕ per-agent DFA embeddings, own first) is the thing to borrow. |

Two properties of this toolchain constrain our own design, so they are worth stating:

1. **One symbol per step.** The alphabet is a set of mutually exclusive tokens, not truth
   assignments over propositions (2^AP) as in LTL2Action/DeepLTL/reward machines. If we
   want RAD compatibility we need a rule that turns "several facts true at once" into one
   symbol, and at most 10 symbols.
2. **Agent i's DFA reads only agent i's label** (`L_i : S_i → Σ`). Driving tasks such as
   "enter after the other car has cleared" need facts about *another* agent. Nothing
   breaks, but this is outside what ACC-MARL evaluated.

---

## 3. Tools

| | **Scenic 3.1.1** (+ MetaDrive interface) | **MetaDrive 0.4.3** multi-agent envs |
|---|---|---|
| **Problem solved** | Probabilistic *scenario specification*: distributions over scenes, `require` constraints, dynamic behaviours, temporal requirements, `record`/`terminate when` | Lightweight multi-agent driving simulation with an RL API |
| **Multi-agent model** | Every object with a `behavior` is an agent, but **all of them are scripted by Scenic**; Scenic owns the simulation loop (`Simulation._run`). No Gymnasium/PettingZoo interface or public step API in the source tree *(code)* | `MultiAgentMetaDrive`: dict-keyed obs/reward/terminated/truncated per agent, `"__all__"`, optional respawn |
| **MetaDrive coupling** | Builds a **single-agent** `BaseEnv` on a **SUMO map**; object 0 is the MetaDrive agent, other cars are spawned as plain objects and driven via `before_step(action)`; a new engine is created per simulation; 2D-compatibility mode only *(code: `simulators/metadrive/simulator.py`)* | Native. `MultiAgentIntersectionEnv`: procedurally generated 4-way intersection; per-agent `spawn_lane_index`, `spawn_longitude`, `spawn_velocity`, `destination` via `agent_configs` *(verified by running)* |
| **Tasks** | Global scenario requirements (monitors), not per-agent task automata | Per-agent destination; built-in driving reward |
| **Observation** | Any property of any object (full state) | Ego state + navigation + 72-ray lidar (91-d); `MultiAgentTinyInter` has a `CommunicationObservation` that appends every other agent's relative pose/velocity, i.e. a ready-made full-state vector |
| **Control** | Continuous throttle/brake/steer actions, PID lane-following behaviours | Continuous `[steer, throttle/brake] ∈ [-1,1]²` |
| **Maps** | OpenDRIVE (+ matching SUMO `.net.xml`); CARLA Town01–10 pairs ship in the repo, not in the wheel | Procedural blocks (PG maps); SUMO and real-data maps also supported |
| **Road semantics we would otherwise write** | `intersection.maneuvers`, `maneuver.conflictingManeuvers`, lane centrelines | Lane graph, route checkpoints, lane-local coordinates |
| **Reusable scripted behaviour** | `FollowTrajectoryBehavior`, `FollowLaneBehavior` | `IDMPolicy` (same-lane car following only), `TinyInterRuleBasedPolicy`, `MixedIDMAgentManager` (mix RL and scripted agents in one env) |
| **Measured here (M1 Max, headless)** | 150-step, 2-car Town05 run: ≈ 1.0 s incl. engine start (≈ 150 steps/s); first map parse 11.6 s, then cached | 2 agents: ≈ 1750 env-steps/s; `reset` 0.024 s (engine reused) |
| **Health** | Active (commit 2026-10-05; 3.1.1 released 2026-05-07) | Slow: last PyPI release 2024-12, last push 2025-08. PyPI 0.4.3 has a known "vehicles may not fully stop" issue fixed on `main` (per Scenic docs) |

Also checked, as a third candidate only: **SMARTS** — natively multi-agent and already
used in `../semantic-driving-alphabet`, but last release 2024-03, last push 2025-01,
231 open issues, and it drags in SUMO binaries. Its one advantage, the existing label
code in that project, is tied to the alphabet we are explicitly not continuing. No reason
to start a new prototype on it.

---

## 4. What this means for us

**Assumptions that differ from our driving setting**

- *Cooperative vs. mixed-motive.* ACC-MARL rewards the team only if every DFA accepts;
  DGRM averages rewards. Two cars contesting a conflict zone can hold tasks that are
  jointly unsatisfiable ("both go first"). A team-`min` reward would hide that; we need
  per-agent outcomes.
- *Labels about other agents.* See §2 point 2.
- *Discrete grid vs. continuous vehicle dynamics.* Only LTL2Action/DeepLTL show continuous
  control, and only single-agent.
- *Simulator in the training loop.* ACC-MARL's speed comes from a jitted env. Ours is a
  physics engine on CPU; throughput is bounded by CPU cores, not the GPU.
- *No style variable anywhere.* None of these works separate "what" from "how"; closest
  is DeepLTL's safety-aware path choice. This is ours to define.
- *Task = goal vs. task = rule.* All four treat the automaton as a goal to reach. The
  traffic-rule literature treats it as a monitor to never violate. We start with goals.

**Reuse, concretely**

| Need | Take from | When |
|---|---|---|
| DFA data type, minimise, shortest-word, distance-to-accept | `dfa` | now |
| Wrapper design: labelling fn → symbols → advance per-agent DFAs → reward/done | `dfa-gym.DFAWrapper` (pattern) | now |
| Reward: sparse accept + potential-based shaping on DFA progress | ACC-MARL (formula) | first RL run |
| Policy input layout: own obs ⊕ own DFA feature ⊕ others' DFA features | ACC-MARL `ActorCritic` (layout) | first RL run |
| Algorithm baseline: parameter-shared IPPO | ACC-MARL / JaxMARL (choice, not code) | first RL run |
| Task embedding for *unseen* tasks | `rad-embeddings` pretrained encoder via `dfax` | when we train on > a handful of DFAs |
| Task distributions | `dfax.samplers` | same |
| Reach–avoid view of a DFA path as policy input | DeepLTL (idea) | only if DFA embeddings underperform |
| Scene sampling with constraints | Scenic | now (thin) / later (full) |
| Multi-agent physics, routes, full-state obs | MetaDrive MARL envs | now |

**Do not reimplement**

- DFA minimisation, equivalence, Boolean operations, random DFA sampling → `dfa` / `dfax`.
- A DFA/graph encoder and its pretraining → `rad-embeddings`.
- LTL → automaton translation → if we ever want LTL input, use an existing translator
  (Spot, `ltlf2dfa`) and stay in DFA-land afterwards; do not port LTL2Action's progression.
- Vehicle dynamics, lane graphs, collision detection, top-down rendering → MetaDrive.
- PPO itself → an existing, tested implementation (decision D4).
- DGRM's κ-hop truncated critic → pointless at n = 2; revisit only with many agents.

**Do reimplement (small, and coupling would cost more than it saves)**

- The per-agent DFA wrapper around the simulator (≈ 100 lines; the original is JAX-only).
- The labelling function for our propositions (it *is* the research object).
- A route-following + conflict-zone scripted controller (MetaDrive's `IDMPolicy` only
  handles a leader in the same lane and is tied to engine internals).

---

## 5. Sources and versions

| Item | Reference | Inspected at |
|---|---|---|
| ACC-MARL | [arXiv 2511.02304](https://arxiv.org/abs/2511.02304), [ICML 2026 poster](https://icml.cc/virtual/2026/poster/63254) | `rad-dfa/acc-marl` @ `d801582` (2026-05-05) |
| DFAx / dfa-gym / rad-embeddings | [github.com/rad-dfa](https://github.com/rad-dfa) | `da1a326` / `3f46af7` / `7ef3bc9` |
| RAD embeddings papers | Yalcinkaya et al., NeurIPS 2024; NeuS 2025 (cited in the repo README) | — |
| DGRM | [arXiv 2110.00096](https://arxiv.org/abs/2110.00096) | paper only; no code found |
| LTL2Action | [arXiv 2102.06858](https://arxiv.org/abs/2102.06858) | `LTL2Action/LTL2Action` @ `b3d2f8f` |
| DeepLTL | [arXiv 2410.04631](https://arxiv.org/abs/2410.04631) | `mathiasj33/deep-ltl` @ `3157200` |
| Scenic | [docs.scenic-lang.org](https://docs.scenic-lang.org/en/latest/simulators.html) | PyPI 3.1.1; source @ `2630b09` (3.2.0b1) |
| MetaDrive | [github.com/metadriverse/metadrive](https://github.com/metadriverse/metadrive) | `main` @ `85e5dad` (version string 0.4.3) |
| SMARTS | [github.com/huawei-noah/SMARTS](https://github.com/huawei-noah/SMARTS) | repository/PyPI metadata only |

**Known gaps.** The ITSC 2026 paper (above). ACC-MARL appendix B.5 (exact hyper-parameters)
was read from the code/configs rather than the paper. DGRM's journal version was not
compared line by line with the preprint.
