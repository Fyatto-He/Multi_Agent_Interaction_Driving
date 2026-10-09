# validation: 1620 episodes, controller = task

## By task pair (A:B)

| tasks | n | both accepted | A outcome | B outcome | collision | timeout | A first | median PET [s] | min gap [m] |
|---|---|---|---|---|---|---|---|---|---|
| CROSS:CROSS | 180 | 100% | accepted 180 | accepted 180 | 0% | 0% | 53% | 2.3 | 1.64 |
| CROSS:YIELD | 180 | 100% | accepted 180 | accepted 180 | 0% | 0% | 100% | 3.1 | 1.65 |
| CROSS:GO_FIRST | 180 | 83% | accepted 180 | accepted 149, rejected 31 | 0% | 0% | 17% | 1.8 | 1.65 |
| YIELD:CROSS | 180 | 100% | accepted 180 | accepted 180 | 0% | 0% | 0% | 1.7 | 3.03 |
| YIELD:YIELD | 180 | 0% | unfinished 180 | unfinished 180 | 0% | 100% | – | – | 16.88 |
| YIELD:GO_FIRST | 180 | 100% | accepted 180 | accepted 180 | 0% | 0% | 0% | 1.6 | 3.06 |
| GO_FIRST:CROSS | 180 | 75% | accepted 135, rejected 45 | accepted 180 | 0% | 0% | 75% | 2.9 | 1.65 |
| GO_FIRST:YIELD | 180 | 100% | accepted 180 | accepted 180 | 0% | 0% | 100% | 3.1 | 1.65 |
| GO_FIRST:GO_FIRST | 180 | 0% | rejected 109, accepted 71 | accepted 109, rejected 71 | 0% | 0% | 39% | 2.1 | 1.65 |

## By task pair and style pair (A:B)

