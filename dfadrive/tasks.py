"""Task state layer: one small DFA per agent, over the symbols of ``labels.SYMBOLS``.

A task says *what* an agent must accomplish; it never mentions speeds, margins or
actions. The three tasks share one alphabet and the tail ``q1 -> q2 -> ACC``.

    CROSS     reach the goal; never crash.
    YIELD     CROSS, and do not enter the conflict zone until the other has cleared it.
    GO_FIRST  CROSS, and enter the conflict zone before the other does.

DFAs are ``dfa.DFA`` objects (github.com/mvcisback/dfa), the base type of the ACC-MARL
toolchain, so they convert to ``dfax`` / RAD embeddings without change (see
``token_dfa``).
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import cached_property

from dfa import DFA, dict2dfa
from dfa.utils import min_distance_to_accept_by_state

from .labels import SYMBOLS

ACC, REJ = "ACC", "REJ"


def _row(default: str, **moves: str) -> dict[str, str]:
    """Transition row: ``default`` for every symbol not named; ``a_b=X`` sets a and b."""
    row = {sym: default for sym in SYMBOLS}
    for syms, target in moves.items():
        for sym in syms.split("_"):
            row[sym] = target
    return row


# Shared tail: inside the zone, then cleared, then at the goal.
_TAIL = {
    "q1": _row("q1", none_other="q2", crash=REJ),
    "q2": _row("q2", goal=ACC, crash=REJ),
    ACC: _row(ACC),
    REJ: _row(REJ),
}

# name -> (start state, {state: {symbol: next state}})
TABLES: dict[str, tuple[str, dict[str, dict[str, str]]]] = {
    "CROSS": ("q0", {"q0": _row("q0", own_both="q1", crash=REJ), **_TAIL}),
    "YIELD": (
        "y0",
        {
            "y0": _row("y0", other="y1", own_both=REJ, crash=REJ),
            "y1": _row("y1", none="y2", own_both=REJ, crash=REJ),
            "y2": _row("y2", own_both="q1", crash=REJ),
            **_TAIL,
        },
    ),
    "GO_FIRST": ("g0", {"g0": _row("g0", own="q1", other_both=REJ, crash=REJ), **_TAIL}),
}

STATE_MEANING = {
    "q0": "approaching",
    "q1": "in the conflict zone",
    "q2": "cleared the zone",
    "y0": "must wait; the other has not entered yet",
    "y1": "must wait; the other is in the zone",
    "y2": "the other has cleared; free to go",
    "g0": "nobody has entered yet",
    ACC: "task accomplished",
    REJ: "task failed",
}

DESCRIPTION = {
    "CROSS": "Reach the goal; never crash.",
    "YIELD": "Reach the goal; never crash; do not enter the conflict zone until the other has cleared it.",
    "GO_FIRST": "Reach the goal; never crash; enter the conflict zone before the other does.",
}

# One global ordering of every state name, used to one-hot encode "own DFA state" across
# tasks. Shared tail states get a shared slot on purpose.
STATE_VOCAB = ("q0", "y0", "y1", "y2", "g0", "q1", "q2", ACC, REJ)


@dataclass(frozen=True)
class Task:
    name: str

    @property
    def start(self) -> str:
        return TABLES[self.name][0]

    @property
    def table(self) -> dict[str, dict[str, str]]:
        return TABLES[self.name][1]

    @property
    def states(self) -> tuple[str, ...]:
        return tuple(self.table)

    @cached_property
    def dfa(self) -> DFA:
        return dict2dfa({q: (q == ACC, row) for q, row in self.table.items()}, start=self.start)

    @cached_property
    def distance_to_accept(self) -> dict[str, int]:
        """Fewest symbols from each state to acceptance; states that cannot accept are absent."""
        return dict(min_distance_to_accept_by_state(self.dfa))

    def token_dfa(self, n_tokens: int = 10) -> DFA:
        """Same automaton over integer tokens 0..n_tokens-1 (unused tokens self-loop).

        This is the form ``dfax.dfa2dfax`` and ``rad_embeddings.Encoder`` accept.
        """
        index = {q: i for i, q in enumerate(self.states)}
        rows = {}
        for q, row in self.table.items():
            moves = {tok: index[q] for tok in range(n_tokens)}
            moves.update({SYMBOLS.index(sym): index[nxt] for sym, nxt in row.items()})
            rows[index[q]] = (q == ACC, moves)
        return dict2dfa(rows, start=index[self.start])


TASKS = {name: Task(name) for name in TABLES}


class TaskMonitor:
    """Tracks one agent's progress through its task. Reads symbols, nothing else."""

    def __init__(self, task: str):
        self.task = TASKS[task]
        self.state = self.task.start

    def step(self, symbol: str) -> str:
        self.state = self.task.table[self.state][symbol]
        return self.state

    @property
    def status(self) -> str:
        return {ACC: "accepted", REJ: "rejected"}.get(self.state, "running")

    @property
    def alive(self) -> bool:
        """Acceptance is still reachable."""
        return self.state in self.task.distance_to_accept

    def forbids(self, symbol: str) -> bool:
        """Would reading ``symbol`` now make acceptance impossible?

        This is how a policy consults its task without knowing which task it has.
        """
        return self.alive and self.task.table[self.state][symbol] not in self.task.distance_to_accept

    @property
    def remaining(self) -> int | None:
        """Fewest symbols still needed to accept; ``None`` once the task is lost."""
        return self.task.distance_to_accept.get(self.state)

    @property
    def next_symbols(self) -> frozenset[str]:
        """Symbols that bring acceptance one step closer from the current state."""
        dist, row = self.task.distance_to_accept, self.task.table[self.state]
        if not self.alive or dist[self.state] == 0:
            return frozenset()
        return frozenset(sym for sym, nxt in row.items() if dist.get(nxt) == dist[self.state] - 1)


# ---------------------------------------------------------------------------- rendering


def transition_table(task: Task) -> str:
    """Markdown transition table: one row per state, one column per symbol."""
    lines = [
        "| state | meaning | " + " | ".join(f"`{s}`" for s in SYMBOLS) + " |",
        "|---|---|" + "---|" * len(SYMBOLS),
    ]
    for q, row in task.table.items():
        name = f"**{q}**" + (" (start)" if q == task.start else "")
        cells = " | ".join("·" if row[s] == q else row[s] for s in SYMBOLS)
        lines.append(f"| {name} | {STATE_MEANING[q]} | {cells} |")
    return "\n".join(lines)


def mermaid(task: Task) -> str:
    """Mermaid state diagram. Self-loops are omitted; every unlisted symbol stays put."""
    lines = ["stateDiagram-v2", f"    [*] --> {task.start}"]
    for q, row in task.table.items():
        if q in (ACC, REJ):
            continue
        by_target: dict[str, list[str]] = {}
        for sym in SYMBOLS:
            if row[sym] != q:
                by_target.setdefault(row[sym], []).append(sym)
        for target, syms in by_target.items():
            lines.append(f"    {q} --> {target}: {' | '.join(syms)}")
    lines += [f"    {ACC} --> [*]"]
    return "\n".join(lines)
