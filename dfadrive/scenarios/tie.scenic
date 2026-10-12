"""Style probe: nobody is clearly first.

Same geometry as the unprotected left turn (A straight, B turning left across A), but
each car starts at the cruise speed of its own style and the two would reach the
conflict zone within 0.3 s of each other if neither reacted. Whatever decides the order
here is the task and the style, not the starting position.
"""

param route_A = "W:straight"
param route_B = "E:left"

param task_A = "CROSS"
param task_B = "CROSS"

param style_A = Range(0, 1)
param style_B = Range(0, 1)

# Start at the style's own cruise speed (6 m/s at style 0, 11 m/s at style 1; see style.py),
# so "arrival_offset" is what would happen if both simply kept driving.
param speed_A = 6 + 5 * globalParameters.style_A
param speed_B = 6 + 5 * globalParameters.style_B
param distance_A = Range(30, 45)       # m, front bumper to the conflict zone

param arrival_offset = Range(-0.3, 0.3)  # s, t_B - t_A at the zone: a tie

distance_B = globalParameters.speed_B * (
    globalParameters.distance_A / globalParameters.speed_A + globalParameters.arrival_offset
)
param distance_B = distance_B
require 15 <= distance_B <= 65
