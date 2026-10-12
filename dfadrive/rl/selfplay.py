"""Self-play wrapper: one simulator, two learning agents that share one policy.

Arrays in, arrays out, no learning-library imports. Each agent occupies one *slot*:

    obs      (2, obs_dim)   flat_observation of each agent
    action   (2, 1) or (2, 2), in [-1, 1]
    reward   (2,)           per agent, from RewardModel
    done     (2,)

Slot conventions (the ones Stable-Baselines3 expects of a vectorised env):
- When a slot reports ``done``, the observation returned with it already belongs to that
  slot's next episode; the last real observation is in ``info["terminal_observation"]``.
- An agent that finishes (arrives or crashes) before the other gets ``done`` at once.
  Until the joint episode ends its slot is *padding*: zero observation, zero reward,
  ``info["padding"] = True``. Padding steps are an absorbing state, not driving data.
- A timeout sets ``info["TimeLimit.truncated"]`` so the learner bootstraps from the value.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from ..controllers import accel_action, steer_along
from ..env import TaskDrivingEnv
from ..policy import AgentView, flat_observation, obs_dim
from ..scenario import make_sampler
from ..sim.metadrive_adapter import MetaDriveIntersection
from .reward import RewardConfig, RewardModel

AGENTS = ("A", "B")
MAX_ACCEL, MAX_BRAKE = 3.0, 6.0  # m/s^2: strongest acceleration and braking a policy can command
MAX_SPEED = 15.0  # m/s commanded at action +1 in "speed" mode
SPEED_GAIN = 2.0  # 1/s, how hard a commanded speed is tracked
ACTIONS = ("speed", "accel")


@dataclass(frozen=True)
class SelfPlayConfig:
    tasks: tuple[tuple[str, str], ...] = (("CROSS", "YIELD"),)  # one pair is drawn per episode
    scenarios: tuple[str, ...] = ("unprotected_left",)  # one scenario is drawn per episode
    longitudinal_only: bool = True  # policy outputs acceleration; steering follows the route
    vision: str = "full"  # what the policy is shown of the other car; see dfadrive/policy.py
    action: str = "speed"  # what the policy's output means; see to_action
    horizon_s: float = 40.0
    sampler: str = "auto"
    reward: RewardConfig = field(default_factory=RewardConfig)

    @property
    def action_dim(self) -> int:
        return 1 if self.longitudinal_only else 2


def to_action(view: AgentView, raw: np.ndarray, longitudinal_only: bool, mode: str = "speed") -> np.ndarray:
    """Policy output in [-1, 1] -> simulator action ``[steer, accel]``.

    "speed"  the output is a target speed, -1 = stand still, +1 = 15 m/s, tracked within
             +3 / -6 m/s^2. A policy that outputs noise keeps the car rolling, and a
             stopped car starts again as soon as the target rises.
    "accel"  the output is an acceleration, +1 = 3 m/s^2, -1 = -6 m/s^2. Kept for the
             first runs; a policy that has learned to brake can park the car for good,
             because from rest only a run of positive outputs moves it (docs/07).
    """
    raw = np.clip(np.asarray(raw, dtype=float).ravel(), -1.0, 1.0)
    me = view.world.agents[view.agent]
    if mode == "speed":
        target = (raw[-1] + 1.0) / 2.0 * MAX_SPEED
        accel = float(np.clip(SPEED_GAIN * (target - me.speed), -MAX_BRAKE, MAX_ACCEL))
        if target < 0.2 and me.speed < 0.3:
            accel = -1.0  # hold the brake while asked to stand
    else:
        accel = raw[-1] * (MAX_ACCEL if raw[-1] >= 0 else MAX_BRAKE)
    steer = steer_along(view.geometry.routes[view.agent], me, view.limits) if longitudinal_only else float(raw[0])
    return np.array([steer, accel_action(accel, view.limits)])


class SelfPlay:
    def __init__(self, cfg: SelfPlayConfig | None = None, seed: int = 0):
        self.cfg = cfg or SelfPlayConfig()
        self.env = TaskDrivingEnv(MetaDriveIntersection(), horizon_s=self.cfg.horizon_s)
        self.rng = np.random.default_rng(seed)
        self.samplers = [
            make_sampler(self.cfg.sampler, scenario, task_A=a, task_B=b)
            for scenario in self.cfg.scenarios
            for a, b in self.cfg.tasks
        ]
        self.reward = RewardModel(self.cfg.reward)
        self.episodes = 0
        self._next_seed = seed
        self._views: dict[str, AgentView] = {}
        self._padding = [False, False]
        self._ret, self._len = np.zeros(2), np.zeros(2, dtype=int)
        self._terms: list[dict[str, float]] = [{}, {}]

    def reset(self) -> np.ndarray:
        sampler = self.samplers[self.rng.integers(len(self.samplers))]
        self._views = self.env.reset(sampler.sample(self._next_seed))
        self._next_seed += 1
        self.episodes += 1
        self.reward.reset(self._views)
        self._padding = [False, False]
        self._ret[:], self._len[:] = 0.0, 0
        self._terms = [{}, {}]
        return np.stack([flat_observation(self._views[a], self.cfg.vision) for a in AGENTS])

    def step(self, raw_actions: np.ndarray):
        acting = [a for i, a in enumerate(AGENTS) if not self._padding[i]]
        actions = {
            a: to_action(self._views[a], raw_actions[AGENTS.index(a)], self.cfg.longitudinal_only, self.cfg.action)
            for a in acting
        }
        self._views, task_reward, joint_done, info = self.env.step(actions)
        rewards = self.reward.step({a: self._views[a] for a in acting}, info["facts"], task_reward, self.env.sim.dt)

        obs = np.zeros((2, obs_dim(self.cfg.vision)), dtype=np.float32)
        rew, done, infos = np.zeros(2, dtype=np.float32), np.zeros(2, dtype=bool), [{}, {}]
        for i, a in enumerate(AGENTS):
            if self._padding[i]:
                done[i], infos[i] = joint_done, dict(padding=True)
                if joint_done:
                    infos[i]["terminal_observation"] = obs[i].copy()
                continue
            view = self._views[a]
            finished = not view.world.agents[a].active
            obs[i], (rew[i], terms) = flat_observation(view, self.cfg.vision), rewards[a]
            self._ret[i] += rew[i]
            self._len[i] += 1
            for k, v in terms.items():
                self._terms[i][k] = self._terms[i].get(k, 0.0) + v
            if finished or joint_done:
                done[i] = True
                infos[i] = {
                    "terminal_observation": obs[i].copy(),
                    "TimeLimit.truncated": bool(joint_done and not finished),
                    "episode": dict(r=float(self._ret[i]), l=int(self._len[i]), t=float(view.world.t)),
                    "outcome": dict(
                        agent=a,
                        task=view.task.task.name,
                        status=view.task.status,
                        crashed=bool(info["facts"][a].crashed),
                        style=float(view.style),
                        terms=dict(self._terms[i]),
                    ),
                }
                self._padding[i] = not joint_done
                obs[i] = 0.0  # first observation of the padding episode, replaced below on a joint reset
        if joint_done:
            obs = self.reset()
        return obs, rew, done, infos

    def close(self) -> None:
        self.env.close()
