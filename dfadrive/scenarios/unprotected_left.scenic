"""Unprotected left turn at a four-way intersection.

    A  enters from the west and goes straight.
    B  enters from the east and turns left, across A's lane.

Scenic is used here as a constrained sampler only: this file has no world model and no
objects. Every quantity is route-relative (distances along each agent's own route), so
the file does not depend on a particular map or simulator. Any `param` can be fixed from
Python (`ScenicSampler(overrides={...})`).
"""

# --- routes: "entry arm:manoeuvre" (arms W, S, E, N)
param route_A = "W:straight"
param route_B = "E:left"

# --- intent: which task automaton each agent holds (see dfadrive/tasks.py)
param task_A = "CROSS"
param task_B = "YIELD"

# --- style: 0 = conservative, 1 = aggressive. Not part of the task.
param style_A = Range(0, 1)
param style_B = Range(0, 1)

# --- initial conditions
param speed_A = Range(5, 10)         # m/s
param speed_B = Range(5, 10)         # m/s
param distance_A = Range(25, 50)     # m, front bumper to the conflict zone

# --- timing: nominal arrival-time difference at the conflict zone, t_B - t_A, if both
#     kept their initial speed. 0 means they would meet; |offset| large means no conflict.
param arrival_offset = Range(-2, 2)  # s

distance_B = globalParameters.speed_B * (
    globalParameters.distance_A / globalParameters.speed_A + globalParameters.arrival_offset
)
param distance_B = distance_B        # m, derived

require 15 <= distance_B <= 60       # B must start on its approach lane
