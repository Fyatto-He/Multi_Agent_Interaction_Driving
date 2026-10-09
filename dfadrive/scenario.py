"""Scenario description: what one concrete episode looks like, and how to sample one.

A ``ScenarioInstance`` is plain data and fully determines an episode (together with the
policies). Two interchangeable samplers produce it:

``ScenicSampler``  reads ``scenarios/unprotected_left.scenic`` (the readable spec).
``PythonSampler``  the same distribution in NumPy, for machines without Scenic.

They draw from the same distribution but not the same random stream, so a seed means
"the same episode" only within one sampler; the sampler name is stored in the instance.
"""

from __future__ import annotations

import random
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Protocol

import numpy as np

SCENIC_FILE = Path(__file__).parent / "scenarios" / "unprotected_left.scenic"

# Fixed for this scenario: (entry arm, manoeuvre).
ROUTES = {"A": ("W", "straight"), "B": ("E", "left")}


@dataclass(frozen=True)
class AgentSpec:
    route: tuple[str, str]  # (entry arm W/S/E/N, manoeuvre straight/left/right)
    distance_to_conflict: float  # m, front bumper to the conflict zone at t = 0
    initial_speed: float  # m/s
    task: str  # key of dfadrive.tasks.TASKS
    style: float  # 0 conservative .. 1 aggressive


@dataclass(frozen=True)
class ScenarioInstance:
    name: str
    seed: int
    sampler: str
    agents: dict[str, AgentSpec]
    arrival_offset: float  # s, nominal t_B - t_A at the conflict zone

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "ScenarioInstance":
        agents = {k: AgentSpec(**{**v, "route": tuple(v["route"])}) for k, v in d["agents"].items()}
        return cls(**{**d, "agents": agents})


class Sampler(Protocol):
    def sample(self, seed: int) -> ScenarioInstance: ...


def _instance(seed: int, sampler: str, p: dict) -> ScenarioInstance:
    agents = {
        k: AgentSpec(
            route=ROUTES[k],
            distance_to_conflict=float(p[f"distance_{k}"]),
            initial_speed=float(p[f"speed_{k}"]),
            task=str(p[f"task_{k}"]),
            style=float(p[f"style_{k}"]),
        )
        for k in ("A", "B")
    }
    return ScenarioInstance("unprotected_left", seed, sampler, agents, float(p["arrival_offset"]))


@dataclass
class ScenicSampler:
    """Sample instances from the Scenic file. ``overrides`` fixes any of its params."""

    overrides: dict = field(default_factory=dict)
    path: Path = SCENIC_FILE

    def __post_init__(self):
        import scenic  # optional dependency

        self._scenario = scenic.scenarioFromFile(str(self.path), params=dict(self.overrides), mode2D=True)

    def sample(self, seed: int) -> ScenarioInstance:
        random.seed(seed)  # Scenic draws from Python's and NumPy's global generators
        np.random.seed(seed)
        scene, _ = self._scenario.generate(maxIterations=10_000)
        return _instance(seed, "scenic", dict(scene.params))


@dataclass
class PythonSampler:
    """The distribution of the Scenic file, written out by hand (rejection sampling)."""

    overrides: dict = field(default_factory=dict)

    DEFAULTS = dict(
        task_A="CROSS", task_B="YIELD",
        style_A=(0.0, 1.0), style_B=(0.0, 1.0),
        speed_A=(5.0, 10.0), speed_B=(5.0, 10.0),
        distance_A=(25.0, 50.0), arrival_offset=(-2.0, 2.0),
    )  # fmt: skip
    DISTANCE_B = (15.0, 60.0)

    def sample(self, seed: int) -> ScenarioInstance:
        rng = np.random.default_rng(seed)
        spec = {**self.DEFAULTS, **self.overrides}
        for _ in range(10_000):
            p = {k: float(rng.uniform(*v)) if isinstance(v, tuple) else v for k, v in spec.items()}
            p["distance_B"] = p["speed_B"] * (p["distance_A"] / p["speed_A"] + p["arrival_offset"])
            if self.DISTANCE_B[0] <= p["distance_B"] <= self.DISTANCE_B[1]:
                return _instance(seed, "python", p)
        raise RuntimeError("no scenario satisfies the constraints")


def make_sampler(kind: str = "auto", **overrides) -> Sampler:
    if kind == "python":
        return PythonSampler(overrides)
    try:
        return ScenicSampler(overrides)
    except ModuleNotFoundError:
        if kind == "scenic":
            raise
        return PythonSampler(overrides)
