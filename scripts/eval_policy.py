"""Evaluate a trained policy with the same recorder and metrics as the scripted controllers.

    python scripts/eval_policy.py runs/rl/smoke/model.zip --seeds 50
    python scripts/eval_policy.py runs/rl/smoke/model.zip --tasks CROSS:YIELD YIELD:CROSS --styles 0.1 0.9

Both agents run the learned policy (deterministic actions). Scenario seeds start at
1,000,000 so they do not overlap with training. Prints the learned policy next to the
scripted TaskController on identical scenarios and writes eval.md and eval_episodes.csv
next to the model.
"""

import argparse
import csv
import itertools
import json
from pathlib import Path

from dfadrive.metrics import episode_metrics, flatten, summary_table
from dfadrive.rl.sb3 import LearnedPolicy
from dfadrive.run import make_env, run_episode
from dfadrive.scenario import SCENARIOS, make_sampler

FIRST_SEED = 1_000_000


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("model", type=Path)
    ap.add_argument("--seeds", type=int, default=50)
    ap.add_argument("--scenario", choices=SCENARIOS, default="unprotected_left")
    ap.add_argument("--out", default="eval", help="file stem for the report and CSV next to the model")
    ap.add_argument("--arrival-offset", type=float, help="fix the nominal t_B - t_A at the conflict zone [s]")
    ap.add_argument("--tasks", nargs="+", help="pairs A:B (default: the pairs the model was trained on)")
    ap.add_argument("--styles", type=float, nargs="+", help="fix both styles to each combination (default: sampled)")
    ap.add_argument("--save-episodes", type=int, default=0, help="save this many learned-policy episodes per cell")
    args = ap.parse_args()

    config = json.loads((args.model.parent / "config.json").read_text())
    pairs = [tuple(p.split(":")) for p in (args.tasks or config["tasks"])]
    learned = LearnedPolicy(args.model, longitudinal_only=config["selfplay"]["longitudinal_only"])
    styles = list(itertools.product(args.styles, args.styles)) if args.styles else [(None, None)]

    env, rows = make_env(), []
    for (task_a, task_b), (style_a, style_b) in itertools.product(pairs, styles):
        fixed = dict(style_A=style_a, style_B=style_b, arrival_offset=args.arrival_offset)
        fixed = {k: v for k, v in fixed.items() if v is not None}
        sampler = make_sampler(config["selfplay"]["sampler"], args.scenario, task_A=task_a, task_B=task_b, **fixed)
        cell = f"{style_a:g}:{style_b:g}" if args.styles else "sampled"
        for k in range(args.seeds):
            instance = sampler.sample(FIRST_SEED + k)
            for label, controller in (("learned", learned), ("scripted", "task")):
                episode = run_episode(env, instance, controller)
                rows.append(dict(policy=label, tasks=f"{task_a}:{task_b}", styles=cell, **flatten(episode_metrics(episode))))
                if label == "learned" and k < args.save_episodes:
                    episode.save(args.model.parent / "episodes" / f"{args.scenario}_{task_a}-{task_b}_{cell.replace(':', '-')}_seed{k}.npz")
    env.close()

    by = ("policy", "tasks", "styles") if args.styles else ("policy", "tasks")
    report = f"# Evaluation of {args.model} on {args.scenario} ({args.seeds} held-out scenarios per cell)\n\n{summary_table(rows, by)}\n"
    (args.model.parent / f"{args.out}.md").write_text(report)
    with open(args.model.parent / f"{args.out}_episodes.csv", "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    print(report)


if __name__ == "__main__":
    main()
