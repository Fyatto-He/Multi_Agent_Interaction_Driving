"""Per-agent reward for learned policies (decision D4, docs/02_architecture.md).

    reward = task outcome            +1 on accept, -1 on reject          (sparse, from the DFA)
           + shaping                 difference of a potential on DFA progress
           + collision               extra penalty for a crash
           + style                   costs whose weights or thresholds depend on the agent's style

The task terms never read the style, and the style terms never read the task: intent and
style stay separate in the objective as they are everywhere else.

Shaping potential. Let ``k`` be the fewest symbols the agent's DFA still needs to accept,
and ``f`` in [0, 1] the remaining fraction of the driving needed to produce the next of
those symbols (distance to the zone, to clearing it, or to the goal). Then

    Phi = -shaping * (k - 1 + f)

which is continuous across DFA transitions, 0 at acceptance, and constant while the
next symbol is not the agent's to produce (a yielding agent waiting for the other).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ..labels import Facts
from ..policy import AgentView
from ..style import style_params
from ..tasks import ACC, REJ

APPROACH = 60.0  # m, distance over which "approaching the zone" is normalised


@dataclass(frozen=True)
class RewardConfig:
    gamma: float = 0.995  # the learner's discount
    accept: float = 1.0
    reject: float = -1.0
    collision: float = -1.0  # in addition to the rejection a crash causes
    shaping: float = 1.0  # potential per DFA step; neutral in theory, sets how loud progress is
    # Style terms. All are costs; only their weight or threshold depends on style.
    time_cost: tuple[float, float] = (0.005, 0.03)  # per second, at style 0 and at style 1
    over_speed: float = 0.5  # per second, per unit of relative excess over the style's cruise speed
    over_accel: float = 0.05  # per second, per m/s^2 beyond the style's acceleration / braking limit
    margin: float = 1.5  # at zone entry, per unit of relative shortfall of the style's time margin


def potential(view: AgentView, cfg: RewardConfig) -> float:
    task, g, a = view.task, view.geometry, view.agent
    me, route = view.world.agents[a], g.routes[a]
    if task.state == ACC:
        return 0.0
    to_goal = max(route.length - me.s, 0.0)
    if not task.alive:  # task lost: one level below any live state, still prefer leaving the road network
        return -cfg.shaping * (max(task.task.distance_to_accept.values()) + to_goal / route.length)
    nxt = task.next_symbols
    if nxt & {"own", "both"}:  # must get into the zone
        f = min(max(g.dist_to_entry(a, me), 0.0) / APPROACH, 1.0)
    elif "goal" in nxt:  # must reach the end of the route
        f = min(to_goal / (route.length - g.exit_s[a]), 1.0)
    elif g.occupies(a, me):  # must get out of the zone
        f = min(max(g.dist_to_clear(a, me), 0.0) / (g.exit_s[a] - g.entry_s[a] + me.length), 1.0)
    else:  # the next symbol is the other agent's to produce
        f = 1.0
    return -cfg.shaping * (task.remaining - 1 + f)


@dataclass
class _Memory:
    phi: float
    speed: float
    entered: bool = False
    exit_time: float | None = None  # when this agent's footprint left the zone


@dataclass
class RewardModel:
    """Stateful only in what a reward needs from the previous step."""

    cfg: RewardConfig = field(default_factory=RewardConfig)
    _mem: dict[str, _Memory] = field(default_factory=dict)

    def reset(self, views: dict[str, AgentView]) -> None:
        self._mem = {a: _Memory(potential(v, self.cfg), v.world.agents[a].speed) for a, v in views.items()}

    def step(self, views: dict[str, AgentView], facts: dict[str, Facts], task_reward: dict[str, float], dt: float):
        """Reward and its breakdown for every agent in ``views`` (those active during this step)."""
        entering = {}
        for a, view in views.items():  # zone bookkeeping first, so both agents see the same step
            mem = self._mem[a]
            entering[a] = facts[a].own_in_cz and not mem.entered
            if facts[a].own_in_cz:
                mem.entered = True
            elif mem.entered and mem.exit_time is None:
                mem.exit_time = view.world.t
        out = {}
        for a, view in views.items():
            mem, me = self._mem[a], view.world.agents[a]
            terms = dict(
                task=task_reward[a] * (self.cfg.accept if task_reward[a] > 0 else -self.cfg.reject),
                collision=self.cfg.collision if facts[a].crashed else 0.0,
                shaping=self._shaping(view, mem, terminal=not me.active),
                **self._style(view, facts[a], mem, entering[a], dt),
            )
            mem.speed = me.speed
            out[a] = (sum(terms.values()), terms)
        return out

    def _shaping(self, view: AgentView, mem: _Memory, terminal: bool) -> float:
        phi = 0.0 if terminal else potential(view, self.cfg)  # a terminal state has no future to shape
        # Undiscounted difference on purpose. The textbook form, gamma * phi' - phi, pays a
        # small positive reward on every step spent standing still (phi is negative), and
        # "everybody stops" then becomes a stable solution that training can fall into.
        # This form pays exactly nothing for standing still. The price: it is no longer
        # strictly neutral, but equal to the neutral form plus a rent of (1 - gamma) * |phi'|
        # per step, i.e. a mild urgency that grows with the distance left to the task.
        shaped = phi - mem.phi
        mem.phi = phi
        return shaped

    def _style(self, view: AgentView, facts: Facts, mem: _Memory, entering: bool, dt: float) -> dict[str, float]:
        cfg, p = self.cfg, style_params(view.style)
        me = view.world.agents[view.agent]
        lo, hi = cfg.time_cost
        accel = (me.speed - mem.speed) / dt
        excess = max(accel - p.max_accel, 0.0) + max(-accel - p.comfort_decel, 0.0)
        terms = dict(
            time=-(lo + view.style * (hi - lo)) * dt,
            over_speed=-cfg.over_speed * max(me.speed - p.cruise_speed, 0.0) / p.cruise_speed * dt,
            over_accel=-cfg.over_accel * excess * dt,
            margin=0.0,
        )
        if entering:  # the step in which this agent's footprint enters the zone
            gap = min(self._gap_to(view, o) for o in view.world.others(view.agent))
            terms["margin"] = -cfg.margin * max(p.commit_margin - gap, 0.0) / p.commit_margin
        return terms

    def _gap_to(self, view: AgentView, other: str) -> float:
        """Time separating this agent's entry from ``other``'s use of the shared zone."""
        g, ot, mem = view.geometry, view.world.agents[other], self._mem.get(other)
        if not g.conflicts(view.agent, other):
            return float("inf")
        if g.blocks(view.agent, other, ot):
            return 0.0
        if mem is not None and mem.exit_time is not None:  # following it: time since it left
            return view.world.t - mem.exit_time
        if not ot.present:
            return float("inf")
        # ahead of it: time until it would arrive at its current speed
        return max(g.dist_to_entry(other, ot), 0.0) / max(ot.speed, 0.1)
