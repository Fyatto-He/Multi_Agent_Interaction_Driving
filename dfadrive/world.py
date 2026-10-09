"""World facts layer, part 1: simulator-agnostic geometry and state.

Nothing in this module knows about tasks, automata, policies, or MetaDrive.
Coordinates are metres in a right-handed frame; headings are radians, counter-clockwise
from +x; arclength ``s`` is measured along an agent's own route centreline.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from functools import cached_property

import numpy as np
from shapely import affinity
from shapely.geometry import LineString, Point, Polygon, box


def wrap_angle(a: float) -> float:
    return (a + math.pi) % (2 * math.pi) - math.pi


@dataclass(frozen=True, eq=False)
class Route:
    """An agent's intended path: lane centreline as a polyline, plus the lane width."""

    points: np.ndarray  # (N, 2)
    lane_width: float

    @cached_property
    def line(self) -> LineString:
        return LineString(self.points)

    @property
    def length(self) -> float:
        return self.line.length

    def project(self, x: float, y: float) -> float:
        """Arclength of the route point closest to (x, y)."""
        return self.line.project(Point(x, y))

    def point(self, s: float) -> np.ndarray:
        p = self.line.interpolate(min(max(s, 0.0), self.length))
        return np.array([p.x, p.y])

    def heading(self, s: float, eps: float = 0.25) -> float:
        a, b = self.point(s - eps), self.point(s + eps)
        return math.atan2(b[1] - a[1], b[0] - a[0])

    def lateral(self, x: float, y: float) -> float:
        """Signed offset from the centreline, positive to the left of travel."""
        s = self.project(x, y)
        p, h = self.point(s), self.heading(s)
        return -math.sin(h) * (x - p[0]) + math.cos(h) * (y - p[1])

    @cached_property
    def corridor(self) -> Polygon:
        return self.line.buffer(self.lane_width / 2, cap_style="flat")


@dataclass(frozen=True)
class AgentState:
    x: float
    y: float
    heading: float
    speed: float
    length: float
    width: float
    s: float  # arclength of the vehicle centre along its own route
    collided: bool = False  # in contact with another vehicle
    off_road: bool = False
    arrived: bool = False  # reached the end of its route
    active: bool = True  # still being simulated and controlled

    @property
    def present(self) -> bool:
        """Physically on the road. A wreck stays present; an arrived vehicle is gone."""
        return not self.arrived

    def footprint(self) -> Polygon:
        rect = box(-self.length / 2, -self.width / 2, self.length / 2, self.width / 2)
        rect = affinity.rotate(rect, self.heading, origin=(0, 0), use_radians=True)
        return affinity.translate(rect, self.x, self.y)


@dataclass(frozen=True)
class WorldState:
    """Full, shared world state at one time step."""

    t: float
    agents: dict[str, AgentState]

    def other(self, agent: str) -> str:
        (other,) = (a for a in self.agents if a != agent)
        return other


@dataclass(frozen=True)
class VehicleLimits:
    """What a controller needs to turn physical commands into normalised actions.

    Supplied by the simulator adapter; the numbers are properties of the simulated car.
    """

    wheelbase: float  # m
    max_steer: float  # rad at steer action = 1
    accel_per_throttle: float  # m/s^2 at throttle action = 1 (linear below that)
    decel_per_brake: float  # m/s^2 per unit of brake action, until tyres saturate
    max_decel: float  # m/s^2, tyre limit


@dataclass(frozen=True, eq=False)
class ConflictGeometry:
    """Static geometry of a two-agent conflict: both routes and the zone they share.

    The conflict zone is the overlap of the two lane corridors. It is derived from route
    geometry alone, so it means the same thing in any simulator.
    """

    routes: dict[str, Route]
    zone: Polygon
    entry_s: dict[str, float]  # arclength at which each route's lane first reaches the zone
    exit_s: dict[str, float]  # ... and at which it has fully left it

    @classmethod
    def from_routes(cls, routes: dict[str, Route]) -> "ConflictGeometry":
        if len(routes) != 2:
            raise ValueError("this prototype handles exactly two agents")
        a, b = routes.values()
        overlap = a.corridor.intersection(b.corridor)
        parts = [g for g in getattr(overlap, "geoms", [overlap]) if g.geom_type == "Polygon"]
        if not parts or max(p.area for p in parts) < 1.0:
            raise ValueError("the two routes do not conflict")
        zone = max(parts, key=lambda p: p.area)
        # Project the whole zone, not just the centreline crossing: the zone is skewed when
        # the routes cross obliquely, and a lane-wide vehicle meets its corner first.
        entry, exit_ = {}, {}
        for name, route in routes.items():
            ss = [route.project(x, y) for x, y in zone.exterior.coords]
            entry[name], exit_[name] = min(ss), max(ss)
        return cls(routes=dict(routes), zone=zone, entry_s=entry, exit_s=exit_)

    def dist_to_entry(self, agent: str, state: AgentState) -> float:
        """Front bumper to zone entry along the route; negative once the front is past it."""
        return self.entry_s[agent] - (state.s + state.length / 2)

    def dist_to_clear(self, agent: str, state: AgentState) -> float:
        """Rear bumper to zone exit along the route; negative once the vehicle has cleared."""
        return self.exit_s[agent] - (state.s - state.length / 2)

    def occupies(self, state: AgentState) -> bool:
        """Does the vehicle's footprint overlap the conflict zone?"""
        return state.present and state.footprint().intersects(self.zone)
