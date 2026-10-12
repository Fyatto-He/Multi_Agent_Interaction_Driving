"""Validation matrix: every task pair x style pair x seed, with scripted controllers.

    python scripts/run_matrix.py --name validation --seeds 20
    python scripts/run_matrix.py --name blind --controller blind --tasks CROSS:CROSS --seeds 60

Writes runs/<name>/episodes.csv (one row per episode) and runs/<name>/summary.md.
"""

import argparse
import csv
import itertools
import time
from pathlib import Path

from dfadrive.metrics import episode_metrics, flatten, summary_table
from dfadrive.run import make_env, run_episode
from dfadrive.scenario import SCENARIOS, make_sampler
from dfadrive.tasks import TASKS


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--name", default="validation")
    ap.add_argument("--seeds", type=int, default=20)
    ap.add_argument("--styles", type=float, nargs="+", default=[0.1, 0.9])
    ap.add_argument("--tasks", nargs="+", help="pairs like CROSS:YIELD (default: all nine)")
    ap.add_argument("--scenario", choices=SCENARIOS, default="unprotected_left")
    ap.add_argument("--arrival-offset", type=float, help="fix the nominal t_B - t_A at the conflict zone [s]")
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
        fixed = {} if args.arrival_offset is None else dict(arrival_offset=args.arrival_offset)
        sampler = make_sampler(args.sampler, args.scenario, task_A=task_a, task_B=task_b, style_A=style_a, style_B=style_b, **fixed)
        for seed in range(args.seeds):
            episode = run_episode(env, sampler.sample(seed), args.controller)
            rows.append(dict(scenario=args.scenario, tasks=f"{task_a}:{task_b}", styles=f"{style_a:g}:{style_b:g}", **flatten(episode_metrics(episode))))
            if args.save_trajectories:
                episode.save(out / "episodes" / f"{task_a}-{task_b}_{style_a:g}-{style_b:g}_seed{seed}.npz")
    env.close()

    with open(out / "episodes.csv", "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    summary = (
        f"# {args.name}: {len(rows)} episodes, scenario = {args.scenario}, controller = {args.controller}\n\n"
        f"## By task pair (A:B)\n\n{summary_table(rows, ('tasks',))}\n\n"
        f"## By task pair and style pair (A:B)\n\n{summary_table(rows, ('tasks', 'styles'))}\n"
    )
    (out / "summary.md").write_text(summary)
    print(summary)
    print(f"{len(rows)} episodes in {time.time() - start:.0f} s -> {out}/")


if __name__ == "__main__":
    main()
