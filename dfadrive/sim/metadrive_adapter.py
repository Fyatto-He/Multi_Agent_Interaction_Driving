"""The only module that imports MetaDrive.

Turns a ``ScenarioInstance`` into a two-agent episode on MetaDrive's procedural four-way
intersection and reports plain ``WorldState`` objects. MetaDrive's frame is already
right-handed with counter-clockwise headings and "positive steer = left", so no
conversion is needed.

Intersection layout (one lane per direction, arms listed counter-clockwise):

                 N
                 |
          W ---- + ---- E        from arm i:  right -> i+1, straight -> i+2, left -> i+3
                 |
                 S
"""

from __future__ import annotations

import logging
import math
from dataclasses import replace

import numpy as np
from metadrive.envs.marl_envs import MultiAgentIntersectionEnv

from ..scenario import AgentSpec, ScenarioInstance
from ..world import AgentState, ConflictGeometry, Route, VehicleLimits, WorldState

ARMS = ("W", "S", "E", "N")
TURN = {"right": 1, "straight": 2, "left": 3}

# Measured on MetaDrive main@85e5dad, default vehicle, dt = 0.1 s (scripts/calibrate_vehicle.py):
# acceleration is linear in throttle and independent of speed up to 15 m/s; braking is
# linear in the brake command until the tyres saturate near 9.8 m/s^2.
ACCEL_PER_THROTTLE = 2.91
DECEL_PER_BRAKE = 27.3
MAX_DECEL = 9.8
VEHICLE_LENGTH = 4.515  # m, MetaDrive default vehicle


def _inbound(arm: str) -> tuple[str, str]:
    k = ARMS.index(arm) - 1
    return (">>", ">>>") if arm == "W" else (f"-1X{k}_1_", f"-1X{k}_0_")


def _outbound(arm: str) -> tuple[str, str]:
    k = ARMS.index(arm) - 1
    return ("->>>", "->>") if arm == "W" else (f"1X{k}_0_", f"1X{k}_1_")


def route_nodes(entry: str, manoeuvre: str) -> list[str]:
    """Road-network nodes of a route: inbound lane, connector, outbound lane."""
    exit_arm = ARMS[(ARMS.index(entry) + TURN[manoeuvre]) % 4]
    return [*_inbound(entry), *_outbound(exit_arm)]


