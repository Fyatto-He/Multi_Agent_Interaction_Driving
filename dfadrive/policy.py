"""Policy decisions layer: the interface every policy, scripted or learned, implements.

    world state + own DFA state + own style  ->  low-level action

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


@dataclass(frozen=True)
class AgentView:
    """Everything one agent's policy may condition on at one step."""

    agent: str
    world: WorldState  # full, shared
    geometry: ConflictGeometry  # static: routes and conflict zone
    task: TaskMonitor  # own task only; read via .state / .alive / .forbids()
    style: float  # own style only
    limits: VehicleLimits


class Policy(Protocol):
    def act(self, view: AgentView) -> np.ndarray: ...


# ------------------------------------------------------------- flat vector for networks

# Fixed scales, not learned statistics, so the vector means the same thing in every run.
_SPEED, _DIST = 15.0, 50.0

OBS_LAYOUT = (
    ("own", ("speed", "dist_to_entry", "dist_to_clear", "lateral", "heading_error", "remaining")),
    ("other", ("rel_x", "rel_y", "rel_vx", "rel_vy", "cos_dpsi", "sin_dpsi", "dist_to_entry", "dist_to_clear", "present")),
    ("task", tuple(f"state={q}" for q in STATE_VOCAB)),
    ("style", ("style",)),
)
OBS_DIM = sum(len(names) for _, names in OBS_LAYOUT)


def flat_observation(view: AgentView) -> np.ndarray:
    """The proposed input of a learned policy; see ``OBS_LAYOUT`` for the field order.

    Own DFA state is a one-hot over ``STATE_VOCAB`` (unambiguous across the three tasks).
    A RAD embedding of ``view.task`` is the drop-in replacement once tasks are sampled
    from a distribution rather than picked from three.
    """
    g, me_id = view.geometry, view.agent
    ot_id = view.world.other(me_id)
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
    task = [float(view.task.state == q) for q in STATE_VOCAB]
    return np.asarray(own + other + task + [view.style], dtype=np.float32)
