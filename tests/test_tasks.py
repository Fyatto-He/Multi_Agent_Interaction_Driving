import itertools

import pytest

from dfadrive.labels import SYMBOLS, Facts, symbol_of
from dfadrive.tasks import ACC, REJ, STATE_VOCAB, TASKS, TaskMonitor, mermaid, transition_table


def run(task, word):
    m = TaskMonitor(task)
    for sym in word:
        m.step(sym)
    return m


@pytest.mark.parametrize("task", TASKS.values(), ids=list(TASKS))
def test_dfa_is_complete_and_minimal(task):
    for row in task.table.values():
        assert set(row) == set(SYMBOLS)
        assert set(row.values()) <= set(task.table)
    assert len(task.dfa.minimize().states()) == len(task.states)
    assert set(task.states) <= set(STATE_VOCAB)


def test_cross():
    assert run("CROSS", ["none", "own", "own", "none", "goal"]).status == "accepted"
    assert run("CROSS", ["other", "both", "other", "goal"]).status == "accepted"  # order is free
    assert run("CROSS", ["none", "own", "crash"]).status == "rejected"
    assert run("CROSS", ["none", "own", "none"]).status == "running"  # timeout = unfinished


def test_yield_requires_the_other_to_clear_first():
    assert run("YIELD", ["none", "other", "none", "own", "none", "goal"]).status == "accepted"
    assert run("YIELD", ["none", "own"]).status == "rejected"  # entered before the other came
    assert run("YIELD", ["other", "both"]).status == "rejected"  # entered while the other was inside
    assert run("YIELD", ["none"] * 50).state == "y0"  # the other never comes: stuck, not failed


def test_go_first_requires_strict_precedence():
    assert run("GO_FIRST", ["none", "own", "both", "other", "goal"]).status == "accepted"
    assert run("GO_FIRST", ["none", "other"]).status == "rejected"
    assert run("GO_FIRST", ["none", "both"]).status == "rejected"  # a tie is not "first"


def test_joint_satisfiability():
    """One interleaving of zone occupancy, read by both agents from their own side."""
    mirror = {"own": "other", "other": "own"}
    a_then_b = ["none", "own", "none", "other", "none", "goal"]  # as seen by A
    seen_by_b = [mirror.get(s, s) for s in a_then_b[:-1]] + ["none", "goal"]
    assert run("GO_FIRST", a_then_b).status == "accepted"
    assert run("YIELD", seen_by_b).status == "accepted"
    assert run("GO_FIRST", seen_by_b).status == "rejected"  # both cannot be first
    assert run("YIELD", a_then_b).status == "rejected"  # A went first, so A did not yield


def test_forbids_is_how_a_policy_reads_its_task():
    assert TaskMonitor("YIELD").forbids("own") and not TaskMonitor("YIELD").forbids("other")
    assert TaskMonitor("GO_FIRST").forbids("other") and not TaskMonitor("GO_FIRST").forbids("own")
    assert not any(TaskMonitor("CROSS").forbids(s) for s in ("own", "other", "both"))
    assert all(TaskMonitor(t).forbids("crash") for t in TASKS)
    lost = run("YIELD", ["own"])
    assert lost.state == REJ and not lost.alive and not lost.forbids("own")  # nothing left to protect


def test_token_dfa_matches_symbol_dfa():
    for task in TASKS.values():
        tokens = task.token_dfa(n_tokens=10)
        assert set(tokens.inputs) == set(range(10))
        for word in itertools.product(SYMBOLS, repeat=4):
            assert tokens.label([SYMBOLS.index(s) for s in word]) == (run(task.name, word).state == ACC)


def test_symbol_priority_is_total():
    seen = set()
    for bits in itertools.product([False, True], repeat=4):
        f = Facts(*bits)
        sym = symbol_of(f)
        seen.add(sym)
        if f.crashed:
            assert sym == "crash"
        elif f.at_goal:
            assert sym == "goal"
    assert seen == set(SYMBOLS)


def test_rendering_mentions_every_state():
    for task in TASKS.values():
        table, diagram = transition_table(task), mermaid(task)
        assert all(f"**{q}**" in table for q in task.states)
        assert diagram.startswith("stateDiagram-v2") and f"[*] --> {task.start}" in diagram