| tasks | styles | n | both accepted | A outcome | B outcome | collision | timeout | A first | median PET [s] | min gap [m] |
|---|---|---|---|---|---|---|---|---|---|---|
| CROSS:CROSS | 0.1:0.1 | 20 | 100% | accepted 20 | accepted 20 | 0% | 0% | 60% | 3.7 | 1.65 |
| CROSS:CROSS | 0.1:0.5 | 20 | 100% | accepted 20 | accepted 20 | 0% | 0% | 55% | 3.3 | 1.65 |
| CROSS:CROSS | 0.1:0.9 | 20 | 100% | accepted 20 | accepted 20 | 0% | 0% | 10% | 1.5 | 1.65 |
| CROSS:CROSS | 0.5:0.1 | 20 | 100% | accepted 20 | accepted 20 | 0% | 0% | 50% | 2.5 | 1.65 |
| CROSS:CROSS | 0.5:0.5 | 20 | 100% | accepted 20 | accepted 20 | 0% | 0% | 60% | 3.1 | 1.65 |
| CROSS:CROSS | 0.5:0.9 | 20 | 100% | accepted 20 | accepted 20 | 0% | 0% | 15% | 1.7 | 1.65 |
| CROSS:CROSS | 0.9:0.1 | 20 | 100% | accepted 20 | accepted 20 | 0% | 0% | 85% | 2.9 | 1.65 |
| CROSS:CROSS | 0.9:0.5 | 20 | 100% | accepted 20 | accepted 20 | 0% | 0% | 75% | 2.6 | 1.65 |
| CROSS:CROSS | 0.9:0.9 | 20 | 100% | accepted 20 | accepted 20 | 0% | 0% | 65% | 2.3 | 1.64 |
| CROSS:YIELD | 0.1:0.1 | 20 | 100% | accepted 20 | accepted 20 | 0% | 0% | 100% | 3.8 | 1.65 |
| CROSS:YIELD | 0.1:0.5 | 20 | 100% | accepted 20 | accepted 20 | 0% | 0% | 100% | 3.4 | 1.65 |
| CROSS:YIELD | 0.1:0.9 | 20 | 100% | accepted 20 | accepted 20 | 0% | 0% | 100% | 2.6 | 1.65 |
| CROSS:YIELD | 0.5:0.1 | 20 | 100% | accepted 20 | accepted 20 | 0% | 0% | 100% | 3.6 | 1.65 |
| CROSS:YIELD | 0.5:0.5 | 20 | 100% | accepted 20 | accepted 20 | 0% | 0% | 100% | 3.2 | 1.65 |
| CROSS:YIELD | 0.5:0.9 | 20 | 100% | accepted 20 | accepted 20 | 0% | 0% | 100% | 2.5 | 1.65 |
| CROSS:YIELD | 0.9:0.1 | 20 | 100% | accepted 20 | accepted 20 | 0% | 0% | 100% | 3.4 | 1.65 |
| CROSS:YIELD | 0.9:0.5 | 20 | 100% | accepted 20 | accepted 20 | 0% | 0% | 100% | 3.1 | 1.65 |
| CROSS:YIELD | 0.9:0.9 | 20 | 100% | accepted 20 | accepted 20 | 0% | 0% | 100% | 2.4 | 1.65 |
| CROSS:GO_FIRST | 0.1:0.1 | 20 | 100% | accepted 20 | accepted 20 | 0% | 0% | 0% | 2.1 | 3.09 |
| CROSS:GO_FIRST | 0.1:0.5 | 20 | 100% | accepted 20 | accepted 20 | 0% | 0% | 0% | 1.9 | 3.19 |
| CROSS:GO_FIRST | 0.1:0.9 | 20 | 100% | accepted 20 | accepted 20 | 0% | 0% | 0% | 1.5 | 3.27 |
| CROSS:GO_FIRST | 0.5:0.1 | 20 | 70% | accepted 20 | accepted 14, rejected 6 | 0% | 0% | 30% | 1.9 | 1.65 |
| CROSS:GO_FIRST | 0.5:0.5 | 20 | 100% | accepted 20 | accepted 20 | 0% | 0% | 0% | 1.8 | 3.16 |
| CROSS:GO_FIRST | 0.5:0.9 | 20 | 100% | accepted 20 | accepted 20 | 0% | 0% | 0% | 1.7 | 3.25 |
| CROSS:GO_FIRST | 0.9:0.1 | 20 | 25% | accepted 20 | rejected 15, accepted 5 | 0% | 0% | 75% | 2.8 | 1.65 |
| CROSS:GO_FIRST | 0.9:0.5 | 20 | 70% | accepted 20 | accepted 14, rejected 6 | 0% | 0% | 30% | 1.5 | 1.65 |
| CROSS:GO_FIRST | 0.9:0.9 | 20 | 80% | accepted 20 | accepted 16, rejected 4 | 0% | 0% | 20% | 1.5 | 1.65 |
| YIELD:CROSS | 0.1:0.1 | 20 | 100% | accepted 20 | accepted 20 | 0% | 0% | 0% | 2.1 | 3.07 |
| YIELD:CROSS | 0.1:0.5 | 20 | 100% | accepted 20 | accepted 20 | 0% | 0% | 0% | 2.1 | 3.09 |
| YIELD:CROSS | 0.1:0.9 | 20 | 100% | accepted 20 | accepted 20 | 0% | 0% | 0% | 1.5 | 3.11 |
| YIELD:CROSS | 0.5:0.1 | 20 | 100% | accepted 20 | accepted 20 | 0% | 0% | 0% | 1.8 | 3.04 |
| YIELD:CROSS | 0.5:0.5 | 20 | 100% | accepted 20 | accepted 20 | 0% | 0% | 0% | 1.8 | 3.07 |
| YIELD:CROSS | 0.5:0.9 | 20 | 100% | accepted 20 | accepted 20 | 0% | 0% | 0% | 1.7 | 3.08 |
| YIELD:CROSS | 0.9:0.1 | 20 | 100% | accepted 20 | accepted 20 | 0% | 0% | 0% | 1.5 | 3.03 |
| YIELD:CROSS | 0.9:0.5 | 20 | 100% | accepted 20 | accepted 20 | 0% | 0% | 0% | 1.5 | 3.06 |
| YIELD:CROSS | 0.9:0.9 | 20 | 100% | accepted 20 | accepted 20 | 0% | 0% | 0% | 1.5 | 3.07 |
| YIELD:YIELD | 0.1:0.1 | 20 | 0% | unfinished 20 | unfinished 20 | 0% | 100% | – | – | 16.95 |
| YIELD:YIELD | 0.1:0.5 | 20 | 0% | unfinished 20 | unfinished 20 | 0% | 100% | – | – | 16.93 |
| YIELD:YIELD | 0.1:0.9 | 20 | 0% | unfinished 20 | unfinished 20 | 0% | 100% | – | – | 16.91 |
| YIELD:YIELD | 0.5:0.1 | 20 | 0% | unfinished 20 | unfinished 20 | 0% | 100% | – | – | 16.93 |
| YIELD:YIELD | 0.5:0.5 | 20 | 0% | unfinished 20 | unfinished 20 | 0% | 100% | – | – | 16.91 |
| YIELD:YIELD | 0.5:0.9 | 20 | 0% | unfinished 20 | unfinished 20 | 0% | 100% | – | – | 16.89 |
| YIELD:YIELD | 0.9:0.1 | 20 | 0% | unfinished 20 | unfinished 20 | 0% | 100% | – | – | 16.90 |
| YIELD:YIELD | 0.9:0.5 | 20 | 0% | unfinished 20 | unfinished 20 | 0% | 100% | – | – | 16.89 |
| YIELD:YIELD | 0.9:0.9 | 20 | 0% | unfinished 20 | unfinished 20 | 0% | 100% | – | – | 16.88 |
| YIELD:GO_FIRST | 0.1:0.1 | 20 | 100% | accepted 20 | accepted 20 | 0% | 0% | 0% | 2.1 | 3.09 |
| YIELD:GO_FIRST | 0.1:0.5 | 20 | 100% | accepted 20 | accepted 20 | 0% | 0% | 0% | 1.9 | 3.19 |
| YIELD:GO_FIRST | 0.1:0.9 | 20 | 100% | accepted 20 | accepted 20 | 0% | 0% | 0% | 1.5 | 3.27 |
| YIELD:GO_FIRST | 0.5:0.1 | 20 | 100% | accepted 20 | accepted 20 | 0% | 0% | 0% | 1.8 | 3.07 |
| YIELD:GO_FIRST | 0.5:0.5 | 20 | 100% | accepted 20 | accepted 20 | 0% | 0% | 0% | 1.8 | 3.16 |
| YIELD:GO_FIRST | 0.5:0.9 | 20 | 100% | accepted 20 | accepted 20 | 0% | 0% | 0% | 1.7 | 3.25 |
| YIELD:GO_FIRST | 0.9:0.1 | 20 | 100% | accepted 20 | accepted 20 | 0% | 0% | 0% | 1.5 | 3.06 |
| YIELD:GO_FIRST | 0.9:0.5 | 20 | 100% | accepted 20 | accepted 20 | 0% | 0% | 0% | 1.5 | 3.15 |
| YIELD:GO_FIRST | 0.9:0.9 | 20 | 100% | accepted 20 | accepted 20 | 0% | 0% | 0% | 1.5 | 3.22 |
| GO_FIRST:CROSS | 0.1:0.1 | 20 | 90% | accepted 18, rejected 2 | accepted 20 | 0% | 0% | 90% | 3.8 | 1.65 |
| GO_FIRST:CROSS | 0.1:0.5 | 20 | 70% | accepted 14, rejected 6 | accepted 20 | 0% | 0% | 70% | 3.3 | 1.65 |
| GO_FIRST:CROSS | 0.1:0.9 | 20 | 15% | rejected 17, accepted 3 | accepted 20 | 0% | 0% | 15% | 1.5 | 1.65 |
| GO_FIRST:CROSS | 0.5:0.1 | 20 | 100% | accepted 20 | accepted 20 | 0% | 0% | 100% | 3.6 | 1.65 |
| GO_FIRST:CROSS | 0.5:0.5 | 20 | 90% | accepted 18, rejected 2 | accepted 20 | 0% | 0% | 90% | 3.2 | 1.65 |
| GO_FIRST:CROSS | 0.5:0.9 | 20 | 40% | rejected 12, accepted 8 | accepted 20 | 0% | 0% | 40% | 1.8 | 1.65 |
| GO_FIRST:CROSS | 0.9:0.1 | 20 | 100% | accepted 20 | accepted 20 | 0% | 0% | 100% | 3.4 | 1.65 |
| GO_FIRST:CROSS | 0.9:0.5 | 20 | 95% | accepted 19, rejected 1 | accepted 20 | 0% | 0% | 95% | 3.0 | 1.65 |
| GO_FIRST:CROSS | 0.9:0.9 | 20 | 75% | accepted 15, rejected 5 | accepted 20 | 0% | 0% | 75% | 2.4 | 1.65 |
| GO_FIRST:YIELD | 0.1:0.1 | 20 | 100% | accepted 20 | accepted 20 | 0% | 0% | 100% | 3.8 | 1.65 |
| GO_FIRST:YIELD | 0.1:0.5 | 20 | 100% | accepted 20 | accepted 20 | 0% | 0% | 100% | 3.4 | 1.65 |
| GO_FIRST:YIELD | 0.1:0.9 | 20 | 100% | accepted 20 | accepted 20 | 0% | 0% | 100% | 2.6 | 1.65 |
| GO_FIRST:YIELD | 0.5:0.1 | 20 | 100% | accepted 20 | accepted 20 | 0% | 0% | 100% | 3.6 | 1.65 |
| GO_FIRST:YIELD | 0.5:0.5 | 20 | 100% | accepted 20 | accepted 20 | 0% | 0% | 100% | 3.2 | 1.65 |
| GO_FIRST:YIELD | 0.5:0.9 | 20 | 100% | accepted 20 | accepted 20 | 0% | 0% | 100% | 2.5 | 1.65 |
| GO_FIRST:YIELD | 0.9:0.1 | 20 | 100% | accepted 20 | accepted 20 | 0% | 0% | 100% | 3.4 | 1.65 |
| GO_FIRST:YIELD | 0.9:0.5 | 20 | 100% | accepted 20 | accepted 20 | 0% | 0% | 100% | 3.0 | 1.65 |
| GO_FIRST:YIELD | 0.9:0.9 | 20 | 100% | accepted 20 | accepted 20 | 0% | 0% | 100% | 2.4 | 1.65 |
| GO_FIRST:GO_FIRST | 0.1:0.1 | 20 | 0% | rejected 14, accepted 6 | accepted 14, rejected 6 | 0% | 0% | 30% | 2.1 | 1.65 |
| GO_FIRST:GO_FIRST | 0.1:0.5 | 20 | 0% | rejected 17, accepted 3 | accepted 17, rejected 3 | 0% | 0% | 15% | 1.9 | 1.65 |
| GO_FIRST:GO_FIRST | 0.1:0.9 | 20 | 0% | rejected 20 | accepted 20 | 0% | 0% | 0% | 1.5 | 3.27 |
| GO_FIRST:GO_FIRST | 0.5:0.1 | 20 | 0% | accepted 16, rejected 4 | rejected 16, accepted 4 | 0% | 0% | 80% | 3.6 | 1.65 |
| GO_FIRST:GO_FIRST | 0.5:0.5 | 20 | 0% | rejected 14, accepted 6 | accepted 14, rejected 6 | 0% | 0% | 30% | 1.8 | 1.65 |
| GO_FIRST:GO_FIRST | 0.5:0.9 | 20 | 0% | rejected 16, accepted 4 | accepted 16, rejected 4 | 0% | 0% | 20% | 1.7 | 1.65 |
| GO_FIRST:GO_FIRST | 0.9:0.1 | 20 | 0% | accepted 18, rejected 2 | rejected 18, accepted 2 | 0% | 0% | 90% | 3.0 | 1.65 |
| GO_FIRST:GO_FIRST | 0.9:0.5 | 20 | 0% | accepted 12, rejected 8 | rejected 12, accepted 8 | 0% | 0% | 60% | 2.1 | 1.65 |
| GO_FIRST:GO_FIRST | 0.9:0.9 | 20 | 0% | rejected 14, accepted 6 | accepted 14, rejected 6 | 0% | 0% | 30% | 1.5 | 1.65 |
