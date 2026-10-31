# E1 2x2x2 因子消融汇总

效应 = 高水位均值 − 低水位均值。attribution：on(保留标签) − off(移除标签)；operator_set：union(六算子) − own(情景原值)；intensity：common(统一上限) − own(原值)。

## public_coordination

| 臂 | n | 最大净增建 | 最大临街释放 | Pareto | HV |
|---|---:|---:|---:|---:|---:|
| `attr-off__ops-own__int-own` | 1 | 0.000% | 0.332% | 6.0 | 0.153 |
| `attr-on__ops-own__int-own` | 1 | 0.360% | 0.121% | 8.0 | 0.102 |

> 该情景的臂不全或各臂 seed 数不等，已跳过效应估计（设计不是平衡的）。

## 容量探针（确定性贪心，320 次原始评价）

