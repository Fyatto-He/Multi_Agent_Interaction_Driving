"""Run and record one episode.

    python scripts/run_episode.py --seed 0
    python scripts/run_episode.py --seed 3 --task-a GO_FIRST --task-b GO_FIRST --style-a 0.9 --style-b 0.9
    python scripts/run_episode.py --seed 0 --controller blind
"""

import argparse
import json
from pathlib import Path

from dfadrive.metrics import episode_metrics
from dfadrive.run import make_env, run_episode
from dfadrive.scenario import SCENARIOS, make_sampler
from dfadrive.tasks import TASKS


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--scenario", choices=SCENARIOS, default="unprotected_left")
    ap.add_argument("--sampler", choices=("auto", "scenic", "python"), default="auto")
    ap.add_argument("--controller", choices=("task", "full", "blind"), default="task")
    ap.add_argument("--task-a", choices=TASKS), ap.add_argument("--task-b", choices=TASKS)
    ap.add_argument("--style-a", type=float), ap.add_argument("--style-b", type=float)
    ap.add_argument("--arrival-offset", type=float, help="nominal t_B - t_A at the conflict zone [s]")
    ap.add_argument("--out", type=Path, default=Path("runs/episodes"))
    args = ap.parse_args()

    names = ("task_A", "task_B", "style_A", "style_B", "arrival_offset")
    values = (args.task_a, args.task_b, args.style_a, args.style_b, args.arrival_offset)
    overrides = {k: v for k, v in zip(names, values) if v is not None}

    instance = make_sampler(args.sampler, args.scenario, **overrides).sample(args.seed)
    env = make_env(exact=True)  # a single episode: always bit-for-bit replayable
    episode = run_episode(env, instance, args.controller)
    env.close()

    tasks = "-".join(spec.task for spec in instance.agents.values())
    prefix = "" if args.scenario == "unprotected_left" else f"{args.scenario}_"
    path = episode.save(args.out / f"{prefix}{tasks}_{args.controller}_seed{args.seed}.npz")
    print(json.dumps(episode_metrics(episode), indent=2))
    for agent in episode.agents:
        states, t = episode.data[agent]["dfa_state"], episode.t
        trace = [f"{t[i]:.1f}s {states[i]}" for i in range(len(t)) if i == 0 or states[i] != states[i - 1]]
        print(f"{agent} [{instance.agents[agent].task}]: " + " -> ".join(trace))
    print(f"saved {path}")


if __name__ == "__main__":
    main()
