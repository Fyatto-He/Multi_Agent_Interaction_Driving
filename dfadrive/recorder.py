"""Trajectory logging: everything needed to inspect or replay one episode, in one file.

An ``Episode`` holds per-step arrays for each agent plus the metadata that produced them
(scenario instance, controllers, package versions). Saved as a single ``.npz``; the
metadata travels inside it as JSON.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

import numpy as np

from .labels import Facts
from .policy import AgentView
from .scenario import ScenarioInstance

FIELDS = ("x", "y", "heading", "speed", "s", "dist_to_entry", "dist_to_clear", "active", "steer", "accel")
FACTS = ("crashed", "at_goal", "own_in_cz", "other_in_cz")


def _versions() -> dict[str, str]:
    out = {}
    for pkg in ("dfadrive", "metadrive-simulator", "dfa", "scenic", "numpy", "shapely"):
        try:
            out[pkg] = version(pkg)
        except PackageNotFoundError:
            pass
    return out


@dataclass
class Episode:
    meta: dict  # instance, controllers, dt, versions, geometry summary
    t: np.ndarray  # (T,)
    data: dict[str, dict[str, np.ndarray]]  # agent -> field -> (T,) array

    @property
    def instance(self) -> ScenarioInstance:
        return ScenarioInstance.from_dict(self.meta["instance"])

    @property
    def agents(self) -> list[str]:
        return list(self.data)

    def save(self, path: str | Path) -> Path:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        arrays = {f"{a}/{k}": v for a, fields in self.data.items() for k, v in fields.items()}
        np.savez_compressed(path, t=self.t, meta=json.dumps(self.meta), **arrays)
        return path

    @classmethod
    def load(cls, path: str | Path) -> "Episode":
        with np.load(path, allow_pickle=False) as z:
            data: dict[str, dict[str, np.ndarray]] = {}
            for key in z.files:
                if "/" in key:
                    agent, field = key.split("/", 1)
                    data.setdefault(agent, {})[field] = z[key]
            return cls(meta=json.loads(str(z["meta"])), t=z["t"], data=data)


class Recorder:
    """Accumulates one episode step by step."""

    def __init__(self, instance: ScenarioInstance, controllers: dict[str, str], dt: float, geometry):
        self._rows: dict[str, dict[str, list]] = {
            a: {k: [] for k in (*FIELDS, *FACTS, "symbol", "dfa_state")} for a in instance.agents
        }
        self._t: list[float] = []
        self.meta = dict(
            instance=instance.to_dict(),
            controllers=controllers,
            dt=dt,
            versions=_versions(),
            zone=[list(c) for c in geometry.zone.exterior.coords],
            conflicts=sorted(sorted(pair) for pair in geometry.zones),
            routes={a: r.points.round(3).tolist() for a, r in geometry.routes.items()},
            lane_width={a: r.lane_width for a, r in geometry.routes.items()},
        )

    def log(self, views: dict[str, AgentView], actions: dict, facts: dict[str, Facts] | None, symbols: dict | None):
        """Record the state in ``views`` and the action each agent takes from it.

        ``facts``/``symbols`` are the labels of this state (``None`` for the initial state,
        which the DFAs do not read).
        """
        any_view = next(iter(views.values()))
        self._t.append(any_view.world.t)
        for a, view in views.items():
            st, row = view.world.agents[a], self._rows[a]
            g = view.geometry
            u = actions.get(a, (np.nan, np.nan))
            values = (st.x, st.y, st.heading, st.speed, st.s, g.dist_to_entry(a, st), g.dist_to_clear(a, st),
                      st.active, u[0], u[1])  # fmt: skip
            for k, v in zip(FIELDS, values):
                row[k].append(v)
            for k in FACTS:
                row[k].append(bool(getattr(facts[a], k)) if facts else False)
            row["symbol"].append(symbols[a] if symbols else "")
            row["dfa_state"].append(view.task.state)

    def finish(self, extra: dict | None = None) -> Episode:
        data = {a: {k: np.asarray(v) for k, v in row.items()} for a, row in self._rows.items()}
        return Episode(meta={**self.meta, **(extra or {})}, t=np.asarray(self._t), data=data)
