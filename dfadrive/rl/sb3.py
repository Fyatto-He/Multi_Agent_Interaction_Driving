"""Stable-Baselines3 glue: the only module that imports SB3 / PyTorch.

``SelfPlayVecEnv``  runs several ``SelfPlay`` simulators in subprocesses and presents their
                    agents as slots of one vectorised env, so a single PPO policy is
                    trained on all of them (parameter sharing) with per-agent rewards.
``OutcomeLogger``   logs task outcomes (accepted / rejected / unfinished, crashes) per rollout.
``LearnedPolicy``   wraps a saved model as a ``dfadrive.policy.Policy`` for evaluation with
                    the same recorder and metrics as the scripted controllers.

Workers are separate processes because MetaDrive allows one engine per process, and are
restarted every ``recycle_after`` episodes because MetaDrive leaks about 1.3 MB per reset.
"""

from __future__ import annotations

import multiprocessing as mp
from collections import Counter, deque
from pathlib import Path

import gymnasium as gym
import numpy as np
from stable_baselines3 import PPO
from stable_baselines3.common.callbacks import BaseCallback
from stable_baselines3.common.vec_env import VecEnv

from ..policy import AgentView, flat_observation, obs_dim
from .selfplay import SelfPlay, SelfPlayConfig, to_action


def _worker(conn, cfg: SelfPlayConfig, seed: int, recycle_after: int) -> None:
    sim = SelfPlay(cfg, seed)
    try:
        while True:
            cmd, data = conn.recv()
            if cmd == "reset":
                conn.send(sim.reset())
            elif cmd == "step":
                obs, rew, done, infos = sim.step(data)
                conn.send((obs, rew, done, infos, bool(done.all()) and sim.episodes > recycle_after))
            else:
                break
    finally:
        sim.close()
        conn.close()


class SelfPlayVecEnv(VecEnv):
    def __init__(self, n_sims: int, cfg: SelfPlayConfig | None = None, seed: int = 0, recycle_after: int = 300):
        self.cfg, self.recycle_after = cfg or SelfPlayConfig(), recycle_after
        self._ctx = mp.get_context("spawn")
        self._seeds = [seed + 1_000_003 * i for i in range(n_sims)]
        self._procs, self._conns = [None] * n_sims, [None] * n_sims
        for i in range(n_sims):
            self._start(i)
        observation_space = gym.spaces.Box(-np.inf, np.inf, (obs_dim(self.cfg.vision),), np.float32)
        action_space = gym.spaces.Box(-1.0, 1.0, (self.cfg.action_dim,), np.float32)
        super().__init__(2 * n_sims, observation_space, action_space)

    def _start(self, i: int) -> None:
        parent, child = self._ctx.Pipe()
        proc = self._ctx.Process(target=_worker, args=(child, self.cfg, self._seeds[i], self.recycle_after), daemon=True)
        proc.start()
        child.close()
        self._procs[i], self._conns[i] = proc, parent
        self._seeds[i] += 100_000  # a restarted worker continues with fresh scenario seeds

    def _stop(self, i: int) -> None:
        self._conns[i].send(("close", None))
        self._procs[i].join(timeout=10)
        self._conns[i].close()

    def reset(self) -> np.ndarray:
        for conn in self._conns:
            conn.send(("reset", None))
        return np.concatenate([conn.recv() for conn in self._conns])

    def step_async(self, actions: np.ndarray) -> None:
        for i, conn in enumerate(self._conns):
            conn.send(("step", actions[2 * i : 2 * i + 2]))

    def step_wait(self):
        obs, rew, done, infos = [], [], [], []
        for i in range(len(self._conns)):
            o, r, d, info, recycle = self._conns[i].recv()
            if recycle:  # the worker has just started a new episode; replace it with a fresh process
                self._stop(i)
                self._start(i)
                self._conns[i].send(("reset", None))
                o = self._conns[i].recv()
            obs.append(o), rew.append(r), done.append(d), infos.extend(info)
        return np.concatenate(obs), np.concatenate(rew), np.concatenate(done), infos

    def close(self) -> None:
        for i in range(len(self._conns)):
            if self._procs[i] is not None and self._procs[i].is_alive():
                self._stop(i)

    # The rest of the VecEnv interface is not meaningful across processes here.
    def get_attr(self, attr_name, indices=None):
        return [getattr(self.cfg, attr_name, None)] * self.num_envs

    def set_attr(self, attr_name, value, indices=None):
        raise NotImplementedError

    def env_method(self, method_name, *method_args, indices=None, **method_kwargs):
        raise NotImplementedError

    def env_is_wrapped(self, wrapper_class, indices=None):
        return [False] * self.num_envs


class OutcomeLogger(BaseCallback):
    """Adds per-task outcome rates over the last ``window`` agent-episodes to the SB3 log."""

    def __init__(self, window: int = 400):
        super().__init__()
        self.recent: deque = deque(maxlen=window)

    def _on_step(self) -> bool:
        self.recent.extend(info["outcome"] for info in self.locals["infos"] if "outcome" in info)
        return True

    def _on_rollout_end(self) -> None:
        for task in sorted({o["task"] for o in self.recent}):
            group = [o for o in self.recent if o["task"] == task]
            counts = Counter(o["status"] for o in group)
            for status in ("accepted", "rejected", "running"):
                self.logger.record(f"task/{task}_{'unfinished' if status == 'running' else status}", counts[status] / len(group))
            self.logger.record(f"task/{task}_crashed", sum(o["crashed"] for o in group) / len(group))


def make_ppo(env: SelfPlayVecEnv, seed: int = 0, **overrides) -> PPO:
    """PPO with one policy for all slots. ``gamma`` is taken from the reward config."""
    params = dict(
        learning_rate=3e-4, n_steps=512, batch_size=1024, n_epochs=10, gae_lambda=0.95, clip_range=0.2,
        ent_coef=0.005, policy_kwargs=dict(net_arch=[64, 64]), device="cpu", verbose=0,
    )  # fmt: skip
    params.update(overrides)
    return PPO("MlpPolicy", env, gamma=env.cfg.reward.gamma, seed=seed, **params)


class LearnedPolicy:
    """A saved PPO model as a per-agent policy: same interface as the scripted controllers."""

    def __init__(self, path: str | Path, longitudinal_only=True, vision="full", action="speed", deterministic=True):
        self.model = PPO.load(str(path), device="cpu")
        self.longitudinal_only, self.vision, self.action = longitudinal_only, vision, action
        self.deterministic = deterministic
        self.name = f"ppo:{Path(path).parent.name}"

    def act(self, view: AgentView) -> np.ndarray:
        raw, _ = self.model.predict(flat_observation(view, self.vision), deterministic=self.deterministic)
        return to_action(view, raw, self.longitudinal_only, self.action)
