"""Reward and self-play wrapper. The reward tests need no simulator and no SB3."""

import numpy as np
import pytest

from dfadrive.labels import Facts
from dfadrive.policy import AgentView, obs_dim
from dfadrive.rl.reward import RewardConfig, RewardModel, potential
from dfadrive.tasks import TaskMonitor
from dfadrive.world import AgentState, ConflictGeometry, Route, VehicleLimits, WorldState

LIMITS = VehicleLimits(wheelbase=2.5, max_steer=0.7, accel_per_throttle=2.9, decel_per_brake=27.3, max_decel=9.8)
ROUTES = {
    "A": Route(np.linspace((0, 0), (200, 0), 400), lane_width=3.5),
    "B": Route(np.linspace((100, 100), (100, -100), 400), lane_width=3.5),
}
GEOMETRY = ConflictGeometry.from_routes(ROUTES)
NO_FACTS = Facts(False, False, False, False)


def car(agent, s, speed=5.0, **kw):
    x, y = ROUTES[agent].point(s)
    return AgentState(x=x, y=y, heading=ROUTES[agent].heading(s), speed=speed, length=4.5, width=1.8, s=s, **kw)


def views(t, a, b, tasks, style=0.5):
    world = WorldState(t=t, agents={"A": a, "B": b})
    return {k: AgentView(k, world, GEOMETRY, tasks, {"A": style, "B": style}, {"A": 0.0, "B": 0.0}, LIMITS) for k in "AB"}


def monitors(a="CROSS", b="YIELD"):
    return {"A": TaskMonitor(a), "B": TaskMonitor(b)}


def test_potential_rises_along_an_accepting_run():
    cfg, tasks = RewardConfig(), monitors()
    far = car("B", 150)  # B has passed the crossing and is out of the way
    phis = []
    for s in (40, 80, 95):  # approaching
        phis.append(potential(views(0, car("A", s), far, tasks)["A"], cfg))
    tasks["A"].step("own")
    phis.append(potential(views(0, car("A", 100), far, tasks)["A"], cfg))  # in the zone
    tasks["A"].step("none")
    for s in (110, 150, 195):  # cleared, heading for the goal
        phis.append(potential(views(0, car("A", s), far, tasks)["A"], cfg))
    tasks["A"].step("goal")
    phis.append(potential(views(0, car("A", 199), far, tasks)["A"], cfg))
    assert phis == sorted(phis) and phis[-1] == 0.0
    assert max(np.diff(phis)) < cfg.shaping  # a DFA transition never jumps a whole level


def test_waiting_for_the_other_is_not_shaped():
    cfg, tasks = RewardConfig(), monitors()
    waiting = [potential(views(0, car("A", 50), car("B", s), tasks)["B"], cfg) for s in (40, 70, 90)]
    assert len(set(waiting)) == 1  # y0: the next symbol is A's to produce, B's position is irrelevant
    tasks["B"].step("other"), tasks["B"].step("none")
    free = [potential(views(0, car("A", 150), car("B", s), tasks)["B"], cfg) for s in (40, 70, 90)]
    assert free == sorted(free) and free[0] > waiting[0]


def test_a_lost_task_is_below_every_live_state():
    cfg, tasks = RewardConfig(), monitors()
    live = potential(views(0, car("A", 50), car("B", 10), tasks)["B"], cfg)
    tasks["B"].step("own")
    assert potential(views(0, car("A", 50), car("B", 10), tasks)["B"], cfg) < live


def step_reward(model, t, a, b, tasks, facts=None, task_reward=None, style=0.5):
    v = views(t, a, b, tasks, style)
    return model.step(v, facts or {"A": NO_FACTS, "B": NO_FACTS}, task_reward or {"A": 0.0, "B": 0.0}, dt=0.1)


def test_outcome_and_collision_terms():
    model, tasks = RewardModel(), monitors()
    model.reset(views(0, car("A", 50), car("B", 50), tasks))
    crashed = Facts(True, False, False, False)
    out = step_reward(model, 0.1, car("A", 50.5, collided=True, active=False), car("B", 50.5), tasks,
                      facts={"A": crashed, "B": NO_FACTS}, task_reward={"A": -1.0, "B": 0.0})  # fmt: skip
    assert out["A"][1]["task"] == -1.0 and out["A"][1]["collision"] == -1.0
    assert out["B"][1]["task"] == 0.0 and out["B"][1]["collision"] == 0.0


