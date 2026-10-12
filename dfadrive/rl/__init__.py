"""Learning layer (decision D4): parameter-shared independent PPO.

    reward.py     per-agent reward: task outcome, DFA-progress shaping, collision, style
    selfplay.py   one simulator, two learners sharing a policy; arrays in, arrays out
    sb3.py        the only module that imports Stable-Baselines3 / PyTorch
"""
