# Online LL-BTS 与传统 Offline BTS 对比

Offline 直接将完整 DFA 视为已知，对每个可达估计和每个可容许控制模式计算完整 UR、NX，先建立 BTS，再剪枝。不使用前视窗口、Qf/Qe 证书或提前终止。Online 使用当前保存的 u 和认证 LL-BTS。两者采用相同的无死锁目标和计数剪枝。

Offline 导出为 `offline/bts.json`、`offline/bts.dot`（小图另有 `bts.png`），对应 `supervisor_offline.json`、`offline/closed_loop_system_offline.json/png/svg`。不可解模型提供明确状态说明，不伪造闭环。Online 对应 `closed_loop_system_online.*`。

## 时间和空间的口径

每例 11 次交替顺序的新鲜求解，取中位数。计时包含根极大控制模式筛选；分别列出 online-only 和 preprocessing+online，公平的一次性总成本比较采用后者。输入 DFA 及其公共不可变转移索引已建立；模型读取、参数 u 的实验标定、图形/导出、策略验证不计入求解计时。u 标定使用 offline 解作实验对照，因此当前结果不是无离线先验的端到端部署计时。

内存另行通过 tracemalloc 测 Python 新分配峰值，online 计入预处理，双方排除同一输入模型。这不是进程 RSS，也不覆盖所有 C 扩展内存。另提供真实构建节点数、边数、集合成员数。节约率 = (offline − online) / offline；负值表示 online 更贵，均原样保留。小模型耗时很短，计时比例易受解释器/调度影响，应与结构计数一起看。

## 复杂度：不能把实测节约率当作最坏阶下降

令 n=|Q|，m=|δ|，c=|Σc|，o=|Σo|，P=2^c；传统 BTS 的逻辑图规模为 D、O、E。令 A 为实际存储的估计—控制模式记录数，H 为这些记录的观测后继关联总数；同一 O 节点可被不同 D 复用。
- D ≤ 2^n−1，O ≤ P·D，E ≤ P·D + o·O。
- 完整 UR/NX 构建为 O(P·D·(n+m))；当前按估计—模式记录计数的剪枝为 O(D+A+H)，其中 A=P·D、H≤oA。根极大模式比较保守为 O(P²(c+1))。若另实现共享 O 节点的显式图剪枝才可直接写 O(D+O+E)。
- 逻辑图的显式集合/模式编码存储为 O(nD+(n+c)O+E)。当前 Python 实现还保存 A 份记录及 H 份后继估计关联，保守额外计 O((n+c)A+nH)；另加共同输入 O(n+m)。峰值实测涵盖这些记录、反向索引及临时集合。不能只把每个集合视为一个字节常数，也不能用逻辑节点数冒充实际内存。
- Online 构建相应的 D_L、O_L、E_L，但完整 UR/NX 可能走出窗口，单次处理成本仍可能达到 O(n+m)。
- Online 总成本还需加预处理；最长不可观测简单路径预处理存在阶乘级最坏情形。因此没有普遍更低时间阶或普遍正节约率的结论。
- 下表的时间/内存百分比是当前模型上的测量结果；节点/边削减来自窗口、证书及提前拒绝坏模式。

## 汇总

### 具体数值与运算

`T_on=T_pre+T_solve`：每次运行先相加，再对总时间取中位数；不一定等于两个中位数之和。`T_off` 是传统 BTS 总求解时间的中位数。

- 时间绝对节约 `ΔT=T_off−T_on`（秒）；乘1000得到毫秒。
- 时间节约率 `ΔT/T_off×100%`；速度倍数 `T_off/T_on`。
- 内存绝对节约 `ΔM=M_off−M_on`（bytes）；内存节约率 `ΔM/M_off×100%`。
- `KiB=bytes/1024`，`MiB=bytes/1048576`；比较各自运行的峰值，不是同一时刻内存差。
- 节点/边绝对削减分别为 `V_off−V_on`、`E_off−E_on`；负差值原样保留。

