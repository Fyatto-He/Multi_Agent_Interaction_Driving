"""Three cars from three arms, with a turn, all arriving together.

    A  west to east, straight
    B  from the east, turning left (across A, and across C)
    C  south to north, straight

Every pair of paths crosses, so any order needs all three to agree. All hold CROSS.
Timing as in four_way.scenic.
"""

param route_A = "W:straight"
param route_B = "E:left"
param route_C = "S:straight"

param task_A = "CROSS"
param task_B = "CROSS"
param task_C = "CROSS"

param style_A = Range(0, 1)
param style_B = Range(0, 1)
param style_C = Range(0, 1)

param speed_A = 6 + 5 * globalParameters.style_A
param speed_B = 6 + 5 * globalParameters.style_B
param speed_C = 6 + 5 * globalParameters.style_C

param arrival_time = Range(3.5, 5.0)
param arrival_offset = 0

param distance_A = globalParameters.speed_A * (globalParameters.arrival_time + Range(-0.5, 0.5))
param distance_B = globalParameters.speed_B * (globalParameters.arrival_time + Range(-0.5, 0.5))
param distance_C = globalParameters.speed_C * (globalParameters.arrival_time + Range(-0.5, 0.5))
