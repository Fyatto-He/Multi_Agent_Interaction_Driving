# cmp_gap: 300 episodes, three cars, B must yield


## controller = task: share of episodes in which B goes between A1 and A2

| B's style | headway 2 s | headway 3 s | headway 4 s | headway 5 s | headway 6 s | all accepted | collisions |
|---|---|---|---|---|---|---|---|
| 0.1 | 0% | 0% | 0% | 0% | 0% | 50/50 | 0 |
| 0.5 | 0% | 0% | 0% | 0% | 0% | 50/50 | 0 |
| 0.9 | 0% | 0% | 0% | 20% | 30% | 50/50 | 0 |

## controller = full: share of episodes in which B goes between A1 and A2

| B's style | headway 2 s | headway 3 s | headway 4 s | headway 5 s | headway 6 s | all accepted | collisions |
|---|---|---|---|---|---|---|---|
| 0.1 | 0% | 0% | 0% | 100% | 100% | 50/50 | 0 |
| 0.5 | 0% | 100% | 100% | 100% | 100% | 50/50 | 0 |
| 0.9 | 0% | 100% | 100% | 100% | 100% | 50/50 | 0 |
