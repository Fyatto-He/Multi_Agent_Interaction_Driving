"""Plot task acceptance during training, one panel per run.

    python scripts/plot_training.py runs/rl/smoke_first_attempt runs/rl/smoke \
        --titles "gamma 0.99, shaping 0.2" "gamma 0.995, shaping 1.0, entropy 0.005" --out docs/figures/rl_smoke_training.png
"""

import argparse
import csv
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

# Same reference palette as plot_episode.py; colour carries the task identity only.
PALETTE = ("#2a78d6", "#eb6834", "#1baf7a", "#eda100")
INK, INK2, MUTED, GRID, AXIS, SURFACE = "#0b0b0b", "#52514e", "#898781", "#e1e0d9", "#c3c2b7", "#fcfcfb"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("runs", type=Path, nargs="+")
    ap.add_argument("--titles", nargs="+")
    ap.add_argument("--out", type=Path, default=Path("training.png"))
    args = ap.parse_args()

    fig, axes = plt.subplots(1, len(args.runs), figsize=(5.2 * len(args.runs), 3.4), sharey=True, facecolor=SURFACE, squeeze=False)
    for k, (ax, run) in enumerate(zip(axes[0], args.runs)):
        rows = list(csv.DictReader(open(run / "progress.csv")))
        steps = [float(r["time/total_timesteps"]) / 1e6 for r in rows]
        tasks = sorted(c[len("task/") : -len("_accepted")] for c in rows[0] if c.startswith("task/") and c.endswith("_accepted"))
        for colour, task in zip(PALETTE, tasks):
            rate = [float(r[f"task/{task}_accepted"] or "nan") for r in rows]
            ax.plot(steps, rate, color=colour, linewidth=2, label=task)
        ax.set_facecolor(SURFACE)
        for side in ("top", "right"):
            ax.spines[side].set_visible(False)
        for side in ("left", "bottom"):
            ax.spines[side].set_color(AXIS)
        ax.tick_params(colors=MUTED, labelsize=8, length=0)
        ax.grid(color=GRID, linewidth=0.6)
        ax.set_axisbelow(True)
        ax.set_ylim(-0.03, 1.03), ax.set_xlim(0, steps[-1])
        ax.legend(frameon=False, fontsize=8, labelcolor=INK, loc="center right")
        ax.set_xlabel("agent-steps [millions]", fontsize=8, color=INK2)
        ax.set_title(args.titles[k] if args.titles else run.name, fontsize=10, color=INK, loc="left")
    axes[0][0].set_ylabel("share of recent episodes accepted", fontsize=8, color=INK2)
    fig.savefig(args.out, dpi=150, bbox_inches="tight", facecolor=SURFACE)
    print(args.out)


if __name__ == "__main__":
    main()
