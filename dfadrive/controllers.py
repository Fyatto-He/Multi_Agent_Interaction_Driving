"""Scripted policies used to validate the architecture before any learning.

``RouteFollower``  ignores the other agent: a negative control that shows whether the
                   scenario really produces a conflict.
``TaskController`` realises whatever task its automaton encodes. It never looks at the
                   task's name or state names; it asks the monitor which symbols are
                   currently forbidden (``TaskMonitor.forbids``) and combines that with
                   its style. It is a pure function of the ``AgentView``.
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
    """Follow the route at the style's cruise speed. Blind to the other agent."""

    def act(self, view: AgentView) -> np.ndarray:
        me = view.world.agents[view.agent]
        p = style_params(view.style)
        route = view.geometry.routes[view.agent]
        accel = track_speed(p.cruise_speed, me, p, view.limits)
        return np.array([steer_along(route, me, view.limits), accel_action(accel, view.limits)])


class TaskController:
    """Route following plus a wait/go decision at the conflict zone."""

    def act(self, view: AgentView) -> np.ndarray:
        g, me = view.geometry, view.world.agents[view.agent]
        p = style_params(view.style)
        before_zone = not g.occupies(me) and g.dist_to_clear(view.agent, me) > 0
        if before_zone and self.should_wait(view, p):
            accel = stop_at(g.dist_to_entry(view.agent, me) - STOP_GAP, me, p, view.limits)
        else:
            accel = track_speed(p.cruise_speed, me, p, view.limits)
        return np.array([steer_along(g.routes[view.agent], me, view.limits), accel_action(accel, view.limits)])

    @staticmethod
    def should_wait(view: AgentView, p: StyleParams) -> bool:
        g, task = view.geometry, view.task
        me_id, ot_id = view.agent, view.world.other(view.agent)
        me, ot = view.world.agents[me_id], view.world.agents[ot_id]
        d_in = g.dist_to_entry(me_id, me)

        # 1. Task: my automaton forbids entering now.
        if task.forbids("own"):
            return True
        # 2. The zone is occupied.
        if g.occupies(ot):
            return True
        # 3. Physics: too late to stop before the zone, and stopping inside would block it.
        if me.speed**2 / (2 * HARD_DECEL) > d_in:
            return False
        # 4. The other is no longer a factor (through the zone, or gone).
        ot_d_in, ot_d_clear = g.dist_to_entry(ot_id, ot), g.dist_to_clear(ot_id, ot)
        if not ot.present or ot_d_clear <= 0:
            return False

        # 5. Timing. My own plan is known; the other is extrapolated at its current speed.
        my_in = travel_time(d_in, me.speed, p.cruise_speed, p.max_accel)
        ot_speed = max(ot.speed, STANDING_SPEED)
        ot_in, ot_out = max(ot_d_in, 0.0) / ot_speed, ot_d_clear / ot_speed

        # Task: the other entering first would fail my task, so the only question is
        # whether I can still be first. No courtesy margin.
        if task.forbids("other"):
            return my_in >= ot_in
        # Style: commit only with the required time margin, either clearly ahead of the
        # other or clearly behind it.
        lead = my_in + p.commit_margin <= ot_in
        follow = ot_out + p.commit_margin <= my_in
        return not (lead or follow)


CONTROLLERS = {"task": TaskController, "blind": RouteFollower}
