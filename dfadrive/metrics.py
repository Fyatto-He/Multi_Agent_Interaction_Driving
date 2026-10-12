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

from .controllers import travel_time
from .recorder import Episode
from .style import style_params
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
    # Delay: time to the goal minus the time this car would need on an empty road, driving
    # as its style prefers (accelerate to its cruise speed and hold it).
    style, arrived = ep.meta["instance"]["agents"][agent]["style"], d["at_goal"].astype(bool)
    delay = float("nan")
    if arrived.any():
        p, i = style_params(style), int(np.argmax(arrived))
        delay = float(t[i]) - travel_time(float(d["s"][i] - d["s"][0]), float(d["speed"][0]), p.cruise_speed, p.max_accel)
    return dict(
        task=ep.meta["instance"]["agents"][agent]["task"],
        style=ep.meta["instance"]["agents"][agent]["style"],
        outcome={ACC: "accepted", REJ: "rejected"}.get(final, "unfinished"),
        final_state=final,
        crashed=bool(d["crashed"].any()),
        t_enter=_first(d["own_in_cz"], t),
        t_exit=_last(d["own_in_cz"], t),
        t_goal=_first(d["at_goal"], t),
        delay=delay,
        mean_speed=float(d["speed"][live].mean()),
        free_speed=float(d["speed"][free].mean()) if free.any() else float("nan"),
        max_accel=float(accel.max()),
        max_decel=float(-accel.min()),
        wait_time=float(((d["speed"] < 0.3) & approaching & live).sum() * dt),
    )


def episode_metrics(ep: Episode) -> dict:
    agents = ep.agents
    per_agent = {k: agent_metrics(ep, k) for k in agents}
    entered = sorted((m["t_enter"], k) for k, m in per_agent.items() if not np.isnan(m["t_enter"]))
    order = [k for _, k in entered]
    pairs = [(a, b) for i, a in enumerate(agents) for b in agents[i + 1 :]]
    conflicts = [tuple(c) for c in ep.meta.get("conflicts", pairs)]

    # Post-encroachment time: gap between one vehicle leaving a conflict zone and the
    # next one entering it. Negative means both were inside at once. Smallest over pairs.
    pets = []
    for a, b in conflicts:
        if a in order and b in order:
            first, second = (a, b) if order.index(a) < order.index(b) else (b, a)
            pets.append(per_agent[second]["t_enter"] - per_agent[first]["t_exit"])

    def gap(a: str, b: str, i: int) -> float:
        fa = _footprint(*(ep.data[a][k][i] for k in ("x", "y", "heading")))
        return fa.distance(_footprint(*(ep.data[b][k][i] for k in ("x", "y", "heading"))))

    gaps = [
        gap(a, b, i)
        for a, b in pairs
        for i in np.flatnonzero(ep.data[a]["active"].astype(bool) | ep.data[b]["active"].astype(bool))
        if not (ep.data[a]["at_goal"][i] or ep.data[b]["at_goal"][i])
    ]
    instance = ep.meta["instance"]
    return dict(
        scenario=instance["name"],
        seed=instance["seed"],
        arrival_offset=instance["arrival_offset"],
        **instance.get("extra", {}),
        duration=float(ep.t[-1]),
        timeout=bool(ep.meta.get("timeout", False)),
        collision=any(m["crashed"] for m in per_agent.values()),
        all_accepted=all(m["outcome"] == "accepted" for m in per_agent.values()),
        # Sums over cars; NaN unless every car reached its goal.
        total_delay=float(sum(m["delay"] for m in per_agent.values())),
        max_delay=float(max(m["delay"] for m in per_agent.values())),
        total_standing=float(sum(m["wait_time"] for m in per_agent.values())),
        hard_brakes=sum(m["max_decel"] > 4.0 for m in per_agent.values()),
        clear_time=float(max(m["t_exit"] for m in per_agent.values())),  # last car out of the conflict area
        first_in_zone=order[0] if order else "",
        order=">".join(order),
        pet=float(min(pets)) if pets else float("nan"),
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
