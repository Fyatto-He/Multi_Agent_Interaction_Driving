"""Episode loop: simulator -> world facts -> per-agent task state -> policy views.

``TaskDrivingEnv`` has a small parallel multi-agent interface (dicts keyed by agent id)
so that the same loop serves scripted controllers and learners. Every agent's view holds
every agent's task monitor, style and latest command (full vision).

Conventions
- A DFA reads the label of every state reached by a step (not the initial state).
- An agent keeps being simulated after its task is accepted or rejected, until it
  physically finishes (arrives or crashes) or the episode times out. A failed task must
  not freeze the car in front of the other agent.
- Task reward is +1 on entering ACC, -1 on entering REJ, 0 otherwise (the ternary
  convention of ``dfax``), per agent, not shared.
"""

from __future__ import annotations

import numpy as np

from .labels import Facts, facts_for, symbol_of
from .policy import AgentView
from .scenario import ScenarioInstance
from .tasks import ACC, REJ, TaskMonitor


class TaskDrivingEnv:
    def __init__(self, sim, horizon_s: float = 40.0):
        self.sim = sim
        self.horizon_s = horizon_s
        self.instance: ScenarioInstance | None = None
        self.monitors: dict[str, TaskMonitor] = {}
        self.last_accel: dict[str, float] = {}
        self.world = None

    @property
    def agents(self) -> list[str]:
        return list(self.instance.agents)

    def reset(self, instance: ScenarioInstance) -> dict[str, AgentView]:
        self.instance = instance
        self.world = self.sim.reset(instance)
        self.monitors = {a: TaskMonitor(spec.task) for a, spec in instance.agents.items()}
        self.last_accel = {a: 0.0 for a in instance.agents}
        return self._views()

    def step(self, actions: dict[str, np.ndarray]):
        """Returns (views, rewards, done, info); ``done`` ends the whole episode."""
        limits = self.sim.limits
        for a, u in actions.items():  # what each car is doing, in m/s^2, visible to all from the next step
            scale = limits.accel_per_throttle if u[1] >= 0 else limits.decel_per_brake
            self.last_accel[a] = float(np.clip(u[1] * scale, -limits.max_decel, limits.accel_per_throttle))
        self.world = self.sim.step(actions)
        geometry = self.sim.geometry
        facts: dict[str, Facts] = {a: facts_for(a, self.world, geometry) for a in self.agents}
        symbols = {a: symbol_of(f) for a, f in facts.items()}
        rewards = {}
        for a, monitor in self.monitors.items():
            before = monitor.state
            after = monitor.step(symbols[a])
            rewards[a] = float(after != before) * {ACC: 1.0, REJ: -1.0}.get(after, 0.0)
        all_finished = not any(s.active for s in self.world.agents.values())
        timeout = self.world.t >= self.horizon_s - 1e-9
        info = dict(facts=facts, symbols=symbols, timeout=timeout and not all_finished)
        return self._views(), rewards, all_finished or timeout, info

    def close(self) -> None:
        self.sim.close()

    def _views(self) -> dict[str, AgentView]:
        styles = {a: spec.style for a, spec in self.instance.agents.items()}
        return {
            a: AgentView(
                agent=a,
                world=self.world,
                geometry=self.sim.geometry,
                tasks=self.monitors,
                styles=styles,
                last_accel=dict(self.last_accel),
                limits=self.sim.limits,
            )
            for a in self.agents
        }
