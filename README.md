# dfa-drive

Research prototype: **multi-agent driving where each vehicle has its own task automaton.**

    world state + own DFA state + own style  ->  low-level action

The DFA says *what* a vehicle must accomplish. The style scalar says *how* it drives.
The policy (scripted for now, learned later) decides the steering and acceleration.

**Start with [REPORT.md](REPORT.md)**: what was read, the setup, and the main experiment,
a paired comparison of drivers that see only each other's motion with drivers that share
task state and style.

![four cars, world vision against full vision](docs/figures/demo_four_way.gif)

**Status (2026-10-12).** Seven scenarios with two to four cars, three task DFAs over a
six-symbol alphabet, scripted drivers with world-only and with full vision, trajectory
logging and metrics. A learned policy (parameter-shared PPO, speed control) follows its
task and its style on the one task pairing trained so far. Scripted results rest on
thousands of paired episodes; learned results on one seed.

## Read first

| Document | Contents |
|---|---|
| [REPORT.md](REPORT.md) | Brief report: reading, setup, the world-vision / full-vision experiment, results, demo |
| [docs/01_related_work_reuse.md](docs/01_related_work_reuse.md) | What ACC-MARL, DGRM, LTL2Action, DeepLTL, Scenic and MetaDrive actually do, and what we reuse |
| [docs/02_architecture.md](docs/02_architecture.md) | Architecture and decision log (alternatives, evidence, what would change each decision) |
| [docs/03_tasks.md](docs/03_tasks.md) | Vocabulary and the three DFAs as transition tables and diagrams (generated from code) |
| [docs/04_validation.md](docs/04_validation.md) | Scripted-controller results: what succeeds, what fails, and why |
| [docs/05_rl_smoke_test.md](docs/05_rl_smoke_test.md) | First learned policy: what was trained, what it shows, what it does not |
| [docs/06_style_probes.md](docs/06_style_probes.md) | Scenarios built to make style show, results on them, further cases, and the open three-car decision |
| [docs/07_full_vision.md](docs/07_full_vision.md) | Full vision of other cars (scripted and learned), and the three-car gap scene |
| [docs/results/](docs/results/) | The episode tables and training logs behind docs/04–07 |

## Setup

Python 3.11 is required (MetaDrive does not support 3.12 yet).

```bash
python3.11 -m venv ~/.venvs/dfa-drive
ln -s ~/.venvs/dfa-drive .venv
.venv/bin/pip install -e ".[scenic,viz,dev,rl]"
```

The venv lives outside the project because this folder is cloud-synced; on another
machine a plain `python3.11 -m venv .venv` is fine. For the exact versions used for the
reported results, install `requirements.lock.txt` first. MetaDrive fetches its assets
(about 170 MB) the first time it is imported. Without the `scenic` extra everything still runs, using the
NumPy sampler.

```bash
.venv/bin/python -m pytest                # 40 tests, about 9 s
.venv/bin/python -m pytest -m "not sim"   # without the simulator
```

## Run

```bash
# one episode: A must cross, B must yield
.venv/bin/python scripts/run_episode.py --seed 0

# incompatible tasks, both aggressive
.venv/bin/python scripts/run_episode.py --seed 0 --task-a GO_FIRST --task-b GO_FIRST --style-a 0.9 --style-b 0.9

# negative control: controllers that ignore each other
.venv/bin/python scripts/run_episode.py --seed 0 --task-a CROSS --task-b CROSS --controller blind

# full vision: every car sees the others' task state, style and latest command
.venv/bin/python scripts/run_episode.py --scenario standing_start --task-a GO_FIRST --task-b GO_FIRST --controller full

# three cars: does the yielding car take the gap between two priority cars?
.venv/bin/python scripts/run_gap.py --name gap --seeds 10

# paired comparison of world vision and full vision, and the side-by-side demo
.venv/bin/python scripts/compare_vision.py --name multi_car --scenarios three_way four_way --seeds 150
.venv/bin/python scripts/make_demo.py --scenario four_way --seed 1

# figure of a recorded episode
.venv/bin/python scripts/plot_episode.py runs/episodes/CROSS-YIELD_task_seed0.npz

# the validation matrix behind docs/04 (9 task pairs x 9 style pairs x 20 seeds)
.venv/bin/python scripts/run_matrix.py --name validation --seeds 20 --styles 0.1 0.5 0.9
```

![Example episode](docs/figures/CROSS-YIELD_task_seed0.png)

## Train

