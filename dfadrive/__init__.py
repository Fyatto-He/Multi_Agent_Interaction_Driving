"""Multi-agent driving with one task automaton per vehicle.

Layers (each only depends on the ones above it):

    world.py, labels.py   world facts      what is true now
    tasks.py              task state       how far along is each agent's task
    style.py              style            how an agent drives (never read by the task)
    policy.py             policy interface (world, own DFA state, own style) -> action
    controllers.py        scripted policies
    scenario.py           scenario instances and samplers (Scenic / Python)
    sim/                  simulator adapters (the only place that imports MetaDrive)
    env.py                episode loop tying the layers together
    recorder.py, metrics.py
"""

__version__ = "0.1.0"
