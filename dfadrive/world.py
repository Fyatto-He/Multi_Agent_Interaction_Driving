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
from shapely.ops import unary_union


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

    def others(self, agent: str) -> list[str]:
        return [a for a in self.agents if a != agent]


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
    """Static geometry of the conflicts between any number of routes.

    Two routes that cross share a *conflict zone*: the overlap of their lane corridors.
    Two cars on the same route share no zone; they follow each other. Everything is
    derived from route geometry alone, so it means the same thing in any simulator.

    Each agent has one stretch of conflict along its own route, from ``entry_s`` to
    ``exit_s``: the union of the zones it takes part in.
    """

    routes: dict[str, Route]
    zones: dict[frozenset, Polygon]  # {a, b} -> zone, for crossing pairs only
    own_zone: dict[str, Polygon]  # union of the zones each agent takes part in
    entry_s: dict[str, float]  # arclength at which each route's lane first reaches its zone
    exit_s: dict[str, float]  # ... and at which it has fully left it

    @classmethod
    def from_routes(cls, routes: dict[str, Route]) -> "ConflictGeometry":
        names, zones = list(routes), {}
        for i, a in enumerate(names):
            for b in names[i + 1 :]:
                if _same_lane(routes[a], routes[b]):
                    continue
                overlap = routes[a].corridor.intersection(routes[b].corridor)
                parts = [g for g in getattr(overlap, "geoms", [overlap]) if g.geom_type == "Polygon"]
                if parts and max(p.area for p in parts) >= 1.0:
                    zones[frozenset((a, b))] = max(parts, key=lambda p: p.area)
        if not zones:
            raise ValueError("the routes do not conflict")
        own, entry, exit_ = {}, {}, {}
        for name, route in routes.items():
            mine = [z for pair, z in zones.items() if name in pair]
            if not mine:
                raise ValueError(f"agent {name} conflicts with nobody")
            own[name] = unary_union(mine)
            # Project the whole zone, not just the centreline crossing: a zone is skewed
            # when routes cross obliquely, and a lane-wide vehicle meets its corner first.
            ss = [route.project(x, y) for z in mine for x, y in z.exterior.coords]
            entry[name], exit_[name] = min(ss), max(ss)
        return cls(routes=dict(routes), zones=zones, own_zone=own, entry_s=entry, exit_s=exit_)

    @cached_property
    def zone(self) -> Polygon:
        """All zones together, for drawing."""
        return unary_union(list(self.zones.values())).convex_hull

    def dist_to_entry(self, agent: str, state: AgentState) -> float:
        """Front bumper to zone entry along the route; negative once the front is past it."""
        return self.entry_s[agent] - (state.s + state.length / 2)

    def dist_to_clear(self, agent: str, state: AgentState) -> float:
        """Rear bumper to zone exit along the route; negative once the vehicle has cleared."""
        return self.exit_s[agent] - (state.s - state.length / 2)

    def occupies(self, agent: str, state: AgentState) -> bool:
        """Does this agent's footprint overlap a conflict zone of its own?"""
        return state.present and state.footprint().intersects(self.own_zone[agent])

    def conflicts(self, a: str, b: str) -> bool:
        return frozenset((a, b)) in self.zones

    def blocks(self, agent: str, other: str, other_state: AgentState) -> bool:
        """Is ``other`` inside the zone it shares with ``agent``?"""
        zone = self.zones.get(frozenset((agent, other)))
        return zone is not None and other_state.present and other_state.footprint().intersects(zone)

    def leader(self, agent: str, world: WorldState) -> str | None:
        """The nearest car ahead of ``agent`` on the same route, if any."""
        me, best = world.agents[agent], None
        for other in world.others(agent):
            st = world.agents[other]
            if st.present and _same_lane(self.routes[agent], self.routes[other]) and st.s > me.s:
                if best is None or st.s < world.agents[best].s:
                    best = other
        return best


def _same_lane(a: Route, b: Route) -> bool:
    return a is b or (a.points.shape == b.points.shape and bool(np.allclose(a.points, b.points)))
