"""Style probe with three cars: the gap between two priority cars.

    A1, A2  enter from the west and go straight, A2 a few seconds behind A1.
    B       enters from the east, turns left across their lane, and must yield.

B's automaton (YIELD) is satisfied once the first car has passed. Whether B then takes
the gap in front of A2 or lets A2 pass as well is not in any task: it is left to style
(decision D5). `headway` is the time between A1 and A2 at the conflict zone.
"""

param route_A1 = "W:straight"
param route_A2 = "W:straight"
param route_B = "E:left"

param task_A1 = "CROSS"
param task_A2 = "CROSS"
param task_B = "YIELD"

param style_A1 = Range(0, 1)
param style_A2 = Range(0, 1)
param style_B = Range(0, 1)

# Everyone starts at the cruise speed of their own style (see style.py).
param speed_A1 = 6 + 5 * globalParameters.style_A1
param speed_A2 = 6 + 5 * globalParameters.style_A2
param speed_B = 6 + 5 * globalParameters.style_B

param distance_A1 = Range(12, 20)    # m, front bumper to the conflict zone
param headway = Range(2, 6)          # s, A2 behind A1 at the zone
param arrival_offset = Range(-0.5, 0.5)  # s, B relative to A1

# Scenic requirements can use local names, not globalParameters, so bind them first.
d_A1 = globalParameters.distance_A1
d_A2 = d_A1 + globalParameters.speed_A2 * globalParameters.headway
d_B = globalParameters.speed_B * (d_A1 / globalParameters.speed_A1 + globalParameters.arrival_offset)
param distance_A2 = d_A2
param distance_B = d_B

require d_A2 - d_A1 >= 10            # A2 starts at least a car length and a gap behind A1
require d_A2 <= 64                   # the approach lane is 66 m long
require 10 <= d_B <= 65
