"""Measure how the MetaDrive default vehicle responds to throttle and brake.

The constants ACCEL_PER_THROTTLE, DECEL_PER_BRAKE and MAX_DECEL in
dfadrive/sim/metadrive_adapter.py come from this script. Re-run it after changing the
MetaDrive version or the vehicle model.
"""

import numpy as np
from metadrive.envs.marl_envs import MultiAgentIntersectionEnv
def make(v0, long=5.0):
    return MultiAgentIntersectionEnv(dict(num_agents=1, allow_respawn=False, use_render=False, horizon=2000, log_level=50,
        map_config=dict(exit_length=200, lane_num=1),
        vehicle_config=dict(lidar=dict(num_lasers=0, distance=0, num_others=0), side_detector=dict(num_lasers=0), lane_line_detector=dict(num_lasers=0)),
        agent_configs={"agent0": dict(spawn_lane_index=(">>", ">>>", 0), destination="1X1_1_", spawn_longitude=long, spawn_velocity=[v0, 0.0])}))
def run(v0, u, n=40):
    env = make(v0); env.reset(); v = env.agents["agent0"]; sp = [v.speed]
    for _ in range(n):
        env.step({"agent0": [0.0, u]}); 
        if "agent0" not in env.agents: break
        sp.append(env.agents["agent0"].speed)
    veh = v; info = (veh.max_steering, veh.config["max_engine_force"], veh.config["max_brake_force"], veh.config["mass"] if "mass" in veh.config else None, veh.FRONT_WHEELBASE + veh.REAR_WHEELBASE)
    env.close(); return np.array(sp), info
print("dt=0.1 s. accel [m/s^2] averaged over first 2 s")
for u in (0.25, 0.5, 1.0):
    for v0 in (0.0, 5.0, 10.0):
        sp, info = run(v0, u); print(f" throttle={u:4.2f} v0={v0:4.1f}: a={np.mean(np.diff(sp[:21]))/0.1:5.2f}  v(2s)={sp[20]:5.2f}")
for u in (-0.1, -0.25, -0.5, -1.0):
    sp, info = run(10.0, u); stop = np.argmax(sp < 0.05) if (sp < 0.05).any() else -1
    k = stop if stop > 0 else 20
    print(f" brake={u:5.2f} v0=10: a={(sp[min(k,10)]-sp[0])/(0.1*min(k,10)):6.2f}  stops_at_step={stop} final_speed={sp[-1]:.3f}")
sp, info = run(10.0, 0.0); print(" coast v0=10: a=%.2f" % (np.mean(np.diff(sp[:21]))/0.1))
print("max_steering(deg), max_engine_force, max_brake_force, mass, wheelbase:", info)
