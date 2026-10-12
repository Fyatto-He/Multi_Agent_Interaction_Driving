"""Side-by-side animation: the same situation driven with world vision and with full vision.

    python scripts/make_demo.py --scenario four_way --seed 1 --out docs/figures/demo_four_way.gif

Left: each car sees only where the others are and how fast they move.
Right: each car also sees the others' task state and style, and all follow one shared schedule.
"""

import argparse
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.animation import FuncAnimation, PillowWriter
from matplotlib.patches import Polygon as Patch
from shapely.geometry import LineString

from dfadrive.metrics import VEHICLE, episode_metrics
from dfadrive.run import make_env, run_episode
from dfadrive.scenario import SCENARIOS, make_sampler

PALETTE = ("#2a78d6", "#eb6834", "#1baf7a", "#eda100")  # one colour per car, same in both panels
INK, INK2, MUTED, GRID, SURFACE = "#0b0b0b", "#52514e", "#898781", "#e1e0d9", "#fcfcfb"
PANELS = (("task", "World vision: cars see each other's motion only"),
          ("full", "Full vision: cars also share task state and style"))  # fmt: skip


def corners(x, y, heading):
    length, width = VEHICLE
    box = np.array([[-length / 2, -width / 2], [length / 2, -width / 2], [length / 2, width / 2], [-length / 2, width / 2]])
    c, s = np.cos(heading), np.sin(heading)
    return box @ np.array([[c, s], [-s, c]]) + (x, y)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--scenario", choices=SCENARIOS, default="four_way")
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--out", type=Path, default=Path("docs/figures/demo_four_way.gif"))
    ap.add_argument("--fps", type=int, default=8)
    args = ap.parse_args()

    instance = make_sampler("scenic", args.scenario).sample(args.seed)
    env = make_env()
    episodes = [run_episode(env, instance, controller) for controller, _ in PANELS]
    env.close()
    metrics = [episode_metrics(ep) for ep in episodes]
    steps = max(len(ep.t) for ep in episodes)
    frames = list(range(0, steps, 2)) + [steps - 1] * (2 * args.fps)  # hold the last frame for two seconds

    fig, axes = plt.subplots(1, 2, figsize=(9.6, 5.2), facecolor=SURFACE)
    fig.subplots_adjust(left=0.02, right=0.98, top=0.86, bottom=0.10, wspace=0.04)
    cars, labels, notes = [], [], []
    zone = np.asarray(episodes[0].meta["zone"])
    cx, cy = zone.mean(axis=0)
    for ax, ep, (_, title) in zip(axes, episodes, PANELS):
        ax.set_facecolor(SURFACE)
        ax.set_aspect("equal")
        ax.set_xlim(cx - 32, cx + 32), ax.set_ylim(cy - 32, cy + 32)
        ax.set_xticks([]), ax.set_yticks([])
        for side in ax.spines.values():
            side.set_visible(False)
        for agent in ep.agents:
            lane = LineString(ep.meta["routes"][agent]).buffer(ep.meta["lane_width"][agent] / 2, cap_style="flat")
            ax.fill(*lane.exterior.xy, color=GRID, linewidth=0, zorder=1)
        ax.fill(*zone.T, color=MUTED, alpha=0.35, linewidth=0, zorder=2)
        ax.set_title(title, fontsize=10, color=INK, loc="left")
        cars.append({a: ax.add_patch(Patch(corners(0, 0, 0), closed=True, color=PALETTE[i % 4], zorder=4)) for i, a in enumerate(ep.agents)})
        labels.append({a: ax.text(0, 0, a, fontsize=8, color=INK, ha="center", va="center", zorder=5) for a in ep.agents})
        notes.append(ax.text(0.02, 0.03, "", transform=ax.transAxes, fontsize=9, color=INK2, va="bottom"))
    styles = ", ".join(f"{a} {spec.style:.1f}" for a, spec in instance.agents.items())
    clock = fig.text(0.02, 0.95, "", fontsize=11, color=INK)
    fig.text(0.98, 0.95, f"{args.scenario}, seed {args.seed}. Style (0 cautious, 1 aggressive): {styles}", fontsize=8, color=INK2, ha="right")

    def draw(step):
        clock.set_text(f"t = {step * episodes[0].meta['dt']:.1f} s")
        for ep, m, car, label, note in zip(episodes, metrics, cars, labels, notes):
            i = min(step, len(ep.t) - 1)
            for agent in ep.agents:
                d = ep.data[agent]
                visible = not d["at_goal"][i]
                car[agent].set_visible(visible), label[agent].set_visible(visible)
                car[agent].set_xy(corners(d["x"][i], d["y"][i], d["heading"][i]))
                label[agent].set_position((d["x"][i], d["y"][i] + 4.0))
            waiting = sum(ep.data[a]["speed"][i] < 0.3 and ep.data[a]["dist_to_entry"][i] > 0 for a in ep.agents)
            if step * ep.meta["dt"] >= m["clear_time"]:
                note.set_text(f"intersection clear after {m['clear_time']:.1f} s   total delay {m['total_delay']:.1f} s")
            else:
                note.set_text(f"cars standing: {waiting}")
        return []

    FuncAnimation(fig, draw, frames=frames, blit=False).save(args.out, writer=PillowWriter(fps=args.fps), dpi=90)
    plt.close(fig)
    for (_, title), m in zip(PANELS, metrics):
        print(f"{title}: order {m['order']}, clear after {m['clear_time']:.1f} s, total delay {m['total_delay']:.1f} s, collision {m['collision']}")
    print(args.out, f"{args.out.stat().st_size / 1e6:.1f} MB")


if __name__ == "__main__":
    main()
