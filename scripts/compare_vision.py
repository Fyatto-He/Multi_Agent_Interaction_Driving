"""Paired comparison of scripted drivers with world vision and with full vision.

Every scenario instance is driven twice, once by ``TaskController`` (each car sees the
others' motion only) and once by ``FullVisionController`` (each car also sees the others'
task state, style and latest command). Same cars, same start, same tasks, same styles:
the only difference is what the drivers are allowed to know.

    # two cars: every scenario x task pairing x style pair
    python scripts/compare_vision.py --name two_car --scenarios unprotected_left tie crossing standing_start \\
        --tasks CROSS:CROSS GO_FIRST:GO_FIRST GO_FIRST:CROSS CROSS:GO_FIRST CROSS:YIELD --styles 0.1 0.5 0.9 --seeds 10

    # three and four cars: tasks from the scenario file, styles sampled per car
    python scripts/compare_vision.py --name multi_car --scenarios three_way four_way --seeds 150

Writes runs/<name>/episodes.csv: one row per (instance, vision).
"""

import argparse
import csv
import itertools
import time
from pathlib import Path

from dfadrive.metrics import episode_metrics, flatten
from dfadrive.run import make_env, run_episode
from dfadrive.scenario import SCENARIOS, make_sampler

VISIONS = {"world": "task", "full": "full"}  # vision -> scripted controller


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--name", required=True)
    ap.add_argument("--scenarios", nargs="+", choices=SCENARIOS, required=True)
    ap.add_argument("--tasks", nargs="+", help="two-car scenarios only: pairings A:B (default: the scenario's own tasks)")
    ap.add_argument("--styles", type=float, nargs="+", help="two-car scenarios only: grid of style pairs (default: sampled)")
    ap.add_argument("--seeds", type=int, default=50)
    args = ap.parse_args()

    pairs = [tuple(p.split(":")) for p in args.tasks] if args.tasks else [None]
    styles = list(itertools.product(args.styles, args.styles)) if args.styles else [None]
    out = Path("runs") / args.name
    out.mkdir(parents=True, exist_ok=True)
    env, rows, start = make_env(), [], time.time()
    for scenario, pair, style in itertools.product(args.scenarios, pairs, styles):
        fixed = {}
        if pair:
            fixed.update(task_A=pair[0], task_B=pair[1])
        if style:
            fixed.update(style_A=style[0], style_B=style[1])
        sampler = make_sampler("scenic", scenario, **fixed)
        for seed in range(args.seeds):
            instance = sampler.sample(seed)
            for vision, controller in VISIONS.items():
                m = flatten(episode_metrics(run_episode(env, instance, controller)))
                rows.append(dict(
                    vision=vision,
                    tasks=":".join(spec.task for spec in instance.agents.values()),
                    styles=":".join(f"{spec.style:.2f}" for spec in instance.agents.values()),
                    cars=len(instance.agents), **m,
                ))  # fmt: skip
    env.close()

    fields = list(dict.fromkeys(k for row in rows for k in row))  # scenarios differ in their columns
    with open(out / "episodes.csv", "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields, restval="")
        writer.writeheader()
        writer.writerows(rows)
    print(f"{len(rows)} episodes ({len(rows) // 2} paired instances) in {time.time() - start:.0f} s -> {out}/episodes.csv")


if __name__ == "__main__":
    main()
