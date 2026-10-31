# E1 2x2x2 因子消融汇总

效应 = 高水位均值 − 低水位均值。attribution：on(保留标签) − off(移除标签)；operator_set：union(六算子) − own(情景原值)；intensity：common(统一上限) − own(原值)。

## development_growth

| 臂 | n | 前沿最大净增建 | 有效候选最大净增建 | 最大临街释放 | Pareto | HV |
|---|---:|---:|---:|---:|---:|---:|
| `attr-off__ops-own__int-common` | 3 | 2.420% | 2.424% | 0.462% | 23.0 | 0.215 |
| `attr-off__ops-own__int-own` | 3 | 2.688% | 2.721% | 0.310% | 17.3 | 0.202 |
| `attr-off__ops-union__int-common` | 3 | 1.707% | 1.707% | 0.748% | 26.7 | 0.222 |
| `attr-off__ops-union__int-own` | 3 | 1.342% | 1.344% | 0.652% | 26.0 | 0.225 |
| `attr-on__ops-own__int-common` | 3 | 0.367% | 0.416% | 0.273% | 18.0 | 0.120 |
| `attr-on__ops-own__int-own` | 3 | 0.623% | 0.635% | 0.243% | 10.3 | 0.119 |
| `attr-on__ops-union__int-common` | 3 | 0.340% | 0.371% | 0.304% | 18.0 | 0.130 |
| `attr-on__ops-union__int-own` | 3 | 0.567% | 0.593% | 0.285% | 17.3 | 0.128 |

**max_net_front 效应**（%）

- attribution：-1.565%
- operator_set：-0.536%
- intensity：-0.096%
- attribution x operator_set：+0.494%
- attribution x intensity：-0.145%
- operator_set x intensity：+0.165%
- attribution x operator_set x intensity：-0.151%

**max_release_front 效应**（%）

- attribution：-0.267%
- operator_set：+0.175%
- intensity：+0.074%
- attribution x operator_set：-0.139%
- attribution x intensity：-0.050%
- operator_set x intensity：-0.016%
- attribution x operator_set x intensity：+0.012%

**hypervolume 效应**（原值）

- attribution：-0.092
- operator_set：+0.012
- intensity：+0.003
- attribution x operator_set：-0.003
- attribution x intensity：-0.002
- operator_set x intensity：-0.003
- attribution x operator_set x intensity：+0.004

参照：该批 R 臂最大净增建均值 0.623%，匹配预算 BL 容量参照 5.948%。

## public_coordination

| 臂 | n | 前沿最大净增建 | 有效候选最大净增建 | 最大临街释放 | Pareto | HV |
|---|---:|---:|---:|---:|---:|---:|
| `attr-off__ops-own__int-common` | 3 | 1.275% | 1.276% | 0.310% | 17.3 | 0.187 |
| `attr-off__ops-own__int-own` | 3 | 0.821% | 0.830% | 0.429% | 20.3 | 0.204 |
| `attr-off__ops-union__int-common` | 3 | 1.028% | 1.028% | 0.401% | 22.7 | 0.179 |
| `attr-off__ops-union__int-own` | 3 | 1.342% | 1.354% | 0.424% | 23.3 | 0.204 |
| `attr-on__ops-own__int-common` | 3 | 0.576% | 0.582% | 0.237% | 13.7 | 0.137 |
| `attr-on__ops-own__int-own` | 3 | 0.599% | 0.601% | 0.157% | 11.7 | 0.130 |
| `attr-on__ops-union__int-common` | 3 | 0.468% | 0.496% | 0.210% | 11.7 | 0.132 |
| `attr-on__ops-union__int-own` | 3 | 0.449% | 0.464% | 0.247% | 14.3 | 0.137 |

**max_net_front 效应**（%）

- attribution：-0.593%
- operator_set：+0.004%
- intensity：+0.034%
- attribution x operator_set：-0.133%
- attribution x intensity：-0.036%
- operator_set x intensity：-0.182%
- attribution x operator_set x intensity：+0.203%

**max_release_front 效应**（%）

- attribution：-0.178%
- operator_set：+0.037%
- intensity：-0.025%
- attribution x operator_set：-0.006%
- attribution x intensity：+0.046%
- operator_set x intensity：-0.006%
- attribution x operator_set x intensity：-0.053%

**hypervolume 效应**（原值）

- attribution：-0.059
- operator_set：-0.001
- intensity：-0.010
- attribution x operator_set：+0.003
- attribution x intensity：+0.011
- operator_set x intensity：-0.005
- attribution x operator_set x intensity：-0.001

参照：该批 R 臂最大净增建均值 0.599%，匹配预算 BL 容量参照 5.948%。

## resident_heritage_priority

