"""Run one recorded episode with scripted policies."""

from __future__ import annotations

from .controllers import CONTROLLERS
from .env import TaskDrivingEnv
from .recorder import Episode, Recorder
from .scenario import ScenarioInstance
from .sim.metadrive_adapter import MetaDriveIntersection


def make_env(horizon_s: float = 40.0, exact: bool = False) -> TaskDrivingEnv:
    """``exact=True`` trades speed for bit-for-bit replay (see ``MetaDriveIntersection``)."""
    return TaskDrivingEnv(MetaDriveIntersection(exact=exact), horizon_s=horizon_s)


def run_episode(env: TaskDrivingEnv, instance: ScenarioInstance, controllers="task") -> Episode:
    """``controllers``: a name from ``CONTROLLERS`` or a policy object, for all agents or one per agent."""
    chosen = {a: controllers[a] if isinstance(controllers, dict) else controllers for a in instance.agents}
    policies = {a: CONTROLLERS[c]() if isinstance(c, str) else c for a, c in chosen.items()}
    kinds = {a: c if isinstance(c, str) else getattr(c, "name", type(c).__name__) for a, c in chosen.items()}

    views = env.reset(instance)
    recorder = Recorder(instance, kinds, env.sim.dt, env.sim.geometry)
    facts = symbols = None
    done, info = False, {}
    while True:
        actions = {} if done else {a: policies[a].act(v) for a, v in views.items() if v.world.agents[a].active}
        recorder.log(views, actions, facts, symbols)
        if done:
            break
        views, _, done, info = env.step(actions)
        facts, symbols = info["facts"], info["symbols"]
    return recorder.finish(dict(timeout=bool(info.get("timeout", False))))
