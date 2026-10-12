"""Summarise the world-vision / full-vision comparison (docs/results/vision/*.csv).

    python scripts/analyze_vision.py

Writes docs/results/vision/summary.md and docs/figures/vision_delay.png.
Every instance was driven once per vision, so all differences are paired.
"""

import csv
import math
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).parent.parent
DATA = ROOT / "docs" / "results" / "vision"
COLOR = {"world": "#2a78d6", "full": "#eb6834"}  # reference palette, as in plot_episode.py
INK, INK2, MUTED, GRID, AXIS, SURFACE = "#0b0b0b", "#52514e", "#898781", "#e1e0d9", "#c3c2b7", "#fcfcfb"

GROUPS = [  # label, scenario filter, task filter
    ("2 cars, order fixed by the tasks", None, {"CROSS:YIELD"}),
    ("2 cars, one must go first", None, {"GO_FIRST:CROSS", "CROSS:GO_FIRST"}),
    ("2 cars, both must go first", None, {"GO_FIRST:GO_FIRST"}),
    ("2 cars, order open", None, {"CROSS:CROSS"}),
    ("3 cars, gap between two priority cars", {"gap"}, None),
    ("3 cars from three arms, order open", {"three_way"}, None),
    ("4 cars from four arms, order open", {"four_way"}, None),
]


def load():
    rows = []
    for name in ("two_car", "multi_car"):
        rows += list(csv.DictReader(open(DATA / f"{name}_episodes.csv")))
    for r in csv.DictReader(open(DATA / "gap_episodes.csv")):  # run_gap.py names the controller, not the vision
        r.update(vision={"task": "world", "full": "full"}[r["controller"]], tasks="CROSS:CROSS:YIELD",
                 styles=f"0.50:0.50:{float(r['style_B']):.2f}/{r['headway']}")  # fmt: skip
        rows.append(r)
    return rows


def pairs(rows, scenarios, tasks):
    keep = [r for r in rows if (scenarios is None or r["scenario"] in scenarios) and (tasks is None or r["tasks"] in tasks)]
    if scenarios is None:
        keep = [r for r in keep if r["cars"] == "2"]
    key = lambda r: (r["scenario"], r["tasks"], r["styles"], r["seed"])
    world = {key(r): r for r in keep if r["vision"] == "world"}
    full = {key(r): r for r in keep if r["vision"] == "full"}
    return [(world[k], full[k]) for k in world if k in full]


def num(r, k):
    return float(r[k]) if r[k] not in ("", "nan") else math.nan


def ci(diffs, rng):
    """Mean and 95% bootstrap interval of paired differences."""
    d = np.asarray(diffs)
    boot = rng.choice(d, size=(4000, len(d)), replace=True).mean(axis=1)
    return d.mean(), np.percentile(boot, 2.5), np.percentile(boot, 97.5)


def main():
    rows, rng = load(), np.random.default_rng(0)
    table = ["| Situation | Instances | All tasks done, world / full | Collisions, world / full | Total delay, world | Total delay, full | "
             "Saved by full vision (95% interval) | Full better / worse | Time standing, world / full |",
             "|---|---|---|---|---|---|---|---|---|"]  # fmt: skip
    bars = []
    for label, scenarios, tasks in GROUPS:
        ps = pairs(rows, scenarios, tasks)
        done = [(w, f) for w, f in ps if not math.isnan(num(w, "total_delay")) and not math.isnan(num(f, "total_delay"))]
        dw, df = [num(w, "total_delay") for w, _ in done], [num(f, "total_delay") for _, f in done]
        diff = [a - b for a, b in zip(dw, df)]
        mean, lo, hi = ci(diff, rng)
        acc = lambda i: sum(p[i]["all_accepted"] == "True" for p in ps)
        col = lambda i: sum(p[i]["collision"] == "True" for p in ps)
        stand = lambda i: np.mean([num(p[i], "total_standing") for p in ps])
        better, worse = sum(x > 0.5 for x in diff) / len(diff), sum(x < -0.5 for x in diff) / len(diff)
        table.append(f"| {label} | {len(ps)} | {acc(0)} / {acc(1)} | {col(0)} / {col(1)} | {np.mean(dw):.1f} s | {np.mean(df):.1f} s | "
                     f"**{mean:.1f} s** ({lo:.1f} to {hi:.1f}) | {better:.0%} / {worse:.0%} | {stand(0):.1f} / {stand(1):.1f} s |")  # fmt: skip
        bars.append((label, np.mean(dw), np.mean(df)))
    note = ("\nTotal delay: summed over the cars, time to reach the goal minus the time the same car would need on an empty road. "
            "Computed over instances in which every car reached its goal under both visions. 'Better / worse': full vision saves / costs "
            "more than 0.5 s. 'All tasks done' is zero by construction when both cars must go first.\n")  # fmt: skip
    (DATA / "summary.md").write_text("# World vision against full vision: paired comparison\n\n" + "\n".join(table) + "\n" + note)
    print("\n".join(table))

    fig, ax = plt.subplots(figsize=(8.6, 4.2), facecolor=SURFACE)
    y = np.arange(len(bars))[::-1]
    for k, (vision, offset) in enumerate((("world", 0.19), ("full", -0.19))):
        values = [b[1 + k] for b in bars]
        ax.barh(y + offset, values, height=0.34, color=COLOR[vision], label=f"{vision} vision")
        for yi, v in zip(y + offset, values):
            ax.text(v + 0.25, yi, f"{v:.1f}", va="center", fontsize=8, color=INK)
    ax.set_yticks(y, [b[0] for b in bars], fontsize=9, color=INK)
    ax.set_xlabel("mean total delay per episode [s], all cars together", fontsize=9, color=INK2)
    ax.set_facecolor(SURFACE)
    for side in ("top", "right", "left"):
        ax.spines[side].set_visible(False)
    ax.spines["bottom"].set_color(AXIS)
    ax.tick_params(colors=MUTED, labelsize=8, length=0)
    ax.tick_params(axis="y", labelcolor=INK)
    ax.grid(axis="x", color=GRID, linewidth=0.6)
    ax.set_axisbelow(True)
    ax.legend(frameon=False, fontsize=9, labelcolor=INK, loc="upper right")
    ax.set_title("Delay with and without shared state (same cars, same starts)", fontsize=10, color=INK, loc="left")
    out = ROOT / "docs" / "figures" / "vision_delay.png"
    fig.savefig(out, dpi=150, bbox_inches="tight", facecolor=SURFACE)
    print(out)


if __name__ == "__main__":
    main()
