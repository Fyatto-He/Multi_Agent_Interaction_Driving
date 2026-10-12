"""Three-car style probe: does the yielding car take the gap between two priority cars?

    python scripts/run_gap.py --name gap --controllers task full --seeds 10

Sweeps the yielder's style and the headway between the two priority cars (their styles
are held at 0.5). Writes runs/<name>/episodes.csv and summary.md.
"""

import argparse
import csv
import itertools
import time
from pathlib import Path

from dfadrive.metrics import episode_metrics, flatten
from dfadrive.run import make_env, run_episode
from dfadrive.scenario import make_sampler


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--name", default="gap")
    ap.add_argument("--controllers", nargs="+", choices=("task", "full"), default=["task", "full"])
    ap.add_argument("--styles", type=float, nargs="+", default=[0.1, 0.5, 0.9], help="styles of the yielding car B")
    ap.add_argument("--headways", type=float, nargs="+", default=[2.0, 3.0, 4.0, 5.0, 6.0], help="seconds between A1 and A2")
    ap.add_argument("--seeds", type=int, default=10)
    args = ap.parse_args()

    out = Path("runs") / args.name
    out.mkdir(parents=True, exist_ok=True)
    env, rows, start = make_env(), [], time.time()
    for controller, style, headway in itertools.product(args.controllers, args.styles, args.headways):
        sampler = make_sampler("scenic", "gap", style_B=style, style_A1=0.5, style_A2=0.5, headway=headway)
        for seed in range(args.seeds):
            m = episode_metrics(run_episode(env, sampler.sample(seed), controller))
            order = m["order"].split(">")
            took_gap = "B" in order and "A2" in order and order.index("B") < order.index("A2")
            rows.append(dict(controller=controller, style_B=style, took_gap=took_gap, **flatten(m)))
    env.close()

    with open(out / "episodes.csv", "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    lines = [f"# {args.name}: {len(rows)} episodes, three cars, B must yield\n"]
    for controller in args.controllers:
        lines += [f"\n## controller = {controller}: share of episodes in which B goes between A1 and A2\n",
                  "| B's style | " + " | ".join(f"headway {h:g} s" for h in args.headways) + " | all accepted | collisions |",
                  "|---|" + "---|" * (len(args.headways) + 2)]  # fmt: skip
        for style in args.styles:
            g = [r for r in rows if r["controller"] == controller and r["style_B"] == style]
            cells = [[r for r in g if r["headway"] == h] for h in args.headways]
            ok = sum(all(r[f"{a}_outcome"] == "accepted" for a in ("A1", "A2", "B")) for r in g)
            lines.append(f"| {style:g} | " + " | ".join(f"{100 * sum(r['took_gap'] for r in c) / len(c):.0f}%" for c in cells)
                         + f" | {ok}/{len(g)} | {sum(r['collision'] for r in g)} |")  # fmt: skip
    (out / "summary.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))
    print(f"\n{len(rows)} episodes in {time.time() - start:.0f} s -> {out}/")


if __name__ == "__main__":
    main()
