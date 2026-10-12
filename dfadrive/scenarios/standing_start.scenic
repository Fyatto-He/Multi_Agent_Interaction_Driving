"""Style probe: both cars start at rest just before the conflict zone.

Like two drivers who have both stopped at an all-way stop. There is no momentum and no
head start; the only question is who moves first and whether the other lets them.
Geometry of the unprotected left turn.
"""

param route_A = "W:straight"
param route_B = "E:left"

param task_A = "CROSS"
param task_B = "CROSS"

param style_A = Range(0, 1)
param style_B = Range(0, 1)

param speed_A = 0
param speed_B = 0
param distance_A = Range(9, 12)        # m; 9 m is as close as A's approach lane allows
param distance_B = Range(9, 12)

param arrival_offset = 0               # not meaningful from rest; kept for the record format
