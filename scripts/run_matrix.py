"""Validation matrix: every task pair x style pair x seed, with scripted controllers.

    python scripts/run_matrix.py --name validation --seeds 20
    python scripts/run_matrix.py --name blind --controller blind --tasks CROSS:CROSS --seeds 60

Writes runs/<name>/episodes.csv (one row per episode) and runs/<name>/summary.md.
"""

import argparse
import csv
import itertools
import math
import time
from collections import Counter
from pathlib import Path

from dfadrive.metrics import episode_metrics, flatten
from dfadrive.run import make_env, run_episode
from dfadrive.scenario import make_sampler
from dfadrive.tasks import TASKS


def summarise(rows: list[dict], by: tuple[str, ...]) -> str:
    groups: dict[tuple, list[dict]] = {}
    for r in rows:
        groups.setdefault(tuple(r[k] for k in by), []).append(r)
    pct = lambda xs: f"{100 * sum(xs) / len(xs):.0f}%"
    head = [*by, "n", "both accepted", "A outcome", "B outcome", "collision", "timeout", "A first", "median PET [s]", "min gap [m]"]
    lines = ["| " + " | ".join(head) + " |", "|" + "---|" * len(head)]
    for key, g in groups.items():
        outcome = lambda agent: ", ".join(f"{k} {v}" for k, v in Counter(r[f"{agent}_outcome"] for r in g).most_common())
        pets = sorted(r["pet"] for r in g if not math.isnan(r["pet"]))
        gaps = [r["min_gap"] for r in g if not math.isnan(r["min_gap"])]
        entered = [r for r in g if r["first_in_zone"]]
        lines.append("| " + " | ".join([
            *map(str, key), str(len(g)),
            pct([r["A_outcome"] == r["B_outcome"] == "accepted" for r in g]),
            outcome("A"), outcome("B"),
            pct([r["collision"] for r in g]), pct([r["timeout"] for r in g]),
            pct([r["first_in_zone"] == "A" for r in entered]) if entered else "–",
            f"{pets[len(pets) // 2]:.1f}" if pets else "–",
            f"{min(gaps):.2f}" if gaps else "–",
        ]) + " |")  # fmt: skip
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--name", default="validation")
    ap.add_argument("--seeds", type=int, default=20)
    ap.add_argument("--styles", type=float, nargs="+", default=[0.1, 0.9])
    ap.add_argument("--tasks", nargs="+", help="pairs like CROSS:YIELD (default: all nine)")
    ap.add_argument("--controller", choices=("task", "blind"), default="task")
    ap.add_argument("--sampler", choices=("auto", "scenic", "python"), default="auto")
    ap.add_argument("--save-trajectories", action="store_true")
    ap.add_argument("--exact", action="store_true", help="fresh simulator per episode; leaks memory, only for short runs")
    args = ap.parse_args()

    pairs = [tuple(p.split(":")) for p in args.tasks] if args.tasks else list(itertools.product(TASKS, TASKS))
    out = Path("runs") / args.name
    out.mkdir(parents=True, exist_ok=True)
    env, rows, start = make_env(exact=args.exact), [], time.time()
    for (task_a, task_b), style_a, style_b in itertools.product(pairs, args.styles, args.styles):
        sampler = make_sampler(args.sampler, task_A=task_a, task_B=task_b, style_A=style_a, style_B=style_b)
        for seed in range(args.seeds):
            episode = run_episode(env, sampler.sample(seed), args.controller)
            rows.append(dict(tasks=f"{task_a}:{task_b}", styles=f"{style_a:g}:{style_b:g}", **flatten(episode_metrics(episode))))
            if args.save_trajectories:
                episode.save(out / "episodes" / f"{task_a}-{task_b}_{style_a:g}-{style_b:g}_seed{seed}.npz")
    env.close()

    with open(out / "episodes.csv", "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    summary = (
        f"# {args.name}: {len(rows)} episodes, controller = {args.controller}\n\n"
        f"## By task pair (A:B)\n\n{summarise(rows, ('tasks',))}\n\n"
        f"## By task pair and style pair (A:B)\n\n{summarise(rows, ('tasks', 'styles'))}\n"
    )
    (out / "summary.md").write_text(summary)
    print(summary)
    print(f"{len(rows)} episodes in {time.time() - start:.0f} s -> {out}/")


if __name__ == "__main__":
    main()