```bash
# one shared PPO policy for both agents, self-play, A = CROSS and B = YIELD (about 4 min on 8 cores)
.venv/bin/python scripts/train_ppo.py --name smoke --steps 1000000

# held-out evaluation next to the scripted controller, with the same metrics
.venv/bin/python scripts/eval_policy.py runs/rl/smoke/model.zip --seeds 30 --styles 0.1 0.5 0.9

# learning curves
.venv/bin/python scripts/plot_training.py runs/rl/smoke --out runs/rl/smoke/training.png
```

The `rl` extra installs CPU PyTorch. On the CUDA machine install the matching PyTorch
build first; the simulator is CPU-bound, so the GPU matters little at this network size.

## Layout

```
dfadrive/
  world.py         routes, agent/world state, conflict-zone geometry   (world facts)
  labels.py        four facts per agent -> one of six symbols          (world facts)
  tasks.py         CROSS, YIELD, GO_FIRST as dfa.DFA; TaskMonitor      (task state)
  style.py         style scalar -> four driving parameters
  policy.py        Policy interface, AgentView, flat observation for networks
  controllers.py   TaskController (world vision), FullVisionController, RouteFollower (blind)
  scenario.py      ScenarioInstance; Scenic and NumPy samplers
  scenarios/unprotected_left.scenic
  sim/metadrive_adapter.py   the only module that imports MetaDrive
  env.py           episode loop: simulator -> facts -> DFAs -> policy views
  recorder.py      one .npz per episode, metadata included
  metrics.py       task outcome, order, post-encroachment time, realised style
  rl/reward.py     per-agent reward: task outcome, DFA-progress shaping, collision, style
  rl/selfplay.py   one simulator, two learners sharing a policy
  rl/sb3.py        the only module that imports Stable-Baselines3 / PyTorch
scripts/           run_episode, run_matrix, run_gap, compare_vision, analyze_vision, make_demo,
                   plot_episode, render_tasks, calibrate_vehicle, train_ppo, eval_policy, plot_training
tests/
```

## Scenarios and how tasks are assigned

Each scenario is one file in [dfadrive/scenarios/](dfadrive/scenarios/): `unprotected_left`
(base), the style probes `tie`, `crossing`, `standing_start` (docs/06), the three-car
`gap` (docs/07), and `three_way` and `four_way` with three and four cars arriving together
(REPORT.md). A file
declares, per car: its route, its **task**, its style, its start speed and its distance
to the conflict zone, as fixed values or ranges to sample from.

A task is assigned by name (`CROSS`, `YIELD`, `GO_FIRST`) in that file, e.g.
`param task_B = "YIELD"`, and can be overridden per run:

```bash
.venv/bin/python scripts/run_episode.py --scenario tie --task-a GO_FIRST --task-b GO_FIRST --style-a 0.9 --style-b 0.1
```

or from Python: `make_sampler(scenario="tie", task_A="GO_FIRST", style_B=0.1).sample(seed)`.
At the start of an episode each car gets a monitor for its own automaton. From then on:

- every car's view holds every car's task state, style and latest command (full vision,
  docs/07). A policy with `vision="world"` uses only its own task state and the others'
  physical state; one with `vision="full"` uses all of it. For a network a task state is a
  one-hot over the nine state names;
- the scripted controller asks its monitor one question, "would this symbol make my task
  unachievable now?", so it works for any automaton over the alphabet;
- during training, one task pairing is drawn per episode from the list given to
  `train_ppo.py --tasks`.

## Reproducibility

- An episode is determined by its `ScenarioInstance` and the controller names; both are
  stored in every recording, together with package versions.
- A seed identifies an episode *within one sampler* (Scenic and NumPy use different
  random streams; the sampler name is recorded).
- A single episode replays bit for bit from a fresh simulator (`make_env(exact=True)`;
  `run_episode.py` always does this). A sweep reuses one simulator, which drifts by
  about 1e-6 m between episodes; the sweep as a whole is still reproducible (same
  command, same order, identical CSV). Details in docs/02.
- MetaDrive is pinned to a commit, not a release; see docs/02 for why.

## Known limits

- Scripted drivers handle any number of cars; learned policies handle exactly two.
- The learned policy controls acceleration only (steering follows the route) and has been
  trained on one task pair with one seed; see docs/05 for what that does and does not show.
- The scripted controller extrapolates the other vehicle at constant speed and does not
  know its task or style.
- "Aggressive" and "conservative" are one axis; the validation shows where that is too coarse.
- The ITSC 2026 reward-machine paper named in the brief could not be found and is not in
  the related-work matrix.
