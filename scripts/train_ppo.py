"""Train one shared PPO policy for both agents by self-play.

    python scripts/train_ppo.py --name smoke --steps 600000
    python scripts/train_ppo.py --name all_pairs --steps 5000000 --tasks CROSS:YIELD YIELD:CROSS CROSS:CROSS

Writes runs/rl/<name>/: model.zip, config.json, progress.csv (one row per PPO update).
"""

import argparse
import json
import time
from dataclasses import asdict
from pathlib import Path

from stable_baselines3.common.logger import configure

from dfadrive.rl.sb3 import OutcomeLogger, SelfPlayVecEnv, make_ppo
from dfadrive.rl.selfplay import SelfPlayConfig


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--name", default="smoke")
    ap.add_argument("--steps", type=int, default=600_000, help="agent-steps (two per simulator step)")
    ap.add_argument("--sims", type=int, default=8, help="simulator processes")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--tasks", nargs="+", default=["CROSS:YIELD"], help="task pairs A:B, one drawn per episode")
    ap.add_argument("--full-control", action="store_true", help="policy also steers (default: acceleration only)")
    args = ap.parse_args()

    cfg = SelfPlayConfig(tasks=tuple(tuple(p.split(":")) for p in args.tasks), longitudinal_only=not args.full_control)
    out = Path("runs/rl") / args.name
    out.mkdir(parents=True, exist_ok=True)
    env = SelfPlayVecEnv(args.sims, cfg, seed=args.seed)
    model = make_ppo(env, seed=args.seed)
    ppo = {k: getattr(model, k) for k in ("n_steps", "batch_size", "n_epochs", "gamma", "gae_lambda", "ent_coef")}
    ppo.update(learning_rate=model.learning_rate, net_arch=model.policy_kwargs["net_arch"], n_envs=env.num_envs)
    (out / "config.json").write_text(json.dumps(dict(selfplay=asdict(cfg), ppo=ppo, **vars(args)), indent=2))
    model.set_logger(configure(str(out), ["csv"]))
    start = time.time()
    model.learn(total_timesteps=args.steps, callback=OutcomeLogger())
    model.save(out / "model")
    env.close()
    print(f"{model.num_timesteps} agent-steps in {time.time() - start:.0f} s -> {out}/")


if __name__ == "__main__":
    main()
