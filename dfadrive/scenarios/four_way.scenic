"""Four cars, one from each arm, all going straight, all arriving together.

An uncontrolled intersection at its busiest: every car crosses two others' paths, no
task says who goes first (all hold CROSS), and nobody has a head start. Each car starts
at the cruise speed of its own style and would reach the intersection within half a
second of the common arrival time.
"""

param route_A = "W:straight"
param route_B = "S:straight"
param route_C = "E:straight"
param route_D = "N:straight"

param task_A = "CROSS"
param task_B = "CROSS"
param task_C = "CROSS"
param task_D = "CROSS"

param style_A = Range(0, 1)
param style_B = Range(0, 1)
param style_C = Range(0, 1)
param style_D = Range(0, 1)

param speed_A = 6 + 5 * globalParameters.style_A
param speed_B = 6 + 5 * globalParameters.style_B
param speed_C = 6 + 5 * globalParameters.style_C
param speed_D = 6 + 5 * globalParameters.style_D

param arrival_time = Range(3.5, 5.0)     # s until the cars would reach the intersection
param arrival_offset = 0                 # two-car notion; unused here

# Each car's distance puts it at the intersection at the common time, give or take 0.5 s.
param distance_A = globalParameters.speed_A * (globalParameters.arrival_time + Range(-0.5, 0.5))
param distance_B = globalParameters.speed_B * (globalParameters.arrival_time + Range(-0.5, 0.5))
param distance_C = globalParameters.speed_C * (globalParameters.arrival_time + Range(-0.5, 0.5))
param distance_D = globalParameters.speed_D * (globalParameters.arrival_time + Range(-0.5, 0.5))
