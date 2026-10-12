# probe_tie: 360 episodes, scenario = tie, controller = task

## By task pair (A:B)

| tasks | n | both accepted | A outcome | B outcome | collision | timeout | A first | median PET [s] | min gap [m] |
|---|---|---|---|---|---|---|---|---|---|
| CROSS:CROSS | 90 | 100% | accepted 90 | accepted 90 | 0% | 0% | 61% | 2.6 | 1.64 |
| GO_FIRST:GO_FIRST | 90 | 0% | rejected 62, accepted 28 | accepted 62, rejected 28 | 0% | 0% | 31% | 2.1 | 1.65 |
| CROSS:YIELD | 90 | 100% | accepted 90 | accepted 90 | 0% | 0% | 100% | 3.2 | 1.65 |
| YIELD:CROSS | 90 | 100% | accepted 90 | accepted 90 | 0% | 0% | 0% | 1.8 | 3.03 |

## By task pair and style pair (A:B)

| tasks | styles | n | both accepted | A outcome | B outcome | collision | timeout | A first | median PET [s] | min gap [m] |
|---|---|---|---|---|---|---|---|---|---|---|
| CROSS:CROSS | 0.1:0.1 | 10 | 100% | accepted 10 | accepted 10 | 0% | 0% | 60% | 3.7 | 1.65 |
| CROSS:CROSS | 0.1:0.5 | 10 | 100% | accepted 10 | accepted 10 | 0% | 0% | 40% | 2.1 | 1.65 |
| CROSS:CROSS | 0.1:0.9 | 10 | 100% | accepted 10 | accepted 10 | 0% | 0% | 10% | 2.1 | 1.65 |
| CROSS:CROSS | 0.5:0.1 | 10 | 100% | accepted 10 | accepted 10 | 0% | 0% | 80% | 3.6 | 1.65 |
| CROSS:CROSS | 0.5:0.5 | 10 | 100% | accepted 10 | accepted 10 | 0% | 0% | 70% | 3.1 | 1.65 |
| CROSS:CROSS | 0.5:0.9 | 10 | 100% | accepted 10 | accepted 10 | 0% | 0% | 30% | 1.8 | 1.65 |
| CROSS:CROSS | 0.9:0.1 | 10 | 100% | accepted 10 | accepted 10 | 0% | 0% | 100% | 3.5 | 1.65 |
| CROSS:CROSS | 0.9:0.5 | 10 | 100% | accepted 10 | accepted 10 | 0% | 0% | 90% | 3.1 | 1.65 |
| CROSS:CROSS | 0.9:0.9 | 10 | 100% | accepted 10 | accepted 10 | 0% | 0% | 70% | 2.4 | 1.64 |
| GO_FIRST:GO_FIRST | 0.1:0.1 | 10 | 0% | rejected 7, accepted 3 | accepted 7, rejected 3 | 0% | 0% | 30% | 2.2 | 1.65 |
| GO_FIRST:GO_FIRST | 0.1:0.5 | 10 | 0% | rejected 7, accepted 3 | accepted 7, rejected 3 | 0% | 0% | 30% | 2.1 | 1.65 |
| GO_FIRST:GO_FIRST | 0.1:0.9 | 10 | 0% | rejected 6, accepted 4 | accepted 6, rejected 4 | 0% | 0% | 40% | 2.1 | 1.65 |
| GO_FIRST:GO_FIRST | 0.5:0.1 | 10 | 0% | rejected 7, accepted 3 | accepted 7, rejected 3 | 0% | 0% | 30% | 1.9 | 1.65 |
| GO_FIRST:GO_FIRST | 0.5:0.5 | 10 | 0% | rejected 7, accepted 3 | accepted 7, rejected 3 | 0% | 0% | 30% | 1.8 | 1.65 |
| GO_FIRST:GO_FIRST | 0.5:0.9 | 10 | 0% | rejected 7, accepted 3 | accepted 7, rejected 3 | 0% | 0% | 30% | 1.8 | 1.65 |
| GO_FIRST:GO_FIRST | 0.9:0.1 | 10 | 0% | rejected 7, accepted 3 | accepted 7, rejected 3 | 0% | 0% | 30% | 1.5 | 1.65 |
| GO_FIRST:GO_FIRST | 0.9:0.5 | 10 | 0% | rejected 7, accepted 3 | accepted 7, rejected 3 | 0% | 0% | 30% | 1.5 | 1.65 |
| GO_FIRST:GO_FIRST | 0.9:0.9 | 10 | 0% | rejected 7, accepted 3 | accepted 7, rejected 3 | 0% | 0% | 30% | 1.5 | 1.65 |
| CROSS:YIELD | 0.1:0.1 | 10 | 100% | accepted 10 | accepted 10 | 0% | 0% | 100% | 3.8 | 1.65 |
| CROSS:YIELD | 0.1:0.5 | 10 | 100% | accepted 10 | accepted 10 | 0% | 0% | 100% | 3.4 | 1.65 |
| CROSS:YIELD | 0.1:0.9 | 10 | 100% | accepted 10 | accepted 10 | 0% | 0% | 100% | 2.6 | 1.65 |
| CROSS:YIELD | 0.5:0.1 | 10 | 100% | accepted 10 | accepted 10 | 0% | 0% | 100% | 3.6 | 1.65 |
| CROSS:YIELD | 0.5:0.5 | 10 | 100% | accepted 10 | accepted 10 | 0% | 0% | 100% | 3.2 | 1.65 |
| CROSS:YIELD | 0.5:0.9 | 10 | 100% | accepted 10 | accepted 10 | 0% | 0% | 100% | 2.5 | 1.65 |
| CROSS:YIELD | 0.9:0.1 | 10 | 100% | accepted 10 | accepted 10 | 0% | 0% | 100% | 3.5 | 1.65 |
| CROSS:YIELD | 0.9:0.5 | 10 | 100% | accepted 10 | accepted 10 | 0% | 0% | 100% | 3.1 | 1.65 |
| CROSS:YIELD | 0.9:0.9 | 10 | 100% | accepted 10 | accepted 10 | 0% | 0% | 100% | 2.4 | 1.65 |
| YIELD:CROSS | 0.1:0.1 | 10 | 100% | accepted 10 | accepted 10 | 0% | 0% | 0% | 2.1 | 3.06 |
| YIELD:CROSS | 0.1:0.5 | 10 | 100% | accepted 10 | accepted 10 | 0% | 0% | 0% | 2.1 | 3.09 |
| YIELD:CROSS | 0.1:0.9 | 10 | 100% | accepted 10 | accepted 10 | 0% | 0% | 0% | 2.1 | 3.11 |
| YIELD:CROSS | 0.5:0.1 | 10 | 100% | accepted 10 | accepted 10 | 0% | 0% | 0% | 1.8 | 3.05 |
| YIELD:CROSS | 0.5:0.5 | 10 | 100% | accepted 10 | accepted 10 | 0% | 0% | 0% | 1.8 | 3.07 |
| YIELD:CROSS | 0.5:0.9 | 10 | 100% | accepted 10 | accepted 10 | 0% | 0% | 0% | 1.8 | 3.08 |
| YIELD:CROSS | 0.9:0.1 | 10 | 100% | accepted 10 | accepted 10 | 0% | 0% | 0% | 1.5 | 3.03 |
| YIELD:CROSS | 0.9:0.5 | 10 | 100% | accepted 10 | accepted 10 | 0% | 0% | 0% | 1.5 | 3.06 |
| YIELD:CROSS | 0.9:0.9 | 10 | 100% | accepted 10 | accepted 10 | 0% | 0% | 0% | 1.5 | 3.07 |