def test_style_changes_costs_but_not_task_terms():
    results = {}
    for style in (0.0, 1.0):
        model, tasks = RewardModel(), monitors()
        model.reset(views(0, car("A", 50, speed=9.0), car("B", 10), tasks, style))
        results[style] = step_reward(model, 0.1, car("A", 50.9, speed=9.0), car("B", 10.5), tasks, style=style)["A"][1]
    lo, hi = results[0.0], results[1.0]
    assert lo["task"] == hi["task"] and lo["collision"] == hi["collision"] and lo["shaping"] == pytest.approx(hi["shaping"])
    assert hi["time"] < lo["time"] < 0  # an aggressive agent pays more for time
    assert lo["over_speed"] < 0 == hi["over_speed"]  # 9 m/s is above the conservative cruise speed only


def test_margin_penalty_depends_on_the_gap_and_the_style():
    def enter(style, other_s):
        model, tasks = RewardModel(), monitors("CROSS", "CROSS")
        model.reset(views(0, car("A", 90), car("B", other_s), tasks, style))
        inside = Facts(False, False, True, False)
        out = step_reward(model, 0.1, car("A", 97), car("B", other_s + 0.5), tasks, facts={"A": inside, "B": NO_FACTS}, style=style)
        return out["A"][1]["margin"]

    assert enter(0.0, other_s=85) < enter(1.0, other_s=85) <= 0  # B is ~2 s away: fine for aggressive, not for conservative
    assert enter(0.0, other_s=20) == 0  # B is far away in time


def test_shaping_sums_to_the_potential_difference():
    cfg = RewardConfig(gamma=1.0)
    model, tasks = RewardModel(cfg), monitors()
    start = views(0, car("A", 40), car("B", 150), tasks)
    model.reset(start)
    total = sum(step_reward(model, 0.1 * k, car("A", 40 + k), car("B", 150), tasks)["A"][1]["shaping"] for k in range(1, 30))
    end = views(3.0, car("A", 69), car("B", 150), tasks)
    assert total == pytest.approx(potential(end["A"], cfg) - potential(start["A"], cfg))


@pytest.mark.sim
def test_selfplay_slot_conventions():
    from dfadrive.rl.selfplay import SelfPlay, SelfPlayConfig

    sim = SelfPlay(SelfPlayConfig(), seed=0)
    obs = sim.reset()
    assert obs.shape == (2, obs_dim("full")) and obs.dtype == np.float32
    finished, padded, episodes = [], 0, sim.episodes
    for _ in range(600):  # full throttle for both: someone arrives or they crash
        obs, rew, done, infos = sim.step(np.ones((2, 1), dtype=np.float32))
        for i, info in enumerate(infos):
            if info.get("padding"):
                padded += 1
                assert rew[i] == 0 and (done[i] or not obs[i].any())
            if "outcome" in info:
                finished.append(info)
                assert done[i] and info["terminal_observation"].shape == (obs_dim("full"),)
                assert info["episode"]["l"] > 0 and set(info["outcome"]["terms"]) >= {"task", "shaping", "collision", "time"}
        if sim.episodes > episodes + 1:
            break
    sim.close()
    assert len(finished) >= 2 and np.isfinite(obs).all()
    assert all(not info["TimeLimit.truncated"] for info in finished)  # they finished, they did not time out


def test_speed_and_accel_action_modes():
    from dfadrive.rl.selfplay import to_action

    tasks = monitors()
    standing = views(0, car("A", 50, speed=0.0), car("B", 10), tasks)["A"]
    rolling = views(0, car("A", 50, speed=10.0), car("B", 10), tasks)["A"]
    go, stop = np.array([1.0]), np.array([-1.0])
    assert to_action(standing, go, True, "speed")[1] > 0 and to_action(standing, stop, True, "speed")[1] < 0
    assert to_action(rolling, np.array([0.0]), True, "speed")[1] < 0  # 10 m/s is above the 7.5 m/s asked for
    assert to_action(rolling, np.array([0.0]), True, "accel")[1] == 0  # in accel mode zero means coast
    assert obs_dim("full") == 36 and obs_dim("world") == 25