class MetaDriveIntersection:
    def __init__(self, arm_length: float = 70.0, dt: float = 0.1, max_steps: int = 600, exact: bool = False):
        """``exact`` rebuilds the simulator at every reset.

        MetaDrive replays an episode bit for bit only from a fresh engine; a reused engine
        carries about 1e-6 m of physics state from the previous episode. Use ``exact`` to
        replay single episodes, not for sweeps: every rebuild leaks about 4 MB and the
        process slows down (measured: 0.24 -> 0.32 s/episode over 100 episodes).
        """
        self.arm_length, self.dt, self.max_steps, self.exact = arm_length, dt, max_steps, exact
        self._env: MultiAgentIntersectionEnv | None = None
        self._names: dict[str, str] = {}  # our agent id -> MetaDrive agent id
        self._vehicles: dict[str, object] = {}  # our agent id -> MetaDrive vehicle
        self._routes: dict[tuple[str, str], Route] = {}
        self._approach_length: dict[tuple[str, str], float] = {}
        self._last: dict[str, AgentState] = {}
        self._steps = 0
        self.geometry: ConflictGeometry | None = None
        self.limits: VehicleLimits | None = None

    # ------------------------------------------------------------------ lifecycle

    def reset(self, instance: ScenarioInstance) -> WorldState:
        self._names = {name: f"agent{i}" for i, name in enumerate(instance.agents)}
        if self.exact:
            self.close()
        if self._env is None:
            self._build(instance)
        routes = {name: self._route(spec.route) for name, spec in instance.agents.items()}
        self.geometry = ConflictGeometry.from_routes(routes)

        # MetaDrive reads per-agent spawn settings from the spawn manager at every reset.
        spawn = self._env.engine.spawn_manager._init_agent_configs
        for name, spec in instance.agents.items():
            spawn[self._names[name]].update(self._spawn_config(name, spec))
        self._env.reset()

        self._vehicles = {name: self._env.agents[md] for name, md in self._names.items()}
        vehicle = next(iter(self._vehicles.values()))
        self.limits = VehicleLimits(
            wheelbase=vehicle.FRONT_WHEELBASE + vehicle.REAR_WHEELBASE,
            max_steer=math.radians(vehicle.max_steering),
            accel_per_throttle=ACCEL_PER_THROTTLE,
            decel_per_brake=DECEL_PER_BRAKE,
            max_decel=MAX_DECEL,
        )
        self._steps, self._last = 0, {}
        return self._observe({})

    def step(self, actions: dict[str, np.ndarray]) -> WorldState:
        """Advance one time step. Actions are needed only for agents that are still active."""
        live = {self._names[a]: np.asarray(u, dtype=float) for a, u in actions.items() if self._last[a].active}
        infos = {}
        if live:
            *_, infos = self._env.step(live)
        self._steps += 1
        return self._observe(infos)

    def close(self) -> None:
        if self._env is not None:
            self._env.close()
            self._env = None
            self._routes.clear()

    def render(self, **kwargs):
        """Top-down frame as an RGB array (no window)."""
        return self._env.render(mode="topdown", window=False, **kwargs)

    # ------------------------------------------------------------------ internals

    def _build(self, instance: ScenarioInstance) -> None:
        no_sensor = dict(num_lasers=0, distance=0)
        self._env = MultiAgentIntersectionEnv(
            dict(
                num_agents=len(instance.agents),
                allow_respawn=False,
                use_render=False,
                log_level=logging.CRITICAL,
                map_config=dict(exit_length=self.arm_length, lane_num=1),
                physics_world_step_size=0.02,
                decision_repeat=round(self.dt / 0.02),
                horizon=self.max_steps + 10,  # our own step limit ends episodes first
                crash_done=True,
                out_of_road_done=True,
                delay_done=self.max_steps + 10,  # a wreck stays where it is
                vehicle_config=dict(
                    lidar=dict(num_others=0, **no_sensor), side_detector=no_sensor, lane_line_detector=no_sensor
                ),
                agent_configs={self._names[n]: self._lane_config(s) for n, s in instance.agents.items()},
            )
        )
        self._env.reset()  # builds the map; vehicles are placed again in reset()

    @staticmethod
    def _lane_config(spec: AgentSpec) -> dict:
        nodes = route_nodes(*spec.route)
        return dict(spawn_lane_index=(nodes[0], nodes[1], 0), destination=nodes[3])

    def _route(self, key: tuple[str, str]) -> Route:
        if key not in self._routes:
            graph = self._env.current_map.road_network.graph
            nodes = route_nodes(*key)
            lanes = [graph[a][b][0] for a, b in zip(nodes[:-1], nodes[1:])]
            pts = [
                lane.position(float(s), 0.0)
                for lane in lanes
                for s in np.linspace(0, lane.length, max(2, round(lane.length / 0.5)), endpoint=False)
            ]
            pts.append(lanes[-1].position(lanes[-1].length, 0.0))
            self._routes[key] = Route(np.asarray(pts, dtype=float), lane_width=float(lanes[0].width))
            self._approach_length[key] = float(lanes[0].length)
        return self._routes[key]

    def _spawn_config(self, name: str, spec: AgentSpec) -> dict:
        """Place the vehicle so its front bumper is ``distance_to_conflict`` from the zone."""
        length = VEHICLE_LENGTH
        s = self.geometry.entry_s[name] - spec.distance_to_conflict - length / 2
        lo, hi = length / 2, self._approach_length[spec.route]
        if not lo <= s <= hi:
            entry = self.geometry.entry_s[name]
            raise ValueError(
                f"agent {name}: distance_to_conflict={spec.distance_to_conflict:.1f} m is off the approach lane; "
                f"allowed {entry - hi - length / 2:.1f}..{entry - lo - length / 2:.1f} m"
            )
        return dict(
            **self._lane_config(spec),
            _specified_spawn_lane=True,
            spawn_longitude=float(s),
            spawn_lateral=0.0,
            spawn_velocity=[spec.initial_speed, 0.0],
            spawn_velocity_car_frame=True,
        )

    def _observe(self, infos: dict) -> WorldState:
        agents = {}
        for name, md in self._names.items():
            prev, info = self._last.get(name), infos.get(md, {})
            if prev is not None and not prev.active:
                agents[name] = prev  # finished earlier: frozen at its last state
            elif info.get("arrive_dest", False):
                # MetaDrive removes an arrived vehicle inside step(); keep its previous pose.
                agents[name] = replace(prev, arrived=True, active=False)
            else:
                vehicle = self._vehicles[name]
                x, y = (float(c) for c in vehicle.position)
                collided = bool(info.get("crash_vehicle", False))
                off_road = bool(info.get("out_of_road", False))
                agents[name] = AgentState(
                    x=x, y=y,
                    heading=float(vehicle.heading_theta),
                    speed=float(vehicle.speed),
                    length=float(vehicle.LENGTH),
                    width=float(vehicle.WIDTH),
                    s=self.geometry.routes[name].project(x, y),
                    collided=collided, off_road=off_road,
                    active=not (collided or off_road),
                )  # fmt: skip
        self._last = agents
        return WorldState(t=self._steps * self.dt, agents=agents)
