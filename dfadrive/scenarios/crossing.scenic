"""Style probe: right-angle crossing, a tie.

A goes straight west to east, B goes straight south to north. Unlike the left turn,
neither path is longer or slower than the other, so the geometry favours nobody.
Speeds and timing as in tie.scenic.
"""

param route_A = "W:straight"
param route_B = "S:straight"

param task_A = "CROSS"
param task_B = "CROSS"

param style_A = Range(0, 1)
param style_B = Range(0, 1)

param speed_A = 6 + 5 * globalParameters.style_A
param speed_B = 6 + 5 * globalParameters.style_B
param distance_A = Range(30, 45)

param arrival_offset = Range(-0.3, 0.3)

distance_B = globalParameters.speed_B * (
    globalParameters.distance_A / globalParameters.speed_A + globalParameters.arrival_offset
)
param distance_B = distance_B
require 15 <= distance_B <= 65
