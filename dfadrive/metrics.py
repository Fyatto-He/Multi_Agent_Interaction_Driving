"""Per-episode metrics, computed from a recorded ``Episode`` only.

Task outcome (per agent)   accepted / rejected / unfinished, final DFA state
Interaction                who entered the conflict zone first, post-encroachment time,
                           minimum bumper-to-bumper gap
Realised style (per agent) mean speed, peak acceleration and braking, time spent standing
                           before the zone. Reported from the trajectory, so a style
                           setting is never assumed to have been achieved.
"""

from __future__ import annotations

import math
from collections import Counter

import numpy as np
from shapely import affinity
from shapely.geometry import box

from .recorder import Episode
from .tasks import ACC, REJ

VEHICLE = (4.515, 1.852)  # length, width; only used for the gap metric


def _first(mask: np.ndarray, t: np.ndarray) -> float:
    return float(t[np.argmax(mask)]) if mask.any() else float("nan")


def _last(mask: np.ndarray, t: np.ndarray) -> float:
    return float(t[len(mask) - 1 - np.argmax(mask[::-1])]) if mask.any() else float("nan")


def _footprint(x, y, h):
    rect = box(-VEHICLE[0] / 2, -VEHICLE[1] / 2, VEHICLE[0] / 2, VEHICLE[1] / 2)
    return affinity.translate(affinity.rotate(rect, h, origin=(0, 0), use_radians=True), x, y)


def agent_metrics(ep: Episode, agent: str) -> dict:
    d, t, dt = ep.data[agent], ep.t, ep.meta["dt"]
    final = str(d["dfa_state"][-1])
    live = d["active"].astype(bool)
    accel = np.diff(d["speed"]) / dt
    accel = accel[live[1:]] if live[1:].any() else np.zeros(1)
    approaching = d["dist_to_entry"] > 0
    free = live & (d["dist_to_clear"] < 0)  # past the zone: only the driver's preference limits speed
    return dict(
        task=ep.meta["instance"]["agents"][agent]["task"],
        style=ep.meta["instance"]["agents"][agent]["style"],
        outcome={ACC: "accepted", REJ: "rejected"}.get(final, "unfinished"),
        final_state=final,
        crashed=bool(d["crashed"].any()),
        t_enter=_first(d["own_in_cz"], t),
        t_exit=_last(d["own_in_cz"], t),
        t_goal=_first(d["at_goal"], t),
        mean_speed=float(d["speed"][live].mean()),
        free_speed=float(d["speed"][free].mean()) if free.any() else float("nan"),
        max_accel=float(accel.max()),
        max_decel=float(-accel.min()),
        wait_time=float(((d["speed"] < 0.3) & approaching & live).sum() * dt),
    )


def episode_metrics(ep: Episode) -> dict:
    a, b = ep.agents
    per_agent = {k: agent_metrics(ep, k) for k in (a, b)}
    enter = {k: m["t_enter"] for k, m in per_agent.items()}
    entered = {k: v for k, v in enter.items() if not np.isnan(v)}
    first = min(entered, key=entered.get) if entered else None
    second = b if first == a else a

    # Post-encroachment time: gap between the first vehicle leaving the conflict zone and
    # the second entering it. Negative means both were inside at once.
    pet = float("nan")
    if first and second in entered:
        pet = per_agent[second]["t_enter"] - per_agent[first]["t_exit"]

    both = ep.data[a]["active"].astype(bool) | ep.data[b]["active"].astype(bool)
    gaps = [
        _footprint(*(ep.data[a][k][i] for k in ("x", "y", "heading"))).distance(
            _footprint(*(ep.data[b][k][i] for k in ("x", "y", "heading")))
        )
        for i in np.flatnonzero(both)
        if not (ep.data[a]["at_goal"][i] or ep.data[b]["at_goal"][i])
    ]
    return dict(
        seed=ep.meta["instance"]["seed"],
        arrival_offset=ep.meta["instance"]["arrival_offset"],
        duration=float(ep.t[-1]),
        timeout=bool(ep.meta.get("timeout", False)),
        collision=any(m["crashed"] for m in per_agent.values()),
        first_in_zone=first or "",
        pet=pet,
        min_gap=float(min(gaps)) if gaps else float("nan"),
        agents=per_agent,
    )


def flatten(m: dict) -> dict:
    """One flat row per episode, for CSV tables."""
    row = {k: v for k, v in m.items() if k != "agents"}
    for agent, am in m["agents"].items():
        row.update({f"{agent}_{k}": v for k, v in am.items()})
    return row


def summary_table(rows: list[dict], by: tuple[str, ...]) -> str:
    """Markdown table of outcomes, grouping flattened episode rows by the columns in ``by``."""
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
