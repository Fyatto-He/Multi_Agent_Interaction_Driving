import math

import numpy as np
import pytest

from dfadrive.scenario import PythonSampler, ScenarioInstance, make_sampler
from dfadrive.style import style_params
from dfadrive.world import AgentState, ConflictGeometry, Route


def straight(p, q, n=50):
    return Route(np.linspace(p, q, n), lane_width=3.5)


def car(x, y, heading, route, **kw):
    return AgentState(x=x, y=y, heading=heading, speed=5.0, length=4.5, width=1.8, s=route.project(x, y), **kw)


def test_route_coordinates():
    r = straight((0, 0), (100, 0))
    assert r.length == pytest.approx(100)
    assert r.project(30, 2) == pytest.approx(30)
    assert r.lateral(30, 2) == pytest.approx(2)  # left of travel is positive
    assert r.heading(50) == pytest.approx(0)


def test_conflict_zone_of_a_right_angle_crossing():
    routes = {"A": straight((0, 0), (100, 0)), "B": straight((50, 50), (50, -50))}
    g = ConflictGeometry.from_routes(routes)
    assert g.zone.area == pytest.approx(3.5 * 3.5)
    assert g.entry_s["A"] == pytest.approx(48.25) and g.exit_s["A"] == pytest.approx(51.75)
    a_before = car(40, 0, 0.0, routes["A"])
    assert not g.occupies("A", a_before) and g.dist_to_entry("A", a_before) == pytest.approx(48.25 - 42.25)
    assert g.occupies("A", car(50, 0, 0.0, routes["A"]))
    a_after = car(56, 0, 0.0, routes["A"])
    assert not g.occupies("A", a_after) and g.dist_to_clear("A", a_after) < 0
    assert not g.occupies("A", car(50, 0, 0.0, routes["A"], arrived=True))  # an arrived car is gone


def test_parallel_routes_do_not_conflict():
    with pytest.raises(ValueError):
        ConflictGeometry.from_routes({"A": straight((0, 0), (100, 0)), "B": straight((100, 3.5), (0, 3.5))})


def test_style_is_monotone():
    lo, hi = style_params(0.0), style_params(1.0)
    assert lo.cruise_speed < hi.cruise_speed and lo.max_accel < hi.max_accel
    assert lo.comfort_decel < hi.comfort_decel and lo.commit_margin > hi.commit_margin
    with pytest.raises(ValueError):
        style_params(1.5)


@pytest.mark.parametrize("kind", ["python", "scenic"])
def test_sampler_is_deterministic_and_respects_constraints(kind):
    if kind == "scenic":
        pytest.importorskip("scenic")
    sampler = make_sampler(kind, task_A="GO_FIRST", style_B=0.25)
    assert sampler.sample(3) == sampler.sample(3)
    assert sampler.sample(3) != sampler.sample(4)
    for seed in range(30):
        inst = sampler.sample(seed)
        a, b = inst.agents["A"], inst.agents["B"]
        assert inst.sampler == kind and a.task == "GO_FIRST" and b.task == "YIELD" and b.style == 0.25
        assert 25 <= a.distance_to_conflict <= 50 and 15 <= b.distance_to_conflict <= 60
        assert 5 <= a.initial_speed <= 10 and 5 <= b.initial_speed <= 10 and 0 <= a.style <= 1
        nominal = b.distance_to_conflict / b.initial_speed - a.distance_to_conflict / a.initial_speed
        assert nominal == pytest.approx(inst.arrival_offset) and abs(nominal) <= 2
        assert ScenarioInstance.from_dict(inst.to_dict()) == inst


def test_python_sampler_needs_no_scenic():
    assert math.isfinite(PythonSampler().sample(0).arrival_offset)


def test_every_scenario_file_samples_a_valid_instance():
    pytest.importorskip("scenic")
    from dfadrive.scenario import SCENARIOS
    from dfadrive.tasks import TASKS

    assert {"unprotected_left", "tie", "crossing", "standing_start"} <= set(SCENARIOS)
    for name in SCENARIOS:
        sampler = make_sampler("scenic", name)
        inst = sampler.sample(5)
        assert inst.name == name and inst == sampler.sample(5)
        for spec in inst.agents.values():
            assert spec.route[0] in "WSEN" and spec.route[1] in ("straight", "left", "right")
            assert spec.task in TASKS and 0 <= spec.style <= 1 and spec.initial_speed >= 0
    tie = make_sampler("scenic", "tie", style_A=1.0, style_B=0.0).sample(0)
    assert tie.agents["A"].initial_speed == pytest.approx(11.0) and tie.agents["B"].initial_speed == pytest.approx(6.0)
    assert abs(tie.arrival_offset) <= 0.3
    with pytest.raises(ValueError):
        make_sampler("python", "tie")  # the probes exist as Scenic files only


def test_three_cars_two_on_the_same_route():
    lane = straight((0, 0), (100, 0))
    routes = {"A1": lane, "A2": straight((0, 0), (100, 0)), "B": straight((50, 50), (50, -50))}
    g = ConflictGeometry.from_routes(routes)
    assert g.conflicts("A1", "B") and g.conflicts("A2", "B") and not g.conflicts("A1", "A2")  # same lane: no zone
    front, back, crossing = car(40, 0, 0.0, lane), car(20, 0, 0.0, lane), car(50, 0, -math.pi / 2, routes["B"])
    from dfadrive.labels import facts_for
    from dfadrive.world import WorldState

    world = WorldState(0.0, {"A1": front, "A2": back, "B": crossing})
    assert g.leader("A2", world) == "A1" and g.leader("A1", world) is None and g.leader("B", world) is None
    assert facts_for("A1", world, g).other_in_cz and facts_for("B", world, g).own_in_cz
    in_zone = WorldState(0.0, {"A1": car(50, 0, 0.0, lane), "A2": back, "B": car(50, 30, -math.pi / 2, routes["B"])})
    assert facts_for("B", in_zone, g).other_in_cz  # any other car in a zone B shares
    assert not facts_for("A2", in_zone, g).other_in_cz  # A1 ahead in the same lane is not a conflict
