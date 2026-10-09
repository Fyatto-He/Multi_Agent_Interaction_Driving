"""Behavioural style: *how* an agent drives, never *what* it must accomplish.

One scalar in [0, 1] (0 conservative, 1 aggressive), interpolated linearly into four
interpretable parameters. The labeller and the DFAs never see it (decision D3).
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class StyleParams:
    cruise_speed: float  # m/s
    max_accel: float  # m/s^2
    comfort_decel: float  # m/s^2, braking used for planned stops
    commit_margin: float  # s, time gap required before committing to the conflict zone


CONSERVATIVE = StyleParams(cruise_speed=6.0, max_accel=1.5, comfort_decel=2.0, commit_margin=3.0)
# max_accel is capped by the simulated car (2.9 m/s^2 at full throttle), not by taste.
AGGRESSIVE = StyleParams(cruise_speed=11.0, max_accel=2.9, comfort_decel=4.5, commit_margin=0.5)


def style_params(style: float) -> StyleParams:
    if not 0.0 <= style <= 1.0:
        raise ValueError(f"style must be in [0, 1], got {style}")
    mix = lambda lo, hi: lo + style * (hi - lo)
    return StyleParams(
        cruise_speed=mix(CONSERVATIVE.cruise_speed, AGGRESSIVE.cruise_speed),
        max_accel=mix(CONSERVATIVE.max_accel, AGGRESSIVE.max_accel),
        comfort_decel=mix(CONSERVATIVE.comfort_decel, AGGRESSIVE.comfort_decel),
        commit_margin=mix(CONSERVATIVE.commit_margin, AGGRESSIVE.commit_margin),
    )
