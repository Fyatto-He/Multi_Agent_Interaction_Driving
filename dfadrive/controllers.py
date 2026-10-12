"""Scripted policies: the reference drivers the learned ones are compared with.

``RouteFollower``         ignores every other car: a negative control that shows whether a
                          scenario really produces a conflict.
``TaskController``        world vision. Realises whatever task its automaton encodes, using
                          only the other cars' physical state. It never looks at a task's
                          name or state names; it asks its monitor which symbols are
                          currently forbidden (``TaskMonitor.forbids``).
``FullVisionController``  full vision. Also reads the other cars' task states and styles,
                          so every car computes the *same* schedule for the intersection
                          from the same information.

All three are pure functions of the ``AgentView``.
"""

from __future__ import annotations

import math

import numpy as np

from .policy import AgentView
from .style import StyleParams, style_params
from .world import AgentState, Route, VehicleLimits, wrap_angle

STOP_GAP = 2.0  # m kept between the front bumper and the conflict zone while waiting
HARD_DECEL = 6.0  # m/s^2 used to decide "I can no longer stop before the zone"
SPEED_GAIN = 2.0  # 1/s, proportional speed tracking
STANDING_SPEED = 0.1  # m/s floor when extrapolating the other: a standing car is far away in time
FOLLOW_GAP = 3.0  # m kept behind a car ahead on the same route when both stand


def steer_along(route: Route, me: AgentState, limits: VehicleLimits) -> float:
    """Pure-pursuit steering toward a look-ahead point on the route."""
    lookahead = min(max(me.speed, 4.0), 10.0)
    tx, ty = route.point(me.s + lookahead)
    alpha = wrap_angle(math.atan2(ty - me.y, tx - me.x) - me.heading)
    delta = math.atan2(2 * limits.wheelbase * math.sin(alpha), lookahead)
    return float(np.clip(delta / limits.max_steer, -1, 1))


def accel_action(accel: float, limits: VehicleLimits) -> float:
    """Desired acceleration in m/s^2 -> normalised throttle (>0) / brake (<0)."""
    scale = limits.accel_per_throttle if accel >= 0 else limits.decel_per_brake
    return float(np.clip(accel / scale, -1, 1))


def track_speed(target: float, me: AgentState, p: StyleParams, limits: VehicleLimits) -> float:
    """Acceleration [m/s^2] that moves the speed toward ``target`` within the style's limits."""
    return float(np.clip(SPEED_GAIN * (target - me.speed), -p.comfort_decel, p.max_accel))


def stop_at(distance: float, me: AgentState, p: StyleParams, limits: VehicleLimits) -> float:
    """Acceleration [m/s^2] that brings the car to rest ``distance`` metres ahead.

    Approaches along a constant-deceleration profile at the style's comfortable braking,
    and brakes as hard as the remaining distance requires if that is not enough.
    """
    if distance <= 0.1:  # at or past the stopping point
        return -limits.max_decel if me.speed > 0.3 else -p.comfort_decel
    accel = track_speed(min(p.cruise_speed, stopping_speed(distance, p.comfort_decel)), me, p, limits)
    required = me.speed**2 / (2 * distance)
    if required >= p.comfort_decel:
        accel = min(accel, -min(required, limits.max_decel))
    return accel


def stopping_speed(distance: float, decel: float) -> float:
    """Highest speed from which one can still stop within ``distance`` at ``decel``."""
    return math.sqrt(2 * decel * max(distance, 0.0))


def travel_time(distance: float, speed: float, cruise: float, accel: float) -> float:
    """Time to cover ``distance`` accelerating from ``speed`` to ``cruise``, then holding."""
    if distance <= 0:
        return 0.0
    speed = min(speed, cruise)
    ramp = (cruise**2 - speed**2) / (2 * accel)
    if ramp >= distance:
        return (-speed + math.sqrt(speed**2 + 2 * accel * distance)) / accel
    return (cruise - speed) / accel + (distance - ramp) / cruise


