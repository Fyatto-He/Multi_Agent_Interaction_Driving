"""End-to-end checks on the simulator. Slower: `pytest -m "not sim"` skips them."""

import numpy as np
import pytest

from dfadrive.metrics import episode_metrics
from dfadrive.policy import flat_observation, obs_dim
from dfadrive.recorder import Episode
from dfadrive.run import make_env, run_episode
from dfadrive.scenario import make_sampler

pytestmark = pytest.mark.sim


@pytest.fixture(scope="module")
def env():
    env = make_env()
    yield env
    env.close()


def sample(seed=0, **overrides):
    return make_sampler("python", **overrides).sample(seed)


def outcomes(ep):
    m = episode_metrics(ep)
    return m, tuple(m["agents"][a]["outcome"] for a in ("A", "B"))


def test_spawn_matches_the_scenario(env):
    inst = sample(1)
    views = env.reset(inst)
    g = env.sim.geometry
    for name, spec in inst.agents.items():
        state = views[name].world.agents[name]
        assert g.dist_to_entry(name, state) == pytest.approx(spec.distance_to_conflict, abs=0.05)
        assert state.speed == pytest.approx(spec.initial_speed, abs=0.05)
        assert abs(g.routes[name].lateral(state.x, state.y)) < 0.05
    for vision in ("world", "full"):
        obs = flat_observation(views["A"], vision)
        assert obs.shape == (obs_dim(vision),) and obs.dtype == np.float32 and np.isfinite(obs).all()
    assert obs_dim("full") - obs_dim("world") == 11  # the other's DFA state (9), style and latest command


def test_replay_is_exact_in_a_fresh_simulator_and_close_in_a_reused_one(env, tmp_path):
    inst = sample(2)
    fields = ("x", "y", "heading", "speed", "steer", "accel")

    env.sim.exact = True  # MetaDrive allows one engine per process, so reuse the fixture
    first, second = run_episode(env, inst), run_episode(env, inst)
    env.sim.exact = False
    for agent in first.agents:
        for field in fields:
            np.testing.assert_array_equal(first.data[agent][field], second.data[agent][field])

    run_episode(env, sample(7))  # leave some state behind in the shared simulator
    reused = run_episode(env, inst)
    for agent in first.agents:
        for field in fields:
            np.testing.assert_allclose(first.data[agent][field], reused.data[agent][field], atol=1e-4)

    loaded = Episode.load(first.save(tmp_path / "ep.npz"))
    assert loaded.instance == inst and episode_metrics(loaded) == episode_metrics(first)


def test_compatible_tasks_are_both_accomplished(env):
    for seed in range(5):
        m, result = outcomes(run_episode(env, sample(seed, task_A="CROSS", task_B="YIELD")))
        assert result == ("accepted", "accepted") and m["first_in_zone"] == "A" and m["pet"] > 0


def test_yield_holds_for_every_style(env):
    """Style changes how B waits, never whether it waits."""
    for style in (0.0, 0.5, 1.0):
        m, result = outcomes(run_episode(env, sample(0, task_A="CROSS", task_B="YIELD", style_B=style)))
        assert result == ("accepted", "accepted") and m["first_in_zone"] == "A"


def test_incompatible_tasks_fail_at_the_task_level(env):
    m, result = outcomes(run_episode(env, sample(0, task_A="YIELD", task_B="YIELD")))
    assert result == ("unfinished", "unfinished") and m["timeout"] and not m["collision"]
    m, result = outcomes(run_episode(env, sample(0, task_A="GO_FIRST", task_B="GO_FIRST")))
    assert sorted(result) == ["accepted", "rejected"] and not m["collision"]


def test_blind_controllers_collide_when_arrivals_coincide(env):
    inst = sample(0, task_A="CROSS", task_B="CROSS", style_A=0.5, style_B=0.5, speed_A=8.5, speed_B=8.5, arrival_offset=0.0)
    m, result = outcomes(run_episode(env, inst, "blind"))
    assert m["collision"] and result == ("rejected", "rejected")
    m, result = outcomes(run_episode(env, inst, "task"))  # same scenario, interactive controllers
    assert not m["collision"] and result == ("accepted", "accepted")


def test_probe_scenarios_run_and_the_crossing_zone_is_square(env):
    pytest.importorskip("scenic")
    for name in ("tie", "crossing", "standing_start"):
        inst = make_sampler("scenic", name, task_A="CROSS", task_B="YIELD").sample(0)
        m, result = outcomes(run_episode(env, inst))
        assert result == ("accepted", "accepted") and m["first_in_zone"] == "A" and not m["collision"]
        if name == "crossing":
            assert env.sim.geometry.zone.area == pytest.approx(3.5 * 3.5, rel=0.02)


def test_full_vision_settles_a_standing_contest_without_a_crash(env):
    pytest.importorskip("scenic")
    sampler = make_sampler("scenic", "standing_start", task_A="GO_FIRST", task_B="GO_FIRST", style_A=0.9, style_B=0.1)
    for seed in range(3):
        m, result = outcomes(run_episode(env, sampler.sample(seed), "full"))
        assert not m["collision"] and result == ("accepted", "rejected")  # the more aggressive car wins, cleanly


def test_full_vision_lets_a_car_that_must_lead_go_first(env):
    inst = sample(0, task_A="CROSS", task_B="GO_FIRST", style_A=0.9, style_B=0.1, arrival_offset=2.0)
    assert outcomes(run_episode(env, inst, "task"))[1] == ("accepted", "rejected")  # world vision: A takes it
    assert outcomes(run_episode(env, inst, "full"))[1] == ("accepted", "accepted")  # full vision: A sees B's task


def test_three_cars_gap_acceptance_follows_style(env):
    pytest.importorskip("scenic")
    orders = {}
    for style in (0.1, 0.9):
        inst = make_sampler("scenic", "gap", style_B=style, style_A1=0.5, style_A2=0.5, headway=4.0).sample(1)
        assert list(inst.agents) == ["A1", "A2", "B"] and inst.extra["headway"] == 4.0
        m = episode_metrics(run_episode(env, inst, "full"))
        assert not m["collision"] and all(a["outcome"] == "accepted" for a in m["agents"].values())
        orders[style] = m["order"]
    assert orders == {0.1: "A1>A2>B", 0.9: "A1>B>A2"}  # the cautious yielder waits for both, the aggressive one takes the gap


def test_shared_schedule_lets_non_conflicting_cars_cross_together(env):
    """Four cars, nobody has priority: full vision must finish everyone, without a crash."""
    pytest.importorskip("scenic")
    inst = make_sampler("scenic", "four_way").sample(1)
    world, full = (episode_metrics(run_episode(env, inst, c)) for c in ("task", "full"))
    for m in (world, full):
        assert not m["collision"] and m["all_accepted"] and len(m["agents"]) == 4
    assert full["total_delay"] < world["total_delay"] and full["clear_time"] < world["clear_time"]