模型数：64；所有模型的根极大控制模式与 offline 一致。
逐例总时间中位数之和：online（含预处理）=0.007524s，offline=0.021371s；工作负载合计节约率=64.79%。
逐例 Python 峰值之和的节约率=75.57%；这是工作负载统计，不是同时运行的内存峰值。

时间绝对差 = 0.021371200 − 0.007524100 = 0.013847100s；速度倍数=2.840。
逐例峰值之和绝对差 = 4222976 − 1031784 = 3191192 bytes。

| 模型 | u | online总时间/ms | offline/ms | 时间绝对差/ms | 时间节约 | online峰值/KiB | offline峰值/KiB | 峰值绝对差/KiB | 峰值节约 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| [yin2016_fig_1a](yin2016_fig_1a/online_offline_comparison.json) | 2 | 0.0239 | 0.2544 | 0.2305 | 90.6% | 8.469 | 63.898 | 55.430 | 86.7% |
| [yin2016_fig_1b](yin2016_fig_1b/online_offline_comparison.json) | 2 | 0.0199 | 0.1514 | 0.1315 | 86.9% | 6.758 | 37.508 | 30.750 | 82.0% |
| [yin2016_fig_1c](yin2016_fig_1c/online_offline_comparison.json) | 1 | 0.0149 | 0.0734 | 0.0585 | 79.7% | 5.195 | 12.484 | 7.289 | 58.4% |
| [yin2016_fig_3a](yin2016_fig_3a/online_offline_comparison.json) | 1 | 0.0312 | 0.1981 | 0.1669 | 84.3% | 8.680 | 53.094 | 44.414 | 83.7% |
| [yin2016_fig_3b](yin2016_fig_3b/online_offline_comparison.json) | 1 | 0.0341 | 0.3001 | 0.2660 | 88.6% | 9.820 | 56.375 | 46.555 | 82.6% |
| [yin2016_fig_3c](yin2016_fig_3c/online_offline_comparison.json) | 1 | 0.0483 | 0.3414 | 0.2931 | 85.9% | 9.797 | 38.719 | 28.922 | 74.7% |
| [15ACCopac_fig_1](15ACCopac_fig_1/online_offline_comparison.json) | 2 | 0.0377 | 0.4956 | 0.4579 | 92.4% | 8.461 | 63.938 | 55.477 | 86.8% |
| [15ACCopac_fig_2a](15ACCopac_fig_2a/online_offline_comparison.json) | 2 | 0.0192 | 0.1990 | 0.1798 | 90.4% | 6.758 | 37.508 | 30.750 | 82.0% |
| [15ACCopac_fig_2b](15ACCopac_fig_2b/online_offline_comparison.json) | 0 | 0.0341 | 0.0662 | 0.0321 | 48.5% | 7.836 | 13.305 | 5.469 | 41.1% |
| [15ACCopac_fig_2c](15ACCopac_fig_2c/online_offline_comparison.json) | 2 | 0.0803 | 0.1358 | 0.0555 | 40.9% | 12.297 | 37.992 | 25.695 | 67.6% |
| [16CDC_fig_2a_G](16CDC_fig_2a_G/online_offline_comparison.json) | 3 | 0.1880 | 0.1494 | -0.0386 | -25.8% | 24.719 | 33.609 | 8.891 | 26.5% |
| [16CDC_fig_2a_K](16CDC_fig_2a_K/online_offline_comparison.json) | 3 | 0.3500 | 0.2798 | -0.0702 | -25.1% | 26.680 | 33.469 | 6.789 | 20.3% |
| [16CDC_fig_2b](16CDC_fig_2b/online_offline_comparison.json) | 2 | 0.1663 | 0.1605 | -0.0058 | -3.6% | 19.312 | 20.297 | 0.984 | 4.8% |
| [14IFAC_fig_1](14IFAC_fig_1/online_offline_comparison.json) | 2 | 0.1304 | 0.3141 | 0.1837 | 58.5% | 19.078 | 68.289 | 49.211 | 72.1% |
| [16WODESmax_fig_1a](16WODESmax_fig_1a/online_offline_comparison.json) | 1 | 0.1143 | 0.0924 | -0.0219 | -23.7% | 15.914 | 22.992 | 7.078 | 30.8% |
| [16WODESmax_fig_1b](16WODESmax_fig_1b/online_offline_comparison.json) | 1 | 0.1474 | 0.1127 | -0.0347 | -30.8% | 16.164 | 23.242 | 7.078 | 30.5% |
| [16WODESmax_fig_2a](16WODESmax_fig_2a/online_offline_comparison.json) | 1 | 0.0680 | 0.0731 | 0.0051 | 7.0% | 14.891 | 20.141 | 5.250 | 26.1% |
| [16WODESmax_fig_3a_Gprime](16WODESmax_fig_3a_Gprime/online_offline_comparison.json) | 2 | 0.1758 | 0.1413 | -0.0345 | -24.4% | 18.742 | 32.062 | 13.320 | 41.5% |
| [17TAC-Range_fig_2a_G](17TAC-Range_fig_2a_G/online_offline_comparison.json) | 1 | 0.1152 | 0.0667 | -0.0485 | -72.7% | 15.867 | 17.461 | 1.594 | 9.1% |
| [17TAC-Range_fig_2a_K](17TAC-Range_fig_2a_K/online_offline_comparison.json) | 1 | 0.0855 | 0.0608 | -0.0247 | -40.6% | 15.617 | 17.211 | 1.594 | 9.3% |
| [17TAC-Range_fig_2c](17TAC-Range_fig_2c/online_offline_comparison.json) | 1 | 0.0629 | 0.0673 | 0.0044 | 6.5% | 15.141 | 20.391 | 5.250 | 25.7% |
| [17TAC-Range_fig_4a](17TAC-Range_fig_4a/online_offline_comparison.json) | 0 | 0.0107 | 0.0507 | 0.0400 | 78.9% | 5.086 | 15.828 | 10.742 | 67.9% |
| [17TAC-Range_fig_4b](17TAC-Range_fig_4b/online_offline_comparison.json) | 1 | 0.0213 | 0.1131 | 0.0918 | 81.2% | 7.672 | 25.781 | 18.109 | 70.2% |
| [17TAC-Range_fig_4c](17TAC-Range_fig_4c/online_offline_comparison.json) | 3 | 0.1508 | 0.1525 | 0.0017 | 1.1% | 26.750 | 40.211 | 13.461 | 33.5% |
| [18TACrange_fig_1a](18TACrange_fig_1a/online_offline_comparison.json) | 4 | 0.2613 | 0.2895 | 0.0282 | 9.7% | 17.492 | 25.648 | 8.156 | 31.8% |
| [18TACrange_fig_1b](18TACrange_fig_1b/online_offline_comparison.json) | 0 | 0.0379 | 0.0739 | 0.0360 | 48.7% | 7.836 | 15.336 | 7.500 | 48.9% |
| [18TACrange_fig_3a](18TACrange_fig_3a/online_offline_comparison.json) | 2 | 0.0626 | 0.2532 | 0.1906 | 75.3% | 12.672 | 25.148 | 12.477 | 49.6% |
| [18TACrange_fig_3b](18TACrange_fig_3b/online_offline_comparison.json) | 1 | 0.0555 | 0.0645 | 0.0090 | 14.0% | 11.406 | 18.297 | 6.891 | 37.7% |
| [16TACNB_fig_7a](16TACNB_fig_7a/online_offline_comparison.json) | 2 | 0.1082 | 0.0785 | -0.0297 | -37.8% | 16.641 | 17.297 | 0.656 | 3.8% |
| [22TACopaque_fig_1](22TACopaque_fig_1/online_offline_comparison.json) | 2 | 0.2018 | 0.3658 | 0.1640 | 44.8% | 14.852 | 49.961 | 35.109 | 70.3% |
| [24TACopa_fig_1a](24TACopa_fig_1a/online_offline_comparison.json) | 3 | 0.0952 | 0.2234 | 0.1282 | 57.4% | 12.648 | 56.594 | 43.945 | 77.7% |
| [24TACopa_fig_1b](24TACopa_fig_1b/online_offline_comparison.json) | 0 | 0.0204 | 0.0398 | 0.0194 | 48.7% | 7.836 | 13.305 | 5.469 | 41.1% |
| [24TACopa_fig_1c](24TACopa_fig_1c/online_offline_comparison.json) | 2 | 0.1479 | 0.2916 | 0.1437 | 49.3% | 10.469 | 45.492 | 35.023 | 77.0% |
| [24TACopa_fig_4](24TACopa_fig_4/online_offline_comparison.json) | 3 | 0.1593 | 0.2664 | 0.1071 | 40.2% | 14.734 | 31.258 | 16.523 | 52.9% |
| [17Mealy_fig_2a](17Mealy_fig_2a/online_offline_comparison.json) | 2 | 0.2111 | 0.3287 | 0.1176 | 35.8% | 12.945 | 41.922 | 28.977 | 69.1% |
| [17Mealy_fig_2b](17Mealy_fig_2b/online_offline_comparison.json) | 2 | 0.0964 | 0.1370 | 0.0406 | 29.6% | 12.648 | 36.523 | 23.875 | 65.4% |
| [17Mealy_fig_3a](17Mealy_fig_3a/online_offline_comparison.json) | 2 | 0.0943 | 0.1434 | 0.0491 | 34.2% | 12.602 | 39.672 | 27.070 | 68.2% |
| [17Mealy_fig_3b](17Mealy_fig_3b/online_offline_comparison.json) | 2 | 0.1055 | 0.1216 | 0.0161 | 13.2% | 12.766 | 31.172 | 18.406 | 59.0% |
| [22TAConline_fig_2](22TAConline_fig_2/online_offline_comparison.json) | 5 | 1.3175 | 2.6627 | 1.3452 | 50.5% | 114.492 | 514.754 | 400.262 | 77.8% |
| [22TAClocal_fig_2](22TAClocal_fig_2/online_offline_comparison.json) | 0 | 0.0413 | 4.4825 | 4.4412 | 99.1% | 10.836 | 776.043 | 765.207 | 98.6% |
| [24AutoOpt_fig_1](24AutoOpt_fig_1/online_offline_comparison.json) | 0 | 0.0202 | 0.1708 | 0.1506 | 88.2% | 5.086 | 24.164 | 19.078 | 79.0% |
| [24AutoOpt_fig_2](24AutoOpt_fig_2/online_offline_comparison.json) | 0 | 0.0153 | 0.0705 | 0.0552 | 78.3% | 7.852 | 22.203 | 14.352 | 64.6% |
| [24AutoOpt_fig_6b](24AutoOpt_fig_6b/online_offline_comparison.json) | 0 | 0.0393 | 1.2588 | 1.2195 | 96.9% | 13.750 | 287.758 | 274.008 | 95.2% |
| [24AutoOpt_fig_6d](24AutoOpt_fig_6d/online_offline_comparison.json) | 0 | 0.0135 | 0.0373 | 0.0238 | 63.8% | 5.930 | 12.609 | 6.680 | 53.0% |
| [21AutomaticaOptimal_fig_2](21AutomaticaOptimal_fig_2/online_offline_comparison.json) | 2 | 0.0493 | 1.0974 | 1.0481 | 95.5% | 15.359 | 192.461 | 177.102 | 92.0% |
| [20CDC2_fig_1a](20CDC2_fig_1a/online_offline_comparison.json) | 1 | 0.0855 | 0.1090 | 0.0235 | 21.6% | 16.664 | 32.445 | 15.781 | 48.6% |
| [20CDC2_fig_1b](20CDC2_fig_1b/online_offline_comparison.json) | 1 | 0.0811 | 0.1127 | 0.0316 | 28.0% | 14.023 | 33.266 | 19.242 | 57.8% |
| [20CDC2_fig_2a](20CDC2_fig_2a/online_offline_comparison.json) | 2 | 0.1341 | 0.2131 | 0.0790 | 37.1% | 14.125 | 41.586 | 27.461 | 66.0% |
| [20CDC2_fig_2b](20CDC2_fig_2b/online_offline_comparison.json) | 2 | 0.2191 | 0.3098 | 0.0907 | 29.3% | 10.875 | 38.836 | 27.961 | 72.0% |
| [20IFAC1_fig_1](20IFAC1_fig_1/online_offline_comparison.json) | 2 | 0.0886 | 0.1056 | 0.0170 | 16.1% | 13.445 | 22.859 | 9.414 | 41.2% |
| [16SEI_fig_1a](16SEI_fig_1a/online_offline_comparison.json) | 1 | 0.0838 | 0.1299 | 0.0461 | 35.5% | 13.500 | 29.156 | 15.656 | 53.7% |
| [16SEI_fig_1b](16SEI_fig_1b/online_offline_comparison.json) | 1 | 0.0872 | 0.1259 | 0.0387 | 30.7% | 12.750 | 25.109 | 12.359 | 49.2% |
| [16SEI_fig_4a](16SEI_fig_4a/online_offline_comparison.json) | 1 | 0.0982 | 0.1731 | 0.0749 | 43.3% | 15.234 | 41.617 | 26.383 | 63.4% |
| [16SEI_fig_4b](16SEI_fig_4b/online_offline_comparison.json) | 1 | 0.1066 | 0.1733 | 0.0667 | 38.5% | 14.734 | 36.477 | 21.742 | 59.6% |
| [17AutomaticaTW_fig_1a](17AutomaticaTW_fig_1a/online_offline_comparison.json) | 1 | 0.0261 | 0.4227 | 0.3966 | 93.8% | 7.664 | 101.086 | 93.422 | 92.4% |
| [23TACsecure_fig_2a](23TACsecure_fig_2a/online_offline_comparison.json) | 1 | 0.0304 | 0.6265 | 0.5961 | 95.1% | 9.703 | 131.461 | 121.758 | 92.6% |
| [23TACsecure_fig_2b](23TACsecure_fig_2b/online_offline_comparison.json) | 1 | 0.0311 | 0.7255 | 0.6944 | 95.7% | 9.703 | 172.891 | 163.188 | 94.4% |
| [23TACsecure_fig_3](23TACsecure_fig_3/online_offline_comparison.json) | 1 | 0.0139 | 0.0693 | 0.0554 | 79.9% | 5.562 | 18.852 | 13.289 | 70.5% |
| [23IFAC-attack_fig_1](23IFAC-attack_fig_1/online_offline_comparison.json) | 2 | 0.2214 | 0.3489 | 0.1275 | 36.5% | 50.703 | 110.812 | 60.109 | 54.2% |
| [23IFAC-attack_fig_2b](23IFAC-attack_fig_2b/online_offline_comparison.json) | 3 | 0.3373 | 0.3483 | 0.0110 | 3.2% | 56.305 | 75.156 | 18.852 | 25.1% |
| [25LCSSattack_fig_1](25LCSSattack_fig_1/online_offline_comparison.json) | 0 | 0.0578 | 0.1112 | 0.0534 | 48.0% | 12.859 | 37.789 | 24.930 | 66.0% |
| [structural_01_long_chain_16](structural_01_long_chain_16/online_offline_comparison.json) | 2 | 0.1135 | 0.1748 | 0.0613 | 35.1% | 16.406 | 21.055 | 4.648 | 22.1% |
| [structural_02_chain_cycle_two_tails_15](structural_02_chain_cycle_two_tails_15/online_offline_comparison.json) | 8 | 0.3871 | 0.4897 | 0.1026 | 21.0% | 24.422 | 50.133 | 25.711 | 51.3% |
| [structural_03_chain_nested_cycles_11](structural_03_chain_nested_cycles_11/online_offline_comparison.json) | 8 | 0.0373 | 0.0948 | 0.0575 | 60.7% | 12.367 | 19.992 | 7.625 | 38.1% |
