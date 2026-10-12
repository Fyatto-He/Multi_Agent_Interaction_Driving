"""Policy decisions layer: the interface every policy, scripted or learned, implements.

    world state + task states + styles + latest commands  ->  low-level action

**Vision.** Every agent's view carries everything about every agent (decision D4, revised
2026-10-12): state, task automaton and its current state, style, and the acceleration it
last commanded. How much of that a policy *uses* is the policy's choice:

    "full"   everything
    "world"  the other cars' physical state only; own task and own style

An action is ``[steer, accel]`` in [-1, 1]^2: steer > 0 turns left; accel > 0 is
throttle, accel < 0 is brake.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Protocol

import numpy as np

from .tasks import STATE_VOCAB, TaskMonitor
from .world import ConflictGeometry, VehicleLimits, WorldState, wrap_angle

VISIONS = ("full", "world")


@dataclass(frozen=True)
class AgentView:
    """Everything one agent's policy may condition on at one step."""

    agent: str
    world: WorldState  # every car's physical state
    geometry: ConflictGeometry  # static: routes and conflict zones
    tasks: dict[str, TaskMonitor]  # every car's task monitor; read via .state / .alive / .forbids()
    styles: dict[str, float]  # every car's style
    last_accel: dict[str, float]  # every car's most recent acceleration command, m/s^2
    limits: VehicleLimits

    @property
    def task(self) -> TaskMonitor:
        return self.tasks[self.agent]

    @property
    def style(self) -> float:
        return self.styles[self.agent]


class Policy(Protocol):
    def act(self, view: AgentView) -> np.ndarray: ...


# ------------------------------------------------------------- flat vector for networks

# Fixed scales, not learned statistics, so the vector means the same thing in every run.
_SPEED, _DIST, _ACCEL = 15.0, 50.0, 6.0

_OWN = ("speed", "dist_to_entry", "dist_to_clear", "lateral", "heading_error", "remaining")
_OTHER = ("rel_x", "rel_y", "rel_vx", "rel_vy", "cos_dpsi", "sin_dpsi", "dist_to_entry", "dist_to_clear", "present")
_TASK = tuple(f"state={q}" for q in STATE_VOCAB)


def obs_layout(vision: str = "full") -> tuple[tuple[str, tuple[str, ...]], ...]:
    """Field names of ``flat_observation``, in order, grouped."""
    layout = [("own", _OWN), ("other", _OTHER), ("own_task", _TASK), ("own_style", ("style",))]
    if vision == "full":
        layout += [("other_task", _TASK), ("other_style", ("style",)), ("other_plan", ("last_accel",))]
    return tuple(layout)


def obs_dim(vision: str = "full") -> int:
    return sum(len(names) for _, names in obs_layout(vision))


def flat_observation(view: AgentView, vision: str = "full") -> np.ndarray:
    """Input of a learned policy; ``obs_layout(vision)`` names the fields.

    A DFA state is a one-hot over ``STATE_VOCAB`` (unambiguous across the three tasks). A
    RAD embedding of the task is the drop-in replacement once tasks are sampled from a
    distribution. Two cars only for now: one block describes "the other".
    """
    if vision not in VISIONS:
        raise ValueError(f"vision must be one of {VISIONS}")
    g, me_id = view.geometry, view.agent
    others = view.world.others(me_id)
    if len(others) != 1:
        raise NotImplementedError("learned policies handle exactly two cars for now")
    ot_id = others[0]
    me, ot = view.world.agents[me_id], view.world.agents[ot_id]
    route = g.routes[me_id]

    own = [
        me.speed / _SPEED,
        g.dist_to_entry(me_id, me) / _DIST,
        g.dist_to_clear(me_id, me) / _DIST,
        route.lateral(me.x, me.y) / route.lane_width,
        wrap_angle(me.heading - route.heading(me.s)) / math.pi,
        (route.length - me.s) / (2 * _DIST),
    ]
    c, s = math.cos(me.heading), math.sin(me.heading)
    dx, dy = ot.x - me.x, ot.y - me.y
    dvx = ot.speed * math.cos(ot.heading) - me.speed * c
    dvy = ot.speed * math.sin(ot.heading) - me.speed * s
    dpsi = ot.heading - me.heading
    other = [
        (c * dx + s * dy) / _DIST,
        (-s * dx + c * dy) / _DIST,
        (c * dvx + s * dvy) / _SPEED,
        (-s * dvx + c * dvy) / _SPEED,
        math.cos(dpsi),
        math.sin(dpsi),
        g.dist_to_entry(ot_id, ot) / _DIST,
        g.dist_to_clear(ot_id, ot) / _DIST,
        float(ot.present),
    ]
    one_hot = lambda monitor: [float(monitor.state == q) for q in STATE_VOCAB]
    vec = own + other + one_hot(view.task) + [view.style]
    if vision == "full":
        vec += one_hot(view.tasks[ot_id]) + [view.styles[ot_id], view.last_accel[ot_id] / _ACCEL]
    return np.asarray(vec, dtype=np.float32)
