"""World facts layer, part 2: propositions and the symbol each agent's DFA reads.

Four boolean facts per agent, collapsed to exactly one symbol per step by a fixed
priority. The priority is a modelling choice (decision D2 in docs/02_architecture.md):
it keeps the alphabet at six mutually exclusive symbols, which is what the ACC-MARL
toolchain (dfax, RAD embeddings) expects, at the cost of hiding lower-priority facts in
a step where a higher-priority one holds.
"""

from __future__ import annotations

from dataclasses import dataclass

from .world import ConflictGeometry, WorldState

# Priority order: the first symbol whose condition holds is the one that is read.
SYMBOLS = ("crash", "goal", "both", "own", "other", "none")


@dataclass(frozen=True)
class Facts:
    crashed: bool  # this vehicle collided or left the road
    at_goal: bool  # this vehicle reached the end of its route
    own_in_cz: bool  # this vehicle's footprint overlaps the conflict zone
    other_in_cz: bool  # the other vehicle's footprint overlaps the conflict zone


def facts_for(agent: str, world: WorldState, geometry: ConflictGeometry) -> Facts:
    me, other = world.agents[agent], world.agents[world.other(agent)]
    return Facts(
        crashed=me.collided or me.off_road,
        at_goal=me.arrived,
        own_in_cz=geometry.occupies(me),
        other_in_cz=geometry.occupies(other),
    )


def symbol_of(f: Facts) -> str:
    if f.crashed:
        return "crash"
    if f.at_goal:
        return "goal"
    if f.own_in_cz and f.other_in_cz:
        return "both"
    if f.own_in_cz:
        return "own"
    if f.other_in_cz:
        return "other"
    return "none"