class RouteFollower:
    """Follow the route at the style's cruise speed. Blind to every other car."""

    vision = "world"

    def act(self, view: AgentView) -> np.ndarray:
        me = view.world.agents[view.agent]
        p = style_params(view.style)
        route = view.geometry.routes[view.agent]
        accel = track_speed(p.cruise_speed, me, p, view.limits)
        return np.array([steer_along(route, me, view.limits), accel_action(accel, view.limits)])


def follow_speed(view: AgentView, p: StyleParams) -> float:
    """Highest speed from which I can still stop behind the car ahead on my route."""
    leader = view.geometry.leader(view.agent, view.world)
    if leader is None:
        return math.inf
    me, ahead = view.world.agents[view.agent], view.world.agents[leader]
    gap = ahead.s - me.s - (ahead.length + me.length) / 2 - FOLLOW_GAP
    return math.sqrt(max(2 * p.comfort_decel * gap + ahead.speed**2, 0.0)) if gap > 0 else 0.0


class TaskController:
    """Route following, car following, and a wait/go decision at the conflict zone.

    World vision: other cars are known by position and speed only, and are extrapolated
    at their current speed.
    """

    vision = "world"

    def act(self, view: AgentView) -> np.ndarray:
        g, me = view.geometry, view.world.agents[view.agent]
        p = style_params(view.style)
        before_zone = not g.occupies(view.agent, me) and g.dist_to_clear(view.agent, me) > 0
        if before_zone and self.should_wait(view, p):
            accel = stop_at(g.dist_to_entry(view.agent, me) - STOP_GAP, me, p, view.limits)
        else:
            accel = track_speed(p.cruise_speed, me, p, view.limits)
        behind = follow_speed(view, p)
        if behind < p.cruise_speed:
            accel = min(accel, track_speed(behind, me, p, view.limits))
        return np.array([steer_along(g.routes[view.agent], me, view.limits), accel_action(accel, view.limits)])

    def should_wait(self, view: AgentView, p: StyleParams) -> bool:
        g, me_id = view.geometry, view.agent
        me, cars = view.world.agents[me_id], view.world.agents
        rivals = [o for o in view.world.others(me_id) if g.conflicts(me_id, o)]

        # 1. Task: my automaton forbids entering now.
        if view.task.forbids("own"):
            return True
        # 2. A zone of mine is occupied.
        if any(g.blocks(me_id, o, cars[o]) for o in rivals):
            return True
        # 3. Physics: too late to stop before the zone, and stopping inside would block it.
        if committed(view, me_id):
            return False
        # 4. One rival at a time; those through the zone, or gone, no longer count.
        ahead = [o for o in rivals if cars[o].present and g.dist_to_clear(o, cars[o]) > 0]
        return any(self.gives_way_to(view, p, o) for o in ahead)

    def gives_way_to(self, view: AgentView, p: StyleParams, other: str) -> bool:
        g, me_id = view.geometry, view.agent
        me, ot = view.world.agents[me_id], view.world.agents[other]
        d_in = g.dist_to_entry(me_id, me)

        # Timing. My own plan is known; the other is extrapolated at its current speed.
        my_in = travel_time(d_in, me.speed, p.cruise_speed, p.max_accel)
        ot_speed = max(ot.speed, STANDING_SPEED)
        ot_in = max(g.dist_to_entry(other, ot), 0.0) / ot_speed
        ot_out = g.dist_to_clear(other, ot) / ot_speed

        # Task: the other entering first would fail my task, so the only question is
        # whether I can still be first. No courtesy margin.
        if view.task.forbids("other"):
            return my_in >= ot_in
        # Style: commit only with the required time margin, either clearly ahead of the
        # other or clearly behind it.
        lead = my_in + p.commit_margin <= ot_in
        follow = ot_out + p.commit_margin <= my_in
        return not (lead or follow)


