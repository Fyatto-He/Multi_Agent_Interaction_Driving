"""Draw one recorded episode: top-down paths, approach to the conflict zone, DFA states.

    python scripts/plot_episode.py runs/episodes/CROSS-YIELD_task_seed0.npz
"""

import argparse
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from shapely.geometry import LineString

from dfadrive.recorder import Episode

# Reference palette of the dataviz guide (validated pair): colour carries agent identity only.
COLOR = {"A": "#2a78d6", "B": "#eb6834"}
INK, INK2, MUTED, GRID, AXIS, SURFACE, ZONE = "#0b0b0b", "#52514e", "#898781", "#e1e0d9", "#c3c2b7", "#fcfcfb", "#e1e0d9"


def _style(ax, grid=True):
    ax.set_facecolor(SURFACE)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color(AXIS)
    ax.tick_params(colors=MUTED, labelsize=8, length=0)
    if grid:
        ax.grid(color=GRID, linewidth=0.6)
        ax.set_axisbelow(True)


def plot(ep: Episode, path: Path) -> Path:
    inst, t = ep.instance, ep.t
    fig = plt.figure(figsize=(11, 5.6), facecolor=SURFACE)
    grid = fig.add_gridspec(2, 2, width_ratios=[1, 1.25], height_ratios=[1.6, 1], hspace=0.42, wspace=0.16)
    ax_map, ax_dist, ax_dfa = fig.add_subplot(grid[:, 0]), fig.add_subplot(grid[0, 1]), fig.add_subplot(grid[1, 1])

    # --- top-down view
    _style(ax_map, grid=False)
    zone = np.asarray(ep.meta["zone"])
    for agent in ep.agents:
        lane = LineString(ep.meta["routes"][agent]).buffer(ep.meta["lane_width"][agent] / 2, cap_style="flat")
        ax_map.fill(*lane.exterior.xy, color=GRID, linewidth=0, zorder=1)
    ax_map.fill(*zone.T, color=MUTED, alpha=0.45, linewidth=0, zorder=2)
    for agent in ep.agents:
        d = ep.data[agent]
        on_road = ~d["at_goal"].astype(bool)
        ax_map.plot(d["x"][on_road], d["y"][on_road], color=COLOR[agent], linewidth=2, zorder=3)
        ticks = on_road & (np.arange(len(t)) % 10 == 0)  # one marker per second
        ax_map.scatter(d["x"][ticks], d["y"][ticks], s=26, color=COLOR[agent], edgecolor=SURFACE, linewidth=1.2, zorder=4)
        ax_map.annotate(f"{agent} start", (d["x"][0], d["y"][0]), xytext=(0, 9), textcoords="offset points",
                        ha="center", fontsize=9, color=INK)  # fmt: skip
    cx, cy = zone.mean(axis=0)
    ax_map.annotate("conflict zone", (cx, cy), xytext=(-58, 44), textcoords="offset points", ha="center", fontsize=8,
                    color=INK2, arrowprops=dict(arrowstyle="-", color=MUTED, linewidth=0.8))  # fmt: skip
    ax_map.set_xlim(cx - 48, cx + 48), ax_map.set_ylim(cy - 48, cy + 48)
    ax_map.set_aspect("equal")
    ax_map.set_xlabel("x [m]", fontsize=8, color=INK2), ax_map.set_ylabel("y [m]", fontsize=8, color=INK2)
    ax_map.set_title("Paths (one dot per second)", fontsize=10, color=INK, loc="left")

    # --- approach to the conflict zone
    _style(ax_dist)
    ax_dist.axhline(0, color=AXIS, linewidth=1)
    for row, agent in enumerate(ep.agents):
        d = ep.data[agent]
        ax_dist.plot(t, d["dist_to_entry"], color=COLOR[agent], linewidth=2, label=f"{agent}: {inst.agents[agent].task}, style {inst.agents[agent].style:.2f}")
        inside = d["own_in_cz"].astype(bool)
        if inside.any():
            ax_dist.axvspan(t[inside][0], t[inside][-1], color=COLOR[agent], alpha=0.14, linewidth=0)
            ax_dist.annotate(f"{agent} in zone", (t[inside][0], 0.12 - 0.07 * row), xycoords=("data", "axes fraction"),
                             xytext=(-4, 0), textcoords="offset points", ha="right", va="center", fontsize=8, color=INK2)  # fmt: skip
    ax_dist.set_ylim(-15, None), ax_dist.set_xlim(0, t[-1])
    ax_dist.set_ylabel("front bumper to zone [m]", fontsize=8, color=INK2)
    ax_dist.legend(frameon=False, fontsize=8, labelcolor=INK, loc="upper right", bbox_to_anchor=(1, 0.86))
    ax_dist.set_title("Approach to the conflict zone", fontsize=10, color=INK, loc="left")

    # --- task state per agent
    _style(ax_dfa, grid=False)
    for row, agent in enumerate(ep.agents):
        states = ep.data[agent]["dfa_state"]
        edges = [0] + [i for i in range(1, len(t)) if states[i] != states[i - 1]] + [len(t) - 1]
        for k, (i, j) in enumerate(zip(edges[:-1], edges[1:])):
            ax_dfa.barh(row, t[j] - t[i], left=t[i], height=0.5, color=COLOR[agent], alpha=0.25 + 0.2 * (k % 2), linewidth=0)
            if t[j] - t[i] > 0.8:
                ax_dfa.text((t[i] + t[j]) / 2, row, str(states[i]), ha="center", va="center", fontsize=8, color=INK)
        ax_dfa.text(t[-1] + 0.2, row, str(states[-1]), ha="left", va="center", fontsize=8, color=INK, fontweight="bold")
    ax_dfa.set_yticks(range(len(ep.agents)), [f"{a} ({inst.agents[a].task})" for a in ep.agents], color=INK, fontsize=8)
    ax_dfa.set_ylim(-0.6, len(ep.agents) - 0.4), ax_dfa.invert_yaxis(), ax_dfa.set_xlim(0, t[-1])
    ax_dfa.set_xlabel("time [s]", fontsize=8, color=INK2)
    ax_dfa.set_title("Task automaton state", fontsize=10, color=INK, loc="left")

    fig.suptitle(f"{inst.name}, seed {inst.seed} ({inst.sampler} sampler), controllers: "
                 + ", ".join(sorted(set(ep.meta["controllers"].values()))), fontsize=11, color=INK, x=0.02, ha="left")  # fmt: skip
    fig.savefig(path, dpi=150, bbox_inches="tight", facecolor=SURFACE)
    plt.close(fig)
    return path


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("episode", type=Path)
    ap.add_argument("--out", type=Path)
    args = ap.parse_args()
    print(plot(Episode.load(args.episode), args.out or args.episode.with_suffix(".png")))


if __name__ == "__main__":
    main()