| 臂 | n | 前沿最大净增建 | 有效候选最大净增建 | 最大临街释放 | Pareto | HV |
|---|---:|---:|---:|---:|---:|---:|
| `attr-off__ops-own__int-common` | 3 | -0.000% | 0.000% | 0.464% | 13.3 | 0.204 |
| `attr-off__ops-own__int-own` | 3 | -0.000% | 0.000% | 0.464% | 13.3 | 0.204 |
| `attr-off__ops-union__int-common` | 3 | 0.580% | 0.589% | 0.446% | 15.3 | 0.210 |
| `attr-off__ops-union__int-own` | 3 | 0.580% | 0.589% | 0.446% | 15.3 | 0.210 |
| `attr-on__ops-own__int-common` | 3 | -0.013% | -0.001% | 0.187% | 6.7 | 0.123 |
| `attr-on__ops-own__int-own` | 3 | -0.013% | -0.001% | 0.187% | 6.7 | 0.123 |
| `attr-on__ops-union__int-common` | 3 | 0.830% | 0.852% | 0.250% | 12.3 | 0.142 |
| `attr-on__ops-union__int-own` | 3 | 0.830% | 0.852% | 0.250% | 12.3 | 0.142 |

**max_net_front 效应**（%）

- attribution：+0.119%
- operator_set：+0.712%
- intensity：+0.000%
- attribution x operator_set：+0.131%
- attribution x intensity：+0.000%
- operator_set x intensity：+0.000%
- attribution x operator_set x intensity：+0.000%

**max_release_front 效应**（%）

- attribution：-0.237%
- operator_set：+0.022%
- intensity：+0.000%
- attribution x operator_set：+0.040%
- attribution x intensity：+0.000%
- operator_set x intensity：+0.000%
- attribution x operator_set x intensity：+0.000%

**hypervolume 效应**（原值）

- attribution：-0.074
- operator_set：+0.013
- intensity：+0.000
- attribution x operator_set：+0.007
- attribution x intensity：+0.000
- operator_set x intensity：+0.000
- attribution x operator_set x intensity：+0.000

参照：该批 R 臂最大净增建均值 -0.013%，匹配预算 BL 容量参照 5.948%。

## 容量探针（确定性贪心，320 次原始评价）

**development_growth**

| 臂 | 容量上限 | 相对 BL | 改动单元 |
|---|---:|---:|---:|
| `attr-off__ops-own__int-own` | 10.450% | 175.7% | 13 |
| `attr-off__ops-own__int-common` | 10.450% | 175.7% | 13 |
| `attr-off__ops-union__int-own` | 10.450% | 175.7% | 13 |
| `attr-off__ops-union__int-common` | 10.450% | 175.7% | 13 |
| `attr-on__ops-own__int-own` | 1.716% | 28.8% | 6 |
| `attr-on__ops-own__int-common` | 1.716% | 28.8% | 6 |
| `attr-on__ops-union__int-own` | 1.716% | 28.8% | 6 |
| `attr-on__ops-union__int-common` | 1.716% | 28.8% | 6 |

- attribution 效应：-8.734%
- operator_set 效应：+0.000%
- intensity 效应：+0.000%

**public_coordination**

| 臂 | 容量上限 | 相对 BL | 改动单元 |
|---|---:|---:|---:|
| `attr-off__ops-own__int-common` | 7.468% | 125.5% | 7 |
| `attr-off__ops-union__int-common` | 7.468% | 125.5% | 7 |
| `attr-off__ops-own__int-own` | 4.115% | 69.2% | 7 |
| `attr-off__ops-union__int-own` | 4.115% | 69.2% | 7 |
| `attr-on__ops-own__int-common` | 1.716% | 28.8% | 6 |
| `attr-on__ops-union__int-common` | 1.716% | 28.8% | 6 |
| `attr-on__ops-own__int-own` | 0.801% | 13.5% | 6 |
| `attr-on__ops-union__int-own` | 0.801% | 13.5% | 6 |

- attribution 效应：-4.533%
- operator_set 效应：+0.000%
- intensity 效应：+2.133%

**resident_heritage_priority**

| 臂 | 容量上限 | 相对 BL | 改动单元 |
|---|---:|---:|---:|
| `attr-off__ops-union__int-own` | 6.337% | 106.5% | 5 |
| `attr-off__ops-union__int-common` | 6.337% | 106.5% | 5 |
| `attr-on__ops-union__int-own` | 1.716% | 28.8% | 6 |
| `attr-on__ops-union__int-common` | 1.716% | 28.8% | 6 |
| `attr-on__ops-own__int-own` | 0.000% | 0.0% | 0 |
| `attr-off__ops-own__int-own` | 0.000% | 0.0% | 0 |
| `attr-on__ops-own__int-common` | 0.000% | 0.0% | 0 |
| `attr-off__ops-own__int-common` | 0.000% | 0.0% | 0 |

- attribution 效应：-2.311%
- operator_set 效应：+4.026%
- intensity 效应：+0.000%

