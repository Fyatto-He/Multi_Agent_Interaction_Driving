# probe_standing_start: 360 episodes, scenario = standing_start, controller = task

## By task pair (A:B)

| tasks | n | both accepted | A outcome | B outcome | collision | timeout | A first | median PET [s] | min gap [m] |
|---|---|---|---|---|---|---|---|---|---|
| CROSS:CROSS | 90 | 100% | accepted 90 | accepted 90 | 0% | 0% | 50% | 2.4 | 1.65 |
| GO_FIRST:GO_FIRST | 90 | 0% | accepted 48, rejected 42 | rejected 54, accepted 36 | 7% | 0% | 60% | 2.1 | 0.08 |
| CROSS:YIELD | 90 | 100% | accepted 90 | accepted 90 | 0% | 0% | 100% | 3.2 | 1.65 |
| YIELD:CROSS | 90 | 100% | accepted 90 | accepted 90 | 0% | 0% | 0% | 1.8 | 3.05 |

## By task pair and style pair (A:B)

| tasks | styles | n | both accepted | A outcome | B outcome | collision | timeout | A first | median PET [s] | min gap [m] |
|---|---|---|---|---|---|---|---|---|---|---|
| CROSS:CROSS | 0.1:0.1 | 10 | 100% | accepted 10 | accepted 10 | 0% | 0% | 50% | 3.7 | 1.65 |
| CROSS:CROSS | 0.1:0.5 | 10 | 100% | accepted 10 | accepted 10 | 0% | 0% | 100% | 3.3 | 1.65 |
| CROSS:CROSS | 0.1:0.9 | 10 | 100% | accepted 10 | accepted 10 | 0% | 0% | 0% | 2.1 | 3.19 |
| CROSS:CROSS | 0.5:0.1 | 10 | 100% | accepted 10 | accepted 10 | 0% | 0% | 0% | 1.8 | 3.05 |
| CROSS:CROSS | 0.5:0.5 | 10 | 100% | accepted 10 | accepted 10 | 0% | 0% | 50% | 3.1 | 1.65 |
| CROSS:CROSS | 0.5:0.9 | 10 | 100% | accepted 10 | accepted 10 | 0% | 0% | 80% | 2.4 | 1.65 |
| CROSS:CROSS | 0.9:0.1 | 10 | 100% | accepted 10 | accepted 10 | 0% | 0% | 100% | 3.5 | 1.65 |
| CROSS:CROSS | 0.9:0.5 | 10 | 100% | accepted 10 | accepted 10 | 0% | 0% | 20% | 1.5 | 1.65 |
| CROSS:CROSS | 0.9:0.9 | 10 | 100% | accepted 10 | accepted 10 | 0% | 0% | 50% | 2.4 | 1.65 |
| GO_FIRST:GO_FIRST | 0.1:0.1 | 10 | 0% | accepted 6, rejected 4 | rejected 6, accepted 4 | 0% | 0% | 60% | 2.1 | 1.10 |
| GO_FIRST:GO_FIRST | 0.1:0.5 | 10 | 0% | rejected 10 | accepted 10 | 0% | 0% | 0% | 2.1 | 3.16 |
| GO_FIRST:GO_FIRST | 0.1:0.9 | 10 | 0% | rejected 10 | accepted 10 | 0% | 0% | 0% | 2.1 | 3.19 |
| GO_FIRST:GO_FIRST | 0.5:0.1 | 10 | 0% | accepted 10 | rejected 10 | 0% | 0% | 100% | 3.6 | 1.65 |
| GO_FIRST:GO_FIRST | 0.5:0.5 | 10 | 0% | accepted 8, rejected 2 | rejected 8, accepted 2 | 0% | 0% | 80% | 1.8 | 0.18 |
| GO_FIRST:GO_FIRST | 0.5:0.9 | 10 | 0% | rejected 10 | accepted 8, rejected 2 | 20% | 0% | 20% | 1.8 | 0.34 |
| GO_FIRST:GO_FIRST | 0.9:0.1 | 10 | 0% | accepted 10 | rejected 10 | 0% | 0% | 100% | 3.5 | 1.65 |
| GO_FIRST:GO_FIRST | 0.9:0.5 | 10 | 0% | accepted 10 | rejected 10 | 0% | 0% | 100% | 3.1 | 1.65 |
| GO_FIRST:GO_FIRST | 0.9:0.9 | 10 | 0% | rejected 6, accepted 4 | rejected 8, accepted 2 | 40% | 0% | 80% | 1.2 | 0.08 |
| CROSS:YIELD | 0.1:0.1 | 10 | 100% | accepted 10 | accepted 10 | 0% | 0% | 100% | 3.8 | 1.65 |
| CROSS:YIELD | 0.1:0.5 | 10 | 100% | accepted 10 | accepted 10 | 0% | 0% | 100% | 3.4 | 1.65 |
| CROSS:YIELD | 0.1:0.9 | 10 | 100% | accepted 10 | accepted 10 | 0% | 0% | 100% | 2.6 | 1.65 |
| CROSS:YIELD | 0.5:0.1 | 10 | 100% | accepted 10 | accepted 10 | 0% | 0% | 100% | 3.6 | 1.65 |
| CROSS:YIELD | 0.5:0.5 | 10 | 100% | accepted 10 | accepted 10 | 0% | 0% | 100% | 3.2 | 1.65 |
| CROSS:YIELD | 0.5:0.9 | 10 | 100% | accepted 10 | accepted 10 | 0% | 0% | 100% | 2.5 | 1.65 |
| CROSS:YIELD | 0.9:0.1 | 10 | 100% | accepted 10 | accepted 10 | 0% | 0% | 100% | 3.5 | 1.65 |
| CROSS:YIELD | 0.9:0.5 | 10 | 100% | accepted 10 | accepted 10 | 0% | 0% | 100% | 3.1 | 1.65 |
| CROSS:YIELD | 0.9:0.9 | 10 | 100% | accepted 10 | accepted 10 | 0% | 0% | 100% | 2.4 | 1.65 |
| YIELD:CROSS | 0.1:0.1 | 10 | 100% | accepted 10 | accepted 10 | 0% | 0% | 0% | 2.2 | 3.06 |
| YIELD:CROSS | 0.1:0.5 | 10 | 100% | accepted 10 | accepted 10 | 0% | 0% | 0% | 2.1 | 3.09 |
| YIELD:CROSS | 0.1:0.9 | 10 | 100% | accepted 10 | accepted 10 | 0% | 0% | 0% | 2.1 | 3.19 |
| YIELD:CROSS | 0.5:0.1 | 10 | 100% | accepted 10 | accepted 10 | 0% | 0% | 0% | 1.8 | 3.05 |
| YIELD:CROSS | 0.5:0.5 | 10 | 100% | accepted 10 | accepted 10 | 0% | 0% | 0% | 1.8 | 3.07 |
| YIELD:CROSS | 0.5:0.9 | 10 | 100% | accepted 10 | accepted 10 | 0% | 0% | 0% | 1.8 | 3.07 |
| YIELD:CROSS | 0.9:0.1 | 10 | 100% | accepted 10 | accepted 10 | 0% | 0% | 0% | 1.5 | 3.05 |
| YIELD:CROSS | 0.9:0.5 | 10 | 100% | accepted 10 | accepted 10 | 0% | 0% | 0% | 1.5 | 3.07 |
| YIELD:CROSS | 0.9:0.9 | 10 | 100% | accepted 10 | accepted 10 | 0% | 0% | 0% | 1.5 | 3.07 |
