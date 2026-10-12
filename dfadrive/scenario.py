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

SCENARIO_DIR = Path(__file__).parent / "scenarios"
SCENARIOS = tuple(sorted(f.stem for f in SCENARIO_DIR.glob("*.scenic")))  # one Scenic file each
BASE = "unprotected_left"


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
    extra: dict = field(default_factory=dict)  # scenario-specific knobs, e.g. headway

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "ScenarioInstance":
        agents = {k: AgentSpec(**{**v, "route": tuple(v["route"])}) for k, v in d["agents"].items()}
        return cls(**{**d, "agents": agents})


class Sampler(Protocol):
    def sample(self, seed: int) -> ScenarioInstance: ...


_PER_AGENT = ("route", "task", "style", "speed", "distance")


def _instance(name: str, seed: int, sampler: str, p: dict) -> ScenarioInstance:
    """Scenario params -> instance. Agents are whatever names have a ``task_<name>`` param."""
    names = sorted(k[len("task_") :] for k in p if k.startswith("task_"))
    agents = {
        k: AgentSpec(
            route=tuple(str(p[f"route_{k}"]).split(":")),
            distance_to_conflict=float(p[f"distance_{k}"]),
            initial_speed=float(p[f"speed_{k}"]),
            task=str(p[f"task_{k}"]),
            style=float(p[f"style_{k}"]),
        )
        for k in names
    }
    known = {f"{field}_{k}" for field in _PER_AGENT for k in names} | {"arrival_offset"}
    extra = {k: float(v) for k, v in p.items() if k not in known and isinstance(v, (int, float))}
    return ScenarioInstance(name, seed, sampler, agents, float(p["arrival_offset"]), extra)


@dataclass
class ScenicSampler:
    """Sample instances from a scenario's Scenic file. ``overrides`` fixes any of its params."""

    overrides: dict = field(default_factory=dict)
    scenario: str = BASE

    def __post_init__(self):
        import scenic  # optional dependency

        path = SCENARIO_DIR / f"{self.scenario}.scenic"
        self._scenario = scenic.scenarioFromFile(str(path), params=dict(self.overrides), mode2D=True)

    def sample(self, seed: int) -> ScenarioInstance:
        random.seed(seed)  # Scenic draws from Python's and NumPy's global generators
        np.random.seed(seed)
        scene, _ = self._scenario.generate(maxIterations=10_000)
        return _instance(self.scenario, seed, "scenic", dict(scene.params))


@dataclass
class PythonSampler:
    """The base scenario's distribution written out by hand, for machines without Scenic.

    Only ``unprotected_left`` is mirrored here; the style probes exist as Scenic files only.
    """

    overrides: dict = field(default_factory=dict)

    DEFAULTS = dict(
        route_A="W:straight", route_B="E:left",
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
                return _instance(BASE, seed, "python", p)
        raise RuntimeError("no scenario satisfies the constraints")


def make_sampler(kind: str = "auto", scenario: str = BASE, **overrides) -> Sampler:
    """``kind``: "scenic", "python" (base scenario only), or "auto" (Scenic if installed)."""
    if scenario not in SCENARIOS:
        raise ValueError(f"unknown scenario {scenario!r}; available: {', '.join(SCENARIOS)}")
    if kind == "python":
        if scenario != BASE:
            raise ValueError(f"scenario {scenario!r} needs Scenic; only {BASE!r} has a NumPy sampler")
        return PythonSampler(overrides)
    try:
        return ScenicSampler(overrides, scenario)
    except ModuleNotFoundError:
        if kind == "scenic" or scenario != BASE:
            raise
        return PythonSampler(overrides)