def committed(view: AgentView, agent: str) -> bool:
    """Can this car no longer stop before its conflict zone?"""
    st = view.world.agents[agent]
    return st.speed > 0.5 and st.speed**2 / (2 * HARD_DECEL) > view.geometry.dist_to_entry(agent, st)


SLOT_BUFFER = 1.0  # s left between one car's planned exit from a zone and the next car's planned entry
SLOT_TOLERANCE = 0.2  # s; a car whose slot starts later than this after its own arrival holds back


def shared_schedule(view: AgentView) -> tuple[dict[str, float], dict[str, float]]:
    """Who may enter when, worked out from what every car can see.

    Returns ``(arrival, slot)``: for each car that currently has a claim, the time from now
    at which it would reach its conflict zone if it drove freely, and the time at which it
    is entitled to enter. Every car computes this from the same information with the same
    rules, so every car gets the same answer.

    Cars are placed in order of priority, each at the earliest time that does not overlap
    the slot of a conflicting car placed before it. Cars whose paths do not cross can
    therefore use the intersection at the same time, and a car is never made to wait for
    one that is itself held up elsewhere unless it would actually get in its way.

    Priority: cars already in a zone or unable to stop; then cars whose task requires them
    to be first; then by *claim* = free arrival time plus the time margin of the car's
    style; ties by agent id. A car whose own task makes it wait holds no claim.
    """
    g, cars = view.geometry, view.world.agents
    arrival, need, priority = {}, {}, {}
    for k, st in cars.items():
        if not st.present or g.dist_to_clear(k, st) <= 0:
            continue  # through the zone, or gone
        inside, task = g.occupies(k, st), view.tasks[k]
        if task.forbids("own") and not inside:
            continue
        p = style_params(view.styles[k])
        t_in = 0.0 if inside else travel_time(max(g.dist_to_entry(k, st), 0.0), st.speed, p.cruise_speed, p.max_accel)
        t_out = travel_time(max(g.dist_to_clear(k, st), 0.0), st.speed, p.cruise_speed, p.max_accel)
        must_lead = task.forbids("other")
        fixed = inside or committed(view, k)
        arrival[k], need[k] = t_in, max(t_out - t_in, 0.0)
        priority[k] = (not fixed, not must_lead, t_in + (0.0 if must_lead else p.commit_margin), k)

    slot: dict[str, float] = {}
    for k in sorted(arrival, key=priority.get):
        start, moved = arrival[k], True
        fixed_k = not priority[k][0]
        while moved:
            moved = False
            for j, s_j in slot.items():
                if not g.conflicts(k, j):
                    continue
                e_j = s_j + need[j] + SLOT_BUFFER
                overlap = start < e_j and s_j < start + need[k] + SLOT_BUFFER
                # A car that must be first is not merely kept undelayed: nobody who can
                # still stop may slip in ahead of it.
                behind_leader = not priority[j][1] and not fixed_k and start < e_j
                if overlap or behind_leader:
                    start, moved = e_j, True
        slot[k] = start
    return arrival, slot


class FullVisionController(TaskController):
    """As ``TaskController``, but precedence comes from a schedule all cars share.

    Each car sees every car's position, speed, task state and style, works out
    ``shared_schedule``, and holds back only if its own slot starts later than it would
    arrive. Nobody has to guess what the others will do, and two cars cannot both conclude
    "I go first".
    """

    vision = "full"

    def should_wait(self, view: AgentView, p: StyleParams) -> bool:
        g, me_id = view.geometry, view.agent
        cars = view.world.agents
        rivals = [o for o in view.world.others(me_id) if g.conflicts(me_id, o)]
        if view.task.forbids("own"):  # my automaton forbids entering now
            return True
        if any(g.blocks(me_id, o, cars[o]) for o in rivals):  # safety net: never enter an occupied zone
            return True
        if committed(view, me_id):
            return False
        arrival, slot = shared_schedule(view)
        return slot[me_id] > arrival[me_id] + SLOT_TOLERANCE


CONTROLLERS = {"task": TaskController, "full": FullVisionController, "blind": RouteFollower}
