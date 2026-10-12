# probe_crossing: 360 episodes, scenario = crossing, controller = task

## By task pair (A:B)

| tasks | n | both accepted | A outcome | B outcome | collision | timeout | A first | median PET [s] | min gap [m] |
|---|---|---|---|---|---|---|---|---|---|
| CROSS:CROSS | 90 | 100% | accepted 90 | accepted 90 | 0% | 0% | 60% | 1.5 | 2.17 |
| GO_FIRST:GO_FIRST | 90 | 0% | rejected 62, accepted 28 | accepted 62, rejected 28 | 0% | 0% | 31% | 1.4 | 2.80 |
| CROSS:YIELD | 90 | 100% | accepted 90 | accepted 90 | 0% | 0% | 100% | 1.5 | 2.81 |
| YIELD:CROSS | 90 | 100% | accepted 90 | accepted 90 | 0% | 0% | 0% | 1.5 | 2.80 |

## By task pair and style pair (A:B)

| tasks | styles | n | both accepted | A outcome | B outcome | collision | timeout | A first | median PET [s] | min gap [m] |
|---|---|---|---|---|---|---|---|---|---|---|
| CROSS:CROSS | 0.1:0.1 | 10 | 100% | accepted 10 | accepted 10 | 0% | 0% | 60% | 1.8 | 2.54 |
| CROSS:CROSS | 0.1:0.5 | 10 | 100% | accepted 10 | accepted 10 | 0% | 0% | 40% | 1.8 | 2.72 |
| CROSS:CROSS | 0.1:0.9 | 10 | 100% | accepted 10 | accepted 10 | 0% | 0% | 10% | 1.8 | 2.82 |
| CROSS:CROSS | 0.5:0.1 | 10 | 100% | accepted 10 | accepted 10 | 0% | 0% | 80% | 1.8 | 2.75 |
| CROSS:CROSS | 0.5:0.5 | 10 | 100% | accepted 10 | accepted 10 | 0% | 0% | 60% | 1.5 | 2.75 |
| CROSS:CROSS | 0.5:0.9 | 10 | 100% | accepted 10 | accepted 10 | 0% | 0% | 30% | 1.5 | 2.49 |
| CROSS:CROSS | 0.9:0.1 | 10 | 100% | accepted 10 | accepted 10 | 0% | 0% | 100% | 1.8 | 2.84 |
| CROSS:CROSS | 0.9:0.5 | 10 | 100% | accepted 10 | accepted 10 | 0% | 0% | 90% | 1.5 | 2.82 |
| CROSS:CROSS | 0.9:0.9 | 10 | 100% | accepted 10 | accepted 10 | 0% | 0% | 70% | 1.4 | 2.17 |
| GO_FIRST:GO_FIRST | 0.1:0.1 | 10 | 0% | rejected 7, accepted 3 | accepted 7, rejected 3 | 0% | 0% | 30% | 1.8 | 2.83 |
| GO_FIRST:GO_FIRST | 0.1:0.5 | 10 | 0% | rejected 7, accepted 3 | accepted 7, rejected 3 | 0% | 0% | 30% | 1.7 | 2.82 |
| GO_FIRST:GO_FIRST | 0.1:0.9 | 10 | 0% | rejected 6, accepted 4 | accepted 6, rejected 4 | 0% | 0% | 40% | 1.4 | 2.80 |
| GO_FIRST:GO_FIRST | 0.5:0.1 | 10 | 0% | rejected 7, accepted 3 | accepted 7, rejected 3 | 0% | 0% | 30% | 1.5 | 2.82 |
| GO_FIRST:GO_FIRST | 0.5:0.5 | 10 | 0% | rejected 7, accepted 3 | accepted 7, rejected 3 | 0% | 0% | 30% | 1.6 | 2.83 |
| GO_FIRST:GO_FIRST | 0.5:0.9 | 10 | 0% | rejected 7, accepted 3 | accepted 7, rejected 3 | 0% | 0% | 30% | 1.4 | 2.84 |
| GO_FIRST:GO_FIRST | 0.9:0.1 | 10 | 0% | rejected 7, accepted 3 | accepted 7, rejected 3 | 0% | 0% | 30% | 1.4 | 2.80 |
| GO_FIRST:GO_FIRST | 0.9:0.5 | 10 | 0% | rejected 7, accepted 3 | accepted 7, rejected 3 | 0% | 0% | 30% | 1.4 | 2.80 |
| GO_FIRST:GO_FIRST | 0.9:0.9 | 10 | 0% | rejected 7, accepted 3 | accepted 7, rejected 3 | 0% | 0% | 30% | 1.1 | 2.91 |
| CROSS:YIELD | 0.1:0.1 | 10 | 100% | accepted 10 | accepted 10 | 0% | 0% | 100% | 1.8 | 2.84 |
| CROSS:YIELD | 0.1:0.5 | 10 | 100% | accepted 10 | accepted 10 | 0% | 0% | 100% | 1.5 | 2.82 |
| CROSS:YIELD | 0.1:0.9 | 10 | 100% | accepted 10 | accepted 10 | 0% | 0% | 100% | 1.4 | 2.81 |
| CROSS:YIELD | 0.5:0.1 | 10 | 100% | accepted 10 | accepted 10 | 0% | 0% | 100% | 1.8 | 2.84 |
| CROSS:YIELD | 0.5:0.5 | 10 | 100% | accepted 10 | accepted 10 | 0% | 0% | 100% | 1.5 | 2.82 |
| CROSS:YIELD | 0.5:0.9 | 10 | 100% | accepted 10 | accepted 10 | 0% | 0% | 100% | 1.4 | 2.81 |
| CROSS:YIELD | 0.9:0.1 | 10 | 100% | accepted 10 | accepted 10 | 0% | 0% | 100% | 1.8 | 2.84 |
| CROSS:YIELD | 0.9:0.5 | 10 | 100% | accepted 10 | accepted 10 | 0% | 0% | 100% | 1.5 | 2.82 |
| CROSS:YIELD | 0.9:0.9 | 10 | 100% | accepted 10 | accepted 10 | 0% | 0% | 100% | 1.4 | 2.81 |
| YIELD:CROSS | 0.1:0.1 | 10 | 100% | accepted 10 | accepted 10 | 0% | 0% | 0% | 1.8 | 2.84 |
| YIELD:CROSS | 0.1:0.5 | 10 | 100% | accepted 10 | accepted 10 | 0% | 0% | 0% | 1.8 | 2.84 |
| YIELD:CROSS | 0.1:0.9 | 10 | 100% | accepted 10 | accepted 10 | 0% | 0% | 0% | 1.8 | 2.84 |
| YIELD:CROSS | 0.5:0.1 | 10 | 100% | accepted 10 | accepted 10 | 0% | 0% | 0% | 1.5 | 2.82 |
| YIELD:CROSS | 0.5:0.5 | 10 | 100% | accepted 10 | accepted 10 | 0% | 0% | 0% | 1.5 | 2.82 |
| YIELD:CROSS | 0.5:0.9 | 10 | 100% | accepted 10 | accepted 10 | 0% | 0% | 0% | 1.5 | 2.82 |
| YIELD:CROSS | 0.9:0.1 | 10 | 100% | accepted 10 | accepted 10 | 0% | 0% | 0% | 1.4 | 2.80 |
| YIELD:CROSS | 0.9:0.5 | 10 | 100% | accepted 10 | accepted 10 | 0% | 0% | 0% | 1.4 | 2.80 |
| YIELD:CROSS | 0.9:0.9 | 10 | 100% | accepted 10 | accepted 10 | 0% | 0% | 0% | 1.4 | 2.80 |
