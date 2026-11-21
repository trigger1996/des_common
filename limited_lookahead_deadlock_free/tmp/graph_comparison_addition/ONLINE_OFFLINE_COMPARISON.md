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

模型数：61；所有模型的根极大控制模式与 offline 一致。
逐例总时间中位数之和：online（含预处理）=0.008462s，offline=0.017063s；工作负载合计节约率=50.40%。
逐例 Python 峰值之和的节约率=69.28%；这是工作负载统计，不是同时运行的内存峰值。

时间绝对差 = 0.017063200 − 0.008462500 = 0.008600700s；速度倍数=2.016。
逐例峰值之和绝对差 = 4354000 − 1337456 = 3016544 bytes。

| 模型 | u | online总时间/ms | offline/ms | 时间绝对差/ms | 时间节约 | online峰值/KiB | offline峰值/KiB | 峰值绝对差/KiB | 峰值节约 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| [yin2016_fig_1a](yin2016_fig_1a/online_offline_comparison.json) | 2 | 0.0210 | 0.2270 | 0.2060 | 90.7% | 8.438 | 63.898 | 55.461 | 86.8% |
| [yin2016_fig_1c](yin2016_fig_1c/online_offline_comparison.json) | 1 | 0.0111 | 0.0443 | 0.0332 | 74.9% | 5.195 | 12.484 | 7.289 | 58.4% |
| [yin2016_fig_3a](yin2016_fig_3a/online_offline_comparison.json) | 1 | 0.0249 | 0.2417 | 0.2168 | 89.7% | 8.680 | 53.094 | 44.414 | 83.7% |
| [yin2016_fig_3b](yin2016_fig_3b/online_offline_comparison.json) | 3 | 0.2710 | 0.2519 | -0.0191 | -7.6% | 39.883 | 59.578 | 19.695 | 33.1% |
| [yin2016_fig_3c](yin2016_fig_3c/online_offline_comparison.json) | 1 | 0.0828 | 0.1658 | 0.0830 | 50.1% | 10.352 | 42.516 | 32.164 | 75.7% |
| [15ACCopac_fig_1](15ACCopac_fig_1/online_offline_comparison.json) | 2 | 0.0965 | 0.2832 | 0.1867 | 65.9% | 13.945 | 77.703 | 63.758 | 82.1% |
| [15ACCopac_fig_2a](15ACCopac_fig_2a/online_offline_comparison.json) | 2 | 0.0745 | 0.1261 | 0.0516 | 40.9% | 11.883 | 37.906 | 26.023 | 68.7% |
| [15ACCopac_fig_2b](15ACCopac_fig_2b/online_offline_comparison.json) | 0 | 0.0198 | 0.0415 | 0.0217 | 52.3% | 7.836 | 13.305 | 5.469 | 41.1% |
| [15ACCopac_fig_2c](15ACCopac_fig_2c/online_offline_comparison.json) | 2 | 0.0829 | 0.1345 | 0.0516 | 38.4% | 12.297 | 37.992 | 25.695 | 67.6% |
| [16CDC_fig_2a_G](16CDC_fig_2a_G/online_offline_comparison.json) | 3 | 0.1619 | 0.1268 | -0.0351 | -27.7% | 24.719 | 33.609 | 8.891 | 26.5% |
| [16CDC_fig_2a_K](16CDC_fig_2a_K/online_offline_comparison.json) | 1 | 0.0777 | 0.0746 | -0.0031 | -4.2% | 11.797 | 18.164 | 6.367 | 35.1% |
| [16CDC_fig_2b](16CDC_fig_2b/online_offline_comparison.json) | 2 | 0.2955 | 0.2532 | -0.0423 | -16.7% | 19.312 | 20.297 | 0.984 | 4.8% |
| [14IFAC_fig_1](14IFAC_fig_1/online_offline_comparison.json) | 2 | 0.1285 | 0.3000 | 0.1715 | 57.2% | 19.078 | 68.289 | 49.211 | 72.1% |
| [16WODESmax_fig_1a](16WODESmax_fig_1a/online_offline_comparison.json) | 1 | 0.1881 | 0.1521 | -0.0360 | -23.7% | 16.633 | 25.305 | 8.672 | 34.3% |
| [16WODESmax_fig_1b](16WODESmax_fig_1b/online_offline_comparison.json) | 2 | 0.1725 | 0.1396 | -0.0329 | -23.6% | 21.641 | 29.805 | 8.164 | 27.4% |
| [16WODESmax_fig_2a](16WODESmax_fig_2a/online_offline_comparison.json) | 1 | 0.0170 | 0.0768 | 0.0598 | 77.9% | 6.766 | 19.961 | 13.195 | 66.1% |
| [16WODESmax_fig_3a_Gprime](16WODESmax_fig_3a_Gprime/online_offline_comparison.json) | 3 | 0.2447 | 0.1874 | -0.0573 | -30.6% | 20.211 | 29.867 | 9.656 | 32.3% |
| [17TAC-Range_fig_2a_G](17TAC-Range_fig_2a_G/online_offline_comparison.json) | 2 | 0.1802 | 0.1432 | -0.0370 | -25.8% | 28.062 | 36.812 | 8.750 | 23.8% |
| [17TAC-Range_fig_2a_K](17TAC-Range_fig_2a_K/online_offline_comparison.json) | 2 | 0.1939 | 0.1341 | -0.0598 | -44.6% | 28.062 | 36.562 | 8.500 | 23.2% |
| [17TAC-Range_fig_4a](17TAC-Range_fig_4a/online_offline_comparison.json) | 0 | 0.0114 | 0.0549 | 0.0435 | 79.2% | 5.086 | 15.828 | 10.742 | 67.9% |
| [17TAC-Range_fig_4b](17TAC-Range_fig_4b/online_offline_comparison.json) | 1 | 0.0184 | 0.1042 | 0.0858 | 82.3% | 7.672 | 25.781 | 18.109 | 70.2% |
| [17TAC-Range_fig_4c](17TAC-Range_fig_4c/online_offline_comparison.json) | 3 | 0.1490 | 0.1502 | 0.0012 | 0.8% | 26.750 | 40.211 | 13.461 | 33.5% |
| [18TACrange_fig_1a](18TACrange_fig_1a/online_offline_comparison.json) | 4 | 0.1350 | 0.1232 | -0.0118 | -9.6% | 17.492 | 25.648 | 8.156 | 31.8% |
| [18TACrange_fig_1b](18TACrange_fig_1b/online_offline_comparison.json) | 0 | 0.0238 | 0.0501 | 0.0263 | 52.5% | 7.836 | 15.336 | 7.500 | 48.9% |
| [18TACrange_fig_3a](18TACrange_fig_3a/online_offline_comparison.json) | 5 | 0.1492 | 0.1084 | -0.0408 | -37.6% | 24.328 | 25.102 | 0.773 | 3.1% |
| [18TACrange_fig_3b](18TACrange_fig_3b/online_offline_comparison.json) | 1 | 0.0602 | 0.0713 | 0.0111 | 15.6% | 11.406 | 18.297 | 6.891 | 37.7% |
| [16TACNB_fig_7a](16TACNB_fig_7a/online_offline_comparison.json) | 2 | 0.1040 | 0.0732 | -0.0308 | -42.1% | 16.641 | 17.297 | 0.656 | 3.8% |
| [22TACopaque_fig_1](22TACopaque_fig_1/online_offline_comparison.json) | 4 | 0.2817 | 0.3436 | 0.0619 | 18.0% | 39.219 | 85.820 | 46.602 | 54.3% |
| [24TACopa_fig_1a](24TACopa_fig_1a/online_offline_comparison.json) | 3 | 0.0897 | 0.3829 | 0.2932 | 76.6% | 12.617 | 112.328 | 99.711 | 88.8% |
| [24TACopa_fig_1c](24TACopa_fig_1c/online_offline_comparison.json) | 2 | 0.0821 | 0.1615 | 0.0794 | 49.2% | 10.469 | 45.492 | 35.023 | 77.0% |
| [24TACopa_fig_4](24TACopa_fig_4/online_offline_comparison.json) | 4 | 0.1548 | 0.1252 | -0.0296 | -23.6% | 27.195 | 33.188 | 5.992 | 18.1% |
| [17Mealy_fig_2a](17Mealy_fig_2a/online_offline_comparison.json) | 3 | 0.1822 | 0.3959 | 0.2137 | 54.0% | 23.180 | 85.375 | 62.195 | 72.8% |
| [17Mealy_fig_2b](17Mealy_fig_2b/online_offline_comparison.json) | 4 | 0.0949 | 0.1486 | 0.0537 | 36.1% | 13.875 | 43.383 | 29.508 | 68.0% |
| [17Mealy_fig_3a](17Mealy_fig_3a/online_offline_comparison.json) | 2 | 0.1040 | 0.1401 | 0.0361 | 25.8% | 12.703 | 34.516 | 21.812 | 63.2% |
| [17Mealy_fig_3b](17Mealy_fig_3b/online_offline_comparison.json) | 2 | 0.0942 | 0.1084 | 0.0142 | 13.1% | 12.766 | 31.312 | 18.547 | 59.2% |
| [22TAConline_fig_2](22TAConline_fig_2/online_offline_comparison.json) | 3 | 0.5599 | 2.0101 | 1.4502 | 72.1% | 45.898 | 515.137 | 469.238 | 91.1% |
| [22TAClocal_fig_2](22TAClocal_fig_2/online_offline_comparison.json) | 3 | 1.7955 | 2.7887 | 0.9932 | 35.6% | 274.883 | 768.168 | 493.285 | 64.2% |
| [24AutoOpt_fig_1](24AutoOpt_fig_1/online_offline_comparison.json) | 0 | 0.0107 | 0.0849 | 0.0742 | 87.4% | 5.086 | 24.164 | 19.078 | 79.0% |
| [24AutoOpt_fig_2](24AutoOpt_fig_2/online_offline_comparison.json) | 1 | 0.0694 | 0.0681 | -0.0013 | -1.9% | 18.258 | 22.523 | 4.266 | 18.9% |
| [24AutoOpt_fig_6b](24AutoOpt_fig_6b/online_offline_comparison.json) | 0 | 0.0351 | 1.0563 | 1.0212 | 96.7% | 13.750 | 287.758 | 274.008 | 95.2% |
| [24AutoOpt_fig_6d](24AutoOpt_fig_6d/online_offline_comparison.json) | 0 | 0.0136 | 0.0378 | 0.0242 | 64.0% | 5.930 | 12.609 | 6.680 | 53.0% |
| [21AutomaticaOptimal_fig_2](21AutomaticaOptimal_fig_2/online_offline_comparison.json) | 2 | 0.0473 | 1.4875 | 1.4402 | 96.8% | 15.359 | 192.461 | 177.102 | 92.0% |
| [20CDC2_fig_1a](20CDC2_fig_1a/online_offline_comparison.json) | 1 | 0.0806 | 0.1098 | 0.0292 | 26.6% | 16.664 | 32.445 | 15.781 | 48.6% |
| [20CDC2_fig_1b](20CDC2_fig_1b/online_offline_comparison.json) | 1 | 0.0810 | 0.1077 | 0.0267 | 24.8% | 14.023 | 33.266 | 19.242 | 57.8% |
| [20CDC2_fig_2a](20CDC2_fig_2a/online_offline_comparison.json) | 2 | 0.1217 | 0.1979 | 0.0762 | 38.5% | 14.133 | 41.586 | 27.453 | 66.0% |
| [20CDC2_fig_2b](20CDC2_fig_2b/online_offline_comparison.json) | 2 | 0.1000 | 0.2428 | 0.1428 | 58.8% | 10.633 | 64.062 | 53.430 | 83.4% |
| [20IFAC1_fig_1](20IFAC1_fig_1/online_offline_comparison.json) | 2 | 0.0689 | 0.0891 | 0.0202 | 22.7% | 13.664 | 22.844 | 9.180 | 40.2% |
| [16SEI_fig_1a](16SEI_fig_1a/online_offline_comparison.json) | 1 | 0.0894 | 0.1083 | 0.0189 | 17.5% | 14.102 | 30.742 | 16.641 | 54.1% |
| [16SEI_fig_1b](16SEI_fig_1b/online_offline_comparison.json) | 1 | 0.0576 | 0.0843 | 0.0267 | 31.7% | 12.719 | 25.961 | 13.242 | 51.0% |
| [16SEI_fig_4a](16SEI_fig_4a/online_offline_comparison.json) | 1 | 0.0859 | 0.1471 | 0.0612 | 41.6% | 15.203 | 44.000 | 28.797 | 65.4% |
| [16SEI_fig_4b](16SEI_fig_4b/online_offline_comparison.json) | 1 | 0.0937 | 0.1276 | 0.0339 | 26.6% | 14.734 | 36.477 | 21.742 | 59.6% |
| [17AutomaticaTW_fig_1a](17AutomaticaTW_fig_1a/online_offline_comparison.json) | 1 | 0.0200 | 0.3516 | 0.3316 | 94.3% | 7.664 | 101.086 | 93.422 | 92.4% |
| [23TACsecure_fig_2a](23TACsecure_fig_2a/online_offline_comparison.json) | 1 | 0.0205 | 0.4948 | 0.4743 | 95.9% | 9.719 | 131.461 | 121.742 | 92.6% |
| [23TACsecure_fig_2b](23TACsecure_fig_2b/online_offline_comparison.json) | 1 | 0.1472 | 0.6007 | 0.4535 | 75.5% | 20.969 | 159.352 | 138.383 | 86.8% |
| [23TACsecure_fig_3](23TACsecure_fig_3/online_offline_comparison.json) | 1 | 0.0133 | 0.0670 | 0.0537 | 80.1% | 5.562 | 18.852 | 13.289 | 70.5% |
| [23IFAC-attack_fig_1](23IFAC-attack_fig_1/online_offline_comparison.json) | 2 | 0.2237 | 0.3533 | 0.1296 | 36.7% | 50.703 | 110.812 | 60.109 | 54.2% |
| [23IFAC-attack_fig_2b](23IFAC-attack_fig_2b/online_offline_comparison.json) | 3 | 0.2585 | 0.2701 | 0.0116 | 4.3% | 56.305 | 75.156 | 18.852 | 25.1% |
| [25LCSSattack_fig_1](25LCSSattack_fig_1/online_offline_comparison.json) | 0 | 0.0831 | 0.1397 | 0.0566 | 40.5% | 12.859 | 37.789 | 24.930 | 66.0% |
| [structural_01_long_chain_16](structural_01_long_chain_16/online_offline_comparison.json) | 2 | 0.0636 | 0.0824 | 0.0188 | 22.8% | 16.477 | 21.055 | 4.578 | 21.7% |
| [structural_02_chain_cycle_two_tails_15](structural_02_chain_cycle_two_tails_15/online_offline_comparison.json) | 8 | 0.2058 | 0.2176 | 0.0118 | 5.4% | 24.422 | 50.133 | 25.711 | 51.3% |
| [structural_03_chain_nested_cycles_11](structural_03_chain_nested_cycles_11/online_offline_comparison.json) | 8 | 0.0374 | 0.0925 | 0.0551 | 59.6% | 12.367 | 19.992 | 7.625 | 38.1% |
