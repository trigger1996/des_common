# 系统事件属性与运行结果与修改意见

本文件供逐例审阅和填写修改意见。事件划分以每例当前的 `plant.json` 为准；填写意见不会自动修改模型。
论文来源未给出可控划分时所采用的测试设定、集中式观测适配等，仍以每例来源备注为准。
可观/不可观与可控/不可控是两组独立划分。事件名称 `uc`、`u` 或 `h` 本身不决定其属性，请按下面的集合判断。

- Σ：全部事件；Σo：可观事件；Σuo = Σ − Σo：不可观事件。
- Σc：可控事件；Σuc = Σ − Σc：不可控事件（控制器始终允许）。
- `winning` 表示当前无死锁目标可解；`losing` 表示当前模型下不可解。
- 每例保留了独立的“修改意见”区；重新运行生成脚本时会保留区内已有内容。

共 64 个原始系统，其中 3 个为新增结构测试。
当前单状态原始 plant 数量：0。本次没有符合删除条件的模型，因此未删除例子。
单节点 LL-BTS 或单状态闭环不等于单状态 plant，不纳入此项删除。详见 `single_state_plant_audit.json`。

<!-- RUN-OVERVIEW: benchmark -->
## 运行结果总览与阅读口径

本文件逐例整理64个原始模型（61个论文模型、3个结构测试）：**30个winning，34个losing**。后面另列两个实际综合成功的千万状态论文乘积。

- Offline以完整已知DFA计算UR/NX，先构建传统BTS再剪枝；不用前视或Qf/Qe证书。
- Online采用认证LL-BTS；只返回已证明winning/losing的结果，窗口不足应为inconclusive。
- 原始DFA状态、D/O信息状态、supervisor记忆、物理闭环状态是不同对象。闭环节点按（实际DFA状态，控制器记忆）计数，不能把单节点证书当成单状态plant。
- 两侧初始根极大模式集合均已核对；各自选定闭环分别验证，不自动等于两套完整闭环语言一致。
- 原论文的标记非阻塞、保密性、攻击/时延、收益等目标未在本实验中复现；这里只验证无死锁。

### 时间、内存与计算公式

64个原始模型各做11次交替顺序新鲜求解，取中位数。Online总时间包含预处理；公共输入模型/索引、u的实验标定、验证和绘图导出不计入求解时间。u标定借助offline根模式对照，因此不是无offline先验的完整部署耗时。
`ΔT=T_off−T_on`；`时间节约率=ΔT/T_off×100%`；`速度倍数=T_off/T_on`。`ΔM=M_off−M_on`；`内存节约率=ΔM/M_off×100%`。1 ms=0.001 s；1 KiB=1024 bytes；1 MiB=1048576 bytes。
内存是另行测量的Python新分配峰值，不是进程RSS；共同输入模型不重复计入。负差值/负节约率保留。逐例峰值之和只是工作负载统计，不是同时运行的内存峰值。
64例总时间中位数之和：offline=0.021371200s，online含预处理=0.007524100s，绝对差=0.013847100s，节约率=64.793%。
逐例峰值之和：offline=4,222,976 bytes，online=1,031,784 bytes，绝对差=3,191,192 bytes，节约率=75.567%。
有55例总时间节约为正，64例Python峰值节约为正。

### 理论复杂度与实测结果分开

令n=|Q|、m=|δ|、c=|Σc|、o=|Σo|、P=2^c。传统BTS的D≤2^n−1、O≤PD；逐模式UR/NX构建为O(PD(n+m))。当前按估计—模式记录计数剪枝，若A是记录数、H是观测后继关联数，成本为O(D+A+H)，不能直接用逻辑合并图的O(V+E)替代。存储还包含估计/模式集合及重复关联，不能只数节点。
Online需额外计预处理，最长不可观测简单路径存在阶乘级最坏情形；完整UR/NX也可能走出窗口。因此节约百分比不是普遍的时间/空间复杂度降阶结论。

[Online/offline并排图集](online_offline_index.html) · [完整对比报告](ONLINE_OFFLINE_COMPARISON.md) · [64例数值CSV](online_offline_comparison.csv) · [两个大乘积实际综合](large_literature_supervisors.html)
<!-- END-RUN-OVERVIEW: benchmark -->

## 快速索引

** TODO 你要说明 每一个系统都采用了原始系统的设计，但是都修改过 **

| 序号 | 系统 | 原始状态数 | 可观事件 Σo | 可控事件 Σc | 当前结果 | 修改意见 |
| --- | --- | ---: | --- | --- | --- |
| 1 | [yin2016_fig_1a](#yin2016_fig_1a) | 7 | `{o1, o2}` | `{a, b, c}` | winning | |
| 2 | [yin2016_fig_1b](#yin2016_fig_1b) | 5 | `{o1, o2}` | `{a, b, c}` | winning | |
| 3 | [yin2016_fig_1c](#yin2016_fig_1c) | 2 | `{o1, o2}` | `{a, b, c}` | winning | |
| 4 | [yin2016_fig_3a](#yin2016_fig_3a) | 6 | `{a, c, d, o}` | `{b, o}` | winning | |
| 5 | [yin2016_fig_3b](#yin2016_fig_3b) | 8 | `{a, c, d, o}` | `{b, o}` | winning | |
| 6 | [yin2016_fig_3c](#yin2016_fig_3c) | 8 | `{a, c, d, o}` | `{b, o}` | winning | |
| 7 | [15ACCopac_fig_1](#15accopac_fig_1) | 7 | `{o1, o2}` | `{a, b, c}` | winning | |
| 8 | [15ACCopac_fig_2a](#15accopac_fig_2a) | 5 | `{o1, o2}` | `{a, b, c}` | winning | |
| 9 | [15ACCopac_fig_2b](#15accopac_fig_2b) | 2 | `{o1, o2}` | `{a, b, c}` | losing | |
| 10 | [15ACCopac_fig_2c](#15accopac_fig_2c) | 6 | `{o1, o2}` | `{a, b, c}` | winning | |
| 11 | [16CDC_fig_2a_G](#16cdc_fig_2a_g) | 9 | `{o}` | `{c1, c2}` | losing | |
| 12 | [16CDC_fig_2a_K](#16cdc_fig_2a_k) | 8 | `{o}` | `{c1, c2}` | losing | |
| 13 | [16CDC_fig_2b](#16cdc_fig_2b) | 3 | `{o}` | `{c1, c2}` | losing | |
| 14 | [14IFAC_fig_1](#14ifac_fig_1) | 8 | `{o, uc}` | `{a, b, c, o}` | losing | |
| 15 | [16WODESmax_fig_1a](#16wodesmax_fig_1a) | 6 | `{a, b}` | `{c1, c2}` | losing | |
| 16 | [16WODESmax_fig_1b](#16wodesmax_fig_1b) | 7 | `{a, b}` | `{c1, c2}` | losing | |
| 17 | [16WODESmax_fig_2a](#16wodesmax_fig_2a) | 5 | `{a, b}` | `{c1, c2}` | losing | |
| 18 | [16WODESmax_fig_3a_Gprime](#16wodesmax_fig_3a_gprime) | 11 | `{a, b}` | `{c1, c2}` | losing | |
| 19 | [17TAC-Range_fig_2a_G](#17tac-range_fig_2a_g) | 7 | `{a, b}` | `{c1, c2}` | losing | |
| 20 | [17TAC-Range_fig_2a_K](#17tac-range_fig_2a_k) | 6 | `{a, b}` | `{c1, c2}` | losing | |
| 21 | [17TAC-Range_fig_2c](#17tac-range_fig_2c) | 5 | `{a, b}` | `{c1, c2}` | losing | |
| 22 | [17TAC-Range_fig_4a](#17tac-range_fig_4a) | 2 | `{a, b, v}` | `{v, w}` | winning | |
| 23 | [17TAC-Range_fig_4b](#17tac-range_fig_4b) | 6 | `{a, b, v}` | `{v, w}` | winning | |
| 24 | [17TAC-Range_fig_4c](#17tac-range_fig_4c) | 7 | `{a, b, v}` | `{v, w}` | winning | |
| 25 | [18TACrange_fig_1a](#18tacrange_fig_1a) | 13 | `{o}` | `{c1, c2}` | winning | |
| 26 | [18TACrange_fig_1b](#18tacrange_fig_1b) | 3 | `{o}` | `{c1, c2}` | losing | |
| 27 | [18TACrange_fig_3a](#18tacrange_fig_3a) | 11 | `{o}` | `{c1, c2}` | winning | |
| 28 | [18TACrange_fig_3b](#18tacrange_fig_3b) | 4 | `{o}` | `{c1, c2}` | losing | |
| 29 | [16TACNB_fig_7a](#16tacnb_fig_7a) | 11 | `{o}` | `{c1, c2}` | winning | |
| 30 | [22TACopaque_fig_1](#22tacopaque_fig_1) | 12 | `{o1, o2, o3}` | `{c1, c2}` | losing | |
| 31 | [24TACopa_fig_1a](#24tacopa_fig_1a) | 9 | `{o1, o2}` | `{a, b, c}` | losing | |
| 32 | [24TACopa_fig_1b](#24tacopa_fig_1b) | 2 | `{o1, o2}` | `{a, b, c}` | losing | |
| 33 | [24TACopa_fig_1c](#24tacopa_fig_1c) | 6 | `{o1, o2}` | `{a, b, c}` | losing | |
| 34 | [24TACopa_fig_4](#24tacopa_fig_4) | 9 | `{o1, o2}` | `{a}` | losing | |
| 35 | [17Mealy_fig_2a](#17mealy_fig_2a) | 10 | `{d1, d2}` | `{s1, s2}` | losing | |
| 36 | [17Mealy_fig_2b](#17mealy_fig_2b) | 8 | `{d1, d2}` | `{s1, s2}` | losing | |
| 37 | [17Mealy_fig_3a](#17mealy_fig_3a) | 9 | `{d1, d2}` | `{s1, s2}` | losing | |
| 38 | [17Mealy_fig_3b](#17mealy_fig_3b) | 7 | `{d1, d2}` | `{s1, s2}` | losing | |
| 39 | [22TAConline_fig_2](#22taconline_fig_2) | 17 | `{a, b}` | `{a, b, u1, u2, u3}` | losing |
| 40 | [22TAClocal_fig_2](#22taclocal_fig_2) | 9 | `{a, b, c, d, e, f, u1, u2, u3, u4, u5, u6}` | `{a, b, c, d, e, f}` | winning |
| 41 | [24AutoOpt_fig_1](#24autoopt_fig_1) | 2 | `{a, b, c}` | `{a, b, c}` | winning |
| 42 | [24AutoOpt_fig_2](#24autoopt_fig_2) | 5 | `{a, d, e}` | `{a}` | winning |
| 43 | [24AutoOpt_fig_6b](#24autoopt_fig_6b) | 13 | `{B, E, N, S, W}` | `{E, N, S, W}` | winning |
| 44 | [24AutoOpt_fig_6d](#24autoopt_fig_6d) | 4 | `{Ebar, H, Wbar}` | ∅ | winning |
| 45 | [21AutomaticaOptimal_fig_2](#21automaticaoptimal_fig_2) | 15 | `{o1, o2, o3, o4}` | `{c1, c2, c3, c4, c5}` | winning |
| 46 | [20CDC2_fig_1a](#20cdc2_fig_1a) | 6 | `{a, b, d}` | `{c, d}` | winning |
| 47 | [20CDC2_fig_1b](#20cdc2_fig_1b) | 6 | `{a, b, d}` | `{c, d}` | losing |
| 48 | [20CDC2_fig_2a](#20cdc2_fig_2a) | 13 | `{c}` | `{a, b, d, e}` | losing |
| 49 | [20CDC2_fig_2b](#20cdc2_fig_2b) | 7 | `{c}` | `{a, b, d, e}` | losing |
| 50 | [20IFAC1_fig_1](#20ifac1_fig_1) | 6 | `{o1, o2, o3}` | `{c1, c2}` | losing |
| 51 | [16SEI_fig_1a](#16sei_fig_1a) | 9 | `{a, b, c, o}` | `{c}` | losing |
| 52 | [16SEI_fig_1b](#16sei_fig_1b) | 7 | `{a, b, c, o}` | `{c}` | losing |
| 53 | [16SEI_fig_4a](#16sei_fig_4a) | 12 | `{a, b, c, o}` | `{c}` | losing |
| 54 | [16SEI_fig_4b](#16sei_fig_4b) | 10 | `{a, b, c, o}` | `{c}` | losing |
| 55 | [17AutomaticaTW_fig_1a](#17automaticatw_fig_1a) | 6 | `{a, b}` | `{a, b, u1, u2}` | winning |
| 56 | [23TACsecure_fig_2a](#23tacsecure_fig_2a) | 8 | `{a, b, c}` | `{a, b, c, u}` | winning |
| 57 | [23TACsecure_fig_2b](#23tacsecure_fig_2b) | 8 | `{a, b, c}` | `{a, b, c, u}` | winning |
| 58 | [23TACsecure_fig_3](#23tacsecure_fig_3) | 3 | `{a}` | `{a, u}` | winning |
| 59 | [23IFAC-attack_fig_1](#23ifac-attack_fig_1) | 5 | `{a, b, c, d, e}` | `{b, c, d, e}` | losing |
| 60 | [23IFAC-attack_fig_2b](#23ifac-attack_fig_2b) | 7 | `{a, b, c, d}` | `{a, c, d}` | winning |
| 61 | [25LCSSattack_fig_1](#25lcssattack_fig_1) | 5 | `{a, b, c}` | `{a, b}` | winning |
| 62 | [structural_01_long_chain_16](#structural_01_long_chain_16) | 16 | `{o}` | `{h}` | losing |
| 63 | [structural_02_chain_cycle_two_tails_15](#structural_02_chain_cycle_two_tails_15) | 15 | `{o, x, y}` | `{h, x, y}` | winning |
| 64 | [structural_03_chain_nested_cycles_11](#structural_03_chain_nested_cycles_11) | 11 | `{o}` | `{h, j}` | winning |

## yin2016_fig_1a

编号：1。类别：论文自动机。
原始状态数：7；转移数：11；初始状态：`0`。
当前结果：`winning`；所选前视深度：`u=2`。

| 事件属性 | 集合 |
| --- | --- |
| 全部事件 Σ | `{a, b, c, e, o1, o2}` |
| 可观事件 Σo | `{o1, o2}` |
| 不可观事件 Σuo | `{a, b, c, e}` |
| 可控事件 Σc | `{a, b, c}` |
| 不可控事件 Σuc | `{e, o1, o2}` |

[原始系统图](yin2016_fig_1a/plant.png) · [原始系统数据](yin2016_fig_1a/plant.json) · [LL-BTS](yin2016_fig_1a/ll_bts.png) · [闭环结果](yin2016_fig_1a/closed_loop.png)

来源：Yin & Lafortune (2016), Fig. 1a。

模型备注：System G; opacity example。

<!-- RUN-RESULTS: yin2016_fig_1a -->
### 运行结果与分析

- 判定：online **winning**，offline **winning**；完整离线结论一致。
- 预处理：Qd=∅；Qf=∅；Qe=`{0, 1, 2, 3, 4, 5, 6}`。
- 深度：草稿阈值=2；最小可判定u=0；恢复offline根极大控制模式的最小u=0；实际采用u=2。
  深度经过逐例扫描标定；草稿阈值本身不等于普遍可解性保证。

| 结构指标 | Online LL-BTS | 传统 Offline BTS |
| --- | ---: | ---: |
| 构建D节点 | 1 | 5 |
| 构建O节点 | 0 | 40 |
| 构建边 | 0 | 95 |
| 全部保留D/O节点 | 1/0 | 5/38 |
| 所选闭环可达状态 | 9 | 9 |
| 所选闭环可达转移 | 14 | 14 |
| 所选控制器记忆状态 | 3 | 3 |

**为什么可解：** 初始估计已完全落在Qe中，允许全部事件即可安全延续。因此online可以在根估计处采用安全终端证书，停止枚举O节点。这不是原始plant只有一个状态；物理闭环仍按实际DFA状态和控制器记忆展开。
**实际控制行为：** 所有导出记忆状态的控制输出均允许全部事件，未禁用任何可控事件。保留的多个估计记忆不表示控制模式一定不同。

**传统BTS初始节点的模式去向（互斥分类）：** 共8个模式，其中UR含plant死锁0个；其余模式直接引入控制死锁2个；局部通过但因后续估计失败而剪除0个；最终保留6个。

| 实测成本 | Online | Offline | 绝对节约（Offline−Online） | 节约率 |
| --- | ---: | ---: | ---: | ---: |
| 总求解时间，含online预处理 / ms | 0.023900 | 0.254400 | 0.230500 | 90.605% |
| Python分配峰值 / KiB | 8.469 | 63.898 | 55.430 | 86.747% |

Online分项中位数：预处理0.021000 ms，求解0.002900 ms。总时间是每次预处理与求解相加后再取中位数，不能一般地把两个中位数直接相加。
运算：ΔT=(0.254400−0.023900) ms=0.230500 ms；时间节约率=ΔT/0.254400 ms=90.605%。
ΔM=65,432−8,672=56,760 bytes；内存节约率=ΔM/65,432=86.747%。
**成本解释：** 本例测得online总成本更低；收益同时包含窗口、Qf/Qe证书和提前拒绝坏模式。这是当前实现/模型的实测，不是对所有系统最坏复杂度下降的证明。

[Offline BTS数据](yin2016_fig_1a/offline/bts.json) · [Offline闭环](yin2016_fig_1a/closed_loop_system_offline.png) · [Offline supervisor](yin2016_fig_1a/supervisor_offline.json) · [逐项测量](yin2016_fig_1a/online_offline_comparison.json)
<!-- END-RUN-RESULTS: yin2016_fig_1a -->

### 修改意见（请填写）

<!-- USER-NOTES: yin2016_fig_1a -->
- 需要修改的状态或转移：
- 可观事件调整：
- 可控事件调整：
- 希望保留的闭环或预期行为：
- 其他意见：
<!-- END-USER-NOTES: yin2016_fig_1a -->

## yin2016_fig_1b

编号：2。类别：论文自动机。
原始状态数：5；转移数：6；初始状态：`0`。
当前结果：`winning`；所选前视深度：`u=2`。

| 事件属性 | 集合 |
| --- | --- |
| 全部事件 Σ | `{a, b, c, e, o1, o2}` |
| 可观事件 Σo | `{o1, o2}` |
| 不可观事件 Σuo | `{a, b, c, e}` |
| 可控事件 Σc | `{a, b, c}` |
| 不可控事件 Σuc | `{e, o1, o2}` |

[原始系统图](yin2016_fig_1b/plant.png) · [原始系统数据](yin2016_fig_1b/plant.json) · [LL-BTS](yin2016_fig_1b/ll_bts.png) · [闭环结果](yin2016_fig_1b/closed_loop.png)

来源：Yin & Lafortune (2016), Fig. 1b。

模型备注：Controlled solution G1; disabled b edge omitted。

<!-- RUN-RESULTS: yin2016_fig_1b -->
### 运行结果与分析

- 判定：online **winning**，offline **winning**；完整离线结论一致。
- 预处理：Qd=∅；Qf=∅；Qe=`{0, 3, 4, 5, 6}`。
- 深度：草稿阈值=2；最小可判定u=0；恢复offline根极大控制模式的最小u=0；实际采用u=2。
  深度经过逐例扫描标定；草稿阈值本身不等于普遍可解性保证。

| 结构指标 | Online LL-BTS | 传统 Offline BTS |
| --- | ---: | ---: |
| 构建D节点 | 1 | 3 |
| 构建O节点 | 0 | 24 |
| 构建边 | 0 | 44 |
| 全部保留D/O节点 | 1/0 | 3/20 |
| 所选闭环可达状态 | 5 | 5 |
| 所选闭环可达转移 | 6 | 6 |
| 所选控制器记忆状态 | 2 | 2 |

**为什么可解：** 初始估计已完全落在Qe中，允许全部事件即可安全延续。因此online可以在根估计处采用安全终端证书，停止枚举O节点。这不是原始plant只有一个状态；物理闭环仍按实际DFA状态和控制器记忆展开。
**实际控制行为：** 所有导出记忆状态的控制输出均允许全部事件，未禁用任何可控事件。保留的多个估计记忆不表示控制模式一定不同。

**传统BTS初始节点的模式去向（互斥分类）：** 共8个模式，其中UR含plant死锁0个；其余模式直接引入控制死锁4个；局部通过但因后续估计失败而剪除0个；最终保留4个。

| 实测成本 | Online | Offline | 绝对节约（Offline−Online） | 节约率 |
| --- | ---: | ---: | ---: | ---: |
| 总求解时间，含online预处理 / ms | 0.019900 | 0.151400 | 0.131500 | 86.856% |
| Python分配峰值 / KiB | 6.758 | 37.508 | 30.750 | 81.983% |

Online分项中位数：预处理0.016900 ms，求解0.003000 ms。总时间是每次预处理与求解相加后再取中位数，不能一般地把两个中位数直接相加。
运算：ΔT=(0.151400−0.019900) ms=0.131500 ms；时间节约率=ΔT/0.151400 ms=86.856%。
ΔM=38,408−6,920=31,488 bytes；内存节约率=ΔM/38,408=81.983%。
**成本解释：** 本例测得online总成本更低；收益同时包含窗口、Qf/Qe证书和提前拒绝坏模式。这是当前实现/模型的实测，不是对所有系统最坏复杂度下降的证明。

[Offline BTS数据](yin2016_fig_1b/offline/bts.json) · [Offline闭环](yin2016_fig_1b/closed_loop_system_offline.png) · [Offline supervisor](yin2016_fig_1b/supervisor_offline.json) · [逐项测量](yin2016_fig_1b/online_offline_comparison.json)
<!-- END-RUN-RESULTS: yin2016_fig_1b -->

### 修改意见（请填写）

<!-- USER-NOTES: yin2016_fig_1b -->
- 需要修改的状态或转移：
- 可观事件调整：
- 可控事件调整：
- 希望保留的闭环或预期行为：
- 其他意见：
<!-- END-USER-NOTES: yin2016_fig_1b -->

## yin2016_fig_1c

编号：3。类别：论文自动机。
原始状态数：2；转移数：2；初始状态：`0`。
当前结果：`winning`；所选前视深度：`u=1`。

| 事件属性 | 集合 |
| --- | --- |
| 全部事件 Σ | `{a, b, c, e, o1, o2}` |
| 可观事件 Σo | `{o1, o2}` |
| 不可观事件 Σuo | `{a, b, c, e}` |
| 可控事件 Σc | `{a, b, c}` |
| 不可控事件 Σuc | `{e, o1, o2}` |

[原始系统图](yin2016_fig_1c/plant.png) · [原始系统数据](yin2016_fig_1c/plant.json) · [LL-BTS](yin2016_fig_1c/ll_bts.png) · [闭环结果](yin2016_fig_1c/closed_loop.png)

来源：Yin & Lafortune (2016), Fig. 1c。

模型备注：Controlled solution G2; disabled a,c edges omitted。

<!-- RUN-RESULTS: yin2016_fig_1c -->
### 运行结果与分析

- 判定：online **winning**，offline **winning**；完整离线结论一致。
- 预处理：Qd=∅；Qf=∅；Qe=`{0, 1}`。
- 深度：草稿阈值=1；最小可判定u=0；恢复offline根极大控制模式的最小u=0；实际采用u=1。
  深度经过逐例扫描标定；草稿阈值本身不等于普遍可解性保证。

| 结构指标 | Online LL-BTS | 传统 Offline BTS |
| --- | ---: | ---: |
| 构建D节点 | 1 | 1 |
| 构建O节点 | 0 | 8 |
| 构建边 | 0 | 8 |
| 全部保留D/O节点 | 1/0 | 1/4 |
| 所选闭环可达状态 | 2 | 2 |
| 所选闭环可达转移 | 2 | 2 |
| 所选控制器记忆状态 | 1 | 1 |

**为什么可解：** 初始估计已完全落在Qe中，允许全部事件即可安全延续。因此online可以在根估计处采用安全终端证书，停止枚举O节点。这不是原始plant只有一个状态；物理闭环仍按实际DFA状态和控制器记忆展开。
**实际控制行为：** 所有导出记忆状态的控制输出均允许全部事件，未禁用任何可控事件。保留的多个估计记忆不表示控制模式一定不同。

**传统BTS初始节点的模式去向（互斥分类）：** 共8个模式，其中UR含plant死锁0个；其余模式直接引入控制死锁4个；局部通过但因后续估计失败而剪除0个；最终保留4个。

| 实测成本 | Online | Offline | 绝对节约（Offline−Online） | 节约率 |
| --- | ---: | ---: | ---: | ---: |
| 总求解时间，含online预处理 / ms | 0.014900 | 0.073400 | 0.058500 | 79.700% |
| Python分配峰值 / KiB | 5.195 | 12.484 | 7.289 | 58.385% |

Online分项中位数：预处理0.012100 ms，求解0.003100 ms。总时间是每次预处理与求解相加后再取中位数，不能一般地把两个中位数直接相加。
运算：ΔT=(0.073400−0.014900) ms=0.058500 ms；时间节约率=ΔT/0.073400 ms=79.700%。
ΔM=12,784−5,320=7,464 bytes；内存节约率=ΔM/12,784=58.385%。
**成本解释：** 本例测得online总成本更低；收益同时包含窗口、Qf/Qe证书和提前拒绝坏模式。这是当前实现/模型的实测，不是对所有系统最坏复杂度下降的证明。

[Offline BTS数据](yin2016_fig_1c/offline/bts.json) · [Offline闭环](yin2016_fig_1c/closed_loop_system_offline.png) · [Offline supervisor](yin2016_fig_1c/supervisor_offline.json) · [逐项测量](yin2016_fig_1c/online_offline_comparison.json)
<!-- END-RUN-RESULTS: yin2016_fig_1c -->

### 修改意见（请填写）

<!-- USER-NOTES: yin2016_fig_1c -->
- 需要修改的状态或转移：
- 可观事件调整：
- 可控事件调整：
- 希望保留的闭环或预期行为：
- 其他意见：
<!-- END-USER-NOTES: yin2016_fig_1c -->

## yin2016_fig_3a

编号：4。类别：论文自动机。
原始状态数：6；转移数：10；初始状态：`0`。
当前结果：`winning`；所选前视深度：`u=1`。

| 事件属性 | 集合 |
| --- | --- |
| 全部事件 Σ | `{a, b, c, d, e, f, o}` |
| 可观事件 Σo | `{a, c, d, o}` |
| 不可观事件 Σuo | `{b, e, f}` |
| 可控事件 Σc | `{b, o}` |
| 不可控事件 Σuc | `{a, c, d, e, f}` |

[原始系统图](yin2016_fig_3a/plant.png) · [原始系统数据](yin2016_fig_3a/plant.json) · [LL-BTS](yin2016_fig_3a/ll_bts.png) · [闭环结果](yin2016_fig_3a/closed_loop.png)

来源：Yin & Lafortune (2016), Fig. 3a。

模型备注：System G; diagnosis example。

<!-- RUN-RESULTS: yin2016_fig_3a -->
### 运行结果与分析

- 判定：online **winning**，offline **winning**；完整离线结论一致。
- 预处理：Qd=∅；Qf=∅；Qe=`{0, 1, 2, 3, 4, 5}`。
- 深度：草稿阈值=1；最小可判定u=0；恢复offline根极大控制模式的最小u=0；实际采用u=1。
  深度经过逐例扫描标定；草稿阈值本身不等于普遍可解性保证。

| 结构指标 | Online LL-BTS | 传统 Offline BTS |
| --- | ---: | ---: |
| 构建D节点 | 1 | 7 |
| 构建O节点 | 0 | 28 |
| 构建边 | 0 | 78 |
| 全部保留D/O节点 | 1/0 | 7/28 |
| 所选闭环可达状态 | 10 | 10 |
| 所选闭环可达转移 | 17 | 17 |
| 所选控制器记忆状态 | 5 | 5 |

**为什么可解：** 初始估计已完全落在Qe中，允许全部事件即可安全延续。因此online可以在根估计处采用安全终端证书，停止枚举O节点。这不是原始plant只有一个状态；物理闭环仍按实际DFA状态和控制器记忆展开。
**实际控制行为：** 所有导出记忆状态的控制输出均允许全部事件，未禁用任何可控事件。保留的多个估计记忆不表示控制模式一定不同。

**传统BTS初始节点的模式去向（互斥分类）：** 共4个模式，其中UR含plant死锁0个；其余模式直接引入控制死锁0个；局部通过但因后续估计失败而剪除0个；最终保留4个。

| 实测成本 | Online | Offline | 绝对节约（Offline−Online） | 节约率 |
| --- | ---: | ---: | ---: | ---: |
| 总求解时间，含online预处理 / ms | 0.031200 | 0.198100 | 0.166900 | 84.250% |
| Python分配峰值 / KiB | 8.680 | 53.094 | 44.414 | 83.652% |

Online分项中位数：预处理0.025100 ms，求解0.004400 ms。总时间是每次预处理与求解相加后再取中位数，不能一般地把两个中位数直接相加。
运算：ΔT=(0.198100−0.031200) ms=0.166900 ms；时间节约率=ΔT/0.198100 ms=84.250%。
ΔM=54,368−8,888=45,480 bytes；内存节约率=ΔM/54,368=83.652%。
**成本解释：** 本例测得online总成本更低；收益同时包含窗口、Qf/Qe证书和提前拒绝坏模式。这是当前实现/模型的实测，不是对所有系统最坏复杂度下降的证明。

[Offline BTS数据](yin2016_fig_3a/offline/bts.json) · [Offline闭环](yin2016_fig_3a/closed_loop_system_offline.png) · [Offline supervisor](yin2016_fig_3a/supervisor_offline.json) · [逐项测量](yin2016_fig_3a/online_offline_comparison.json)
<!-- END-RUN-RESULTS: yin2016_fig_3a -->

### 修改意见（请填写）

<!-- USER-NOTES: yin2016_fig_3a -->
- 需要修改的状态或转移：
- 可观事件调整：
- 可控事件调整：
- 希望保留的闭环或预期行为：
- 其他意见：
<!-- END-USER-NOTES: yin2016_fig_3a -->

## yin2016_fig_3b

编号：5。类别：论文自动机。
原始状态数：8；转移数：13；初始状态：`0^-1`。
当前结果：`winning`；所选前视深度：`u=1`。

| 事件属性 | 集合 |
| --- | --- |
| 全部事件 Σ | `{a, b, c, d, e, f, o}` |
| 可观事件 Σo | `{a, c, d, o}` |
| 不可观事件 Σuo | `{b, e, f}` |
| 可控事件 Σc | `{b, o}` |
| 不可控事件 Σuc | `{a, c, d, e, f}` |

[原始系统图](yin2016_fig_3b/plant.png) · [原始系统数据](yin2016_fig_3b/plant.json) · [LL-BTS](yin2016_fig_3b/ll_bts.png) · [闭环结果](yin2016_fig_3b/closed_loop.png)

来源：Yin & Lafortune (2016), Fig. 3b。

模型备注：Unfolded GD, K=2, Eq. (22)。

<!-- RUN-RESULTS: yin2016_fig_3b -->
### 运行结果与分析

- 判定：online **winning**，offline **winning**；完整离线结论一致。
- 预处理：Qd=∅；Qf=∅；Qe=`{0^-1, 1^0, 2^-1, 3^1, 3^2, 4^-1, 5^-1, 5^2}`。
- 深度：草稿阈值=1；最小可判定u=0；恢复offline根极大控制模式的最小u=0；实际采用u=1。
  深度经过逐例扫描标定；草稿阈值本身不等于普遍可解性保证。

| 结构指标 | Online LL-BTS | 传统 Offline BTS |
| --- | ---: | ---: |
| 构建D节点 | 1 | 8 |
| 构建O节点 | 0 | 32 |
| 构建边 | 0 | 82 |
| 全部保留D/O节点 | 1/0 | 8/32 |
| 所选闭环可达状态 | 11 | 11 |
| 所选闭环可达转移 | 18 | 18 |
| 所选控制器记忆状态 | 6 | 6 |

**为什么可解：** 初始估计已完全落在Qe中，允许全部事件即可安全延续。因此online可以在根估计处采用安全终端证书，停止枚举O节点。这不是原始plant只有一个状态；物理闭环仍按实际DFA状态和控制器记忆展开。
**实际控制行为：** 所有导出记忆状态的控制输出均允许全部事件，未禁用任何可控事件。保留的多个估计记忆不表示控制模式一定不同。

**传统BTS初始节点的模式去向（互斥分类）：** 共4个模式，其中UR含plant死锁0个；其余模式直接引入控制死锁0个；局部通过但因后续估计失败而剪除0个；最终保留4个。

| 实测成本 | Online | Offline | 绝对节约（Offline−Online） | 节约率 |
| --- | ---: | ---: | ---: | ---: |
| 总求解时间，含online预处理 / ms | 0.034100 | 0.300100 | 0.266000 | 88.637% |
| Python分配峰值 / KiB | 9.820 | 56.375 | 46.555 | 82.580% |

Online分项中位数：预处理0.029200 ms，求解0.004600 ms。总时间是每次预处理与求解相加后再取中位数，不能一般地把两个中位数直接相加。
运算：ΔT=(0.300100−0.034100) ms=0.266000 ms；时间节约率=ΔT/0.300100 ms=88.637%。
ΔM=57,728−10,056=47,672 bytes；内存节约率=ΔM/57,728=82.580%。
**成本解释：** 本例测得online总成本更低；收益同时包含窗口、Qf/Qe证书和提前拒绝坏模式。这是当前实现/模型的实测，不是对所有系统最坏复杂度下降的证明。

[Offline BTS数据](yin2016_fig_3b/offline/bts.json) · [Offline闭环](yin2016_fig_3b/closed_loop_system_offline.png) · [Offline supervisor](yin2016_fig_3b/supervisor_offline.json) · [逐项测量](yin2016_fig_3b/online_offline_comparison.json)
<!-- END-RUN-RESULTS: yin2016_fig_3b -->

### 修改意见（请填写）

<!-- USER-NOTES: yin2016_fig_3b -->
- 需要修改的状态或转移：
- 可观事件调整：
- 可控事件调整：
- 希望保留的闭环或预期行为：
- 其他意见：
<!-- END-USER-NOTES: yin2016_fig_3b -->

## yin2016_fig_3c

编号：6。类别：论文自动机。
原始状态数：8；转移数：11；初始状态：`0`。
当前结果：`winning`；所选前视深度：`u=1`。

| 事件属性 | 集合 |
| --- | --- |
| 全部事件 Σ | `{a, b, c, d, e, f, o}` |
| 可观事件 Σo | `{a, c, d, o}` |
| 不可观事件 Σuo | `{b, e, f}` |
| 可控事件 Σc | `{b, o}` |
| 不可控事件 Σuc | `{a, c, d, e, f}` |

[原始系统图](yin2016_fig_3c/plant.png) · [原始系统数据](yin2016_fig_3c/plant.json) · [LL-BTS](yin2016_fig_3c/ll_bts.png) · [闭环结果](yin2016_fig_3c/closed_loop.png)

来源：Yin & Lafortune (2016), Fig. 3c。

模型备注：Controlled language L(S*/G); primed states retained。

<!-- RUN-RESULTS: yin2016_fig_3c -->
### 运行结果与分析

- 判定：online **winning**，offline **winning**；完整离线结论一致。
- 预处理：Qd=∅；Qf=∅；Qe=`{0, 1, 2, 2', 3, 4, 4', 5}`。
- 深度：草稿阈值=1；最小可判定u=0；恢复offline根极大控制模式的最小u=0；实际采用u=1。
  深度经过逐例扫描标定；草稿阈值本身不等于普遍可解性保证。

| 结构指标 | Online LL-BTS | 传统 Offline BTS |
| --- | ---: | ---: |
| 构建D节点 | 1 | 5 |
| 构建O节点 | 0 | 20 |
| 构建边 | 0 | 50 |
| 全部保留D/O节点 | 1/0 | 5/20 |
| 所选闭环可达状态 | 8 | 8 |
| 所选闭环可达转移 | 11 | 11 |
| 所选控制器记忆状态 | 4 | 4 |

**为什么可解：** 初始估计已完全落在Qe中，允许全部事件即可安全延续。因此online可以在根估计处采用安全终端证书，停止枚举O节点。这不是原始plant只有一个状态；物理闭环仍按实际DFA状态和控制器记忆展开。
**实际控制行为：** 所有导出记忆状态的控制输出均允许全部事件，未禁用任何可控事件。保留的多个估计记忆不表示控制模式一定不同。

**传统BTS初始节点的模式去向（互斥分类）：** 共4个模式，其中UR含plant死锁0个；其余模式直接引入控制死锁0个；局部通过但因后续估计失败而剪除0个；最终保留4个。

| 实测成本 | Online | Offline | 绝对节约（Offline−Online） | 节约率 |
| --- | ---: | ---: | ---: | ---: |
| 总求解时间，含online预处理 / ms | 0.048300 | 0.341400 | 0.293100 | 85.852% |
| Python分配峰值 / KiB | 9.797 | 38.719 | 28.922 | 74.697% |

Online分项中位数：预处理0.042500 ms，求解0.005400 ms。总时间是每次预处理与求解相加后再取中位数，不能一般地把两个中位数直接相加。
运算：ΔT=(0.341400−0.048300) ms=0.293100 ms；时间节约率=ΔT/0.341400 ms=85.852%。
ΔM=39,648−10,032=29,616 bytes；内存节约率=ΔM/39,648=74.697%。
**成本解释：** 本例测得online总成本更低；收益同时包含窗口、Qf/Qe证书和提前拒绝坏模式。这是当前实现/模型的实测，不是对所有系统最坏复杂度下降的证明。

[Offline BTS数据](yin2016_fig_3c/offline/bts.json) · [Offline闭环](yin2016_fig_3c/closed_loop_system_offline.png) · [Offline supervisor](yin2016_fig_3c/supervisor_offline.json) · [逐项测量](yin2016_fig_3c/online_offline_comparison.json)
<!-- END-RUN-RESULTS: yin2016_fig_3c -->

### 修改意见（请填写）

<!-- USER-NOTES: yin2016_fig_3c -->
- 需要修改的状态或转移：
- 可观事件调整：
- 可控事件调整：
- 希望保留的闭环或预期行为：
- 其他意见：
<!-- END-USER-NOTES: yin2016_fig_3c -->

## 15ACCopac_fig_1

编号：7。类别：论文自动机。
原始状态数：7；转移数：10；初始状态：`0`。
当前结果：`winning`；所选前视深度：`u=2`。

| 事件属性 | 集合 |
| --- | --- |
| 全部事件 Σ | `{a, b, c, o1, o2}` |
| 可观事件 Σo | `{o1, o2}` |
| 不可观事件 Σuo | `{a, b, c}` |
| 可控事件 Σc | `{a, b, c}` |
| 不可控事件 Σuc | `{o1, o2}` |

[原始系统图](15ACCopac_fig_1/plant.png) · [原始系统数据](15ACCopac_fig_1/plant.json) · [LL-BTS](15ACCopac_fig_1/ll_bts.png) · [闭环结果](15ACCopac_fig_1/closed_loop.png)

来源：15ACCopac.pdf, Fig. 1。

模型备注：p.379; differs from 16TACuniform: state 1 has no e self-loop。

<!-- RUN-RESULTS: 15ACCopac_fig_1 -->
### 运行结果与分析

- 判定：online **winning**，offline **winning**；完整离线结论一致。
- 预处理：Qd=∅；Qf=∅；Qe=`{0, 1, 2, 3, 4, 5, 6}`。
- 深度：草稿阈值=2；最小可判定u=0；恢复offline根极大控制模式的最小u=0；实际采用u=2。
  深度经过逐例扫描标定；草稿阈值本身不等于普遍可解性保证。

| 结构指标 | Online LL-BTS | 传统 Offline BTS |
| --- | ---: | ---: |
| 构建D节点 | 1 | 5 |
| 构建O节点 | 0 | 40 |
| 构建边 | 0 | 95 |
| 全部保留D/O节点 | 1/0 | 5/36 |
| 所选闭环可达状态 | 9 | 9 |
| 所选闭环可达转移 | 13 | 13 |
| 所选控制器记忆状态 | 3 | 3 |

**为什么可解：** 初始估计已完全落在Qe中，允许全部事件即可安全延续。因此online可以在根估计处采用安全终端证书，停止枚举O节点。这不是原始plant只有一个状态；物理闭环仍按实际DFA状态和控制器记忆展开。
**实际控制行为：** 所有导出记忆状态的控制输出均允许全部事件，未禁用任何可控事件。保留的多个估计记忆不表示控制模式一定不同。

**传统BTS初始节点的模式去向（互斥分类）：** 共8个模式，其中UR含plant死锁0个；其余模式直接引入控制死锁4个；局部通过但因后续估计失败而剪除0个；最终保留4个。

| 实测成本 | Online | Offline | 绝对节约（Offline−Online） | 节约率 |
| --- | ---: | ---: | ---: | ---: |
| 总求解时间，含online预处理 / ms | 0.037700 | 0.495600 | 0.457900 | 92.393% |
| Python分配峰值 / KiB | 8.461 | 63.938 | 55.477 | 86.767% |

Online分项中位数：预处理0.033000 ms，求解0.004800 ms。总时间是每次预处理与求解相加后再取中位数，不能一般地把两个中位数直接相加。
运算：ΔT=(0.495600−0.037700) ms=0.457900 ms；时间节约率=ΔT/0.495600 ms=92.393%。
ΔM=65,472−8,664=56,808 bytes；内存节约率=ΔM/65,472=86.767%。
**成本解释：** 本例测得online总成本更低；收益同时包含窗口、Qf/Qe证书和提前拒绝坏模式。这是当前实现/模型的实测，不是对所有系统最坏复杂度下降的证明。

[Offline BTS数据](15ACCopac_fig_1/offline/bts.json) · [Offline闭环](15ACCopac_fig_1/closed_loop_system_offline.png) · [Offline supervisor](15ACCopac_fig_1/supervisor_offline.json) · [逐项测量](15ACCopac_fig_1/online_offline_comparison.json)
<!-- END-RUN-RESULTS: 15ACCopac_fig_1 -->

### 修改意见（请填写）

<!-- USER-NOTES: 15ACCopac_fig_1 -->
- 需要修改的状态或转移：
- 可观事件调整：
- 可控事件调整：
- 希望保留的闭环或预期行为：
- 其他意见：
<!-- END-USER-NOTES: 15ACCopac_fig_1 -->

## 15ACCopac_fig_2a

编号：8。类别：论文自动机。
原始状态数：5；转移数：6；初始状态：`0`。
当前结果：`winning`；所选前视深度：`u=2`。

| 事件属性 | 集合 |
| --- | --- |
| 全部事件 Σ | `{a, b, c, o1, o2}` |
| 可观事件 Σo | `{o1, o2}` |
| 不可观事件 Σuo | `{a, b, c}` |
| 可控事件 Σc | `{a, b, c}` |
| 不可控事件 Σuc | `{o1, o2}` |

[原始系统图](15ACCopac_fig_2a/plant.png) · [原始系统数据](15ACCopac_fig_2a/plant.json) · [LL-BTS](15ACCopac_fig_2a/ll_bts.png) · [闭环结果](15ACCopac_fig_2a/closed_loop.png)

来源：15ACCopac.pdf, Fig. 2a。

模型备注：Solution G1, p.379; alphabet excludes e unlike TAC 2016。

<!-- RUN-RESULTS: 15ACCopac_fig_2a -->
### 运行结果与分析

- 判定：online **winning**，offline **winning**；完整离线结论一致。
- 预处理：Qd=∅；Qf=∅；Qe=`{0, 3, 4, 5, 6}`。
- 深度：草稿阈值=2；最小可判定u=0；恢复offline根极大控制模式的最小u=0；实际采用u=2。
  深度经过逐例扫描标定；草稿阈值本身不等于普遍可解性保证。

| 结构指标 | Online LL-BTS | 传统 Offline BTS |
| --- | ---: | ---: |
| 构建D节点 | 1 | 3 |
| 构建O节点 | 0 | 24 |
| 构建边 | 0 | 44 |
| 全部保留D/O节点 | 1/0 | 3/20 |
| 所选闭环可达状态 | 5 | 5 |
| 所选闭环可达转移 | 6 | 6 |
| 所选控制器记忆状态 | 2 | 2 |

**为什么可解：** 初始估计已完全落在Qe中，允许全部事件即可安全延续。因此online可以在根估计处采用安全终端证书，停止枚举O节点。这不是原始plant只有一个状态；物理闭环仍按实际DFA状态和控制器记忆展开。
**实际控制行为：** 所有导出记忆状态的控制输出均允许全部事件，未禁用任何可控事件。保留的多个估计记忆不表示控制模式一定不同。

**传统BTS初始节点的模式去向（互斥分类）：** 共8个模式，其中UR含plant死锁0个；其余模式直接引入控制死锁4个；局部通过但因后续估计失败而剪除0个；最终保留4个。

| 实测成本 | Online | Offline | 绝对节约（Offline−Online） | 节约率 |
| --- | ---: | ---: | ---: | ---: |
| 总求解时间，含online预处理 / ms | 0.019200 | 0.199000 | 0.179800 | 90.352% |
| Python分配峰值 / KiB | 6.758 | 37.508 | 30.750 | 81.983% |

Online分项中位数：预处理0.016300 ms，求解0.003000 ms。总时间是每次预处理与求解相加后再取中位数，不能一般地把两个中位数直接相加。
运算：ΔT=(0.199000−0.019200) ms=0.179800 ms；时间节约率=ΔT/0.199000 ms=90.352%。
ΔM=38,408−6,920=31,488 bytes；内存节约率=ΔM/38,408=81.983%。
**成本解释：** 本例测得online总成本更低；收益同时包含窗口、Qf/Qe证书和提前拒绝坏模式。这是当前实现/模型的实测，不是对所有系统最坏复杂度下降的证明。

[Offline BTS数据](15ACCopac_fig_2a/offline/bts.json) · [Offline闭环](15ACCopac_fig_2a/closed_loop_system_offline.png) · [Offline supervisor](15ACCopac_fig_2a/supervisor_offline.json) · [逐项测量](15ACCopac_fig_2a/online_offline_comparison.json)
<!-- END-RUN-RESULTS: 15ACCopac_fig_2a -->

### 修改意见（请填写）

<!-- USER-NOTES: 15ACCopac_fig_2a -->
- 需要修改的状态或转移：
- 可观事件调整：
- 可控事件调整：
- 希望保留的闭环或预期行为：
- 其他意见：
<!-- END-USER-NOTES: 15ACCopac_fig_2a -->

## 15ACCopac_fig_2b

编号：9。类别：论文自动机。
原始状态数：2；转移数：1；初始状态：`0`。
当前结果：`losing`；所选前视深度：`u=0`。

| 事件属性 | 集合 |
| --- | --- |
| 全部事件 Σ | `{a, b, c, o1, o2}` |
| 可观事件 Σo | `{o1, o2}` |
| 不可观事件 Σuo | `{a, b, c}` |
| 可控事件 Σc | `{a, b, c}` |
| 不可控事件 Σuc | `{o1, o2}` |

[原始系统图](15ACCopac_fig_2b/plant.png) · [原始系统数据](15ACCopac_fig_2b/plant.json) · [LL-BTS](15ACCopac_fig_2b/ll_bts.png) · [闭环结果](15ACCopac_fig_2b/closed_loop.png)

来源：15ACCopac.pdf, Fig. 2b。

模型备注：Solution G2; terminal state 1 retained, dashed a,c edges omitted。

<!-- RUN-RESULTS: 15ACCopac_fig_2b -->
### 运行结果与分析

- 判定：online **losing**，offline **losing**；完整离线结论一致。
- 预处理：Qd=`{1}`；Qf=`{0}`；Qe=∅。
- 深度：草稿阈值=0；最小可判定u=0；恢复offline根极大控制模式的最小u=0；实际采用u=0。
  深度经过逐例扫描标定；草稿阈值本身不等于普遍可解性保证。

| 结构指标 | Online LL-BTS | 传统 Offline BTS |
| --- | ---: | ---: |
| 构建D节点 | 1 | 1 |
| 构建O节点 | 0 | 8 |
| 构建边 | 0 | 8 |
| 全部保留D/O节点 | 0/0 | 0/0 |

**为什么不可解：** 完整已知系统的offline BTS也将初始决策节点剪除，因此这不是单纯u偏小造成的未判定；当前模型不存在满足本实验无死锁目标的supervisor。
初始状态属于Qf：沿单后继状态链必然到达Qd。允许后继会走向死锁，禁用全部后继则直接引入控制死锁。
未将空图或“不可解”提示图当成一个可行闭环，也未给终止状态补自环。

**传统BTS初始节点的模式去向（互斥分类）：** 共8个模式，其中UR含plant死锁4个；其余模式直接引入控制死锁4个；局部通过但因后续估计失败而剪除0个；最终保留0个。

| 实测成本 | Online | Offline | 绝对节约（Offline−Online） | 节约率 |
| --- | ---: | ---: | ---: | ---: |
| 总求解时间，含online预处理 / ms | 0.034100 | 0.066200 | 0.032100 | 48.489% |
| Python分配峰值 / KiB | 7.836 | 13.305 | 5.469 | 41.104% |

Online分项中位数：预处理0.014200 ms，求解0.019100 ms。总时间是每次预处理与求解相加后再取中位数，不能一般地把两个中位数直接相加。
运算：ΔT=(0.066200−0.034100) ms=0.032100 ms；时间节约率=ΔT/0.066200 ms=48.489%。
ΔM=13,624−8,024=5,600 bytes；内存节约率=ΔM/13,624=41.104%。
**成本解释：** 本例测得online总成本更低；收益同时包含窗口、Qf/Qe证书和提前拒绝坏模式。这是当前实现/模型的实测，不是对所有系统最坏复杂度下降的证明。

[Offline BTS数据](15ACCopac_fig_2b/offline/bts.json) · [Offline闭环](15ACCopac_fig_2b/closed_loop_system_offline.png) · [Offline supervisor](15ACCopac_fig_2b/supervisor_offline.json) · [逐项测量](15ACCopac_fig_2b/online_offline_comparison.json)
<!-- END-RUN-RESULTS: 15ACCopac_fig_2b -->

### 修改意见（请填写）

<!-- USER-NOTES: 15ACCopac_fig_2b -->
- 需要修改的状态或转移：
- 可观事件调整：
- 可控事件调整：
- 希望保留的闭环或预期行为：
- 其他意见：
<!-- END-USER-NOTES: 15ACCopac_fig_2b -->

## 15ACCopac_fig_2c

编号：10。类别：论文自动机。
原始状态数：6；转移数：7；初始状态：`0`。
当前结果：`winning`；所选前视深度：`u=2`。

| 事件属性 | 集合 |
| --- | --- |
| 全部事件 Σ | `{a, b, c, o1, o2}` |
| 可观事件 Σo | `{o1, o2}` |
| 不可观事件 Σuo | `{a, b, c}` |
| 可控事件 Σc | `{a, b, c}` |
| 不可控事件 Σuc | `{o1, o2}` |

[原始系统图](15ACCopac_fig_2c/plant.png) · [原始系统数据](15ACCopac_fig_2c/plant.json) · [LL-BTS](15ACCopac_fig_2c/ll_bts.png) · [闭环结果](15ACCopac_fig_2c/closed_loop.png)

来源：15ACCopac.pdf, Fig. 2c。

模型备注：G3 union-language illustration; not claimed to be a realizable supervisor。

<!-- RUN-RESULTS: 15ACCopac_fig_2c -->
### 运行结果与分析

- 判定：online **winning**，offline **winning**；完整离线结论一致。
- 预处理：Qd=`{1}`；Qf=∅；Qe=`{3, 4, 5, 6}`。
- 深度：草稿阈值=2；最小可判定u=1；恢复offline根极大控制模式的最小u=2；实际采用u=2。
  深度经过逐例扫描标定；草稿阈值本身不等于普遍可解性保证。

| 结构指标 | Online LL-BTS | 传统 Offline BTS |
| --- | ---: | ---: |
| 构建D节点 | 3 | 3 |
| 构建O节点 | 2 | 24 |
| 构建边 | 4 | 44 |
| 全部保留D/O节点 | 3/2 | 3/18 |
| 所选闭环可达状态 | 5 | 5 |
| 所选闭环可达转移 | 6 | 6 |
| 所选控制器记忆状态 | 2 | 2 |

**为什么可解：** 初始估计不能直接用Qe证书终止，但剪枝后仍有认证控制模式。所选supervisor在每个估计处固定选择一个保留模式，所有可能观测均有认证后续控制，并检查不可观测可达集中的每个实际状态都有可用事件。
**实际控制行为：** 不可控事件始终允许；下表列出选定online supervisor的控制输出。

| 记忆 | 估计 | 允许的可控事件 | 禁用的可控事件 |
| --- | --- | --- | --- |
| C0 | `{0}` | `{a, c}` | `{b}` |
| C1 | `{5, 6}` | `{a, b, c}` | ∅ |

**传统BTS初始节点的模式去向（互斥分类）：** 共8个模式，其中UR含plant死锁4个；其余模式直接引入控制死锁2个；局部通过但因后续估计失败而剪除0个；最终保留2个。

| 实测成本 | Online | Offline | 绝对节约（Offline−Online） | 节约率 |
| --- | ---: | ---: | ---: | ---: |
| 总求解时间，含online预处理 / ms | 0.080300 | 0.135800 | 0.055500 | 40.869% |
| Python分配峰值 / KiB | 12.297 | 37.992 | 25.695 | 67.633% |

Online分项中位数：预处理0.017100 ms，求解0.063100 ms。总时间是每次预处理与求解相加后再取中位数，不能一般地把两个中位数直接相加。
运算：ΔT=(0.135800−0.080300) ms=0.055500 ms；时间节约率=ΔT/0.135800 ms=40.869%。
ΔM=38,904−12,592=26,312 bytes；内存节约率=ΔM/38,904=67.633%。
**成本解释：** 本例测得online总成本更低；收益同时包含窗口、Qf/Qe证书和提前拒绝坏模式。这是当前实现/模型的实测，不是对所有系统最坏复杂度下降的证明。

[Offline BTS数据](15ACCopac_fig_2c/offline/bts.json) · [Offline闭环](15ACCopac_fig_2c/closed_loop_system_offline.png) · [Offline supervisor](15ACCopac_fig_2c/supervisor_offline.json) · [逐项测量](15ACCopac_fig_2c/online_offline_comparison.json)
<!-- END-RUN-RESULTS: 15ACCopac_fig_2c -->

### 修改意见（请填写）

<!-- USER-NOTES: 15ACCopac_fig_2c -->
- 需要修改的状态或转移：
- 可观事件调整：
- 可控事件调整：
- 希望保留的闭环或预期行为：
- 其他意见：
<!-- END-USER-NOTES: 15ACCopac_fig_2c -->

## 16CDC_fig_2a_G

编号：11。类别：论文自动机。
原始状态数：9；转移数：13；初始状态：`0`。
当前结果：`losing`；所选前视深度：`u=3`。

| 事件属性 | 集合 |
| --- | --- |
| 全部事件 Σ | `{c1, c2, o}` |
| 可观事件 Σo | `{o}` |
| 不可观事件 Σuo | `{c1, c2}` |
| 可控事件 Σc | `{c1, c2}` |
| 不可控事件 Σuc | `{o}` |

[原始系统图](16CDC_fig_2a_G/plant.png) · [原始系统数据](16CDC_fig_2a_G/plant.json) · [LL-BTS](16CDC_fig_2a_G/ll_bts.png) · [闭环结果](16CDC_fig_2a_G/closed_loop.png)

来源：16CDC.pdf, Fig. 2a_G。

模型备注：p.3926, G; numbering skips state 4; state 9 illegal。

<!-- RUN-RESULTS: 16CDC_fig_2a_G -->
### 运行结果与分析

- 判定：online **losing**，offline **losing**；完整离线结论一致。
- 预处理：Qd=`{9}`；Qf=`{7, 8}`；Qe=∅。
- 深度：草稿阈值=1；最小可判定u=3；恢复offline根极大控制模式的最小u=3；实际采用u=3。
  深度经过逐例扫描标定；草稿阈值本身不等于普遍可解性保证。

| 结构指标 | Online LL-BTS | 传统 Offline BTS |
| --- | ---: | ---: |
| 构建D节点 | 5 | 5 |
| 构建O节点 | 10 | 20 |
| 构建边 | 20 | 32 |
| 全部保留D/O节点 | 0/0 | 0/0 |

**为什么不可解：** 完整已知系统的offline BTS也将初始决策节点剪除，因此这不是单纯u偏小造成的未判定；当前模型不存在满足本实验无死锁目标的supervisor。
未将空图或“不可解”提示图当成一个可行闭环，也未给终止状态补自环。

**传统BTS初始节点的模式去向（互斥分类）：** 共4个模式，其中UR含plant死锁0个；其余模式直接引入控制死锁0个；局部通过但因后续估计失败而剪除4个；最终保留0个。

| 实测成本 | Online | Offline | 绝对节约（Offline−Online） | 节约率 |
| --- | ---: | ---: | ---: | ---: |
| 总求解时间，含online预处理 / ms | 0.188000 | 0.149400 | -0.038600 | -25.837% |
| Python分配峰值 / KiB | 24.719 | 33.609 | 8.891 | 26.453% |

Online分项中位数：预处理0.028800 ms，求解0.152400 ms。总时间是每次预处理与求解相加后再取中位数，不能一般地把两个中位数直接相加。
运算：ΔT=(0.149400−0.188000) ms=-0.038600 ms；时间节约率=ΔT/0.149400 ms=-25.837%。
ΔM=34,416−25,312=9,104 bytes；内存节约率=ΔM/34,416=26.453%。
**成本解释：** 本例online含预处理的总时间反而更高，已保留负节约率。减少图规模不保证抵消预处理成本；小模型的微秒级时间也易受解释器及调度影响。

[Offline BTS数据](16CDC_fig_2a_G/offline/bts.json) · [Offline闭环](16CDC_fig_2a_G/closed_loop_system_offline.png) · [Offline supervisor](16CDC_fig_2a_G/supervisor_offline.json) · [逐项测量](16CDC_fig_2a_G/online_offline_comparison.json)
<!-- END-RUN-RESULTS: 16CDC_fig_2a_G -->

### 修改意见（请填写）

<!-- USER-NOTES: 16CDC_fig_2a_G -->
- 需要修改的状态或转移：
- 可观事件调整：
- 可控事件调整：
- 希望保留的闭环或预期行为：
- 其他意见：
<!-- END-USER-NOTES: 16CDC_fig_2a_G -->

## 16CDC_fig_2a_K

编号：12。类别：论文自动机。
原始状态数：8；转移数：10；初始状态：`0`。
当前结果：`losing`；所选前视深度：`u=3`。

| 事件属性 | 集合 |
| --- | --- |
| 全部事件 Σ | `{c1, c2, o}` |
| 可观事件 Σo | `{o}` |
| 不可观事件 Σuo | `{c1, c2}` |
| 可控事件 Σc | `{c1, c2}` |
| 不可控事件 Σuc | `{o}` |

[原始系统图](16CDC_fig_2a_K/plant.png) · [原始系统数据](16CDC_fig_2a_K/plant.json) · [LL-BTS](16CDC_fig_2a_K/ll_bts.png) · [闭环结果](16CDC_fig_2a_K/closed_loop.png)

来源：16CDC.pdf, Fig. 2a_K。

模型备注：K obtained by removing state 9 and incident transitions。

<!-- RUN-RESULTS: 16CDC_fig_2a_K -->
### 运行结果与分析

- 判定：online **losing**，offline **losing**；完整离线结论一致。
- 预处理：Qd=`{7, 8}`；Qf=∅；Qe=∅。
- 深度：草稿阈值=0；最小可判定u=3；恢复offline根极大控制模式的最小u=3；实际采用u=3。
  深度经过逐例扫描标定；草稿阈值本身不等于普遍可解性保证。

| 结构指标 | Online LL-BTS | 传统 Offline BTS |
| --- | ---: | ---: |
| 构建D节点 | 5 | 5 |
| 构建O节点 | 12 | 20 |
| 构建边 | 24 | 32 |
| 全部保留D/O节点 | 0/0 | 0/0 |

**为什么不可解：** 完整已知系统的offline BTS也将初始决策节点剪除，因此这不是单纯u偏小造成的未判定；当前模型不存在满足本实验无死锁目标的supervisor。
未将空图或“不可解”提示图当成一个可行闭环，也未给终止状态补自环。

**传统BTS初始节点的模式去向（互斥分类）：** 共4个模式，其中UR含plant死锁0个；其余模式直接引入控制死锁0个；局部通过但因后续估计失败而剪除4个；最终保留0个。

| 实测成本 | Online | Offline | 绝对节约（Offline−Online） | 节约率 |
| --- | ---: | ---: | ---: | ---: |
| 总求解时间，含online预处理 / ms | 0.350000 | 0.279800 | -0.070200 | -25.089% |
| Python分配峰值 / KiB | 26.680 | 33.469 | 6.789 | 20.285% |

Online分项中位数：预处理0.033900 ms，求解0.302200 ms。总时间是每次预处理与求解相加后再取中位数，不能一般地把两个中位数直接相加。
运算：ΔT=(0.279800−0.350000) ms=-0.070200 ms；时间节约率=ΔT/0.279800 ms=-25.089%。
ΔM=34,272−27,320=6,952 bytes；内存节约率=ΔM/34,272=20.285%。
**成本解释：** 本例online含预处理的总时间反而更高，已保留负节约率。减少图规模不保证抵消预处理成本；小模型的微秒级时间也易受解释器及调度影响。

[Offline BTS数据](16CDC_fig_2a_K/offline/bts.json) · [Offline闭环](16CDC_fig_2a_K/closed_loop_system_offline.png) · [Offline supervisor](16CDC_fig_2a_K/supervisor_offline.json) · [逐项测量](16CDC_fig_2a_K/online_offline_comparison.json)
<!-- END-RUN-RESULTS: 16CDC_fig_2a_K -->

### 修改意见（请填写）

<!-- USER-NOTES: 16CDC_fig_2a_K -->
- 需要修改的状态或转移：
- 可观事件调整：
- 可控事件调整：
- 希望保留的闭环或预期行为：
- 其他意见：
<!-- END-USER-NOTES: 16CDC_fig_2a_K -->

## 16CDC_fig_2b

编号：13。类别：论文自动机。
原始状态数：3；转移数：3；初始状态：`0`。
当前结果：`losing`；所选前视深度：`u=2`。

| 事件属性 | 集合 |
| --- | --- |
| 全部事件 Σ | `{c1, c2, o}` |
| 可观事件 Σo | `{o}` |
| 不可观事件 Σuo | `{c1, c2}` |
| 可控事件 Σc | `{c1, c2}` |
| 不可控事件 Σuc | `{o}` |

[原始系统图](16CDC_fig_2b/plant.png) · [原始系统数据](16CDC_fig_2b/plant.json) · [LL-BTS](16CDC_fig_2b/ll_bts.png) · [闭环结果](16CDC_fig_2b/closed_loop.png)

来源：16CDC.pdf, Fig. 2b。

模型备注：Lower-bound R, p.3926。

<!-- RUN-RESULTS: 16CDC_fig_2b -->
### 运行结果与分析

- 判定：online **losing**，offline **losing**；完整离线结论一致。
- 预处理：Qd=`{2}`；Qf=∅；Qe=∅。
- 深度：草稿阈值=0；最小可判定u=2；恢复offline根极大控制模式的最小u=2；实际采用u=2。
  深度经过逐例扫描标定；草稿阈值本身不等于普遍可解性保证。

| 结构指标 | Online LL-BTS | 传统 Offline BTS |
| --- | ---: | ---: |
| 构建D节点 | 3 | 3 |
| 构建O节点 | 8 | 12 |
| 构建边 | 16 | 20 |
| 全部保留D/O节点 | 0/0 | 0/0 |

**为什么不可解：** 完整已知系统的offline BTS也将初始决策节点剪除，因此这不是单纯u偏小造成的未判定；当前模型不存在满足本实验无死锁目标的supervisor。
未将空图或“不可解”提示图当成一个可行闭环，也未给终止状态补自环。

**传统BTS初始节点的模式去向（互斥分类）：** 共4个模式，其中UR含plant死锁0个；其余模式直接引入控制死锁0个；局部通过但因后续估计失败而剪除4个；最终保留0个。

| 实测成本 | Online | Offline | 绝对节约（Offline−Online） | 节约率 |
| --- | ---: | ---: | ---: | ---: |
| 总求解时间，含online预处理 / ms | 0.166300 | 0.160500 | -0.005800 | -3.614% |
| Python分配峰值 / KiB | 19.312 | 20.297 | 0.984 | 4.850% |

Online分项中位数：预处理0.019800 ms，求解0.146500 ms。总时间是每次预处理与求解相加后再取中位数，不能一般地把两个中位数直接相加。
运算：ΔT=(0.160500−0.166300) ms=-0.005800 ms；时间节约率=ΔT/0.160500 ms=-3.614%。
ΔM=20,784−19,776=1,008 bytes；内存节约率=ΔM/20,784=4.850%。
**成本解释：** 本例online含预处理的总时间反而更高，已保留负节约率。减少图规模不保证抵消预处理成本；小模型的微秒级时间也易受解释器及调度影响。

[Offline BTS数据](16CDC_fig_2b/offline/bts.json) · [Offline闭环](16CDC_fig_2b/closed_loop_system_offline.png) · [Offline supervisor](16CDC_fig_2b/supervisor_offline.json) · [逐项测量](16CDC_fig_2b/online_offline_comparison.json)
<!-- END-RUN-RESULTS: 16CDC_fig_2b -->

### 修改意见（请填写）

<!-- USER-NOTES: 16CDC_fig_2b -->
- 需要修改的状态或转移：
- 可观事件调整：
- 可控事件调整：
- 希望保留的闭环或预期行为：
- 其他意见：
<!-- END-USER-NOTES: 16CDC_fig_2b -->

## 14IFAC_fig_1

编号：14。类别：论文自动机。
原始状态数：8；转移数：8；初始状态：`1`。
当前结果：`losing`；所选前视深度：`u=2`。

| 事件属性 | 集合 |
| --- | --- |
| 全部事件 Σ | `{a, b, c, o, uc}` |
| 可观事件 Σo | `{o, uc}` |
| 不可观事件 Σuo | `{a, b, c}` |
| 可控事件 Σc | `{a, b, c, o}` |
| 不可控事件 Σuc | `{uc}` |

[原始系统图](14IFAC_fig_1/plant.png) · [原始系统数据](14IFAC_fig_1/plant.json) · [LL-BTS](14IFAC_fig_1/ll_bts.png) · [闭环结果](14IFAC_fig_1/closed_loop.png)

来源：14IFAC.pdf, Fig. 1。

模型备注：p.2424; safety specification is separate; states 3,7,8 have no outgoing edges。

<!-- RUN-RESULTS: 14IFAC_fig_1 -->
### 运行结果与分析

- 判定：online **losing**，offline **losing**；完整离线结论一致。
- 预处理：Qd=`{3, 7, 8}`；Qf=`{5, 6}`；Qe=∅。
- 深度：草稿阈值=1；最小可判定u=2；恢复offline根极大控制模式的最小u=2；实际采用u=2。
  深度经过逐例扫描标定；草稿阈值本身不等于普遍可解性保证。

| 结构指标 | Online LL-BTS | 传统 Offline BTS |
| --- | ---: | ---: |
| 构建D节点 | 3 | 4 |
| 构建O节点 | 6 | 64 |
| 构建边 | 12 | 84 |
| 全部保留D/O节点 | 0/0 | 0/0 |

**为什么不可解：** 完整已知系统的offline BTS也将初始决策节点剪除，因此这不是单纯u偏小造成的未判定；当前模型不存在满足本实验无死锁目标的supervisor。
本例虽有 `1 —b→ 2 —o→ 4 —c→ 1`，但b不可观测。到达1与隐藏到达2的观测历史相同，不能分别禁止/允许o。允许o会同时开放 `1 —o→ 5`，5允许a则到7死锁，禁用a则停在5；禁止o又使2无法安全继续，所以不能只保留期望的环。
未将空图或“不可解”提示图当成一个可行闭环，也未给终止状态补自环。

**传统BTS初始节点的模式去向（互斥分类）：** 共16个模式，其中UR含plant死锁4个；其余模式直接引入控制死锁6个；局部通过但因后续估计失败而剪除6个；最终保留0个。

| 实测成本 | Online | Offline | 绝对节约（Offline−Online） | 节约率 |
| --- | ---: | ---: | ---: | ---: |
| 总求解时间，含online预处理 / ms | 0.130400 | 0.314100 | 0.183700 | 58.485% |
| Python分配峰值 / KiB | 19.078 | 68.289 | 49.211 | 72.063% |

Online分项中位数：预处理0.022900 ms，求解0.108100 ms。总时间是每次预处理与求解相加后再取中位数，不能一般地把两个中位数直接相加。
运算：ΔT=(0.314100−0.130400) ms=0.183700 ms；时间节约率=ΔT/0.314100 ms=58.485%。
ΔM=69,928−19,536=50,392 bytes；内存节约率=ΔM/69,928=72.063%。
**成本解释：** 本例测得online总成本更低；收益同时包含窗口、Qf/Qe证书和提前拒绝坏模式。这是当前实现/模型的实测，不是对所有系统最坏复杂度下降的证明。

[Offline BTS数据](14IFAC_fig_1/offline/bts.json) · [Offline闭环](14IFAC_fig_1/closed_loop_system_offline.png) · [Offline supervisor](14IFAC_fig_1/supervisor_offline.json) · [逐项测量](14IFAC_fig_1/online_offline_comparison.json)
<!-- END-RUN-RESULTS: 14IFAC_fig_1 -->

### 修改意见（请填写）

<!-- USER-NOTES: 14IFAC_fig_1 -->
- 需要修改的状态或转移：
- 可观事件调整：
- 可控事件调整：
- 希望保留的闭环或预期行为：
- 其他意见：
<!-- END-USER-NOTES: 14IFAC_fig_1 -->

## 16WODESmax_fig_1a

编号：15。类别：论文自动机。
原始状态数：6；转移数：9；初始状态：`0`。
当前结果：`losing`；所选前视深度：`u=1`。

| 事件属性 | 集合 |
| --- | --- |
| 全部事件 Σ | `{a, b, c1, c2}` |
| 可观事件 Σo | `{a, b}` |
| 不可观事件 Σuo | `{c1, c2}` |
| 可控事件 Σc | `{c1, c2}` |
| 不可控事件 Σuc | `{a, b}` |

[原始系统图](16WODESmax_fig_1a/plant.png) · [原始系统数据](16WODESmax_fig_1a/plant.json) · [LL-BTS](16WODESmax_fig_1a/ll_bts.png) · [闭环结果](16WODESmax_fig_1a/closed_loop.png)

来源：16WODESmax.pdf, Fig. 1a。

模型备注：Specification K reused as a standalone DFA; terminal states retained。

<!-- RUN-RESULTS: 16WODESmax_fig_1a -->
### 运行结果与分析

- 判定：online **losing**，offline **losing**；完整离线结论一致。
- 预处理：Qd=`{5, 6}`；Qf=∅；Qe=∅。
- 深度：草稿阈值=0；最小可判定u=1；恢复offline根极大控制模式的最小u=1；实际采用u=1。
  深度经过逐例扫描标定；草稿阈值本身不等于普遍可解性保证。

| 结构指标 | Online LL-BTS | 传统 Offline BTS |
| --- | ---: | ---: |
| 构建D节点 | 4 | 4 |
| 构建O节点 | 4 | 16 |
| 构建边 | 12 | 24 |
| 全部保留D/O节点 | 0/0 | 0/0 |

**为什么不可解：** 完整已知系统的offline BTS也将初始决策节点剪除，因此这不是单纯u偏小造成的未判定；当前模型不存在满足本实验无死锁目标的supervisor。
从初始状态可达的原始图无环。有限无环系统的所有执行最终都到达无出边终点，仅通过禁用事件不能产生可持续运行的环。
未将空图或“不可解”提示图当成一个可行闭环，也未给终止状态补自环。

**传统BTS初始节点的模式去向（互斥分类）：** 共4个模式，其中UR含plant死锁0个；其余模式直接引入控制死锁0个；局部通过但因后续估计失败而剪除4个；最终保留0个。

| 实测成本 | Online | Offline | 绝对节约（Offline−Online） | 节约率 |
| --- | ---: | ---: | ---: | ---: |
| 总求解时间，含online预处理 / ms | 0.114300 | 0.092400 | -0.021900 | -23.701% |
| Python分配峰值 / KiB | 15.914 | 22.992 | 7.078 | 30.785% |

Online分项中位数：预处理0.014600 ms，求解0.099400 ms。总时间是每次预处理与求解相加后再取中位数，不能一般地把两个中位数直接相加。
运算：ΔT=(0.092400−0.114300) ms=-0.021900 ms；时间节约率=ΔT/0.092400 ms=-23.701%。
ΔM=23,544−16,296=7,248 bytes；内存节约率=ΔM/23,544=30.785%。
**成本解释：** 本例online含预处理的总时间反而更高，已保留负节约率。减少图规模不保证抵消预处理成本；小模型的微秒级时间也易受解释器及调度影响。

[Offline BTS数据](16WODESmax_fig_1a/offline/bts.json) · [Offline闭环](16WODESmax_fig_1a/closed_loop_system_offline.png) · [Offline supervisor](16WODESmax_fig_1a/supervisor_offline.json) · [逐项测量](16WODESmax_fig_1a/online_offline_comparison.json)
<!-- END-RUN-RESULTS: 16WODESmax_fig_1a -->

### 修改意见（请填写）

<!-- USER-NOTES: 16WODESmax_fig_1a -->
- 需要修改的状态或转移：
- 可观事件调整：
- 可控事件调整：
- 希望保留的闭环或预期行为：
- 其他意见：
<!-- END-USER-NOTES: 16WODESmax_fig_1a -->

## 16WODESmax_fig_1b

编号：16。类别：论文自动机。
原始状态数：7；转移数：11；初始状态：`0`。
当前结果：`losing`；所选前视深度：`u=1`。

| 事件属性 | 集合 |
| --- | --- |
| 全部事件 Σ | `{a, b, c1, c2}` |
| 可观事件 Σo | `{a, b}` |
| 不可观事件 Σuo | `{c1, c2}` |
| 可控事件 Σc | `{c1, c2}` |
| 不可控事件 Σuc | `{a, b}` |

[原始系统图](16WODESmax_fig_1b/plant.png) · [原始系统数据](16WODESmax_fig_1b/plant.json) · [LL-BTS](16WODESmax_fig_1b/ll_bts.png) · [闭环结果](16WODESmax_fig_1b/closed_loop.png)

来源：16WODESmax.pdf, Fig. 1b。

模型备注：System G, illegal state 7 retained。

<!-- RUN-RESULTS: 16WODESmax_fig_1b -->
### 运行结果与分析

- 判定：online **losing**，offline **losing**；完整离线结论一致。
- 预处理：Qd=`{7}`；Qf=`{5, 6}`；Qe=∅。
- 深度：草稿阈值=1；最小可判定u=1；恢复offline根极大控制模式的最小u=1；实际采用u=1。
  深度经过逐例扫描标定；草稿阈值本身不等于普遍可解性保证。

| 结构指标 | Online LL-BTS | 传统 Offline BTS |
| --- | ---: | ---: |
| 构建D节点 | 4 | 4 |
| 构建O节点 | 4 | 16 |
| 构建边 | 12 | 24 |
| 全部保留D/O节点 | 0/0 | 0/0 |

**为什么不可解：** 完整已知系统的offline BTS也将初始决策节点剪除，因此这不是单纯u偏小造成的未判定；当前模型不存在满足本实验无死锁目标的supervisor。
从初始状态可达的原始图无环。有限无环系统的所有执行最终都到达无出边终点，仅通过禁用事件不能产生可持续运行的环。
未将空图或“不可解”提示图当成一个可行闭环，也未给终止状态补自环。

**传统BTS初始节点的模式去向（互斥分类）：** 共4个模式，其中UR含plant死锁0个；其余模式直接引入控制死锁0个；局部通过但因后续估计失败而剪除4个；最终保留0个。

| 实测成本 | Online | Offline | 绝对节约（Offline−Online） | 节约率 |
| --- | ---: | ---: | ---: | ---: |
| 总求解时间，含online预处理 / ms | 0.147400 | 0.112700 | -0.034700 | -30.790% |
| Python分配峰值 / KiB | 16.164 | 23.242 | 7.078 | 30.454% |

Online分项中位数：预处理0.027800 ms，求解0.119600 ms。总时间是每次预处理与求解相加后再取中位数，不能一般地把两个中位数直接相加。
运算：ΔT=(0.112700−0.147400) ms=-0.034700 ms；时间节约率=ΔT/0.112700 ms=-30.790%。
ΔM=23,800−16,552=7,248 bytes；内存节约率=ΔM/23,800=30.454%。
**成本解释：** 本例online含预处理的总时间反而更高，已保留负节约率。减少图规模不保证抵消预处理成本；小模型的微秒级时间也易受解释器及调度影响。

[Offline BTS数据](16WODESmax_fig_1b/offline/bts.json) · [Offline闭环](16WODESmax_fig_1b/closed_loop_system_offline.png) · [Offline supervisor](16WODESmax_fig_1b/supervisor_offline.json) · [逐项测量](16WODESmax_fig_1b/online_offline_comparison.json)
<!-- END-RUN-RESULTS: 16WODESmax_fig_1b -->

### 修改意见（请填写）

<!-- USER-NOTES: 16WODESmax_fig_1b -->
- 需要修改的状态或转移：
- 可观事件调整：
- 可控事件调整：
- 希望保留的闭环或预期行为：
- 其他意见：
<!-- END-USER-NOTES: 16WODESmax_fig_1b -->

## 16WODESmax_fig_2a

编号：17。类别：论文自动机。
原始状态数：5；转移数：4；初始状态：`0`。
当前结果：`losing`；所选前视深度：`u=1`。

| 事件属性 | 集合 |
| --- | --- |
| 全部事件 Σ | `{a, b, c1, c2}` |
| 可观事件 Σo | `{a, b}` |
| 不可观事件 Σuo | `{c1, c2}` |
| 可控事件 Σc | `{c1, c2}` |
| 不可控事件 Σuc | `{a, b}` |

[原始系统图](16WODESmax_fig_2a/plant.png) · [原始系统数据](16WODESmax_fig_2a/plant.json) · [LL-BTS](16WODESmax_fig_2a/ll_bts.png) · [闭环结果](16WODESmax_fig_2a/closed_loop.png)

来源：16WODESmax.pdf, Fig. 2a。

模型备注：Lower-bound R reused as standalone plant; not a range-control experiment。

<!-- RUN-RESULTS: 16WODESmax_fig_2a -->
### 运行结果与分析

- 判定：online **losing**，offline **losing**；完整离线结论一致。
- 预处理：Qd=`{5, 6}`；Qf=`{3, 4}`；Qe=∅。
- 深度：草稿阈值=0；最小可判定u=1；恢复offline根极大控制模式的最小u=1；实际采用u=1。
  深度经过逐例扫描标定；草稿阈值本身不等于普遍可解性保证。

| 结构指标 | Online LL-BTS | 传统 Offline BTS |
| --- | ---: | ---: |
| 构建D节点 | 3 | 3 |
| 构建O节点 | 4 | 12 |
| 构建边 | 12 | 20 |
| 全部保留D/O节点 | 0/0 | 0/0 |

**为什么不可解：** 完整已知系统的offline BTS也将初始决策节点剪除，因此这不是单纯u偏小造成的未判定；当前模型不存在满足本实验无死锁目标的supervisor。
从初始状态可达的原始图无环。有限无环系统的所有执行最终都到达无出边终点，仅通过禁用事件不能产生可持续运行的环。
未将空图或“不可解”提示图当成一个可行闭环，也未给终止状态补自环。

**传统BTS初始节点的模式去向（互斥分类）：** 共4个模式，其中UR含plant死锁0个；其余模式直接引入控制死锁0个；局部通过但因后续估计失败而剪除4个；最终保留0个。

| 实测成本 | Online | Offline | 绝对节约（Offline−Online） | 节约率 |
| --- | ---: | ---: | ---: | ---: |
| 总求解时间，含online预处理 / ms | 0.068000 | 0.073100 | 0.005100 | 6.977% |
| Python分配峰值 / KiB | 14.891 | 20.141 | 5.250 | 26.067% |

Online分项中位数：预处理0.016100 ms，求解0.051900 ms。总时间是每次预处理与求解相加后再取中位数，不能一般地把两个中位数直接相加。
运算：ΔT=(0.073100−0.068000) ms=0.005100 ms；时间节约率=ΔT/0.073100 ms=6.977%。
ΔM=20,624−15,248=5,376 bytes；内存节约率=ΔM/20,624=26.067%。
**成本解释：** 本例测得online总成本更低；收益同时包含窗口、Qf/Qe证书和提前拒绝坏模式。这是当前实现/模型的实测，不是对所有系统最坏复杂度下降的证明。

[Offline BTS数据](16WODESmax_fig_2a/offline/bts.json) · [Offline闭环](16WODESmax_fig_2a/closed_loop_system_offline.png) · [Offline supervisor](16WODESmax_fig_2a/supervisor_offline.json) · [逐项测量](16WODESmax_fig_2a/online_offline_comparison.json)
<!-- END-RUN-RESULTS: 16WODESmax_fig_2a -->

### 修改意见（请填写）

<!-- USER-NOTES: 16WODESmax_fig_2a -->
- 需要修改的状态或转移：
- 可观事件调整：
- 可控事件调整：
- 希望保留的闭环或预期行为：
- 其他意见：
<!-- END-USER-NOTES: 16WODESmax_fig_2a -->

## 16WODESmax_fig_3a_Gprime

编号：18。类别：论文自动机。
原始状态数：11；转移数：17；初始状态：`0`。
当前结果：`losing`；所选前视深度：`u=2`。

| 事件属性 | 集合 |
| --- | --- |
| 全部事件 Σ | `{a, b, c1, c2}` |
| 可观事件 Σo | `{a, b}` |
| 不可观事件 Σuo | `{c1, c2}` |
| 可控事件 Σc | `{c1, c2}` |
| 不可控事件 Σuc | `{a, b}` |

[原始系统图](16WODESmax_fig_3a_Gprime/plant.png) · [原始系统数据](16WODESmax_fig_3a_Gprime/plant.json) · [LL-BTS](16WODESmax_fig_3a_Gprime/ll_bts.png) · [闭环结果](16WODESmax_fig_3a_Gprime/closed_loop.png)

来源：16WODESmax.pdf, Fig. 3a_Gprime。

模型备注：Refined G, Fig.3(a); event labels retained。

<!-- RUN-RESULTS: 16WODESmax_fig_3a_Gprime -->
### 运行结果与分析

- 判定：online **losing**，offline **losing**；完整离线结论一致。
- 预处理：Qd=`{7}`；Qf=`{5, 5', 6, 6'}`；Qe=∅。
- 深度：草稿阈值=1；最小可判定u=2；恢复offline根极大控制模式的最小u=2；实际采用u=2。
  深度经过逐例扫描标定；草稿阈值本身不等于普遍可解性保证。

| 结构指标 | Online LL-BTS | 传统 Offline BTS |
| --- | ---: | ---: |
| 构建D节点 | 5 | 5 |
| 构建O节点 | 4 | 20 |
| 构建边 | 12 | 28 |
| 全部保留D/O节点 | 0/0 | 0/0 |

**为什么不可解：** 完整已知系统的offline BTS也将初始决策节点剪除，因此这不是单纯u偏小造成的未判定；当前模型不存在满足本实验无死锁目标的supervisor。
从初始状态可达的原始图无环。有限无环系统的所有执行最终都到达无出边终点，仅通过禁用事件不能产生可持续运行的环。
未将空图或“不可解”提示图当成一个可行闭环，也未给终止状态补自环。

**传统BTS初始节点的模式去向（互斥分类）：** 共4个模式，其中UR含plant死锁0个；其余模式直接引入控制死锁0个；局部通过但因后续估计失败而剪除4个；最终保留0个。

| 实测成本 | Online | Offline | 绝对节约（Offline−Online） | 节约率 |
| --- | ---: | ---: | ---: | ---: |
| 总求解时间，含online预处理 / ms | 0.175800 | 0.141300 | -0.034500 | -24.416% |
| Python分配峰值 / KiB | 18.742 | 32.062 | 13.320 | 41.545% |

Online分项中位数：预处理0.036600 ms，求解0.137700 ms。总时间是每次预处理与求解相加后再取中位数，不能一般地把两个中位数直接相加。
运算：ΔT=(0.141300−0.175800) ms=-0.034500 ms；时间节约率=ΔT/0.141300 ms=-24.416%。
ΔM=32,832−19,192=13,640 bytes；内存节约率=ΔM/32,832=41.545%。
**成本解释：** 本例online含预处理的总时间反而更高，已保留负节约率。减少图规模不保证抵消预处理成本；小模型的微秒级时间也易受解释器及调度影响。

[Offline BTS数据](16WODESmax_fig_3a_Gprime/offline/bts.json) · [Offline闭环](16WODESmax_fig_3a_Gprime/closed_loop_system_offline.png) · [Offline supervisor](16WODESmax_fig_3a_Gprime/supervisor_offline.json) · [逐项测量](16WODESmax_fig_3a_Gprime/online_offline_comparison.json)
<!-- END-RUN-RESULTS: 16WODESmax_fig_3a_Gprime -->

### 修改意见（请填写）

<!-- USER-NOTES: 16WODESmax_fig_3a_Gprime -->
- 需要修改的状态或转移：
- 可观事件调整：
- 可控事件调整：
- 希望保留的闭环或预期行为：
- 其他意见：
<!-- END-USER-NOTES: 16WODESmax_fig_3a_Gprime -->

## 17TAC-Range_fig_2a_G

编号：19。类别：论文自动机。
原始状态数：7；转移数：11；初始状态：`1`。
当前结果：`losing`；所选前视深度：`u=1`。

| 事件属性 | 集合 |
| --- | --- |
| 全部事件 Σ | `{a, b, c1, c2, u}` |
| 可观事件 Σo | `{a, b}` |
| 不可观事件 Σuo | `{c1, c2, u}` |
| 可控事件 Σc | `{c1, c2}` |
| 不可控事件 Σuc | `{a, b, u}` |

[原始系统图](17TAC-Range_fig_2a_G/plant.png) · [原始系统数据](17TAC-Range_fig_2a_G/plant.json) · [LL-BTS](17TAC-Range_fig_2a_G/ll_bts.png) · [闭环结果](17TAC-Range_fig_2a_G/closed_loop.png)

来源：17TAC-Range.pdf, Fig. 2a_G。

模型备注：p.3918, G; illegal state 7 retained。

<!-- RUN-RESULTS: 17TAC-Range_fig_2a_G -->
### 运行结果与分析

- 判定：online **losing**，offline **losing**；完整离线结论一致。
- 预处理：Qd=`{7}`；Qf=`{5, 6}`；Qe=∅。
- 深度：草稿阈值=1；最小可判定u=1；恢复offline根极大控制模式的最小u=1；实际采用u=1。
  深度经过逐例扫描标定；草稿阈值本身不等于普遍可解性保证。

| 结构指标 | Online LL-BTS | 传统 Offline BTS |
| --- | ---: | ---: |
| 构建D节点 | 2 | 2 |
| 构建O节点 | 4 | 8 |
| 构建边 | 12 | 16 |
| 全部保留D/O节点 | 0/0 | 0/0 |

**为什么不可解：** 完整已知系统的offline BTS也将初始决策节点剪除，因此这不是单纯u偏小造成的未判定；当前模型不存在满足本实验无死锁目标的supervisor。
从初始状态可达的原始图无环。有限无环系统的所有执行最终都到达无出边终点，仅通过禁用事件不能产生可持续运行的环。
未将空图或“不可解”提示图当成一个可行闭环，也未给终止状态补自环。

**传统BTS初始节点的模式去向（互斥分类）：** 共4个模式，其中UR含plant死锁0个；其余模式直接引入控制死锁0个；局部通过但因后续估计失败而剪除4个；最终保留0个。

| 实测成本 | Online | Offline | 绝对节约（Offline−Online） | 节约率 |
| --- | ---: | ---: | ---: | ---: |
| 总求解时间，含online预处理 / ms | 0.115200 | 0.066700 | -0.048500 | -72.714% |
| Python分配峰值 / KiB | 15.867 | 17.461 | 1.594 | 9.128% |

Online分项中位数：预处理0.025200 ms，求解0.090000 ms。总时间是每次预处理与求解相加后再取中位数，不能一般地把两个中位数直接相加。
运算：ΔT=(0.066700−0.115200) ms=-0.048500 ms；时间节约率=ΔT/0.066700 ms=-72.714%。
ΔM=17,880−16,248=1,632 bytes；内存节约率=ΔM/17,880=9.128%。
**成本解释：** 本例online含预处理的总时间反而更高，已保留负节约率。减少图规模不保证抵消预处理成本；小模型的微秒级时间也易受解释器及调度影响。

[Offline BTS数据](17TAC-Range_fig_2a_G/offline/bts.json) · [Offline闭环](17TAC-Range_fig_2a_G/closed_loop_system_offline.png) · [Offline supervisor](17TAC-Range_fig_2a_G/supervisor_offline.json) · [逐项测量](17TAC-Range_fig_2a_G/online_offline_comparison.json)
<!-- END-RUN-RESULTS: 17TAC-Range_fig_2a_G -->

### 修改意见（请填写）

<!-- USER-NOTES: 17TAC-Range_fig_2a_G -->
- 需要修改的状态或转移：
- 可观事件调整：
- 可控事件调整：
- 希望保留的闭环或预期行为：
- 其他意见：
<!-- END-USER-NOTES: 17TAC-Range_fig_2a_G -->

## 17TAC-Range_fig_2a_K

编号：20。类别：论文自动机。
原始状态数：6；转移数：9；初始状态：`1`。
当前结果：`losing`；所选前视深度：`u=1`。

| 事件属性 | 集合 |
| --- | --- |
| 全部事件 Σ | `{a, b, c1, c2, u}` |
| 可观事件 Σo | `{a, b}` |
| 不可观事件 Σuo | `{c1, c2, u}` |
| 可控事件 Σc | `{c1, c2}` |
| 不可控事件 Σuc | `{a, b, u}` |

[原始系统图](17TAC-Range_fig_2a_K/plant.png) · [原始系统数据](17TAC-Range_fig_2a_K/plant.json) · [LL-BTS](17TAC-Range_fig_2a_K/ll_bts.png) · [闭环结果](17TAC-Range_fig_2a_K/closed_loop.png)

来源：17TAC-Range.pdf, Fig. 2a_K。

模型备注：p.3918, K interpreted only as a standalone DFA。

<!-- RUN-RESULTS: 17TAC-Range_fig_2a_K -->
### 运行结果与分析

- 判定：online **losing**，offline **losing**；完整离线结论一致。
- 预处理：Qd=`{5, 6}`；Qf=∅；Qe=∅。
- 深度：草稿阈值=0；最小可判定u=1；恢复offline根极大控制模式的最小u=1；实际采用u=1。
  深度经过逐例扫描标定；草稿阈值本身不等于普遍可解性保证。

| 结构指标 | Online LL-BTS | 传统 Offline BTS |
| --- | ---: | ---: |
| 构建D节点 | 2 | 2 |
| 构建O节点 | 4 | 8 |
| 构建边 | 12 | 16 |
| 全部保留D/O节点 | 0/0 | 0/0 |

**为什么不可解：** 完整已知系统的offline BTS也将初始决策节点剪除，因此这不是单纯u偏小造成的未判定；当前模型不存在满足本实验无死锁目标的supervisor。
从初始状态可达的原始图无环。有限无环系统的所有执行最终都到达无出边终点，仅通过禁用事件不能产生可持续运行的环。
未将空图或“不可解”提示图当成一个可行闭环，也未给终止状态补自环。

**传统BTS初始节点的模式去向（互斥分类）：** 共4个模式，其中UR含plant死锁0个；其余模式直接引入控制死锁0个；局部通过但因后续估计失败而剪除4个；最终保留0个。

| 实测成本 | Online | Offline | 绝对节约（Offline−Online） | 节约率 |
| --- | ---: | ---: | ---: | ---: |
| 总求解时间，含online预处理 / ms | 0.085500 | 0.060800 | -0.024700 | -40.625% |
| Python分配峰值 / KiB | 15.617 | 17.211 | 1.594 | 9.260% |

Online分项中位数：预处理0.014900 ms，求解0.070800 ms。总时间是每次预处理与求解相加后再取中位数，不能一般地把两个中位数直接相加。
运算：ΔT=(0.060800−0.085500) ms=-0.024700 ms；时间节约率=ΔT/0.060800 ms=-40.625%。
ΔM=17,624−15,992=1,632 bytes；内存节约率=ΔM/17,624=9.260%。
**成本解释：** 本例online含预处理的总时间反而更高，已保留负节约率。减少图规模不保证抵消预处理成本；小模型的微秒级时间也易受解释器及调度影响。

[Offline BTS数据](17TAC-Range_fig_2a_K/offline/bts.json) · [Offline闭环](17TAC-Range_fig_2a_K/closed_loop_system_offline.png) · [Offline supervisor](17TAC-Range_fig_2a_K/supervisor_offline.json) · [逐项测量](17TAC-Range_fig_2a_K/online_offline_comparison.json)
<!-- END-RUN-RESULTS: 17TAC-Range_fig_2a_K -->

### 修改意见（请填写）

<!-- USER-NOTES: 17TAC-Range_fig_2a_K -->
- 需要修改的状态或转移：
- 可观事件调整：
- 可控事件调整：
- 希望保留的闭环或预期行为：
- 其他意见：
<!-- END-USER-NOTES: 17TAC-Range_fig_2a_K -->

## 17TAC-Range_fig_2c

编号：21。类别：论文自动机。
原始状态数：5；转移数：4；初始状态：`1`。
当前结果：`losing`；所选前视深度：`u=1`。

| 事件属性 | 集合 |
| --- | --- |
| 全部事件 Σ | `{a, b, c1, c2, u}` |
| 可观事件 Σo | `{a, b}` |
| 不可观事件 Σuo | `{c1, c2, u}` |
| 可控事件 Σc | `{c1, c2}` |
| 不可控事件 Σuc | `{a, b, u}` |

[原始系统图](17TAC-Range_fig_2c/plant.png) · [原始系统数据](17TAC-Range_fig_2c/plant.json) · [LL-BTS](17TAC-Range_fig_2c/ll_bts.png) · [闭环结果](17TAC-Range_fig_2c/closed_loop.png)

来源：17TAC-Range.pdf, Fig. 2c。

模型备注：Lower-bound R。

<!-- RUN-RESULTS: 17TAC-Range_fig_2c -->
### 运行结果与分析

- 判定：online **losing**，offline **losing**；完整离线结论一致。
- 预处理：Qd=`{5, 6}`；Qf=`{3, 4}`；Qe=∅。
- 深度：草稿阈值=0；最小可判定u=1；恢复offline根极大控制模式的最小u=1；实际采用u=1。
  深度经过逐例扫描标定；草稿阈值本身不等于普遍可解性保证。

| 结构指标 | Online LL-BTS | 传统 Offline BTS |
| --- | ---: | ---: |
| 构建D节点 | 3 | 3 |
| 构建O节点 | 4 | 12 |
| 构建边 | 12 | 20 |
| 全部保留D/O节点 | 0/0 | 0/0 |

**为什么不可解：** 完整已知系统的offline BTS也将初始决策节点剪除，因此这不是单纯u偏小造成的未判定；当前模型不存在满足本实验无死锁目标的supervisor。
从初始状态可达的原始图无环。有限无环系统的所有执行最终都到达无出边终点，仅通过禁用事件不能产生可持续运行的环。
未将空图或“不可解”提示图当成一个可行闭环，也未给终止状态补自环。

**传统BTS初始节点的模式去向（互斥分类）：** 共4个模式，其中UR含plant死锁0个；其余模式直接引入控制死锁0个；局部通过但因后续估计失败而剪除4个；最终保留0个。

| 实测成本 | Online | Offline | 绝对节约（Offline−Online） | 节约率 |
| --- | ---: | ---: | ---: | ---: |
| 总求解时间，含online预处理 / ms | 0.062900 | 0.067300 | 0.004400 | 6.538% |
| Python分配峰值 / KiB | 15.141 | 20.391 | 5.250 | 25.747% |

Online分项中位数：预处理0.014300 ms，求解0.048200 ms。总时间是每次预处理与求解相加后再取中位数，不能一般地把两个中位数直接相加。
运算：ΔT=(0.067300−0.062900) ms=0.004400 ms；时间节约率=ΔT/0.067300 ms=6.538%。
ΔM=20,880−15,504=5,376 bytes；内存节约率=ΔM/20,880=25.747%。
**成本解释：** 本例测得online总成本更低；收益同时包含窗口、Qf/Qe证书和提前拒绝坏模式。这是当前实现/模型的实测，不是对所有系统最坏复杂度下降的证明。

[Offline BTS数据](17TAC-Range_fig_2c/offline/bts.json) · [Offline闭环](17TAC-Range_fig_2c/closed_loop_system_offline.png) · [Offline supervisor](17TAC-Range_fig_2c/supervisor_offline.json) · [逐项测量](17TAC-Range_fig_2c/online_offline_comparison.json)
<!-- END-RUN-RESULTS: 17TAC-Range_fig_2c -->

### 修改意见（请填写）

<!-- USER-NOTES: 17TAC-Range_fig_2c -->
- 需要修改的状态或转移：
- 可观事件调整：
- 可控事件调整：
- 希望保留的闭环或预期行为：
- 其他意见：
<!-- END-USER-NOTES: 17TAC-Range_fig_2c -->

## 17TAC-Range_fig_4a

编号：22。类别：论文自动机。
原始状态数：2；转移数：2；初始状态：`1`。
当前结果：`winning`；所选前视深度：`u=0`。

| 事件属性 | 集合 |
| --- | --- |
| 全部事件 Σ | `{a, b, v, w}` |
| 可观事件 Σo | `{a, b, v}` |
| 不可观事件 Σuo | `{w}` |
| 可控事件 Σc | `{v, w}` |
| 不可控事件 Σuc | `{a, b}` |

[原始系统图](17TAC-Range_fig_4a/plant.png) · [原始系统数据](17TAC-Range_fig_4a/plant.json) · [LL-BTS](17TAC-Range_fig_4a/ll_bts.png) · [闭环结果](17TAC-Range_fig_4a/closed_loop.png)

来源：17TAC-Range.pdf, Fig. 4a。

模型备注：R, Fig.4(a), p.3922。

<!-- RUN-RESULTS: 17TAC-Range_fig_4a -->
### 运行结果与分析

- 判定：online **winning**，offline **winning**；完整离线结论一致。
- 预处理：Qd=∅；Qf=∅；Qe=`{1, 3}`。
- 深度：草稿阈值=0；最小可判定u=0；恢复offline根极大控制模式的最小u=0；实际采用u=0。
  深度经过逐例扫描标定；草稿阈值本身不等于普遍可解性保证。

| 结构指标 | Online LL-BTS | 传统 Offline BTS |
| --- | ---: | ---: |
| 构建D节点 | 1 | 2 |
| 构建O节点 | 0 | 8 |
| 构建边 | 0 | 14 |
| 全部保留D/O节点 | 1/0 | 2/6 |
| 所选闭环可达状态 | 2 | 2 |
| 所选闭环可达转移 | 2 | 2 |
| 所选控制器记忆状态 | 2 | 2 |

**为什么可解：** 初始估计已完全落在Qe中，允许全部事件即可安全延续。因此online可以在根估计处采用安全终端证书，停止枚举O节点。这不是原始plant只有一个状态；物理闭环仍按实际DFA状态和控制器记忆展开。
**实际控制行为：** 所有导出记忆状态的控制输出均允许全部事件，未禁用任何可控事件。保留的多个估计记忆不表示控制模式一定不同。

**传统BTS初始节点的模式去向（互斥分类）：** 共4个模式，其中UR含plant死锁0个；其余模式直接引入控制死锁0个；局部通过但因后续估计失败而剪除0个；最终保留4个。

| 实测成本 | Online | Offline | 绝对节约（Offline−Online） | 节约率 |
| --- | ---: | ---: | ---: | ---: |
| 总求解时间，含online预处理 / ms | 0.010700 | 0.050700 | 0.040000 | 78.895% |
| Python分配峰值 / KiB | 5.086 | 15.828 | 10.742 | 67.868% |

Online分项中位数：预处理0.008100 ms，求解0.002700 ms。总时间是每次预处理与求解相加后再取中位数，不能一般地把两个中位数直接相加。
运算：ΔT=(0.050700−0.010700) ms=0.040000 ms；时间节约率=ΔT/0.050700 ms=78.895%。
ΔM=16,208−5,208=11,000 bytes；内存节约率=ΔM/16,208=67.868%。
**成本解释：** 本例测得online总成本更低；收益同时包含窗口、Qf/Qe证书和提前拒绝坏模式。这是当前实现/模型的实测，不是对所有系统最坏复杂度下降的证明。

[Offline BTS数据](17TAC-Range_fig_4a/offline/bts.json) · [Offline闭环](17TAC-Range_fig_4a/closed_loop_system_offline.png) · [Offline supervisor](17TAC-Range_fig_4a/supervisor_offline.json) · [逐项测量](17TAC-Range_fig_4a/online_offline_comparison.json)
<!-- END-RUN-RESULTS: 17TAC-Range_fig_4a -->

### 修改意见（请填写）

<!-- USER-NOTES: 17TAC-Range_fig_4a -->
- 需要修改的状态或转移：
- 可观事件调整：
- 可控事件调整：
- 希望保留的闭环或预期行为：
- 其他意见：
<!-- END-USER-NOTES: 17TAC-Range_fig_4a -->

## 17TAC-Range_fig_4b

编号：23。类别：论文自动机。
原始状态数：6；转移数：8；初始状态：`1`。
当前结果：`winning`；所选前视深度：`u=1`。

| 事件属性 | 集合 |
| --- | --- |
| 全部事件 Σ | `{a, b, v, w}` |
| 可观事件 Σo | `{a, b, v}` |
| 不可观事件 Σuo | `{w}` |
| 可控事件 Σc | `{v, w}` |
| 不可控事件 Σuc | `{a, b}` |

[原始系统图](17TAC-Range_fig_4b/plant.png) · [原始系统数据](17TAC-Range_fig_4b/plant.json) · [LL-BTS](17TAC-Range_fig_4b/ll_bts.png) · [闭环结果](17TAC-Range_fig_4b/closed_loop.png)

来源：17TAC-Range.pdf, Fig. 4b。

模型备注：K, Fig.4(b)。

<!-- RUN-RESULTS: 17TAC-Range_fig_4b -->
### 运行结果与分析

- 判定：online **winning**，offline **winning**；完整离线结论一致。
- 预处理：Qd=∅；Qf=∅；Qe=`{1, 2, 3, 4, 5, 6}`。
- 深度：草稿阈值=1；最小可判定u=0；恢复offline根极大控制模式的最小u=0；实际采用u=1。
  深度经过逐例扫描标定；草稿阈值本身不等于普遍可解性保证。

| 结构指标 | Online LL-BTS | 传统 Offline BTS |
| --- | ---: | ---: |
| 构建D节点 | 1 | 4 |
| 构建O节点 | 0 | 16 |
| 构建边 | 0 | 32 |
| 全部保留D/O节点 | 1/0 | 4/12 |
| 所选闭环可达状态 | 7 | 7 |
| 所选闭环可达转移 | 9 | 9 |
| 所选控制器记忆状态 | 3 | 3 |

**为什么可解：** 初始估计已完全落在Qe中，允许全部事件即可安全延续。因此online可以在根估计处采用安全终端证书，停止枚举O节点。这不是原始plant只有一个状态；物理闭环仍按实际DFA状态和控制器记忆展开。
**实际控制行为：** 所有导出记忆状态的控制输出均允许全部事件，未禁用任何可控事件。保留的多个估计记忆不表示控制模式一定不同。

**传统BTS初始节点的模式去向（互斥分类）：** 共4个模式，其中UR含plant死锁0个；其余模式直接引入控制死锁0个；局部通过但因后续估计失败而剪除0个；最终保留4个。

| 实测成本 | Online | Offline | 绝对节约（Offline−Online） | 节约率 |
| --- | ---: | ---: | ---: | ---: |
| 总求解时间，含online预处理 / ms | 0.021300 | 0.113100 | 0.091800 | 81.167% |
| Python分配峰值 / KiB | 7.672 | 25.781 | 18.109 | 70.242% |

Online分项中位数：预处理0.018500 ms，求解0.002900 ms。总时间是每次预处理与求解相加后再取中位数，不能一般地把两个中位数直接相加。
运算：ΔT=(0.113100−0.021300) ms=0.091800 ms；时间节约率=ΔT/0.113100 ms=81.167%。
ΔM=26,400−7,856=18,544 bytes；内存节约率=ΔM/26,400=70.242%。
**成本解释：** 本例测得online总成本更低；收益同时包含窗口、Qf/Qe证书和提前拒绝坏模式。这是当前实现/模型的实测，不是对所有系统最坏复杂度下降的证明。

[Offline BTS数据](17TAC-Range_fig_4b/offline/bts.json) · [Offline闭环](17TAC-Range_fig_4b/closed_loop_system_offline.png) · [Offline supervisor](17TAC-Range_fig_4b/supervisor_offline.json) · [逐项测量](17TAC-Range_fig_4b/online_offline_comparison.json)
<!-- END-RUN-RESULTS: 17TAC-Range_fig_4b -->

### 修改意见（请填写）

<!-- USER-NOTES: 17TAC-Range_fig_4b -->
- 需要修改的状态或转移：
- 可观事件调整：
- 可控事件调整：
- 希望保留的闭环或预期行为：
- 其他意见：
<!-- END-USER-NOTES: 17TAC-Range_fig_4b -->

## 17TAC-Range_fig_4c

编号：24。类别：论文自动机。
原始状态数：7；转移数：10；初始状态：`1`。
当前结果：`winning`；所选前视深度：`u=3`。

| 事件属性 | 集合 |
| --- | --- |
| 全部事件 Σ | `{a, b, v, w}` |
| 可观事件 Σo | `{a, b, v}` |
| 不可观事件 Σuo | `{w}` |
| 可控事件 Σc | `{v, w}` |
| 不可控事件 Σuc | `{a, b}` |

[原始系统图](17TAC-Range_fig_4c/plant.png) · [原始系统数据](17TAC-Range_fig_4c/plant.json) · [LL-BTS](17TAC-Range_fig_4c/ll_bts.png) · [闭环结果](17TAC-Range_fig_4c/closed_loop.png)

来源：17TAC-Range.pdf, Fig. 4c。

模型备注：G, Fig.4(c); state 7 has no outgoing transition。

<!-- RUN-RESULTS: 17TAC-Range_fig_4c -->
### 运行结果与分析

- 判定：online **winning**，offline **winning**；完整离线结论一致。
- 预处理：Qd=`{7}`；Qf=∅；Qe=∅。
- 深度：草稿阈值=0；最小可判定u=1；恢复offline根极大控制模式的最小u=3；实际采用u=3。
  深度经过逐例扫描标定；草稿阈值本身不等于普遍可解性保证。

| 结构指标 | Online LL-BTS | 传统 Offline BTS |
| --- | ---: | ---: |
| 构建D节点 | 6 | 6 |
| 构建O节点 | 13 | 24 |
| 构建边 | 30 | 46 |
| 全部保留D/O节点 | 4/9 | 4/9 |
| 所选闭环可达状态 | 7 | 7 |
| 所选闭环可达转移 | 8 | 8 |
| 所选控制器记忆状态 | 3 | 3 |

**为什么可解：** 初始估计不能直接用Qe证书终止，但剪枝后仍有认证控制模式。所选supervisor在每个估计处固定选择一个保留模式，所有可能观测均有认证后续控制，并检查不可观测可达集中的每个实际状态都有可用事件。
**实际控制行为：** 不可控事件始终允许；下表列出选定online supervisor的控制输出。

| 记忆 | 估计 | 允许的可控事件 | 禁用的可控事件 |
| --- | --- | --- | --- |
| C0 | `{1}` | `{v, w}` | ∅ |
| C1 | `{3, 4}` | `{w}` | `{v}` |
| C2 | `{6}` | `{w}` | `{v}` |

**传统BTS初始节点的模式去向（互斥分类）：** 共4个模式，其中UR含plant死锁0个；其余模式直接引入控制死锁0个；局部通过但因后续估计失败而剪除0个；最终保留4个。

| 实测成本 | Online | Offline | 绝对节约（Offline−Online） | 节约率 |
| --- | ---: | ---: | ---: | ---: |
| 总求解时间，含online预处理 / ms | 0.150800 | 0.152500 | 0.001700 | 1.115% |
| Python分配峰值 / KiB | 26.750 | 40.211 | 13.461 | 33.476% |

Online分项中位数：预处理0.016900 ms，求解0.133900 ms。总时间是每次预处理与求解相加后再取中位数，不能一般地把两个中位数直接相加。
运算：ΔT=(0.152500−0.150800) ms=0.001700 ms；时间节约率=ΔT/0.152500 ms=1.115%。
ΔM=41,176−27,392=13,784 bytes；内存节约率=ΔM/41,176=33.476%。
**成本解释：** 本例测得online总成本更低；收益同时包含窗口、Qf/Qe证书和提前拒绝坏模式。这是当前实现/模型的实测，不是对所有系统最坏复杂度下降的证明。

[Offline BTS数据](17TAC-Range_fig_4c/offline/bts.json) · [Offline闭环](17TAC-Range_fig_4c/closed_loop_system_offline.png) · [Offline supervisor](17TAC-Range_fig_4c/supervisor_offline.json) · [逐项测量](17TAC-Range_fig_4c/online_offline_comparison.json)
<!-- END-RUN-RESULTS: 17TAC-Range_fig_4c -->

### 修改意见（请填写）

<!-- USER-NOTES: 17TAC-Range_fig_4c -->
- 需要修改的状态或转移：
- 可观事件调整：
- 可控事件调整：
- 希望保留的闭环或预期行为：
- 其他意见：
<!-- END-USER-NOTES: 17TAC-Range_fig_4c -->

## 18TACrange_fig_1a

编号：25。类别：论文自动机。
原始状态数：13；转移数：17；初始状态：`1`。
当前结果：`winning`；所选前视深度：`u=4`。

| 事件属性 | 集合 |
| --- | --- |
| 全部事件 Σ | `{c1, c2, o, u1, u2}` |
| 可观事件 Σo | `{o}` |
| 不可观事件 Σuo | `{c1, c2, u1, u2}` |
| 可控事件 Σc | `{c1, c2}` |
| 不可控事件 Σuc | `{o, u1, u2}` |

[原始系统图](18TACrange_fig_1a/plant.png) · [原始系统数据](18TACrange_fig_1a/plant.json) · [LL-BTS](18TACrange_fig_1a/ll_bts.png) · [闭环结果](18TACrange_fig_1a/closed_loop.png)

来源：18TACrange.pdf, Fig. 1a。

模型备注：p.4437, G; marked states are not automatically deadlock-free。

<!-- RUN-RESULTS: 18TACrange_fig_1a -->
### 运行结果与分析

- 判定：online **winning**，offline **winning**；完整离线结论一致。
- 预处理：Qd=`{12, 13}`；Qf=`{2, 4}`；Qe=∅。
- 深度：草稿阈值=1；最小可判定u=4；恢复offline根极大控制模式的最小u=4；实际采用u=4。
  深度经过逐例扫描标定；草稿阈值本身不等于普遍可解性保证。

| 结构指标 | Online LL-BTS | 传统 Offline BTS |
| --- | ---: | ---: |
| 构建D节点 | 3 | 4 |
| 构建O节点 | 5 | 16 |
| 构建边 | 10 | 28 |
| 全部保留D/O节点 | 3/5 | 3/7 |
| 所选闭环可达状态 | 7 | 8 |
| 所选闭环可达转移 | 8 | 10 |
| 所选控制器记忆状态 | 3 | 3 |

**为什么可解：** 初始估计不能直接用Qe证书终止，但剪枝后仍有认证控制模式。所选supervisor在每个估计处固定选择一个保留模式，所有可能观测均有认证后续控制，并检查不可观测可达集中的每个实际状态都有可用事件。
**实际控制行为：** 不可控事件始终允许；下表列出选定online supervisor的控制输出。

| 记忆 | 估计 | 允许的可控事件 | 禁用的可控事件 |
| --- | --- | --- | --- |
| C0 | `{1}` | `{c2}` | `{c1}` |
| C1 | `{3}` | `{c1, c2}` | ∅ |
| C2 | `{8, 9}` | ∅ | `{c1, c2}` |

两侧所选闭环的节点/边数不同，说明所选策略或记忆图不同。当前只核对了根极大模式集合一致，并分别验证了闭环无死锁；不据此宣称两个完整闭环语言相同。

**传统BTS初始节点的模式去向（互斥分类）：** 共4个模式，其中UR含plant死锁0个；其余模式直接引入控制死锁0个；局部通过但因后续估计失败而剪除2个；最终保留2个。

| 实测成本 | Online | Offline | 绝对节约（Offline−Online） | 节约率 |
| --- | ---: | ---: | ---: | ---: |
| 总求解时间，含online预处理 / ms | 0.261300 | 0.289500 | 0.028200 | 9.741% |
| Python分配峰值 / KiB | 17.492 | 25.648 | 8.156 | 31.800% |

Online分项中位数：预处理0.062500 ms，求解0.199500 ms。总时间是每次预处理与求解相加后再取中位数，不能一般地把两个中位数直接相加。
运算：ΔT=(0.289500−0.261300) ms=0.028200 ms；时间节约率=ΔT/0.289500 ms=9.741%。
ΔM=26,264−17,912=8,352 bytes；内存节约率=ΔM/26,264=31.800%。
**成本解释：** 本例测得online总成本更低；收益同时包含窗口、Qf/Qe证书和提前拒绝坏模式。这是当前实现/模型的实测，不是对所有系统最坏复杂度下降的证明。

[Offline BTS数据](18TACrange_fig_1a/offline/bts.json) · [Offline闭环](18TACrange_fig_1a/closed_loop_system_offline.png) · [Offline supervisor](18TACrange_fig_1a/supervisor_offline.json) · [逐项测量](18TACrange_fig_1a/online_offline_comparison.json)
<!-- END-RUN-RESULTS: 18TACrange_fig_1a -->

### 修改意见（请填写）

<!-- USER-NOTES: 18TACrange_fig_1a -->
- 需要修改的状态或转移：
- 可观事件调整：
- 可控事件调整：
- 希望保留的闭环或预期行为：
- 其他意见：
<!-- END-USER-NOTES: 18TACrange_fig_1a -->

## 18TACrange_fig_1b

编号：26。类别：论文自动机。
原始状态数：3；转移数：2；初始状态：`1`。
当前结果：`losing`；所选前视深度：`u=0`。

| 事件属性 | 集合 |
| --- | --- |
| 全部事件 Σ | `{c1, c2, o, u1, u2}` |
| 可观事件 Σo | `{o}` |
| 不可观事件 Σuo | `{c1, c2, u1, u2}` |
| 可控事件 Σc | `{c1, c2}` |
| 不可控事件 Σuc | `{o, u1, u2}` |

[原始系统图](18TACrange_fig_1b/plant.png) · [原始系统数据](18TACrange_fig_1b/plant.json) · [LL-BTS](18TACrange_fig_1b/ll_bts.png) · [闭环结果](18TACrange_fig_1b/closed_loop.png)

来源：18TACrange.pdf, Fig. 1b。

模型备注：R; original terminal state 5 preserved。

<!-- RUN-RESULTS: 18TACrange_fig_1b -->
### 运行结果与分析

- 判定：online **losing**，offline **losing**；完整离线结论一致。
- 预处理：Qd=`{5}`；Qf=`{1, 3}`；Qe=∅。
- 深度：草稿阈值=0；最小可判定u=0；恢复offline根极大控制模式的最小u=0；实际采用u=0。
  深度经过逐例扫描标定；草稿阈值本身不等于普遍可解性保证。

| 结构指标 | Online LL-BTS | 传统 Offline BTS |
| --- | ---: | ---: |
| 构建D节点 | 1 | 2 |
| 构建O节点 | 0 | 8 |
| 构建边 | 0 | 12 |
| 全部保留D/O节点 | 0/0 | 0/0 |

**为什么不可解：** 完整已知系统的offline BTS也将初始决策节点剪除，因此这不是单纯u偏小造成的未判定；当前模型不存在满足本实验无死锁目标的supervisor。
初始状态属于Qf：沿单后继状态链必然到达Qd。允许后继会走向死锁，禁用全部后继则直接引入控制死锁。
未将空图或“不可解”提示图当成一个可行闭环，也未给终止状态补自环。

**传统BTS初始节点的模式去向（互斥分类）：** 共4个模式，其中UR含plant死锁0个；其余模式直接引入控制死锁0个；局部通过但因后续估计失败而剪除4个；最终保留0个。

| 实测成本 | Online | Offline | 绝对节约（Offline−Online） | 节约率 |
| --- | ---: | ---: | ---: | ---: |
| 总求解时间，含online预处理 / ms | 0.037900 | 0.073900 | 0.036000 | 48.714% |
| Python分配峰值 / KiB | 7.836 | 15.336 | 7.500 | 48.905% |

Online分项中位数：预处理0.017600 ms，求解0.020000 ms。总时间是每次预处理与求解相加后再取中位数，不能一般地把两个中位数直接相加。
运算：ΔT=(0.073900−0.037900) ms=0.036000 ms；时间节约率=ΔT/0.073900 ms=48.714%。
ΔM=15,704−8,024=7,680 bytes；内存节约率=ΔM/15,704=48.905%。
**成本解释：** 本例测得online总成本更低；收益同时包含窗口、Qf/Qe证书和提前拒绝坏模式。这是当前实现/模型的实测，不是对所有系统最坏复杂度下降的证明。

[Offline BTS数据](18TACrange_fig_1b/offline/bts.json) · [Offline闭环](18TACrange_fig_1b/closed_loop_system_offline.png) · [Offline supervisor](18TACrange_fig_1b/supervisor_offline.json) · [逐项测量](18TACrange_fig_1b/online_offline_comparison.json)
<!-- END-RUN-RESULTS: 18TACrange_fig_1b -->

### 修改意见（请填写）

<!-- USER-NOTES: 18TACrange_fig_1b -->
- 需要修改的状态或转移：
- 可观事件调整：
- 可控事件调整：
- 希望保留的闭环或预期行为：
- 其他意见：
<!-- END-USER-NOTES: 18TACrange_fig_1b -->

## 18TACrange_fig_3a

编号：27。类别：论文自动机。
原始状态数：11；转移数：14；初始状态：`1`。
当前结果：`winning`；所选前视深度：`u=2`。

| 事件属性 | 集合 |
| --- | --- |
| 全部事件 Σ | `{c1, c2, o, u1, u2}` |
| 可观事件 Σo | `{o}` |
| 不可观事件 Σuo | `{c1, c2, u1, u2}` |
| 可控事件 Σc | `{c1, c2}` |
| 不可控事件 Σuc | `{o, u1, u2}` |

[原始系统图](18TACrange_fig_3a/plant.png) · [原始系统数据](18TACrange_fig_3a/plant.json) · [LL-BTS](18TACrange_fig_3a/ll_bts.png) · [闭环结果](18TACrange_fig_3a/closed_loop.png)

来源：18TACrange.pdf, Fig. 3a。

模型备注：p.4438, closed-loop language; primed states retained。

<!-- RUN-RESULTS: 18TACrange_fig_3a -->
### 运行结果与分析

- 判定：online **winning**，offline **winning**；完整离线结论一致。
- 预处理：Qd=∅；Qf=∅；Qe=`{1, 10, 11, 3, 5, 6, 7, 8, 8', 9, 9'}`。
- 深度：草稿阈值=2；最小可判定u=0；恢复offline根极大控制模式的最小u=0；实际采用u=2。
  深度经过逐例扫描标定；草稿阈值本身不等于普遍可解性保证。

| 结构指标 | Online LL-BTS | 传统 Offline BTS |
| --- | ---: | ---: |
| 构建D节点 | 1 | 4 |
| 构建O节点 | 0 | 16 |
| 构建边 | 0 | 30 |
| 全部保留D/O节点 | 1/0 | 4/14 |
| 所选闭环可达状态 | 11 | 11 |
| 所选闭环可达转移 | 14 | 14 |
| 所选控制器记忆状态 | 4 | 4 |

**为什么可解：** 初始估计已完全落在Qe中，允许全部事件即可安全延续。因此online可以在根估计处采用安全终端证书，停止枚举O节点。这不是原始plant只有一个状态；物理闭环仍按实际DFA状态和控制器记忆展开。
**实际控制行为：** 所有导出记忆状态的控制输出均允许全部事件，未禁用任何可控事件。保留的多个估计记忆不表示控制模式一定不同。

**传统BTS初始节点的模式去向（互斥分类）：** 共4个模式，其中UR含plant死锁0个；其余模式直接引入控制死锁0个；局部通过但因后续估计失败而剪除0个；最终保留4个。

| 实测成本 | Online | Offline | 绝对节约（Offline−Online） | 节约率 |
| --- | ---: | ---: | ---: | ---: |
| 总求解时间，含online预处理 / ms | 0.062600 | 0.253200 | 0.190600 | 75.276% |
| Python分配峰值 / KiB | 12.672 | 25.148 | 12.477 | 49.612% |

Online分项中位数：预处理0.056400 ms，求解0.005800 ms。总时间是每次预处理与求解相加后再取中位数，不能一般地把两个中位数直接相加。
运算：ΔT=(0.253200−0.062600) ms=0.190600 ms；时间节约率=ΔT/0.253200 ms=75.276%。
ΔM=25,752−12,976=12,776 bytes；内存节约率=ΔM/25,752=49.612%。
**成本解释：** 本例测得online总成本更低；收益同时包含窗口、Qf/Qe证书和提前拒绝坏模式。这是当前实现/模型的实测，不是对所有系统最坏复杂度下降的证明。

[Offline BTS数据](18TACrange_fig_3a/offline/bts.json) · [Offline闭环](18TACrange_fig_3a/closed_loop_system_offline.png) · [Offline supervisor](18TACrange_fig_3a/supervisor_offline.json) · [逐项测量](18TACrange_fig_3a/online_offline_comparison.json)
<!-- END-RUN-RESULTS: 18TACrange_fig_3a -->

### 修改意见（请填写）

<!-- USER-NOTES: 18TACrange_fig_3a -->
- 需要修改的状态或转移：
- 可观事件调整：
- 可控事件调整：
- 希望保留的闭环或预期行为：
- 其他意见：
<!-- END-USER-NOTES: 18TACrange_fig_3a -->

## 18TACrange_fig_3b

编号：28。类别：论文自动机。
原始状态数：4；转移数：3；初始状态：`1`。
当前结果：`losing`；所选前视深度：`u=1`。

| 事件属性 | 集合 |
| --- | --- |
| 全部事件 Σ | `{c1, c2, o, u1, u2}` |
| 可观事件 Σo | `{o}` |
| 不可观事件 Σuo | `{c1, c2, u1, u2}` |
| 可控事件 Σc | `{c1, c2}` |
| 不可控事件 Σuc | `{o, u1, u2}` |

[原始系统图](18TACrange_fig_3b/plant.png) · [原始系统数据](18TACrange_fig_3b/plant.json) · [LL-BTS](18TACrange_fig_3b/ll_bts.png) · [闭环结果](18TACrange_fig_3b/closed_loop.png)

来源：18TACrange.pdf, Fig. 3b。

模型备注：Closed-loop language L(S/G)。

<!-- RUN-RESULTS: 18TACrange_fig_3b -->
### 运行结果与分析

- 判定：online **losing**，offline **losing**；完整离线结论一致。
- 预处理：Qd=`{3, 4}`；Qf=`{2}`；Qe=∅。
- 深度：草稿阈值=1；最小可判定u=1；恢复offline根极大控制模式的最小u=1；实际采用u=1。
  深度经过逐例扫描标定；草稿阈值本身不等于普遍可解性保证。

| 结构指标 | Online LL-BTS | 传统 Offline BTS |
| --- | ---: | ---: |
| 构建D节点 | 2 | 3 |
| 构建O节点 | 2 | 12 |
| 构建边 | 4 | 16 |
| 全部保留D/O节点 | 0/0 | 0/0 |

**为什么不可解：** 完整已知系统的offline BTS也将初始决策节点剪除，因此这不是单纯u偏小造成的未判定；当前模型不存在满足本实验无死锁目标的supervisor。
从初始状态可达的原始图无环。有限无环系统的所有执行最终都到达无出边终点，仅通过禁用事件不能产生可持续运行的环。
未将空图或“不可解”提示图当成一个可行闭环，也未给终止状态补自环。

**传统BTS初始节点的模式去向（互斥分类）：** 共4个模式，其中UR含plant死锁0个；其余模式直接引入控制死锁0个；局部通过但因后续估计失败而剪除4个；最终保留0个。

| 实测成本 | Online | Offline | 绝对节约（Offline−Online） | 节约率 |
| --- | ---: | ---: | ---: | ---: |
| 总求解时间，含online预处理 / ms | 0.055500 | 0.064500 | 0.009000 | 13.953% |
| Python分配峰值 / KiB | 11.406 | 18.297 | 6.891 | 37.660% |

Online分项中位数：预处理0.013400 ms，求解0.042200 ms。总时间是每次预处理与求解相加后再取中位数，不能一般地把两个中位数直接相加。
运算：ΔT=(0.064500−0.055500) ms=0.009000 ms；时间节约率=ΔT/0.064500 ms=13.953%。
ΔM=18,736−11,680=7,056 bytes；内存节约率=ΔM/18,736=37.660%。
**成本解释：** 本例测得online总成本更低；收益同时包含窗口、Qf/Qe证书和提前拒绝坏模式。这是当前实现/模型的实测，不是对所有系统最坏复杂度下降的证明。

[Offline BTS数据](18TACrange_fig_3b/offline/bts.json) · [Offline闭环](18TACrange_fig_3b/closed_loop_system_offline.png) · [Offline supervisor](18TACrange_fig_3b/supervisor_offline.json) · [逐项测量](18TACrange_fig_3b/online_offline_comparison.json)
<!-- END-RUN-RESULTS: 18TACrange_fig_3b -->

### 修改意见（请填写）

<!-- USER-NOTES: 18TACrange_fig_3b -->
- 需要修改的状态或转移：
- 可观事件调整：
- 可控事件调整：
- 希望保留的闭环或预期行为：
- 其他意见：
<!-- END-USER-NOTES: 18TACrange_fig_3b -->

## 16TACNB_fig_7a

编号：29。类别：论文自动机。
原始状态数：11；转移数：14；初始状态：`0`。
当前结果：`winning`；所选前视深度：`u=2`。

| 事件属性 | 集合 |
| --- | --- |
| 全部事件 Σ | `{a1, a2, b1, b2, c1, c2, o}` |
| 可观事件 Σo | `{o}` |
| 不可观事件 Σuo | `{a1, a2, b1, b2, c1, c2}` |
| 可控事件 Σc | `{c1, c2}` |
| 不可控事件 Σuc | `{a1, a2, b1, b2, o}` |

[原始系统图](16TACNB_fig_7a/plant.png) · [原始系统数据](16TACNB_fig_7a/plant.json) · [LL-BTS](16TACNB_fig_7a/ll_bts.png) · [闭环结果](16TACNB_fig_7a/closed_loop.png)

来源：16TACNB.pdf, Fig. 7a。

模型备注：p.1252; marks 7,8 ignored for deadlock objective。

<!-- RUN-RESULTS: 16TACNB_fig_7a -->
### 运行结果与分析

- 判定：online **winning**，offline **winning**；完整离线结论一致。
- 预处理：Qd=`{10, 9}`；Qf=∅；Qe=∅。
- 深度：草稿阈值=0；最小可判定u=2；恢复offline根极大控制模式的最小u=2；实际采用u=2。
  深度经过逐例扫描标定；草稿阈值本身不等于普遍可解性保证。

| 结构指标 | Online LL-BTS | 传统 Offline BTS |
| --- | ---: | ---: |
| 构建D节点 | 2 | 2 |
| 构建O节点 | 5 | 8 |
| 构建边 | 10 | 16 |
| 全部保留D/O节点 | 2/5 | 2/7 |
| 所选闭环可达状态 | 5 | 7 |
| 所选闭环可达转移 | 6 | 9 |
| 所选控制器记忆状态 | 2 | 2 |

**为什么可解：** 初始估计不能直接用Qe证书终止，但剪枝后仍有认证控制模式。所选supervisor在每个估计处固定选择一个保留模式，所有可能观测均有认证后续控制，并检查不可观测可达集中的每个实际状态都有可用事件。
**实际控制行为：** 不可控事件始终允许；下表列出选定online supervisor的控制输出。

| 记忆 | 估计 | 允许的可控事件 | 禁用的可控事件 |
| --- | --- | --- | --- |
| C0 | `{0}` | `{c1, c2}` | ∅ |
| C1 | `{3, 4}` | ∅ | `{c1, c2}` |

两侧所选闭环的节点/边数不同，说明所选策略或记忆图不同。当前只核对了根极大模式集合一致，并分别验证了闭环无死锁；不据此宣称两个完整闭环语言相同。

**传统BTS初始节点的模式去向（互斥分类）：** 共4个模式，其中UR含plant死锁0个；其余模式直接引入控制死锁0个；局部通过但因后续估计失败而剪除0个；最终保留4个。

| 实测成本 | Online | Offline | 绝对节约（Offline−Online） | 节约率 |
| --- | ---: | ---: | ---: | ---: |
| 总求解时间，含online预处理 / ms | 0.108200 | 0.078500 | -0.029700 | -37.834% |
| Python分配峰值 / KiB | 16.641 | 17.297 | 0.656 | 3.794% |

Online分项中位数：预处理0.021600 ms，求解0.086600 ms。总时间是每次预处理与求解相加后再取中位数，不能一般地把两个中位数直接相加。
运算：ΔT=(0.078500−0.108200) ms=-0.029700 ms；时间节约率=ΔT/0.078500 ms=-37.834%。
ΔM=17,712−17,040=672 bytes；内存节约率=ΔM/17,712=3.794%。
**成本解释：** 本例online含预处理的总时间反而更高，已保留负节约率。减少图规模不保证抵消预处理成本；小模型的微秒级时间也易受解释器及调度影响。

[Offline BTS数据](16TACNB_fig_7a/offline/bts.json) · [Offline闭环](16TACNB_fig_7a/closed_loop_system_offline.png) · [Offline supervisor](16TACNB_fig_7a/supervisor_offline.json) · [逐项测量](16TACNB_fig_7a/online_offline_comparison.json)
<!-- END-RUN-RESULTS: 16TACNB_fig_7a -->

### 修改意见（请填写）

<!-- USER-NOTES: 16TACNB_fig_7a -->
- 需要修改的状态或转移：
- 可观事件调整：
- 可控事件调整：
- 希望保留的闭环或预期行为：
- 其他意见：
<!-- END-USER-NOTES: 16TACNB_fig_7a -->

## 22TACopaque_fig_1

编号：30。类别：论文自动机。
原始状态数：12；转移数：17；初始状态：`0`。
当前结果：`losing`；所选前视深度：`u=2`。

| 事件属性 | 集合 |
| --- | --- |
| 全部事件 Σ | `{c1, c2, o1, o2, o3}` |
| 可观事件 Σo | `{o1, o2, o3}` |
| 不可观事件 Σuo | `{c1, c2}` |
| 可控事件 Σc | `{c1, c2}` |
| 不可控事件 Σuc | `{o1, o2, o3}` |

[原始系统图](22TACopaque_fig_1/plant.png) · [原始系统数据](22TACopaque_fig_1/plant.json) · [LL-BTS](22TACopaque_fig_1/ll_bts.png) · [闭环结果](22TACopaque_fig_1/closed_loop.png)

来源：22TACopaque.pdf, Fig. 1。

模型备注：p.6569; no invented self-loops on terminal states 4,8,9,10,11。

<!-- RUN-RESULTS: 22TACopaque_fig_1 -->
### 运行结果与分析

- 判定：online **losing**，offline **losing**；完整离线结论一致。
- 预处理：Qd=`{10, 11, 4, 8, 9}`；Qf=`{2}`；Qe=∅。
- 深度：草稿阈值=2；最小可判定u=2；恢复offline根极大控制模式的最小u=2；实际采用u=2。
  深度经过逐例扫描标定；草稿阈值本身不等于普遍可解性保证。

| 结构指标 | Online LL-BTS | 传统 Offline BTS |
| --- | ---: | ---: |
| 构建D节点 | 3 | 9 |
| 构建O节点 | 2 | 36 |
| 构建边 | 6 | 55 |
| 全部保留D/O节点 | 0/0 | 0/0 |

**为什么不可解：** 完整已知系统的offline BTS也将初始决策节点剪除，因此这不是单纯u偏小造成的未判定；当前模型不存在满足本实验无死锁目标的supervisor。
从初始状态可达的原始图无环。有限无环系统的所有执行最终都到达无出边终点，仅通过禁用事件不能产生可持续运行的环。
未将空图或“不可解”提示图当成一个可行闭环，也未给终止状态补自环。

**传统BTS初始节点的模式去向（互斥分类）：** 共4个模式，其中UR含plant死锁0个；其余模式直接引入控制死锁1个；局部通过但因后续估计失败而剪除3个；最终保留0个。

| 实测成本 | Online | Offline | 绝对节约（Offline−Online） | 节约率 |
| --- | ---: | ---: | ---: | ---: |
| 总求解时间，含online预处理 / ms | 0.201800 | 0.365800 | 0.164000 | 44.833% |
| Python分配峰值 / KiB | 14.852 | 49.961 | 35.109 | 70.274% |

Online分项中位数：预处理0.049200 ms，求解0.152800 ms。总时间是每次预处理与求解相加后再取中位数，不能一般地把两个中位数直接相加。
运算：ΔT=(0.365800−0.201800) ms=0.164000 ms；时间节约率=ΔT/0.365800 ms=44.833%。
ΔM=51,160−15,208=35,952 bytes；内存节约率=ΔM/51,160=70.274%。
**成本解释：** 本例测得online总成本更低；收益同时包含窗口、Qf/Qe证书和提前拒绝坏模式。这是当前实现/模型的实测，不是对所有系统最坏复杂度下降的证明。

[Offline BTS数据](22TACopaque_fig_1/offline/bts.json) · [Offline闭环](22TACopaque_fig_1/closed_loop_system_offline.png) · [Offline supervisor](22TACopaque_fig_1/supervisor_offline.json) · [逐项测量](22TACopaque_fig_1/online_offline_comparison.json)
<!-- END-RUN-RESULTS: 22TACopaque_fig_1 -->

### 修改意见（请填写）

<!-- USER-NOTES: 22TACopaque_fig_1 -->
- 需要修改的状态或转移：
- 可观事件调整：
- 可控事件调整：
- 希望保留的闭环或预期行为：
- 其他意见：
<!-- END-USER-NOTES: 22TACopaque_fig_1 -->

## 24TACopa_fig_1a

编号：31。类别：论文自动机。
原始状态数：9；转移数：11；初始状态：`0`。
当前结果：`losing`；所选前视深度：`u=3`。

| 事件属性 | 集合 |
| --- | --- |
| 全部事件 Σ | `{a, b, c, o1, o2}` |
| 可观事件 Σo | `{o1, o2}` |
| 不可观事件 Σuo | `{a, b, c}` |
| 可控事件 Σc | `{a, b, c}` |
| 不可控事件 Σuc | `{o1, o2}` |

[原始系统图](24TACopa_fig_1a/plant.png) · [原始系统数据](24TACopa_fig_1a/plant.json) · [LL-BTS](24TACopa_fig_1a/ll_bts.png) · [闭环结果](24TACopa_fig_1a/closed_loop.png)

来源：24TACopa.pdf, Fig. 1a。

模型备注：p.4960, G。

<!-- RUN-RESULTS: 24TACopa_fig_1a -->
### 运行结果与分析

- 判定：online **losing**，offline **losing**；完整离线结论一致。
- 预处理：Qd=`{6}`；Qf=`{3, 5, 7, 8}`；Qe=∅。
- 深度：草稿阈值=3；最小可判定u=0；恢复offline根极大控制模式的最小u=0；实际采用u=3。
  深度经过逐例扫描标定；草稿阈值本身不等于普遍可解性保证。

| 结构指标 | Online LL-BTS | 传统 Offline BTS |
| --- | ---: | ---: |
| 构建D节点 | 1 | 5 |
| 构建O节点 | 0 | 40 |
| 构建边 | 0 | 70 |
| 全部保留D/O节点 | 0/0 | 0/0 |

**为什么不可解：** 完整已知系统的offline BTS也将初始决策节点剪除，因此这不是单纯u偏小造成的未判定；当前模型不存在满足本实验无死锁目标的supervisor。
从初始状态可达的原始图无环。有限无环系统的所有执行最终都到达无出边终点，仅通过禁用事件不能产生可持续运行的环。
未将空图或“不可解”提示图当成一个可行闭环，也未给终止状态补自环。

**传统BTS初始节点的模式去向（互斥分类）：** 共8个模式，其中UR含plant死锁0个；其余模式直接引入控制死锁4个；局部通过但因后续估计失败而剪除4个；最终保留0个。

| 实测成本 | Online | Offline | 绝对节约（Offline−Online） | 节约率 |
| --- | ---: | ---: | ---: | ---: |
| 总求解时间，含online预处理 / ms | 0.095200 | 0.223400 | 0.128200 | 57.386% |
| Python分配峰值 / KiB | 12.648 | 56.594 | 43.945 | 77.650% |

Online分项中位数：预处理0.027100 ms，求解0.067700 ms。总时间是每次预处理与求解相加后再取中位数，不能一般地把两个中位数直接相加。
运算：ΔT=(0.223400−0.095200) ms=0.128200 ms；时间节约率=ΔT/0.223400 ms=57.386%。
ΔM=57,952−12,952=45,000 bytes；内存节约率=ΔM/57,952=77.650%。
**成本解释：** 本例测得online总成本更低；收益同时包含窗口、Qf/Qe证书和提前拒绝坏模式。这是当前实现/模型的实测，不是对所有系统最坏复杂度下降的证明。

[Offline BTS数据](24TACopa_fig_1a/offline/bts.json) · [Offline闭环](24TACopa_fig_1a/closed_loop_system_offline.png) · [Offline supervisor](24TACopa_fig_1a/supervisor_offline.json) · [逐项测量](24TACopa_fig_1a/online_offline_comparison.json)
<!-- END-RUN-RESULTS: 24TACopa_fig_1a -->

### 修改意见（请填写）

<!-- USER-NOTES: 24TACopa_fig_1a -->
- 需要修改的状态或转移：
- 可观事件调整：
- 可控事件调整：
- 希望保留的闭环或预期行为：
- 其他意见：
<!-- END-USER-NOTES: 24TACopa_fig_1a -->

## 24TACopa_fig_1b

编号：32。类别：论文自动机。
原始状态数：2；转移数：1；初始状态：`0`。
当前结果：`losing`；所选前视深度：`u=0`。

| 事件属性 | 集合 |
| --- | --- |
| 全部事件 Σ | `{a, b, c, o1, o2}` |
| 可观事件 Σo | `{o1, o2}` |
| 不可观事件 Σuo | `{a, b, c}` |
| 可控事件 Σc | `{a, b, c}` |
| 不可控事件 Σuc | `{o1, o2}` |

[原始系统图](24TACopa_fig_1b/plant.png) · [原始系统数据](24TACopa_fig_1b/plant.json) · [LL-BTS](24TACopa_fig_1b/ll_bts.png) · [闭环结果](24TACopa_fig_1b/closed_loop.png)

来源：24TACopa.pdf, Fig. 1b。

模型备注：G1; dashed disabled b edge omitted。

<!-- RUN-RESULTS: 24TACopa_fig_1b -->
### 运行结果与分析

- 判定：online **losing**，offline **losing**；完整离线结论一致。
- 预处理：Qd=`{1}`；Qf=`{0}`；Qe=∅。
- 深度：草稿阈值=0；最小可判定u=0；恢复offline根极大控制模式的最小u=0；实际采用u=0。
  深度经过逐例扫描标定；草稿阈值本身不等于普遍可解性保证。

| 结构指标 | Online LL-BTS | 传统 Offline BTS |
| --- | ---: | ---: |
| 构建D节点 | 1 | 1 |
| 构建O节点 | 0 | 8 |
| 构建边 | 0 | 8 |
| 全部保留D/O节点 | 0/0 | 0/0 |

**为什么不可解：** 完整已知系统的offline BTS也将初始决策节点剪除，因此这不是单纯u偏小造成的未判定；当前模型不存在满足本实验无死锁目标的supervisor。
初始状态属于Qf：沿单后继状态链必然到达Qd。允许后继会走向死锁，禁用全部后继则直接引入控制死锁。
未将空图或“不可解”提示图当成一个可行闭环，也未给终止状态补自环。

**传统BTS初始节点的模式去向（互斥分类）：** 共8个模式，其中UR含plant死锁4个；其余模式直接引入控制死锁4个；局部通过但因后续估计失败而剪除0个；最终保留0个。

| 实测成本 | Online | Offline | 绝对节约（Offline−Online） | 节约率 |
| --- | ---: | ---: | ---: | ---: |
| 总求解时间，含online预处理 / ms | 0.020400 | 0.039800 | 0.019400 | 48.744% |
| Python分配峰值 / KiB | 7.836 | 13.305 | 5.469 | 41.104% |

Online分项中位数：预处理0.009000 ms，求解0.011300 ms。总时间是每次预处理与求解相加后再取中位数，不能一般地把两个中位数直接相加。
运算：ΔT=(0.039800−0.020400) ms=0.019400 ms；时间节约率=ΔT/0.039800 ms=48.744%。
ΔM=13,624−8,024=5,600 bytes；内存节约率=ΔM/13,624=41.104%。
**成本解释：** 本例测得online总成本更低；收益同时包含窗口、Qf/Qe证书和提前拒绝坏模式。这是当前实现/模型的实测，不是对所有系统最坏复杂度下降的证明。

[Offline BTS数据](24TACopa_fig_1b/offline/bts.json) · [Offline闭环](24TACopa_fig_1b/closed_loop_system_offline.png) · [Offline supervisor](24TACopa_fig_1b/supervisor_offline.json) · [逐项测量](24TACopa_fig_1b/online_offline_comparison.json)
<!-- END-RUN-RESULTS: 24TACopa_fig_1b -->

### 修改意见（请填写）

<!-- USER-NOTES: 24TACopa_fig_1b -->
- 需要修改的状态或转移：
- 可观事件调整：
- 可控事件调整：
- 希望保留的闭环或预期行为：
- 其他意见：
<!-- END-USER-NOTES: 24TACopa_fig_1b -->

## 24TACopa_fig_1c

编号：33。类别：论文自动机。
原始状态数：6；转移数：6；初始状态：`0`。
当前结果：`losing`；所选前视深度：`u=2`。

| 事件属性 | 集合 |
| --- | --- |
| 全部事件 Σ | `{a, b, c, o1, o2}` |
| 可观事件 Σo | `{o1, o2}` |
| 不可观事件 Σuo | `{a, b, c}` |
| 可控事件 Σc | `{a, b, c}` |
| 不可控事件 Σuc | `{o1, o2}` |

[原始系统图](24TACopa_fig_1c/plant.png) · [原始系统数据](24TACopa_fig_1c/plant.json) · [LL-BTS](24TACopa_fig_1c/ll_bts.png) · [闭环结果](24TACopa_fig_1c/closed_loop.png)

来源：24TACopa.pdf, Fig. 1c。

模型备注：G2; dashed disabled a edge omitted。

<!-- RUN-RESULTS: 24TACopa_fig_1c -->
### 运行结果与分析

- 判定：online **losing**，offline **losing**；完整离线结论一致。
- 预处理：Qd=`{6}`；Qf=`{5, 7, 8}`；Qe=∅。
- 深度：草稿阈值=2；最小可判定u=0；恢复offline根极大控制模式的最小u=0；实际采用u=2。
  深度经过逐例扫描标定；草稿阈值本身不等于普遍可解性保证。

| 结构指标 | Online LL-BTS | 传统 Offline BTS |
| --- | ---: | ---: |
| 构建D节点 | 1 | 4 |
| 构建O节点 | 0 | 32 |
| 构建边 | 0 | 52 |
| 全部保留D/O节点 | 0/0 | 0/0 |

**为什么不可解：** 完整已知系统的offline BTS也将初始决策节点剪除，因此这不是单纯u偏小造成的未判定；当前模型不存在满足本实验无死锁目标的supervisor。
从初始状态可达的原始图无环。有限无环系统的所有执行最终都到达无出边终点，仅通过禁用事件不能产生可持续运行的环。
未将空图或“不可解”提示图当成一个可行闭环，也未给终止状态补自环。

**传统BTS初始节点的模式去向（互斥分类）：** 共8个模式，其中UR含plant死锁0个；其余模式直接引入控制死锁4个；局部通过但因后续估计失败而剪除4个；最终保留0个。

| 实测成本 | Online | Offline | 绝对节约（Offline−Online） | 节约率 |
| --- | ---: | ---: | ---: | ---: |
| 总求解时间，含online预处理 / ms | 0.147900 | 0.291600 | 0.143700 | 49.280% |
| Python分配峰值 / KiB | 10.469 | 45.492 | 35.023 | 76.988% |

Online分项中位数：预处理0.041800 ms，求解0.106100 ms。总时间是每次预处理与求解相加后再取中位数，不能一般地把两个中位数直接相加。
运算：ΔT=(0.291600−0.147900) ms=0.143700 ms；时间节约率=ΔT/0.291600 ms=49.280%。
ΔM=46,584−10,720=35,864 bytes；内存节约率=ΔM/46,584=76.988%。
**成本解释：** 本例测得online总成本更低；收益同时包含窗口、Qf/Qe证书和提前拒绝坏模式。这是当前实现/模型的实测，不是对所有系统最坏复杂度下降的证明。

[Offline BTS数据](24TACopa_fig_1c/offline/bts.json) · [Offline闭环](24TACopa_fig_1c/closed_loop_system_offline.png) · [Offline supervisor](24TACopa_fig_1c/supervisor_offline.json) · [逐项测量](24TACopa_fig_1c/online_offline_comparison.json)
<!-- END-RUN-RESULTS: 24TACopa_fig_1c -->

### 修改意见（请填写）

<!-- USER-NOTES: 24TACopa_fig_1c -->
- 需要修改的状态或转移：
- 可观事件调整：
- 可控事件调整：
- 希望保留的闭环或预期行为：
- 其他意见：
<!-- END-USER-NOTES: 24TACopa_fig_1c -->

## 24TACopa_fig_4

编号：34。类别：论文自动机。
原始状态数：9；转移数：10；初始状态：`0`。
当前结果：`losing`；所选前视深度：`u=3`。

| 事件属性 | 集合 |
| --- | --- |
| 全部事件 Σ | `{a, o1, o2}` |
| 可观事件 Σo | `{o1, o2}` |
| 不可观事件 Σuo | `{a}` |
| 可控事件 Σc | `{a}` |
| 不可控事件 Σuc | `{o1, o2}` |

[原始系统图](24TACopa_fig_4/plant.png) · [原始系统数据](24TACopa_fig_4/plant.json) · [LL-BTS](24TACopa_fig_4/ll_bts.png) · [闭环结果](24TACopa_fig_4/closed_loop.png)

来源：24TACopa.pdf, Fig. 4。

模型备注：p.4967, quantitative-opacity plant reused with deadlock-free objective。

<!-- RUN-RESULTS: 24TACopa_fig_4 -->
### 运行结果与分析

- 判定：online **losing**，offline **losing**；完整离线结论一致。
- 预处理：Qd=`{8}`；Qf=`{1, 3, 5, 6, 7}`；Qe=∅。
- 深度：草稿阈值=1；最小可判定u=3；恢复offline根极大控制模式的最小u=3；实际采用u=3。
  深度经过逐例扫描标定；草稿阈值本身不等于普遍可解性保证。

| 结构指标 | Online LL-BTS | 传统 Offline BTS |
| --- | ---: | ---: |
| 构建D节点 | 4 | 9 |
| 构建O节点 | 4 | 18 |
| 构建边 | 8 | 36 |
| 全部保留D/O节点 | 0/0 | 0/0 |

**为什么不可解：** 完整已知系统的offline BTS也将初始决策节点剪除，因此这不是单纯u偏小造成的未判定；当前模型不存在满足本实验无死锁目标的supervisor。
从初始状态可达的原始图无环。有限无环系统的所有执行最终都到达无出边终点，仅通过禁用事件不能产生可持续运行的环。
未将空图或“不可解”提示图当成一个可行闭环，也未给终止状态补自环。

**传统BTS初始节点的模式去向（互斥分类）：** 共2个模式，其中UR含plant死锁0个；其余模式直接引入控制死锁0个；局部通过但因后续估计失败而剪除2个；最终保留0个。

| 实测成本 | Online | Offline | 绝对节约（Offline−Online） | 节约率 |
| --- | ---: | ---: | ---: | ---: |
| 总求解时间，含online预处理 / ms | 0.159300 | 0.266400 | 0.107100 | 40.203% |
| Python分配峰值 / KiB | 14.734 | 31.258 | 16.523 | 52.862% |

Online分项中位数：预处理0.048000 ms，求解0.113600 ms。总时间是每次预处理与求解相加后再取中位数，不能一般地把两个中位数直接相加。
运算：ΔT=(0.266400−0.159300) ms=0.107100 ms；时间节约率=ΔT/0.266400 ms=40.203%。
ΔM=32,008−15,088=16,920 bytes；内存节约率=ΔM/32,008=52.862%。
**成本解释：** 本例测得online总成本更低；收益同时包含窗口、Qf/Qe证书和提前拒绝坏模式。这是当前实现/模型的实测，不是对所有系统最坏复杂度下降的证明。

[Offline BTS数据](24TACopa_fig_4/offline/bts.json) · [Offline闭环](24TACopa_fig_4/closed_loop_system_offline.png) · [Offline supervisor](24TACopa_fig_4/supervisor_offline.json) · [逐项测量](24TACopa_fig_4/online_offline_comparison.json)
<!-- END-RUN-RESULTS: 24TACopa_fig_4 -->

### 修改意见（请填写）

<!-- USER-NOTES: 24TACopa_fig_4 -->
- 需要修改的状态或转移：
- 可观事件调整：
- 可控事件调整：
- 希望保留的闭环或预期行为：
- 其他意见：
<!-- END-USER-NOTES: 24TACopa_fig_4 -->

## 17Mealy_fig_2a

编号：35。类别：论文自动机。
原始状态数：10；转移数：12；初始状态：`0`。
当前结果：`losing`；所选前视深度：`u=2`。

| 事件属性 | 集合 |
| --- | --- |
| 全部事件 Σ | `{d1, d2, eps, s1, s2}` |
| 可观事件 Σo | `{d1, d2}` |
| 不可观事件 Σuo | `{eps, s1, s2}` |
| 可控事件 Σc | `{s1, s2}` |
| 不可控事件 Σuc | `{d1, d2, eps}` |

[原始系统图](17Mealy_fig_2a/plant.png) · [原始系统数据](17Mealy_fig_2a/plant.json) · [LL-BTS](17Mealy_fig_2a/ll_bts.png) · [闭环结果](17Mealy_fig_2a/closed_loop.png)

来源：17Mealy.pdf, Fig. 2a, PDF p.4。

模型备注：s1,s2=source sigma1,sigma2; d1,d2=delta1,delta2; eps is the explicit hidden symbol in Delta_epsilon. Marked terminal states retained.。

<!-- RUN-RESULTS: 17Mealy_fig_2a -->
### 运行结果与分析

- 判定：online **losing**，offline **losing**；完整离线结论一致。
- 预处理：Qd=`{3, 4}`；Qf=`{0_s2, 1_s1, 1_s2, 2, 2_s2}`；Qe=∅。
- 深度：草稿阈值=1；最小可判定u=2；恢复offline根极大控制模式的最小u=2；实际采用u=2。
  深度经过逐例扫描标定；草稿阈值本身不等于普遍可解性保证。

| 结构指标 | Online LL-BTS | 传统 Offline BTS |
| --- | ---: | ---: |
| 构建D节点 | 2 | 7 |
| 构建O节点 | 1 | 28 |
| 构建边 | 3 | 45 |
| 全部保留D/O节点 | 0/0 | 0/0 |

**为什么不可解：** 完整已知系统的offline BTS也将初始决策节点剪除，因此这不是单纯u偏小造成的未判定；当前模型不存在满足本实验无死锁目标的supervisor。
从初始状态可达的原始图无环。有限无环系统的所有执行最终都到达无出边终点，仅通过禁用事件不能产生可持续运行的环。
未将空图或“不可解”提示图当成一个可行闭环，也未给终止状态补自环。

**传统BTS初始节点的模式去向（互斥分类）：** 共4个模式，其中UR含plant死锁0个；其余模式直接引入控制死锁1个；局部通过但因后续估计失败而剪除3个；最终保留0个。

| 实测成本 | Online | Offline | 绝对节约（Offline−Online） | 节约率 |
| --- | ---: | ---: | ---: | ---: |
| 总求解时间，含online预处理 / ms | 0.211100 | 0.328700 | 0.117600 | 35.777% |
| Python分配峰值 / KiB | 12.945 | 41.922 | 28.977 | 69.120% |

Online分项中位数：预处理0.075100 ms，求解0.142900 ms。总时间是每次预处理与求解相加后再取中位数，不能一般地把两个中位数直接相加。
运算：ΔT=(0.328700−0.211100) ms=0.117600 ms；时间节约率=ΔT/0.328700 ms=35.777%。
ΔM=42,928−13,256=29,672 bytes；内存节约率=ΔM/42,928=69.120%。
**成本解释：** 本例测得online总成本更低；收益同时包含窗口、Qf/Qe证书和提前拒绝坏模式。这是当前实现/模型的实测，不是对所有系统最坏复杂度下降的证明。

[Offline BTS数据](17Mealy_fig_2a/offline/bts.json) · [Offline闭环](17Mealy_fig_2a/closed_loop_system_offline.png) · [Offline supervisor](17Mealy_fig_2a/supervisor_offline.json) · [逐项测量](17Mealy_fig_2a/online_offline_comparison.json)
<!-- END-RUN-RESULTS: 17Mealy_fig_2a -->

### 修改意见（请填写）

<!-- USER-NOTES: 17Mealy_fig_2a -->
- 需要修改的状态或转移：
- 可观事件调整：
- 可控事件调整：
- 希望保留的闭环或预期行为：
- 其他意见：
<!-- END-USER-NOTES: 17Mealy_fig_2a -->

## 17Mealy_fig_2b

编号：36。类别：论文自动机。
原始状态数：8；转移数：10；初始状态：`0`。
当前结果：`losing`；所选前视深度：`u=2`。

| 事件属性 | 集合 |
| --- | --- |
| 全部事件 Σ | `{d1, d2, eps, s1, s2}` |
| 可观事件 Σo | `{d1, d2}` |
| 不可观事件 Σuo | `{eps, s1, s2}` |
| 可控事件 Σc | `{s1, s2}` |
| 不可控事件 Σuc | `{d1, d2, eps}` |

[原始系统图](17Mealy_fig_2b/plant.png) · [原始系统数据](17Mealy_fig_2b/plant.json) · [LL-BTS](17Mealy_fig_2b/ll_bts.png) · [闭环结果](17Mealy_fig_2b/closed_loop.png)

来源：17Mealy.pdf, Fig. 2b, PDF p.4。

模型备注：s1,s2=source sigma1,sigma2; d1,d2=delta1,delta2; eps is the explicit hidden symbol in Delta_epsilon. Marked terminal states retained.。

<!-- RUN-RESULTS: 17Mealy_fig_2b -->
### 运行结果与分析

- 判定：online **losing**，offline **losing**；完整离线结论一致。
- 预处理：Qd=`{2, 3}`；Qf=`{0_s2, 1_s1, 1_s2}`；Qe=∅。
- 深度：草稿阈值=1；最小可判定u=2；恢复offline根极大控制模式的最小u=2；实际采用u=2。
  深度经过逐例扫描标定；草稿阈值本身不等于普遍可解性保证。

| 结构指标 | Online LL-BTS | 传统 Offline BTS |
| --- | ---: | ---: |
| 构建D节点 | 2 | 6 |
| 构建O节点 | 1 | 24 |
| 构建边 | 3 | 35 |
| 全部保留D/O节点 | 0/0 | 0/0 |

**为什么不可解：** 完整已知系统的offline BTS也将初始决策节点剪除，因此这不是单纯u偏小造成的未判定；当前模型不存在满足本实验无死锁目标的supervisor。
从初始状态可达的原始图无环。有限无环系统的所有执行最终都到达无出边终点，仅通过禁用事件不能产生可持续运行的环。
未将空图或“不可解”提示图当成一个可行闭环，也未给终止状态补自环。

**传统BTS初始节点的模式去向（互斥分类）：** 共4个模式，其中UR含plant死锁0个；其余模式直接引入控制死锁1个；局部通过但因后续估计失败而剪除3个；最终保留0个。

| 实测成本 | Online | Offline | 绝对节约（Offline−Online） | 节约率 |
| --- | ---: | ---: | ---: | ---: |
| 总求解时间，含online预处理 / ms | 0.096400 | 0.137000 | 0.040600 | 29.635% |
| Python分配峰值 / KiB | 12.648 | 36.523 | 23.875 | 65.369% |

Online分项中位数：预处理0.025500 ms，求解0.069600 ms。总时间是每次预处理与求解相加后再取中位数，不能一般地把两个中位数直接相加。
运算：ΔT=(0.137000−0.096400) ms=0.040600 ms；时间节约率=ΔT/0.137000 ms=29.635%。
ΔM=37,400−12,952=24,448 bytes；内存节约率=ΔM/37,400=65.369%。
**成本解释：** 本例测得online总成本更低；收益同时包含窗口、Qf/Qe证书和提前拒绝坏模式。这是当前实现/模型的实测，不是对所有系统最坏复杂度下降的证明。

[Offline BTS数据](17Mealy_fig_2b/offline/bts.json) · [Offline闭环](17Mealy_fig_2b/closed_loop_system_offline.png) · [Offline supervisor](17Mealy_fig_2b/supervisor_offline.json) · [逐项测量](17Mealy_fig_2b/online_offline_comparison.json)
<!-- END-RUN-RESULTS: 17Mealy_fig_2b -->

### 修改意见（请填写）

<!-- USER-NOTES: 17Mealy_fig_2b -->
- 需要修改的状态或转移：
- 可观事件调整：
- 可控事件调整：
- 希望保留的闭环或预期行为：
- 其他意见：
<!-- END-USER-NOTES: 17Mealy_fig_2b -->

## 17Mealy_fig_3a

编号：37。类别：论文自动机。
原始状态数：9；转移数：11；初始状态：`0`。
当前结果：`losing`；所选前视深度：`u=2`。

| 事件属性 | 集合 |
| --- | --- |
| 全部事件 Σ | `{d1, d2, eps, s1, s2}` |
| 可观事件 Σo | `{d1, d2}` |
| 不可观事件 Σuo | `{eps, s1, s2}` |
| 可控事件 Σc | `{s1, s2}` |
| 不可控事件 Σuc | `{d1, d2, eps}` |

[原始系统图](17Mealy_fig_3a/plant.png) · [原始系统数据](17Mealy_fig_3a/plant.json) · [LL-BTS](17Mealy_fig_3a/ll_bts.png) · [闭环结果](17Mealy_fig_3a/closed_loop.png)

来源：17Mealy.pdf, Fig. 3a, PDF p.5。

模型备注：s1,s2=source sigma1,sigma2; d1,d2=delta1,delta2; eps is the explicit hidden symbol in Delta_epsilon. Marked terminal states retained.。

<!-- RUN-RESULTS: 17Mealy_fig_3a -->
### 运行结果与分析

- 判定：online **losing**，offline **losing**；完整离线结论一致。
- 预处理：Qd=`{2, 3}`；Qf=`{0_s2, 1', 1_s1, 1_s2}`；Qe=∅。
- 深度：草稿阈值=1；最小可判定u=2；恢复offline根极大控制模式的最小u=2；实际采用u=2。
  深度经过逐例扫描标定；草稿阈值本身不等于普遍可解性保证。

| 结构指标 | Online LL-BTS | 传统 Offline BTS |
| --- | ---: | ---: |
| 构建D节点 | 3 | 7 |
| 构建O节点 | 1 | 28 |
| 构建边 | 3 | 40 |
| 全部保留D/O节点 | 0/0 | 0/0 |

**为什么不可解：** 完整已知系统的offline BTS也将初始决策节点剪除，因此这不是单纯u偏小造成的未判定；当前模型不存在满足本实验无死锁目标的supervisor。
从初始状态可达的原始图无环。有限无环系统的所有执行最终都到达无出边终点，仅通过禁用事件不能产生可持续运行的环。
未将空图或“不可解”提示图当成一个可行闭环，也未给终止状态补自环。

**传统BTS初始节点的模式去向（互斥分类）：** 共4个模式，其中UR含plant死锁0个；其余模式直接引入控制死锁1个；局部通过但因后续估计失败而剪除3个；最终保留0个。

| 实测成本 | Online | Offline | 绝对节约（Offline−Online） | 节约率 |
| --- | ---: | ---: | ---: | ---: |
| 总求解时间，含online预处理 / ms | 0.094300 | 0.143400 | 0.049100 | 34.240% |
| Python分配峰值 / KiB | 12.602 | 39.672 | 27.070 | 68.236% |

Online分项中位数：预处理0.025900 ms，求解0.068300 ms。总时间是每次预处理与求解相加后再取中位数，不能一般地把两个中位数直接相加。
运算：ΔT=(0.143400−0.094300) ms=0.049100 ms；时间节约率=ΔT/0.143400 ms=34.240%。
ΔM=40,624−12,904=27,720 bytes；内存节约率=ΔM/40,624=68.236%。
**成本解释：** 本例测得online总成本更低；收益同时包含窗口、Qf/Qe证书和提前拒绝坏模式。这是当前实现/模型的实测，不是对所有系统最坏复杂度下降的证明。

[Offline BTS数据](17Mealy_fig_3a/offline/bts.json) · [Offline闭环](17Mealy_fig_3a/closed_loop_system_offline.png) · [Offline supervisor](17Mealy_fig_3a/supervisor_offline.json) · [逐项测量](17Mealy_fig_3a/online_offline_comparison.json)
<!-- END-RUN-RESULTS: 17Mealy_fig_3a -->

### 修改意见（请填写）

<!-- USER-NOTES: 17Mealy_fig_3a -->
- 需要修改的状态或转移：
- 可观事件调整：
- 可控事件调整：
- 希望保留的闭环或预期行为：
- 其他意见：
<!-- END-USER-NOTES: 17Mealy_fig_3a -->

## 17Mealy_fig_3b

编号：38。类别：论文自动机。
原始状态数：7；转移数：8；初始状态：`0`。
当前结果：`losing`；所选前视深度：`u=2`。

| 事件属性 | 集合 |
| --- | --- |
| 全部事件 Σ | `{d1, d2, eps, s1, s2}` |
| 可观事件 Σo | `{d1, d2}` |
| 不可观事件 Σuo | `{eps, s1, s2}` |
| 可控事件 Σc | `{s1, s2}` |
| 不可控事件 Σuc | `{d1, d2, eps}` |

[原始系统图](17Mealy_fig_3b/plant.png) · [原始系统数据](17Mealy_fig_3b/plant.json) · [LL-BTS](17Mealy_fig_3b/ll_bts.png) · [闭环结果](17Mealy_fig_3b/closed_loop.png)

来源：17Mealy.pdf, Fig. 3b, PDF p.5。

模型备注：s1,s2=source sigma1,sigma2; d1,d2=delta1,delta2; eps is the explicit hidden symbol in Delta_epsilon. Marked terminal states retained.。

<!-- RUN-RESULTS: 17Mealy_fig_3b -->
### 运行结果与分析

- 判定：online **losing**，offline **losing**；完整离线结论一致。
- 预处理：Qd=`{2, 3}`；Qf=`{1_s1, 1_s2}`；Qe=∅。
- 深度：草稿阈值=1；最小可判定u=2；恢复offline根极大控制模式的最小u=2；实际采用u=2。
  深度经过逐例扫描标定；草稿阈值本身不等于普遍可解性保证。

| 结构指标 | Online LL-BTS | 传统 Offline BTS |
| --- | ---: | ---: |
| 构建D节点 | 2 | 5 |
| 构建O节点 | 2 | 20 |
| 构建边 | 6 | 27 |
| 全部保留D/O节点 | 0/0 | 0/0 |

**为什么不可解：** 完整已知系统的offline BTS也将初始决策节点剪除，因此这不是单纯u偏小造成的未判定；当前模型不存在满足本实验无死锁目标的supervisor。
从初始状态可达的原始图无环。有限无环系统的所有执行最终都到达无出边终点，仅通过禁用事件不能产生可持续运行的环。
未将空图或“不可解”提示图当成一个可行闭环，也未给终止状态补自环。

**传统BTS初始节点的模式去向（互斥分类）：** 共4个模式，其中UR含plant死锁0个；其余模式直接引入控制死锁2个；局部通过但因后续估计失败而剪除2个；最终保留0个。

| 实测成本 | Online | Offline | 绝对节约（Offline−Online） | 节约率 |
| --- | ---: | ---: | ---: | ---: |
| 总求解时间，含online预处理 / ms | 0.105500 | 0.121600 | 0.016100 | 13.240% |
| Python分配峰值 / KiB | 12.766 | 31.172 | 18.406 | 59.048% |

Online分项中位数：预处理0.024600 ms，求解0.078200 ms。总时间是每次预处理与求解相加后再取中位数，不能一般地把两个中位数直接相加。
运算：ΔT=(0.121600−0.105500) ms=0.016100 ms；时间节约率=ΔT/0.121600 ms=13.240%。
ΔM=31,920−13,072=18,848 bytes；内存节约率=ΔM/31,920=59.048%。
**成本解释：** 本例测得online总成本更低；收益同时包含窗口、Qf/Qe证书和提前拒绝坏模式。这是当前实现/模型的实测，不是对所有系统最坏复杂度下降的证明。

[Offline BTS数据](17Mealy_fig_3b/offline/bts.json) · [Offline闭环](17Mealy_fig_3b/closed_loop_system_offline.png) · [Offline supervisor](17Mealy_fig_3b/supervisor_offline.json) · [逐项测量](17Mealy_fig_3b/online_offline_comparison.json)
<!-- END-RUN-RESULTS: 17Mealy_fig_3b -->

### 修改意见（请填写）

<!-- USER-NOTES: 17Mealy_fig_3b -->
- 需要修改的状态或转移：
- 可观事件调整：
- 可控事件调整：
- 希望保留的闭环或预期行为：
- 其他意见：
<!-- END-USER-NOTES: 17Mealy_fig_3b -->

## 22TAConline_fig_2

编号：39。类别：论文自动机。
原始状态数：17；转移数：17；初始状态：`1`。
当前结果：`losing`；所选前视深度：`u=5`。

| 事件属性 | 集合 |
| --- | --- |
| 全部事件 Σ | `{a, b, u1, u2, u3}` |
| 可观事件 Σo | `{a, b}` |
| 不可观事件 Σuo | `{u1, u2, u3}` |
| 可控事件 Σc | `{a, b, u1, u2, u3}` |
| 不可控事件 Σuc | ∅ |

[原始系统图](22TAConline_fig_2/plant.png) · [原始系统数据](22TAConline_fig_2/plant.json) · [LL-BTS](22TAConline_fig_2/ll_bts.png) · [闭环结果](22TAConline_fig_2/closed_loop.png)

来源：22TAConline.pdf, Fig. 2, PDF p.5。

模型备注：Plant topology and partitions only; control-channel delay Nc=1 is not simulated.。

<!-- RUN-RESULTS: 22TAConline_fig_2 -->
### 运行结果与分析

- 判定：online **losing**，offline **losing**；完整离线结论一致。
- 预处理：Qd=`{10, 15, 16, 17, 7}`；Qf=`{11, 12, 13, 14}`；Qe=∅。
- 深度：草稿阈值=1；最小可判定u=5；恢复offline根极大控制模式的最小u=5；实际采用u=5。
  深度经过逐例扫描标定；草稿阈值本身不等于普遍可解性保证。

| 结构指标 | Online LL-BTS | 传统 Offline BTS |
| --- | ---: | ---: |
| 构建D节点 | 8 | 14 |
| 构建O节点 | 68 | 448 |
| 构建边 | 152 | 634 |
| 全部保留D/O节点 | 0/0 | 0/0 |

**为什么不可解：** 完整已知系统的offline BTS也将初始决策节点剪除，因此这不是单纯u偏小造成的未判定；当前模型不存在满足本实验无死锁目标的supervisor。
从初始状态可达的原始图无环。有限无环系统的所有执行最终都到达无出边终点，仅通过禁用事件不能产生可持续运行的环。
未将空图或“不可解”提示图当成一个可行闭环，也未给终止状态补自环。

**传统BTS初始节点的模式去向（互斥分类）：** 共32个模式，其中UR含plant死锁0个；其余模式直接引入控制死锁16个；局部通过但因后续估计失败而剪除16个；最终保留0个。

| 实测成本 | Online | Offline | 绝对节约（Offline−Online） | 节约率 |
| --- | ---: | ---: | ---: | ---: |
| 总求解时间，含online预处理 / ms | 1.317500 | 2.662700 | 1.345200 | 50.520% |
| Python分配峰值 / KiB | 114.492 | 514.754 | 400.262 | 77.758% |

Online分项中位数：预处理0.059800 ms，求解1.259300 ms。总时间是每次预处理与求解相加后再取中位数，不能一般地把两个中位数直接相加。
运算：ΔT=(2.662700−1.317500) ms=1.345200 ms；时间节约率=ΔT/2.662700 ms=50.520%。
ΔM=527,108−117,240=409,868 bytes；内存节约率=ΔM/527,108=77.758%。
**成本解释：** 本例测得online总成本更低；收益同时包含窗口、Qf/Qe证书和提前拒绝坏模式。这是当前实现/模型的实测，不是对所有系统最坏复杂度下降的证明。

[Offline BTS数据](22TAConline_fig_2/offline/bts.json) · [Offline闭环](22TAConline_fig_2/closed_loop_system_offline.png) · [Offline supervisor](22TAConline_fig_2/supervisor_offline.json) · [逐项测量](22TAConline_fig_2/online_offline_comparison.json)
<!-- END-RUN-RESULTS: 22TAConline_fig_2 -->

### 修改意见（请填写）

<!-- USER-NOTES: 22TAConline_fig_2 -->
- 需要修改的状态或转移：
- 可观事件调整：
- 可控事件调整：
- 希望保留的闭环或预期行为：
- 其他意见：
<!-- END-USER-NOTES: 22TAConline_fig_2 -->

## 22TAClocal_fig_2

编号：40。类别：论文自动机。
原始状态数：9；转移数：12；初始状态：`x0`。
当前结果：`winning`；所选前视深度：`u=0`。

| 事件属性 | 集合 |
| --- | --- |
| 全部事件 Σ | `{a, b, c, d, e, f, u1, u2, u3, u4, u5, u6}` |
| 可观事件 Σo | `{a, b, c, d, e, f, u1, u2, u3, u4, u5, u6}` |
| 不可观事件 Σuo | ∅ |
| 可控事件 Σc | `{a, b, c, d, e, f}` |
| 不可控事件 Σuc | `{u1, u2, u3, u4, u5, u6}` |

[原始系统图](22TAClocal_fig_2/plant.png) · [原始系统数据](22TAClocal_fig_2/plant.json) · [LL-BTS](22TAClocal_fig_2/ll_bts.png) · [闭环结果](22TAClocal_fig_2/closed_loop.png)

来源：22TAClocal.pdf, Fig. 2, PDF p.4。

模型备注：Full observation as stated on PDF p.3; weights ignored. Unsafe x8 is NOT a deadlock: its original u5 return edge is preserved.。

<!-- RUN-RESULTS: 22TAClocal_fig_2 -->
### 运行结果与分析

- 判定：online **winning**，offline **winning**；完整离线结论一致。
- 预处理：Qd=∅；Qf=∅；Qe=`{x0, x1, x2, x3, x4, x5, x6, x7, x8}`。
- 深度：草稿阈值=0；最小可判定u=0；恢复offline根极大控制模式的最小u=0；实际采用u=0。
  深度经过逐例扫描标定；草稿阈值本身不等于普遍可解性保证。

| 结构指标 | Online LL-BTS | 传统 Offline BTS |
| --- | ---: | ---: |
| 构建D节点 | 1 | 9 |
| 构建O节点 | 0 | 576 |
| 构建边 | 0 | 1152 |
| 全部保留D/O节点 | 1/0 | 9/480 |
| 所选闭环可达状态 | 9 | 9 |
| 所选闭环可达转移 | 12 | 12 |
| 所选控制器记忆状态 | 9 | 9 |

**为什么可解：** 初始估计已完全落在Qe中，允许全部事件即可安全延续。因此online可以在根估计处采用安全终端证书，停止枚举O节点。这不是原始plant只有一个状态；物理闭环仍按实际DFA状态和控制器记忆展开。
**实际控制行为：** 所有导出记忆状态的控制输出均允许全部事件，未禁用任何可控事件。保留的多个估计记忆不表示控制模式一定不同。

**传统BTS初始节点的模式去向（互斥分类）：** 共64个模式，其中UR含plant死锁0个；其余模式直接引入控制死锁0个；局部通过但因后续估计失败而剪除0个；最终保留64个。

| 实测成本 | Online | Offline | 绝对节约（Offline−Online） | 节约率 |
| --- | ---: | ---: | ---: | ---: |
| 总求解时间，含online预处理 / ms | 0.041300 | 4.482500 | 4.441200 | 99.079% |
| Python分配峰值 / KiB | 10.836 | 776.043 | 765.207 | 98.604% |

Online分项中位数：预处理0.035500 ms，求解0.005800 ms。总时间是每次预处理与求解相加后再取中位数，不能一般地把两个中位数直接相加。
运算：ΔT=(4.482500−0.041300) ms=4.441200 ms；时间节约率=ΔT/4.482500 ms=99.079%。
ΔM=794,668−11,096=783,572 bytes；内存节约率=ΔM/794,668=98.604%。
**成本解释：** 本例测得online总成本更低；收益同时包含窗口、Qf/Qe证书和提前拒绝坏模式。这是当前实现/模型的实测，不是对所有系统最坏复杂度下降的证明。

[Offline BTS数据](22TAClocal_fig_2/offline/bts.json) · [Offline闭环](22TAClocal_fig_2/closed_loop_system_offline.png) · [Offline supervisor](22TAClocal_fig_2/supervisor_offline.json) · [逐项测量](22TAClocal_fig_2/online_offline_comparison.json)
<!-- END-RUN-RESULTS: 22TAClocal_fig_2 -->

### 修改意见（请填写）

<!-- USER-NOTES: 22TAClocal_fig_2 -->
- 需要修改的状态或转移：
- 可观事件调整：
- 可控事件调整：
- 希望保留的闭环或预期行为：
- 其他意见：
<!-- END-USER-NOTES: 22TAClocal_fig_2 -->

## 24AutoOpt_fig_1

编号：41。类别：论文自动机。
原始状态数：2；转移数：3；初始状态：`q0`。
当前结果：`winning`；所选前视深度：`u=0`。

| 事件属性 | 集合 |
| --- | --- |
| 全部事件 Σ | `{a, b, c}` |
| 可观事件 Σo | `{a, b, c}` |
| 不可观事件 Σuo | ∅ |
| 可控事件 Σc | `{a, b, c}` |
| 不可控事件 Σuc | ∅ |

[原始系统图](24AutoOpt_fig_1/plant.png) · [原始系统数据](24AutoOpt_fig_1/plant.json) · [LL-BTS](24AutoOpt_fig_1/ll_bts.png) · [闭环结果](24AutoOpt_fig_1/closed_loop.png)

来源：24AutoOpt.pdf, Fig. 1, PDF p.4。

模型备注：Fully observed optimal cyclic-task source; costs and marks ignored.。

<!-- RUN-RESULTS: 24AutoOpt_fig_1 -->
### 运行结果与分析

- 判定：online **winning**，offline **winning**；完整离线结论一致。
- 预处理：Qd=∅；Qf=∅；Qe=`{q0, q1}`。
- 深度：草稿阈值=0；最小可判定u=0；恢复offline根极大控制模式的最小u=0；实际采用u=0。
  深度经过逐例扫描标定；草稿阈值本身不等于普遍可解性保证。

| 结构指标 | Online LL-BTS | 传统 Offline BTS |
| --- | ---: | ---: |
| 构建D节点 | 1 | 2 |
| 构建O节点 | 0 | 16 |
| 构建边 | 0 | 28 |
| 全部保留D/O节点 | 1/0 | 2/10 |
| 所选闭环可达状态 | 2 | 2 |
| 所选闭环可达转移 | 3 | 3 |
| 所选控制器记忆状态 | 2 | 2 |

**为什么可解：** 初始估计已完全落在Qe中，允许全部事件即可安全延续。因此online可以在根估计处采用安全终端证书，停止枚举O节点。这不是原始plant只有一个状态；物理闭环仍按实际DFA状态和控制器记忆展开。
**实际控制行为：** 所有导出记忆状态的控制输出均允许全部事件，未禁用任何可控事件。保留的多个估计记忆不表示控制模式一定不同。

**传统BTS初始节点的模式去向（互斥分类）：** 共8个模式，其中UR含plant死锁0个；其余模式直接引入控制死锁2个；局部通过但因后续估计失败而剪除0个；最终保留6个。

| 实测成本 | Online | Offline | 绝对节约（Offline−Online） | 节约率 |
| --- | ---: | ---: | ---: | ---: |
| 总求解时间，含online预处理 / ms | 0.020200 | 0.170800 | 0.150600 | 88.173% |
| Python分配峰值 / KiB | 5.086 | 24.164 | 19.078 | 78.952% |

Online分项中位数：预处理0.016100 ms，求解0.004200 ms。总时间是每次预处理与求解相加后再取中位数，不能一般地把两个中位数直接相加。
运算：ΔT=(0.170800−0.020200) ms=0.150600 ms；时间节约率=ΔT/0.170800 ms=88.173%。
ΔM=24,744−5,208=19,536 bytes；内存节约率=ΔM/24,744=78.952%。
**成本解释：** 本例测得online总成本更低；收益同时包含窗口、Qf/Qe证书和提前拒绝坏模式。这是当前实现/模型的实测，不是对所有系统最坏复杂度下降的证明。

[Offline BTS数据](24AutoOpt_fig_1/offline/bts.json) · [Offline闭环](24AutoOpt_fig_1/closed_loop_system_offline.png) · [Offline supervisor](24AutoOpt_fig_1/supervisor_offline.json) · [逐项测量](24AutoOpt_fig_1/online_offline_comparison.json)
<!-- END-RUN-RESULTS: 24AutoOpt_fig_1 -->

### 修改意见（请填写）

<!-- USER-NOTES: 24AutoOpt_fig_1 -->
- 需要修改的状态或转移：
- 可观事件调整：
- 可控事件调整：
- 希望保留的闭环或预期行为：
- 其他意见：
<!-- END-USER-NOTES: 24AutoOpt_fig_1 -->

## 24AutoOpt_fig_2

编号：42。类别：论文自动机。
原始状态数：5；转移数：10；初始状态：`q0`。
当前结果：`winning`；所选前视深度：`u=0`。

| 事件属性 | 集合 |
| --- | --- |
| 全部事件 Σ | `{a, d, e}` |
| 可观事件 Σo | `{a, d, e}` |
| 不可观事件 Σuo | ∅ |
| 可控事件 Σc | `{a}` |
| 不可控事件 Σuc | `{d, e}` |

[原始系统图](24AutoOpt_fig_2/plant.png) · [原始系统数据](24AutoOpt_fig_2/plant.json) · [LL-BTS](24AutoOpt_fig_2/ll_bts.png) · [闭环结果](24AutoOpt_fig_2/closed_loop.png)

来源：24AutoOpt.pdf, Fig. 2, PDF p.5。

模型备注：Full observation; costs/marked states ignored.。

<!-- RUN-RESULTS: 24AutoOpt_fig_2 -->
### 运行结果与分析

- 判定：online **winning**，offline **winning**；完整离线结论一致。
- 预处理：Qd=∅；Qf=∅；Qe=`{q0, q1, q2, q3, q4}`。
- 深度：草稿阈值=0；最小可判定u=0；恢复offline根极大控制模式的最小u=0；实际采用u=0。
  深度经过逐例扫描标定；草稿阈值本身不等于普遍可解性保证。

| 结构指标 | Online LL-BTS | 传统 Offline BTS |
| --- | ---: | ---: |
| 构建D节点 | 1 | 5 |
| 构建O节点 | 0 | 10 |
| 构建边 | 0 | 27 |
| 全部保留D/O节点 | 1/0 | 5/10 |
| 所选闭环可达状态 | 5 | 5 |
| 所选闭环可达转移 | 10 | 10 |
| 所选控制器记忆状态 | 5 | 5 |

**为什么可解：** 初始估计已完全落在Qe中，允许全部事件即可安全延续。因此online可以在根估计处采用安全终端证书，停止枚举O节点。这不是原始plant只有一个状态；物理闭环仍按实际DFA状态和控制器记忆展开。
**实际控制行为：** 所有导出记忆状态的控制输出均允许全部事件，未禁用任何可控事件。保留的多个估计记忆不表示控制模式一定不同。

**传统BTS初始节点的模式去向（互斥分类）：** 共2个模式，其中UR含plant死锁0个；其余模式直接引入控制死锁0个；局部通过但因后续估计失败而剪除0个；最终保留2个。

| 实测成本 | Online | Offline | 绝对节约（Offline−Online） | 节约率 |
| --- | ---: | ---: | ---: | ---: |
| 总求解时间，含online预处理 / ms | 0.015300 | 0.070500 | 0.055200 | 78.298% |
| Python分配峰值 / KiB | 7.852 | 22.203 | 14.352 | 64.638% |

Online分项中位数：预处理0.012700 ms，求解0.002600 ms。总时间是每次预处理与求解相加后再取中位数，不能一般地把两个中位数直接相加。
运算：ΔT=(0.070500−0.015300) ms=0.055200 ms；时间节约率=ΔT/0.070500 ms=78.298%。
ΔM=22,736−8,040=14,696 bytes；内存节约率=ΔM/22,736=64.638%。
**成本解释：** 本例测得online总成本更低；收益同时包含窗口、Qf/Qe证书和提前拒绝坏模式。这是当前实现/模型的实测，不是对所有系统最坏复杂度下降的证明。

[Offline BTS数据](24AutoOpt_fig_2/offline/bts.json) · [Offline闭环](24AutoOpt_fig_2/closed_loop_system_offline.png) · [Offline supervisor](24AutoOpt_fig_2/supervisor_offline.json) · [逐项测量](24AutoOpt_fig_2/online_offline_comparison.json)
<!-- END-RUN-RESULTS: 24AutoOpt_fig_2 -->

### 修改意见（请填写）

<!-- USER-NOTES: 24AutoOpt_fig_2 -->
- 需要修改的状态或转移：
- 可观事件调整：
- 可控事件调整：
- 希望保留的闭环或预期行为：
- 其他意见：
<!-- END-USER-NOTES: 24AutoOpt_fig_2 -->

## 24AutoOpt_fig_6b

编号：43。类别：论文自动机。
原始状态数：13；转移数：32；初始状态：`q0`。
当前结果：`winning`；所选前视深度：`u=0`。

| 事件属性 | 集合 |
| --- | --- |
| 全部事件 Σ | `{B, E, N, S, W}` |
| 可观事件 Σo | `{B, E, N, S, W}` |
| 不可观事件 Σuo | ∅ |
| 可控事件 Σc | `{E, N, S, W}` |
| 不可控事件 Σuc | `{B}` |

[原始系统图](24AutoOpt_fig_6b/plant.png) · [原始系统数据](24AutoOpt_fig_6b/plant.json) · [LL-BTS](24AutoOpt_fig_6b/ll_bts.png) · [闭环结果](24AutoOpt_fig_6b/closed_loop.png)

来源：24AutoOpt.pdf, Fig. 6b, PDF p.11。

模型备注：UGV component only; B uncontrollable. One-way q8 -> q4 and q12 -> q0 retained.。

<!-- RUN-RESULTS: 24AutoOpt_fig_6b -->
### 运行结果与分析

- 判定：online **winning**，offline **winning**；完整离线结论一致。
- 预处理：Qd=∅；Qf=∅；Qe=`{q0, q1, q10, q11, q12, q2, q3, q4, q5, q6, q7, q8, q9}`。
- 深度：草稿阈值=0；最小可判定u=0；恢复offline根极大控制模式的最小u=0；实际采用u=0。
  深度经过逐例扫描标定；草稿阈值本身不等于普遍可解性保证。

| 结构指标 | Online LL-BTS | 传统 Offline BTS |
| --- | ---: | ---: |
| 构建D节点 | 1 | 13 |
| 构建O节点 | 0 | 208 |
| 构建边 | 0 | 472 |
| 全部保留D/O节点 | 1/0 | 13/172 |
| 所选闭环可达状态 | 13 | 13 |
| 所选闭环可达转移 | 32 | 32 |
| 所选控制器记忆状态 | 13 | 13 |

**为什么可解：** 初始估计已完全落在Qe中，允许全部事件即可安全延续。因此online可以在根估计处采用安全终端证书，停止枚举O节点。这不是原始plant只有一个状态；物理闭环仍按实际DFA状态和控制器记忆展开。
**实际控制行为：** 所有导出记忆状态的控制输出均允许全部事件，未禁用任何可控事件。保留的多个估计记忆不表示控制模式一定不同。

**传统BTS初始节点的模式去向（互斥分类）：** 共16个模式，其中UR含plant死锁0个；其余模式直接引入控制死锁8个；局部通过但因后续估计失败而剪除0个；最终保留8个。

| 实测成本 | Online | Offline | 绝对节约（Offline−Online） | 节约率 |
| --- | ---: | ---: | ---: | ---: |
| 总求解时间，含online预处理 / ms | 0.039300 | 1.258800 | 1.219500 | 96.878% |
| Python分配峰值 / KiB | 13.750 | 287.758 | 274.008 | 95.222% |

Online分项中位数：预处理0.034700 ms，求解0.004600 ms。总时间是每次预处理与求解相加后再取中位数，不能一般地把两个中位数直接相加。
运算：ΔT=(1.258800−0.039300) ms=1.219500 ms；时间节约率=ΔT/1.258800 ms=96.878%。
ΔM=294,664−14,080=280,584 bytes；内存节约率=ΔM/294,664=95.222%。
**成本解释：** 本例测得online总成本更低；收益同时包含窗口、Qf/Qe证书和提前拒绝坏模式。这是当前实现/模型的实测，不是对所有系统最坏复杂度下降的证明。

[Offline BTS数据](24AutoOpt_fig_6b/offline/bts.json) · [Offline闭环](24AutoOpt_fig_6b/closed_loop_system_offline.png) · [Offline supervisor](24AutoOpt_fig_6b/supervisor_offline.json) · [逐项测量](24AutoOpt_fig_6b/online_offline_comparison.json)
<!-- END-RUN-RESULTS: 24AutoOpt_fig_6b -->

### 修改意见（请填写）

<!-- USER-NOTES: 24AutoOpt_fig_6b -->
- 需要修改的状态或转移：
- 可观事件调整：
- 可控事件调整：
- 希望保留的闭环或预期行为：
- 其他意见：
<!-- END-USER-NOTES: 24AutoOpt_fig_6b -->

## 24AutoOpt_fig_6d

编号：44。类别：论文自动机。
原始状态数：4；转移数：8；初始状态：`q0`。
当前结果：`winning`；所选前视深度：`u=0`。

| 事件属性 | 集合 |
| --- | --- |
| 全部事件 Σ | `{Ebar, H, Wbar}` |
| 可观事件 Σo | `{Ebar, H, Wbar}` |
| 不可观事件 Σuo | ∅ |
| 可控事件 Σc | ∅ |
| 不可控事件 Σuc | `{Ebar, H, Wbar}` |

[原始系统图](24AutoOpt_fig_6d/plant.png) · [原始系统数据](24AutoOpt_fig_6d/plant.json) · [LL-BTS](24AutoOpt_fig_6d/ll_bts.png) · [闭环结果](24AutoOpt_fig_6d/closed_loop.png)

来源：24AutoOpt.pdf, Fig. 6d, PDF p.11。

模型备注：UAV component only; movement and hovering uncontrollable; overbars renamed.。

<!-- RUN-RESULTS: 24AutoOpt_fig_6d -->
### 运行结果与分析

- 判定：online **winning**，offline **winning**；完整离线结论一致。
- 预处理：Qd=∅；Qf=∅；Qe=`{q0, q6, q7, q8}`。
- 深度：草稿阈值=0；最小可判定u=0；恢复offline根极大控制模式的最小u=0；实际采用u=0。
  深度经过逐例扫描标定；草稿阈值本身不等于普遍可解性保证。

| 结构指标 | Online LL-BTS | 传统 Offline BTS |
| --- | ---: | ---: |
| 构建D节点 | 1 | 4 |
| 构建O节点 | 0 | 4 |
| 构建边 | 0 | 12 |
| 全部保留D/O节点 | 1/0 | 4/4 |
| 所选闭环可达状态 | 4 | 4 |
| 所选闭环可达转移 | 8 | 8 |
| 所选控制器记忆状态 | 4 | 4 |

**为什么可解：** 初始估计已完全落在Qe中，允许全部事件即可安全延续。因此online可以在根估计处采用安全终端证书，停止枚举O节点。这不是原始plant只有一个状态；物理闭环仍按实际DFA状态和控制器记忆展开。
**实际控制行为：** 所有导出记忆状态的控制输出均允许全部事件，未禁用任何可控事件。保留的多个估计记忆不表示控制模式一定不同。

**传统BTS初始节点的模式去向（互斥分类）：** 共1个模式，其中UR含plant死锁0个；其余模式直接引入控制死锁0个；局部通过但因后续估计失败而剪除0个；最终保留1个。

| 实测成本 | Online | Offline | 绝对节约（Offline−Online） | 节约率 |
| --- | ---: | ---: | ---: | ---: |
| 总求解时间，含online预处理 / ms | 0.013500 | 0.037300 | 0.023800 | 63.807% |
| Python分配峰值 / KiB | 5.930 | 12.609 | 6.680 | 52.974% |

Online分项中位数：预处理0.011000 ms，求解0.002500 ms。总时间是每次预处理与求解相加后再取中位数，不能一般地把两个中位数直接相加。
运算：ΔT=(0.037300−0.013500) ms=0.023800 ms；时间节约率=ΔT/0.037300 ms=63.807%。
ΔM=12,912−6,072=6,840 bytes；内存节约率=ΔM/12,912=52.974%。
**成本解释：** 本例测得online总成本更低；收益同时包含窗口、Qf/Qe证书和提前拒绝坏模式。这是当前实现/模型的实测，不是对所有系统最坏复杂度下降的证明。

[Offline BTS数据](24AutoOpt_fig_6d/offline/bts.json) · [Offline闭环](24AutoOpt_fig_6d/closed_loop_system_offline.png) · [Offline supervisor](24AutoOpt_fig_6d/supervisor_offline.json) · [逐项测量](24AutoOpt_fig_6d/online_offline_comparison.json)
<!-- END-RUN-RESULTS: 24AutoOpt_fig_6d -->

### 修改意见（请填写）

<!-- USER-NOTES: 24AutoOpt_fig_6d -->
- 需要修改的状态或转移：
- 可观事件调整：
- 可控事件调整：
- 希望保留的闭环或预期行为：
- 其他意见：
<!-- END-USER-NOTES: 24AutoOpt_fig_6d -->

## 21AutomaticaOptimal_fig_2

编号：45。类别：论文自动机。
原始状态数：15；转移数：24；初始状态：`x0`。
当前结果：`winning`；所选前视深度：`u=2`。

| 事件属性 | 集合 |
| --- | --- |
| 全部事件 Σ | `{a1, a2, a3, a4, b1, b2, c1, c2, c3, c4, c5, o1, o2, o3, o4}` |
| 可观事件 Σo | `{o1, o2, o3, o4}` |
| 不可观事件 Σuo | `{a1, a2, a3, a4, b1, b2, c1, c2, c3, c4, c5}` |
| 可控事件 Σc | `{c1, c2, c3, c4, c5}` |
| 不可控事件 Σuc | `{a1, a2, a3, a4, b1, b2, o1, o2, o3, o4}` |

[原始系统图](21AutomaticaOptimal_fig_2/plant.png) · [原始系统数据](21AutomaticaOptimal_fig_2/plant.json) · [LL-BTS](21AutomaticaOptimal_fig_2/ll_bts.png) · [闭环结果](21AutomaticaOptimal_fig_2/closed_loop.png)

来源：21AutomaticaOptimal.pdf, Fig. 2, PDF p.7。

模型备注：Mean payoff weights ignored; inherited Ec and Eo from Example 2, PDF p.7.。

<!-- RUN-RESULTS: 21AutomaticaOptimal_fig_2 -->
### 运行结果与分析

- 判定：online **winning**，offline **winning**；完整离线结论一致。
- 预处理：Qd=∅；Qf=∅；Qe=`{x0, x1, x10, x12, x13, x14, x15, x2, x3, x4, x5, x6, x7, x8, x9}`。
- 深度：草稿阈值=2；最小可判定u=0；恢复offline根极大控制模式的最小u=0；实际采用u=2。
  深度经过逐例扫描标定；草稿阈值本身不等于普遍可解性保证。

| 结构指标 | Online LL-BTS | 传统 Offline BTS |
| --- | ---: | ---: |
| 构建D节点 | 1 | 4 |
| 构建O节点 | 0 | 128 |
| 构建边 | 0 | 296 |
| 全部保留D/O节点 | 1/0 | 4/120 |
| 所选闭环可达状态 | 17 | 17 |
| 所选闭环可达转移 | 26 | 26 |
| 所选控制器记忆状态 | 4 | 4 |

**为什么可解：** 初始估计已完全落在Qe中，允许全部事件即可安全延续。因此online可以在根估计处采用安全终端证书，停止枚举O节点。这不是原始plant只有一个状态；物理闭环仍按实际DFA状态和控制器记忆展开。
**实际控制行为：** 所有导出记忆状态的控制输出均允许全部事件，未禁用任何可控事件。保留的多个估计记忆不表示控制模式一定不同。

**传统BTS初始节点的模式去向（互斥分类）：** 共32个模式，其中UR含plant死锁0个；其余模式直接引入控制死锁0个；局部通过但因后续估计失败而剪除0个；最终保留32个。

| 实测成本 | Online | Offline | 绝对节约（Offline−Online） | 节约率 |
| --- | ---: | ---: | ---: | ---: |
| 总求解时间，含online预处理 / ms | 0.049300 | 1.097400 | 1.048100 | 95.508% |
| Python分配峰值 / KiB | 15.359 | 192.461 | 177.102 | 92.019% |

Online分项中位数：预处理0.045000 ms，求解0.004300 ms。总时间是每次预处理与求解相加后再取中位数，不能一般地把两个中位数直接相加。
运算：ΔT=(1.097400−0.049300) ms=1.048100 ms；时间节约率=ΔT/1.097400 ms=95.508%。
ΔM=197,080−15,728=181,352 bytes；内存节约率=ΔM/197,080=92.019%。
**成本解释：** 本例测得online总成本更低；收益同时包含窗口、Qf/Qe证书和提前拒绝坏模式。这是当前实现/模型的实测，不是对所有系统最坏复杂度下降的证明。

[Offline BTS数据](21AutomaticaOptimal_fig_2/offline/bts.json) · [Offline闭环](21AutomaticaOptimal_fig_2/closed_loop_system_offline.png) · [Offline supervisor](21AutomaticaOptimal_fig_2/supervisor_offline.json) · [逐项测量](21AutomaticaOptimal_fig_2/online_offline_comparison.json)
<!-- END-RUN-RESULTS: 21AutomaticaOptimal_fig_2 -->

### 修改意见（请填写）

<!-- USER-NOTES: 21AutomaticaOptimal_fig_2 -->
- 需要修改的状态或转移：
- 可观事件调整：
- 可控事件调整：
- 希望保留的闭环或预期行为：
- 其他意见：
<!-- END-USER-NOTES: 21AutomaticaOptimal_fig_2 -->

## 20CDC2_fig_1a

编号：46。类别：论文自动机。
原始状态数：6；转移数：6；初始状态：`1`。
当前结果：`winning`；所选前视深度：`u=1`。

| 事件属性 | 集合 |
| --- | --- |
| 全部事件 Σ | `{a, b, c, d}` |
| 可观事件 Σo | `{a, b, d}` |
| 不可观事件 Σuo | `{c}` |
| 可控事件 Σc | `{c, d}` |
| 不可控事件 Σuc | `{a, b}` |

[原始系统图](20CDC2_fig_1a/plant.png) · [原始系统数据](20CDC2_fig_1a/plant.json) · [LL-BTS](20CDC2_fig_1a/ll_bts.png) · [闭环结果](20CDC2_fig_1a/closed_loop.png)

来源：20CDC2.pdf, Fig. 1a, PDF p.3。

模型备注：Nominal G. Attack models and safety objective are not simulated.。

<!-- RUN-RESULTS: 20CDC2_fig_1a -->
### 运行结果与分析

- 判定：online **winning**，offline **winning**；完整离线结论一致。
- 预处理：Qd=`{6}`；Qf=`{4, 5}`；Qe=`{3}`。
- 深度：草稿阈值=1；最小可判定u=1；恢复offline根极大控制模式的最小u=1；实际采用u=1。
  深度经过逐例扫描标定；草稿阈值本身不等于普遍可解性保证。

| 结构指标 | Online LL-BTS | 传统 Offline BTS |
| --- | ---: | ---: |
| 构建D节点 | 3 | 5 |
| 构建O节点 | 6 | 20 |
| 构建边 | 12 | 35 |
| 全部保留D/O节点 | 3/6 | 3/8 |
| 所选闭环可达状态 | 3 | 3 |
| 所选闭环可达转移 | 3 | 3 |
| 所选控制器记忆状态 | 3 | 3 |

**为什么可解：** 初始估计不能直接用Qe证书终止，但剪枝后仍有认证控制模式。所选supervisor在每个估计处固定选择一个保留模式，所有可能观测均有认证后续控制，并检查不可观测可达集中的每个实际状态都有可用事件。
**实际控制行为：** 不可控事件始终允许；下表列出选定online supervisor的控制输出。

| 记忆 | 估计 | 允许的可控事件 | 禁用的可控事件 |
| --- | --- | --- | --- |
| C0 | `{1}` | `{c, d}` | ∅ |
| C1 | `{2}` | `{d}` | `{c}` |
| C2 | `{3}` | `{c, d}` | ∅ |

**传统BTS初始节点的模式去向（互斥分类）：** 共4个模式，其中UR含plant死锁0个；其余模式直接引入控制死锁0个；局部通过但因后续估计失败而剪除0个；最终保留4个。

| 实测成本 | Online | Offline | 绝对节约（Offline−Online） | 节约率 |
| --- | ---: | ---: | ---: | ---: |
| 总求解时间，含online预处理 / ms | 0.085500 | 0.109000 | 0.023500 | 21.560% |
| Python分配峰值 / KiB | 16.664 | 32.445 | 15.781 | 48.640% |

Online分项中位数：预处理0.019700 ms，求解0.066100 ms。总时间是每次预处理与求解相加后再取中位数，不能一般地把两个中位数直接相加。
运算：ΔT=(0.109000−0.085500) ms=0.023500 ms；时间节约率=ΔT/0.109000 ms=21.560%。
ΔM=33,224−17,064=16,160 bytes；内存节约率=ΔM/33,224=48.640%。
**成本解释：** 本例测得online总成本更低；收益同时包含窗口、Qf/Qe证书和提前拒绝坏模式。这是当前实现/模型的实测，不是对所有系统最坏复杂度下降的证明。

[Offline BTS数据](20CDC2_fig_1a/offline/bts.json) · [Offline闭环](20CDC2_fig_1a/closed_loop_system_offline.png) · [Offline supervisor](20CDC2_fig_1a/supervisor_offline.json) · [逐项测量](20CDC2_fig_1a/online_offline_comparison.json)
<!-- END-RUN-RESULTS: 20CDC2_fig_1a -->

### 修改意见（请填写）

<!-- USER-NOTES: 20CDC2_fig_1a -->
- 需要修改的状态或转移：
- 可观事件调整：
- 可控事件调整：
- 希望保留的闭环或预期行为：
- 其他意见：
<!-- END-USER-NOTES: 20CDC2_fig_1a -->

## 20CDC2_fig_1b

编号：47。类别：论文自动机。
原始状态数：6；转移数：6；初始状态：`1`。
当前结果：`losing`；所选前视深度：`u=1`。

| 事件属性 | 集合 |
| --- | --- |
| 全部事件 Σ | `{a, b, c, c_attack, d}` |
| 可观事件 Σo | `{a, b, d}` |
| 不可观事件 Σuo | `{c, c_attack}` |
| 可控事件 Σc | `{c, d}` |
| 不可控事件 Σuc | `{a, b, c_attack}` |

[原始系统图](20CDC2_fig_1b/plant.png) · [原始系统数据](20CDC2_fig_1b/plant.json) · [LL-BTS](20CDC2_fig_1b/ll_bts.png) · [闭环结果](20CDC2_fig_1b/closed_loop.png)

来源：20CDC2.pdf, Fig. 1b, PDF p.3。

模型备注：Attacked G_a: c^a renamed c_attack, unobservable and uncontrollable; partition of nominal c,d inherited only for surviving nominal events.。

<!-- RUN-RESULTS: 20CDC2_fig_1b -->
### 运行结果与分析

- 判定：online **losing**，offline **losing**；完整离线结论一致。
- 预处理：Qd=`{6}`；Qf=`{4, 5}`；Qe=`{3}`。
- 深度：草稿阈值=1；最小可判定u=1；恢复offline根极大控制模式的最小u=1；实际采用u=1。
  深度经过逐例扫描标定；草稿阈值本身不等于普遍可解性保证。

| 结构指标 | Online LL-BTS | 传统 Offline BTS |
| --- | ---: | ---: |
| 构建D节点 | 2 | 5 |
| 构建O节点 | 4 | 20 |
| 构建边 | 8 | 36 |
| 全部保留D/O节点 | 0/0 | 1/2 |

**为什么不可解：** 完整已知系统的offline BTS也将初始决策节点剪除，因此这不是单纯u偏小造成的未判定；当前模型不存在满足本实验无死锁目标的supervisor。
未将空图或“不可解”提示图当成一个可行闭环，也未给终止状态补自环。

**传统BTS初始节点的模式去向（互斥分类）：** 共4个模式，其中UR含plant死锁0个；其余模式直接引入控制死锁0个；局部通过但因后续估计失败而剪除4个；最终保留0个。

| 实测成本 | Online | Offline | 绝对节约（Offline−Online） | 节约率 |
| --- | ---: | ---: | ---: | ---: |
| 总求解时间，含online预处理 / ms | 0.081100 | 0.112700 | 0.031600 | 28.039% |
| Python分配峰值 / KiB | 14.023 | 33.266 | 19.242 | 57.844% |

Online分项中位数：预处理0.018000 ms，求解0.062800 ms。总时间是每次预处理与求解相加后再取中位数，不能一般地把两个中位数直接相加。
运算：ΔT=(0.112700−0.081100) ms=0.031600 ms；时间节约率=ΔT/0.112700 ms=28.039%。
ΔM=34,064−14,360=19,704 bytes；内存节约率=ΔM/34,064=57.844%。
**成本解释：** 本例测得online总成本更低；收益同时包含窗口、Qf/Qe证书和提前拒绝坏模式。这是当前实现/模型的实测，不是对所有系统最坏复杂度下降的证明。

[Offline BTS数据](20CDC2_fig_1b/offline/bts.json) · [Offline闭环](20CDC2_fig_1b/closed_loop_system_offline.png) · [Offline supervisor](20CDC2_fig_1b/supervisor_offline.json) · [逐项测量](20CDC2_fig_1b/online_offline_comparison.json)
<!-- END-RUN-RESULTS: 20CDC2_fig_1b -->

### 修改意见（请填写）

<!-- USER-NOTES: 20CDC2_fig_1b -->
- 需要修改的状态或转移：
- 可观事件调整：
- 可控事件调整：
- 希望保留的闭环或预期行为：
- 其他意见：
<!-- END-USER-NOTES: 20CDC2_fig_1b -->

## 20CDC2_fig_2a

编号：48。类别：论文自动机。
原始状态数：13；转移数：12；初始状态：`1`。
当前结果：`losing`；所选前视深度：`u=2`。

| 事件属性 | 集合 |
| --- | --- |
| 全部事件 Σ | `{a, b, c, d, e}` |
| 可观事件 Σo | `{c}` |
| 不可观事件 Σuo | `{a, b, d, e}` |
| 可控事件 Σc | `{a, b, d, e}` |
| 不可控事件 Σuc | `{c}` |

[原始系统图](20CDC2_fig_2a/plant.png) · [原始系统数据](20CDC2_fig_2a/plant.json) · [LL-BTS](20CDC2_fig_2a/ll_bts.png) · [闭环结果](20CDC2_fig_2a/closed_loop.png)

来源：20CDC2.pdf, Fig. 2a, PDF p.6。

模型备注：All original terminal states retained; no implicit accepting-state loops.。

<!-- RUN-RESULTS: 20CDC2_fig_2a -->
### 运行结果与分析

- 判定：online **losing**，offline **losing**；完整离线结论一致。
- 预处理：Qd=`{10, 11, 13, 5}`；Qf=`{12, 3, 4, 7, 8, 9}`；Qe=∅。
- 深度：草稿阈值=2；最小可判定u=0；恢复offline根极大控制模式的最小u=0；实际采用u=2。
  深度经过逐例扫描标定；草稿阈值本身不等于普遍可解性保证。

| 结构指标 | Online LL-BTS | 传统 Offline BTS |
| --- | ---: | ---: |
| 构建D节点 | 1 | 2 |
| 构建O节点 | 0 | 32 |
| 构建边 | 0 | 40 |
| 全部保留D/O节点 | 0/0 | 0/0 |

**为什么不可解：** 完整已知系统的offline BTS也将初始决策节点剪除，因此这不是单纯u偏小造成的未判定；当前模型不存在满足本实验无死锁目标的supervisor。
从初始状态可达的原始图无环。有限无环系统的所有执行最终都到达无出边终点，仅通过禁用事件不能产生可持续运行的环。
未将空图或“不可解”提示图当成一个可行闭环，也未给终止状态补自环。

**传统BTS初始节点的模式去向（互斥分类）：** 共16个模式，其中UR含plant死锁4个；其余模式直接引入控制死锁8个；局部通过但因后续估计失败而剪除4个；最终保留0个。

| 实测成本 | Online | Offline | 绝对节约（Offline−Online） | 节约率 |
| --- | ---: | ---: | ---: | ---: |
| 总求解时间，含online预处理 / ms | 0.134100 | 0.213100 | 0.079000 | 37.072% |
| Python分配峰值 / KiB | 14.125 | 41.586 | 27.461 | 66.034% |

Online分项中位数：预处理0.034900 ms，求解0.093700 ms。总时间是每次预处理与求解相加后再取中位数，不能一般地把两个中位数直接相加。
运算：ΔT=(0.213100−0.134100) ms=0.079000 ms；时间节约率=ΔT/0.213100 ms=37.072%。
ΔM=42,584−14,464=28,120 bytes；内存节约率=ΔM/42,584=66.034%。
**成本解释：** 本例测得online总成本更低；收益同时包含窗口、Qf/Qe证书和提前拒绝坏模式。这是当前实现/模型的实测，不是对所有系统最坏复杂度下降的证明。

[Offline BTS数据](20CDC2_fig_2a/offline/bts.json) · [Offline闭环](20CDC2_fig_2a/closed_loop_system_offline.png) · [Offline supervisor](20CDC2_fig_2a/supervisor_offline.json) · [逐项测量](20CDC2_fig_2a/online_offline_comparison.json)
<!-- END-RUN-RESULTS: 20CDC2_fig_2a -->

### 修改意见（请填写）

<!-- USER-NOTES: 20CDC2_fig_2a -->
- 需要修改的状态或转移：
- 可观事件调整：
- 可控事件调整：
- 希望保留的闭环或预期行为：
- 其他意见：
<!-- END-USER-NOTES: 20CDC2_fig_2a -->

## 20CDC2_fig_2b

编号：49。类别：论文自动机。
原始状态数：7；转移数：6；初始状态：`1`。
当前结果：`losing`；所选前视深度：`u=2`。

| 事件属性 | 集合 |
| --- | --- |
| 全部事件 Σ | `{a, b, c, d, e}` |
| 可观事件 Σo | `{c}` |
| 不可观事件 Σuo | `{a, b, d, e}` |
| 可控事件 Σc | `{a, b, d, e}` |
| 不可控事件 Σuc | `{c}` |

[原始系统图](20CDC2_fig_2b/plant.png) · [原始系统数据](20CDC2_fig_2b/plant.json) · [LL-BTS](20CDC2_fig_2b/ll_bts.png) · [闭环结果](20CDC2_fig_2b/closed_loop.png)

来源：20CDC2.pdf, Fig. 2b, PDF p.6。

模型备注：Controlled language Sp/G used as standalone DFA.。

<!-- RUN-RESULTS: 20CDC2_fig_2b -->
### 运行结果与分析

- 判定：online **losing**，offline **losing**；完整离线结论一致。
- 预处理：Qd=`{10, 7}`；Qf=`{4, 6, 9}`；Qe=∅。
- 深度：草稿阈值=2；最小可判定u=0；恢复offline根极大控制模式的最小u=0；实际采用u=2。
  深度经过逐例扫描标定；草稿阈值本身不等于普遍可解性保证。

| 结构指标 | Online LL-BTS | 传统 Offline BTS |
| --- | ---: | ---: |
| 构建D节点 | 1 | 2 |
| 构建O节点 | 0 | 32 |
| 构建边 | 0 | 40 |
| 全部保留D/O节点 | 0/0 | 0/0 |

**为什么不可解：** 完整已知系统的offline BTS也将初始决策节点剪除，因此这不是单纯u偏小造成的未判定；当前模型不存在满足本实验无死锁目标的supervisor。
从初始状态可达的原始图无环。有限无环系统的所有执行最终都到达无出边终点，仅通过禁用事件不能产生可持续运行的环。
未将空图或“不可解”提示图当成一个可行闭环，也未给终止状态补自环。

**传统BTS初始节点的模式去向（互斥分类）：** 共16个模式，其中UR含plant死锁0个；其余模式直接引入控制死锁8个；局部通过但因后续估计失败而剪除8个；最终保留0个。

| 实测成本 | Online | Offline | 绝对节约（Offline−Online） | 节约率 |
| --- | ---: | ---: | ---: | ---: |
| 总求解时间，含online预处理 / ms | 0.219100 | 0.309800 | 0.090700 | 29.277% |
| Python分配峰值 / KiB | 10.875 | 38.836 | 27.961 | 71.998% |

Online分项中位数：预处理0.040000 ms，求解0.180800 ms。总时间是每次预处理与求解相加后再取中位数，不能一般地把两个中位数直接相加。
运算：ΔT=(0.309800−0.219100) ms=0.090700 ms；时间节约率=ΔT/0.309800 ms=29.277%。
ΔM=39,768−11,136=28,632 bytes；内存节约率=ΔM/39,768=71.998%。
**成本解释：** 本例测得online总成本更低；收益同时包含窗口、Qf/Qe证书和提前拒绝坏模式。这是当前实现/模型的实测，不是对所有系统最坏复杂度下降的证明。

[Offline BTS数据](20CDC2_fig_2b/offline/bts.json) · [Offline闭环](20CDC2_fig_2b/closed_loop_system_offline.png) · [Offline supervisor](20CDC2_fig_2b/supervisor_offline.json) · [逐项测量](20CDC2_fig_2b/online_offline_comparison.json)
<!-- END-RUN-RESULTS: 20CDC2_fig_2b -->

### 修改意见（请填写）

<!-- USER-NOTES: 20CDC2_fig_2b -->
- 需要修改的状态或转移：
- 可观事件调整：
- 可控事件调整：
- 希望保留的闭环或预期行为：
- 其他意见：
<!-- END-USER-NOTES: 20CDC2_fig_2b -->

## 20IFAC1_fig_1

编号：50。类别：论文自动机。
原始状态数：6；转移数：9；初始状态：`0`。
当前结果：`losing`；所选前视深度：`u=2`。

| 事件属性 | 集合 |
| --- | --- |
| 全部事件 Σ | `{c1, c2, o1, o2, o3}` |
| 可观事件 Σo | `{o1, o2, o3}` |
| 不可观事件 Σuo | `{c1, c2}` |
| 可控事件 Σc | `{c1, c2}` |
| 不可控事件 Σuc | `{o1, o2, o3}` |

[原始系统图](20IFAC1_fig_1/plant.png) · [原始系统数据](20IFAC1_fig_1/plant.json) · [LL-BTS](20IFAC1_fig_1/ll_bts.png) · [闭环结果](20IFAC1_fig_1/closed_loop.png)

来源：20IFAC1.pdf, Fig. 1, PDF p.2。

模型备注：Original six-state opacity example; terminal 5,6 retained. Number 4 absent.。

<!-- RUN-RESULTS: 20IFAC1_fig_1 -->
### 运行结果与分析

- 判定：online **losing**，offline **losing**；完整离线结论一致。
- 预处理：Qd=`{5, 6}`；Qf=`{2}`；Qe=∅。
- 深度：草稿阈值=2；最小可判定u=2；恢复offline根极大控制模式的最小u=2；实际采用u=2。
  深度经过逐例扫描标定；草稿阈值本身不等于普遍可解性保证。

| 结构指标 | Online LL-BTS | 传统 Offline BTS |
| --- | ---: | ---: |
| 构建D节点 | 3 | 4 |
| 构建O节点 | 2 | 16 |
| 构建边 | 6 | 23 |
| 全部保留D/O节点 | 0/0 | 0/0 |

**为什么不可解：** 完整已知系统的offline BTS也将初始决策节点剪除，因此这不是单纯u偏小造成的未判定；当前模型不存在满足本实验无死锁目标的supervisor。
从初始状态可达的原始图无环。有限无环系统的所有执行最终都到达无出边终点，仅通过禁用事件不能产生可持续运行的环。
未将空图或“不可解”提示图当成一个可行闭环，也未给终止状态补自环。

**传统BTS初始节点的模式去向（互斥分类）：** 共4个模式，其中UR含plant死锁0个；其余模式直接引入控制死锁1个；局部通过但因后续估计失败而剪除3个；最终保留0个。

| 实测成本 | Online | Offline | 绝对节约（Offline−Online） | 节约率 |
| --- | ---: | ---: | ---: | ---: |
| 总求解时间，含online预处理 / ms | 0.088600 | 0.105600 | 0.017000 | 16.098% |
| Python分配峰值 / KiB | 13.445 | 22.859 | 9.414 | 41.183% |

Online分项中位数：预处理0.023400 ms，求解0.065200 ms。总时间是每次预处理与求解相加后再取中位数，不能一般地把两个中位数直接相加。
运算：ΔT=(0.105600−0.088600) ms=0.017000 ms；时间节约率=ΔT/0.105600 ms=16.098%。
ΔM=23,408−13,768=9,640 bytes；内存节约率=ΔM/23,408=41.183%。
**成本解释：** 本例测得online总成本更低；收益同时包含窗口、Qf/Qe证书和提前拒绝坏模式。这是当前实现/模型的实测，不是对所有系统最坏复杂度下降的证明。

[Offline BTS数据](20IFAC1_fig_1/offline/bts.json) · [Offline闭环](20IFAC1_fig_1/closed_loop_system_offline.png) · [Offline supervisor](20IFAC1_fig_1/supervisor_offline.json) · [逐项测量](20IFAC1_fig_1/online_offline_comparison.json)
<!-- END-RUN-RESULTS: 20IFAC1_fig_1 -->

### 修改意见（请填写）

<!-- USER-NOTES: 20IFAC1_fig_1 -->
- 需要修改的状态或转移：
- 可观事件调整：
- 可控事件调整：
- 希望保留的闭环或预期行为：
- 其他意见：
<!-- END-USER-NOTES: 20IFAC1_fig_1 -->

## 16SEI_fig_1a

编号：51。类别：论文自动机。
原始状态数：9；转移数：8；初始状态：`1`。
当前结果：`losing`；所选前视深度：`u=1`。

| 事件属性 | 集合 |
| --- | --- |
| 全部事件 Σ | `{a, b, c, o}` |
| 可观事件 Σo | `{a, b, c, o}` |
| 不可观事件 Σuo | ∅ |
| 可控事件 Σc | `{c}` |
| 不可控事件 Σuc | `{a, b, o}` |

[原始系统图](16SEI_fig_1a/plant.png) · [原始系统数据](16SEI_fig_1a/plant.json) · [LL-BTS](16SEI_fig_1a/ll_bts.png) · [闭环结果](16SEI_fig_1a/closed_loop.png)

来源：16SEI.pdf, Fig. 1a, PDF p.3。

模型备注：Centralized union of local partitions: Sigma_c={c}, Sigma_o={a,b,o,c}; not a decentralized-control reproduction. Terminal states retained.。

<!-- RUN-RESULTS: 16SEI_fig_1a -->
### 运行结果与分析

- 判定：online **losing**，offline **losing**；完整离线结论一致。
- 预处理：Qd=`{7, 8, 9}`；Qf=`{2, 3, 4, 5, 6}`；Qe=∅。
- 深度：草稿阈值=0；最小可判定u=1；恢复offline根极大控制模式的最小u=1；实际采用u=1。
  深度经过逐例扫描标定；草稿阈值本身不等于普遍可解性保证。

| 结构指标 | Online LL-BTS | 传统 Offline BTS |
| --- | ---: | ---: |
| 构建D节点 | 4 | 9 |
| 构建O节点 | 2 | 18 |
| 构建边 | 8 | 31 |
| 全部保留D/O节点 | 0/0 | 0/0 |

**为什么不可解：** 完整已知系统的offline BTS也将初始决策节点剪除，因此这不是单纯u偏小造成的未判定；当前模型不存在满足本实验无死锁目标的supervisor。
从初始状态可达的原始图无环。有限无环系统的所有执行最终都到达无出边终点，仅通过禁用事件不能产生可持续运行的环。
未将空图或“不可解”提示图当成一个可行闭环，也未给终止状态补自环。

**传统BTS初始节点的模式去向（互斥分类）：** 共2个模式，其中UR含plant死锁0个；其余模式直接引入控制死锁0个；局部通过但因后续估计失败而剪除2个；最终保留0个。

| 实测成本 | Online | Offline | 绝对节约（Offline−Online） | 节约率 |
| --- | ---: | ---: | ---: | ---: |
| 总求解时间，含online预处理 / ms | 0.083800 | 0.129900 | 0.046100 | 35.489% |
| Python分配峰值 / KiB | 13.500 | 29.156 | 15.656 | 53.698% |

Online分项中位数：预处理0.027000 ms，求解0.056000 ms。总时间是每次预处理与求解相加后再取中位数，不能一般地把两个中位数直接相加。
运算：ΔT=(0.129900−0.083800) ms=0.046100 ms；时间节约率=ΔT/0.129900 ms=35.489%。
ΔM=29,856−13,824=16,032 bytes；内存节约率=ΔM/29,856=53.698%。
**成本解释：** 本例测得online总成本更低；收益同时包含窗口、Qf/Qe证书和提前拒绝坏模式。这是当前实现/模型的实测，不是对所有系统最坏复杂度下降的证明。

[Offline BTS数据](16SEI_fig_1a/offline/bts.json) · [Offline闭环](16SEI_fig_1a/closed_loop_system_offline.png) · [Offline supervisor](16SEI_fig_1a/supervisor_offline.json) · [逐项测量](16SEI_fig_1a/online_offline_comparison.json)
<!-- END-RUN-RESULTS: 16SEI_fig_1a -->

### 修改意见（请填写）

<!-- USER-NOTES: 16SEI_fig_1a -->
- 需要修改的状态或转移：
- 可观事件调整：
- 可控事件调整：
- 希望保留的闭环或预期行为：
- 其他意见：
<!-- END-USER-NOTES: 16SEI_fig_1a -->

## 16SEI_fig_1b

编号：52。类别：论文自动机。
原始状态数：7；转移数：6；初始状态：`1`。
当前结果：`losing`；所选前视深度：`u=1`。

| 事件属性 | 集合 |
| --- | --- |
| 全部事件 Σ | `{a, b, c, o}` |
| 可观事件 Σo | `{a, b, c, o}` |
| 不可观事件 Σuo | ∅ |
| 可控事件 Σc | `{c}` |
| 不可控事件 Σuc | `{a, b, o}` |

[原始系统图](16SEI_fig_1b/plant.png) · [原始系统数据](16SEI_fig_1b/plant.json) · [LL-BTS](16SEI_fig_1b/ll_bts.png) · [闭环结果](16SEI_fig_1b/closed_loop.png)

来源：16SEI.pdf, Fig. 1b, PDF p.3。

模型备注：Centralized union of local partitions: Sigma_c={c}, Sigma_o={a,b,o,c}; not a decentralized-control reproduction. Terminal states retained.。

<!-- RUN-RESULTS: 16SEI_fig_1b -->
### 运行结果与分析

- 判定：online **losing**，offline **losing**；完整离线结论一致。
- 预处理：Qd=`{4, 6, 8}`；Qf=`{2, 3, 5}`；Qe=∅。
- 深度：草稿阈值=0；最小可判定u=1；恢复offline根极大控制模式的最小u=1；实际采用u=1。
  深度经过逐例扫描标定；草稿阈值本身不等于普遍可解性保证。

| 结构指标 | Online LL-BTS | 传统 Offline BTS |
| --- | ---: | ---: |
| 构建D节点 | 4 | 7 |
| 构建O节点 | 2 | 14 |
| 构建边 | 8 | 25 |
| 全部保留D/O节点 | 0/0 | 0/0 |

**为什么不可解：** 完整已知系统的offline BTS也将初始决策节点剪除，因此这不是单纯u偏小造成的未判定；当前模型不存在满足本实验无死锁目标的supervisor。
从初始状态可达的原始图无环。有限无环系统的所有执行最终都到达无出边终点，仅通过禁用事件不能产生可持续运行的环。
未将空图或“不可解”提示图当成一个可行闭环，也未给终止状态补自环。

**传统BTS初始节点的模式去向（互斥分类）：** 共2个模式，其中UR含plant死锁0个；其余模式直接引入控制死锁0个；局部通过但因后续估计失败而剪除2个；最终保留0个。

| 实测成本 | Online | Offline | 绝对节约（Offline−Online） | 节约率 |
| --- | ---: | ---: | ---: | ---: |
| 总求解时间，含online预处理 / ms | 0.087200 | 0.125900 | 0.038700 | 30.739% |
| Python分配峰值 / KiB | 12.750 | 25.109 | 12.359 | 49.222% |

Online分项中位数：预处理0.024000 ms，求解0.060400 ms。总时间是每次预处理与求解相加后再取中位数，不能一般地把两个中位数直接相加。
运算：ΔT=(0.125900−0.087200) ms=0.038700 ms；时间节约率=ΔT/0.125900 ms=30.739%。
ΔM=25,712−13,056=12,656 bytes；内存节约率=ΔM/25,712=49.222%。
**成本解释：** 本例测得online总成本更低；收益同时包含窗口、Qf/Qe证书和提前拒绝坏模式。这是当前实现/模型的实测，不是对所有系统最坏复杂度下降的证明。

[Offline BTS数据](16SEI_fig_1b/offline/bts.json) · [Offline闭环](16SEI_fig_1b/closed_loop_system_offline.png) · [Offline supervisor](16SEI_fig_1b/supervisor_offline.json) · [逐项测量](16SEI_fig_1b/online_offline_comparison.json)
<!-- END-RUN-RESULTS: 16SEI_fig_1b -->

### 修改意见（请填写）

<!-- USER-NOTES: 16SEI_fig_1b -->
- 需要修改的状态或转移：
- 可观事件调整：
- 可控事件调整：
- 希望保留的闭环或预期行为：
- 其他意见：
<!-- END-USER-NOTES: 16SEI_fig_1b -->

## 16SEI_fig_4a

编号：53。类别：论文自动机。
原始状态数：12；转移数：11；初始状态：`1`。
当前结果：`losing`；所选前视深度：`u=1`。

| 事件属性 | 集合 |
| --- | --- |
| 全部事件 Σ | `{a, b, c, o}` |
| 可观事件 Σo | `{a, b, c, o}` |
| 不可观事件 Σuo | ∅ |
| 可控事件 Σc | `{c}` |
| 不可控事件 Σuc | `{a, b, o}` |

[原始系统图](16SEI_fig_4a/plant.png) · [原始系统数据](16SEI_fig_4a/plant.json) · [LL-BTS](16SEI_fig_4a/ll_bts.png) · [闭环结果](16SEI_fig_4a/closed_loop.png)

来源：16SEI.pdf, Fig. 4a, PDF p.6。

模型备注：Centralized union of local partitions: Sigma_c={c}, Sigma_o={a,b,o,c}; not a decentralized-control reproduction. Terminal states retained.。

<!-- RUN-RESULTS: 16SEI_fig_4a -->
### 运行结果与分析

- 判定：online **losing**，offline **losing**；完整离线结论一致。
- 预处理：Qd=`{10, 11, 12, 9}`；Qf=`{3, 4, 5, 6, 7, 8}`；Qe=∅。
- 深度：草稿阈值=0；最小可判定u=1；恢复offline根极大控制模式的最小u=1；实际采用u=1。
  深度经过逐例扫描标定；草稿阈值本身不等于普遍可解性保证。

| 结构指标 | Online LL-BTS | 传统 Offline BTS |
| --- | ---: | ---: |
| 构建D节点 | 4 | 12 |
| 构建O节点 | 2 | 24 |
| 构建边 | 8 | 42 |
| 全部保留D/O节点 | 0/0 | 0/0 |

**为什么不可解：** 完整已知系统的offline BTS也将初始决策节点剪除，因此这不是单纯u偏小造成的未判定；当前模型不存在满足本实验无死锁目标的supervisor。
从初始状态可达的原始图无环。有限无环系统的所有执行最终都到达无出边终点，仅通过禁用事件不能产生可持续运行的环。
未将空图或“不可解”提示图当成一个可行闭环，也未给终止状态补自环。

**传统BTS初始节点的模式去向（互斥分类）：** 共2个模式，其中UR含plant死锁0个；其余模式直接引入控制死锁0个；局部通过但因后续估计失败而剪除2个；最终保留0个。

| 实测成本 | Online | Offline | 绝对节约（Offline−Online） | 节约率 |
| --- | ---: | ---: | ---: | ---: |
| 总求解时间，含online预处理 / ms | 0.098200 | 0.173100 | 0.074900 | 43.270% |
| Python分配峰值 / KiB | 15.234 | 41.617 | 26.383 | 63.394% |

Online分项中位数：预处理0.031100 ms，求解0.067100 ms。总时间是每次预处理与求解相加后再取中位数，不能一般地把两个中位数直接相加。
运算：ΔT=(0.173100−0.098200) ms=0.074900 ms；时间节约率=ΔT/0.173100 ms=43.270%。
ΔM=42,616−15,600=27,016 bytes；内存节约率=ΔM/42,616=63.394%。
**成本解释：** 本例测得online总成本更低；收益同时包含窗口、Qf/Qe证书和提前拒绝坏模式。这是当前实现/模型的实测，不是对所有系统最坏复杂度下降的证明。

[Offline BTS数据](16SEI_fig_4a/offline/bts.json) · [Offline闭环](16SEI_fig_4a/closed_loop_system_offline.png) · [Offline supervisor](16SEI_fig_4a/supervisor_offline.json) · [逐项测量](16SEI_fig_4a/online_offline_comparison.json)
<!-- END-RUN-RESULTS: 16SEI_fig_4a -->

### 修改意见（请填写）

<!-- USER-NOTES: 16SEI_fig_4a -->
- 需要修改的状态或转移：
- 可观事件调整：
- 可控事件调整：
- 希望保留的闭环或预期行为：
- 其他意见：
<!-- END-USER-NOTES: 16SEI_fig_4a -->

## 16SEI_fig_4b

编号：54。类别：论文自动机。
原始状态数：10；转移数：9；初始状态：`1`。
当前结果：`losing`；所选前视深度：`u=1`。

| 事件属性 | 集合 |
| --- | --- |
| 全部事件 Σ | `{a, b, c, o}` |
| 可观事件 Σo | `{a, b, c, o}` |
| 不可观事件 Σuo | ∅ |
| 可控事件 Σc | `{c}` |
| 不可控事件 Σuc | `{a, b, o}` |

[原始系统图](16SEI_fig_4b/plant.png) · [原始系统数据](16SEI_fig_4b/plant.json) · [LL-BTS](16SEI_fig_4b/ll_bts.png) · [闭环结果](16SEI_fig_4b/closed_loop.png)

来源：16SEI.pdf, Fig. 4b, PDF p.6。

模型备注：Centralized union of local partitions: Sigma_c={c}, Sigma_o={a,b,o,c}; not a decentralized-control reproduction. Terminal states retained.。

<!-- RUN-RESULTS: 16SEI_fig_4b -->
### 运行结果与分析

- 判定：online **losing**，offline **losing**；完整离线结论一致。
- 预处理：Qd=`{10, 5, 8, 9}`；Qf=`{3, 4, 6, 7}`；Qe=∅。
- 深度：草稿阈值=0；最小可判定u=1；恢复offline根极大控制模式的最小u=1；实际采用u=1。
  深度经过逐例扫描标定；草稿阈值本身不等于普遍可解性保证。

| 结构指标 | Online LL-BTS | 传统 Offline BTS |
| --- | ---: | ---: |
| 构建D节点 | 4 | 10 |
| 构建O节点 | 2 | 20 |
| 构建边 | 8 | 36 |
| 全部保留D/O节点 | 0/0 | 0/0 |

**为什么不可解：** 完整已知系统的offline BTS也将初始决策节点剪除，因此这不是单纯u偏小造成的未判定；当前模型不存在满足本实验无死锁目标的supervisor。
从初始状态可达的原始图无环。有限无环系统的所有执行最终都到达无出边终点，仅通过禁用事件不能产生可持续运行的环。
未将空图或“不可解”提示图当成一个可行闭环，也未给终止状态补自环。

**传统BTS初始节点的模式去向（互斥分类）：** 共2个模式，其中UR含plant死锁0个；其余模式直接引入控制死锁0个；局部通过但因后续估计失败而剪除2个；最终保留0个。

| 实测成本 | Online | Offline | 绝对节约（Offline−Online） | 节约率 |
| --- | ---: | ---: | ---: | ---: |
| 总求解时间，含online预处理 / ms | 0.106600 | 0.173300 | 0.066700 | 38.488% |
| Python分配峰值 / KiB | 14.734 | 36.477 | 21.742 | 59.606% |

Online分项中位数：预处理0.031900 ms，求解0.071200 ms。总时间是每次预处理与求解相加后再取中位数，不能一般地把两个中位数直接相加。
运算：ΔT=(0.173300−0.106600) ms=0.066700 ms；时间节约率=ΔT/0.173300 ms=38.488%。
ΔM=37,352−15,088=22,264 bytes；内存节约率=ΔM/37,352=59.606%。
**成本解释：** 本例测得online总成本更低；收益同时包含窗口、Qf/Qe证书和提前拒绝坏模式。这是当前实现/模型的实测，不是对所有系统最坏复杂度下降的证明。

[Offline BTS数据](16SEI_fig_4b/offline/bts.json) · [Offline闭环](16SEI_fig_4b/closed_loop_system_offline.png) · [Offline supervisor](16SEI_fig_4b/supervisor_offline.json) · [逐项测量](16SEI_fig_4b/online_offline_comparison.json)
<!-- END-RUN-RESULTS: 16SEI_fig_4b -->

### 修改意见（请填写）

<!-- USER-NOTES: 16SEI_fig_4b -->
- 需要修改的状态或转移：
- 可观事件调整：
- 可控事件调整：
- 希望保留的闭环或预期行为：
- 其他意见：
<!-- END-USER-NOTES: 16SEI_fig_4b -->

## 17AutomaticaTW_fig_1a

编号：55。类别：论文自动机。
原始状态数：6；转移数：7；初始状态：`0`。
当前结果：`winning`；所选前视深度：`u=1`。

| 事件属性 | 集合 |
| --- | --- |
| 全部事件 Σ | `{a, b, u1, u2}` |
| 可观事件 Σo | `{a, b}` |
| 不可观事件 Σuo | `{u1, u2}` |
| 可控事件 Σc | `{a, b, u1, u2}` |
| 不可控事件 Σuc | ∅ |

[原始系统图](17AutomaticaTW_fig_1a/plant.png) · [原始系统数据](17AutomaticaTW_fig_1a/plant.json) · [LL-BTS](17AutomaticaTW_fig_1a/ll_bts.png) · [闭环结果](17AutomaticaTW_fig_1a/closed_loop.png)

来源：17AutomaticaTW.pdf, Fig. 1a, PDF p.3。

模型备注：Verification source has no control partition. For this deadlock-free test only, all events are declared controllable; observation partition and transitions are inherited. No claim of source control reproduction.。

<!-- RUN-RESULTS: 17AutomaticaTW_fig_1a -->
### 运行结果与分析

- 判定：online **winning**，offline **winning**；完整离线结论一致。
- 预处理：Qd=∅；Qf=∅；Qe=`{0, 1, 2, 3, 4, 5}`。
- 深度：草稿阈值=1；最小可判定u=0；恢复offline根极大控制模式的最小u=0；实际采用u=1。
  深度经过逐例扫描标定；草稿阈值本身不等于普遍可解性保证。

| 结构指标 | Online LL-BTS | 传统 Offline BTS |
| --- | ---: | ---: |
| 构建D节点 | 1 | 5 |
| 构建O节点 | 0 | 80 |
| 构建边 | 0 | 126 |
| 全部保留D/O节点 | 1/0 | 5/34 |
| 所选闭环可达状态 | 6 | 6 |
| 所选闭环可达转移 | 7 | 7 |
| 所选控制器记忆状态 | 3 | 3 |

**为什么可解：** 初始估计已完全落在Qe中，允许全部事件即可安全延续。因此online可以在根估计处采用安全终端证书，停止枚举O节点。这不是原始plant只有一个状态；物理闭环仍按实际DFA状态和控制器记忆展开。
**实际控制行为：** 所有导出记忆状态的控制输出均允许全部事件，未禁用任何可控事件。保留的多个估计记忆不表示控制模式一定不同。

**传统BTS初始节点的模式去向（互斥分类）：** 共16个模式，其中UR含plant死锁0个；其余模式直接引入控制死锁10个；局部通过但因后续估计失败而剪除0个；最终保留6个。

| 实测成本 | Online | Offline | 绝对节约（Offline−Online） | 节约率 |
| --- | ---: | ---: | ---: | ---: |
| 总求解时间，含online预处理 / ms | 0.026100 | 0.422700 | 0.396600 | 93.825% |
| Python分配峰值 / KiB | 7.664 | 101.086 | 93.422 | 92.418% |

Online分项中位数：预处理0.022100 ms，求解0.004000 ms。总时间是每次预处理与求解相加后再取中位数，不能一般地把两个中位数直接相加。
运算：ΔT=(0.422700−0.026100) ms=0.396600 ms；时间节约率=ΔT/0.422700 ms=93.825%。
ΔM=103,512−7,848=95,664 bytes；内存节约率=ΔM/103,512=92.418%。
**成本解释：** 本例测得online总成本更低；收益同时包含窗口、Qf/Qe证书和提前拒绝坏模式。这是当前实现/模型的实测，不是对所有系统最坏复杂度下降的证明。

[Offline BTS数据](17AutomaticaTW_fig_1a/offline/bts.json) · [Offline闭环](17AutomaticaTW_fig_1a/closed_loop_system_offline.png) · [Offline supervisor](17AutomaticaTW_fig_1a/supervisor_offline.json) · [逐项测量](17AutomaticaTW_fig_1a/online_offline_comparison.json)
<!-- END-RUN-RESULTS: 17AutomaticaTW_fig_1a -->

### 修改意见（请填写）

<!-- USER-NOTES: 17AutomaticaTW_fig_1a -->
- 需要修改的状态或转移：
- 可观事件调整：
- 可控事件调整：
- 希望保留的闭环或预期行为：
- 其他意见：
<!-- END-USER-NOTES: 17AutomaticaTW_fig_1a -->

## 23TACsecure_fig_2a

编号：56。类别：论文自动机。
原始状态数：8；转移数：9；初始状态：`0`。
当前结果：`winning`；所选前视深度：`u=1`。

| 事件属性 | 集合 |
| --- | --- |
| 全部事件 Σ | `{a, b, c, u}` |
| 可观事件 Σo | `{a, b, c}` |
| 不可观事件 Σuo | `{u}` |
| 可控事件 Σc | `{a, b, c, u}` |
| 不可控事件 Σuc | ∅ |

[原始系统图](23TACsecure_fig_2a/plant.png) · [原始系统数据](23TACsecure_fig_2a/plant.json) · [LL-BTS](23TACsecure_fig_2a/ll_bts.png) · [闭环结果](23TACsecure_fig_2a/closed_loop.png)

来源：23TACsecure.pdf, Fig. 2a, PDF p.3。

模型备注：Verification source has no control partition. For this deadlock-free test only, all events are declared controllable; observation partition and transitions are inherited. No claim of source control reproduction.。

<!-- RUN-RESULTS: 23TACsecure_fig_2a -->
### 运行结果与分析

- 判定：online **winning**，offline **winning**；完整离线结论一致。
- 预处理：Qd=∅；Qf=∅；Qe=`{0, 1, 2, 3, 4, 5, 6, 7}`。
- 深度：草稿阈值=1；最小可判定u=0；恢复offline根极大控制模式的最小u=0；实际采用u=1。
  深度经过逐例扫描标定；草稿阈值本身不等于普遍可解性保证。

| 结构指标 | Online LL-BTS | 传统 Offline BTS |
| --- | ---: | ---: |
| 构建D节点 | 1 | 7 |
| 构建O节点 | 0 | 112 |
| 构建边 | 0 | 176 |
| 全部保留D/O节点 | 1/0 | 7/52 |
| 所选闭环可达状态 | 9 | 9 |
| 所选闭环可达转移 | 10 | 10 |
| 所选控制器记忆状态 | 5 | 5 |

**为什么可解：** 初始估计已完全落在Qe中，允许全部事件即可安全延续。因此online可以在根估计处采用安全终端证书，停止枚举O节点。这不是原始plant只有一个状态；物理闭环仍按实际DFA状态和控制器记忆展开。
**实际控制行为：** 所有导出记忆状态的控制输出均允许全部事件，未禁用任何可控事件。保留的多个估计记忆不表示控制模式一定不同。

**传统BTS初始节点的模式去向（互斥分类）：** 共16个模式，其中UR含plant死锁0个；其余模式直接引入控制死锁8个；局部通过但因后续估计失败而剪除0个；最终保留8个。

| 实测成本 | Online | Offline | 绝对节约（Offline−Online） | 节约率 |
| --- | ---: | ---: | ---: | ---: |
| 总求解时间，含online预处理 / ms | 0.030400 | 0.626500 | 0.596100 | 95.148% |
| Python分配峰值 / KiB | 9.703 | 131.461 | 121.758 | 92.619% |

Online分项中位数：预处理0.026000 ms，求解0.003900 ms。总时间是每次预处理与求解相加后再取中位数，不能一般地把两个中位数直接相加。
运算：ΔT=(0.626500−0.030400) ms=0.596100 ms；时间节约率=ΔT/0.626500 ms=95.148%。
ΔM=134,616−9,936=124,680 bytes；内存节约率=ΔM/134,616=92.619%。
**成本解释：** 本例测得online总成本更低；收益同时包含窗口、Qf/Qe证书和提前拒绝坏模式。这是当前实现/模型的实测，不是对所有系统最坏复杂度下降的证明。

[Offline BTS数据](23TACsecure_fig_2a/offline/bts.json) · [Offline闭环](23TACsecure_fig_2a/closed_loop_system_offline.png) · [Offline supervisor](23TACsecure_fig_2a/supervisor_offline.json) · [逐项测量](23TACsecure_fig_2a/online_offline_comparison.json)
<!-- END-RUN-RESULTS: 23TACsecure_fig_2a -->

### 修改意见（请填写）

<!-- USER-NOTES: 23TACsecure_fig_2a -->
- 需要修改的状态或转移：
- 可观事件调整：
- 可控事件调整：
- 希望保留的闭环或预期行为：
- 其他意见：
<!-- END-USER-NOTES: 23TACsecure_fig_2a -->

## 23TACsecure_fig_2b

编号：57。类别：论文自动机。
原始状态数：8；转移数：11；初始状态：`0`。
当前结果：`winning`；所选前视深度：`u=1`。

| 事件属性 | 集合 |
| --- | --- |
| 全部事件 Σ | `{a, b, c, u}` |
| 可观事件 Σo | `{a, b, c}` |
| 不可观事件 Σuo | `{u}` |
| 可控事件 Σc | `{a, b, c, u}` |
| 不可控事件 Σuc | ∅ |

[原始系统图](23TACsecure_fig_2b/plant.png) · [原始系统数据](23TACsecure_fig_2b/plant.json) · [LL-BTS](23TACsecure_fig_2b/ll_bts.png) · [闭环结果](23TACsecure_fig_2b/closed_loop.png)

来源：23TACsecure.pdf, Fig. 2b, PDF p.3。

模型备注：Verification source has no control partition. For this deadlock-free test only, all events are declared controllable; observation partition and transitions are inherited. No claim of source control reproduction.。

<!-- RUN-RESULTS: 23TACsecure_fig_2b -->
### 运行结果与分析

- 判定：online **winning**，offline **winning**；完整离线结论一致。
- 预处理：Qd=∅；Qf=∅；Qe=`{0, 1, 2, 3, 4, 5, 6, 7}`。
- 深度：草稿阈值=1；最小可判定u=0；恢复offline根极大控制模式的最小u=0；实际采用u=1。
  深度经过逐例扫描标定；草稿阈值本身不等于普遍可解性保证。

| 结构指标 | Online LL-BTS | 传统 Offline BTS |
| --- | ---: | ---: |
| 构建D节点 | 1 | 9 |
| 构建O节点 | 0 | 144 |
| 构建边 | 0 | 240 |
| 全部保留D/O节点 | 1/0 | 9/68 |
| 所选闭环可达状态 | 13 | 13 |
| 所选闭环可达转移 | 16 | 16 |
| 所选控制器记忆状态 | 8 | 8 |

**为什么可解：** 初始估计已完全落在Qe中，允许全部事件即可安全延续。因此online可以在根估计处采用安全终端证书，停止枚举O节点。这不是原始plant只有一个状态；物理闭环仍按实际DFA状态和控制器记忆展开。
**实际控制行为：** 所有导出记忆状态的控制输出均允许全部事件，未禁用任何可控事件。保留的多个估计记忆不表示控制模式一定不同。

**传统BTS初始节点的模式去向（互斥分类）：** 共16个模式，其中UR含plant死锁0个；其余模式直接引入控制死锁4个；局部通过但因后续估计失败而剪除0个；最终保留12个。

| 实测成本 | Online | Offline | 绝对节约（Offline−Online） | 节约率 |
| --- | ---: | ---: | ---: | ---: |
| 总求解时间，含online预处理 / ms | 0.031100 | 0.725500 | 0.694400 | 95.713% |
| Python分配峰值 / KiB | 9.703 | 172.891 | 163.188 | 94.388% |

Online分项中位数：预处理0.026300 ms，求解0.004000 ms。总时间是每次预处理与求解相加后再取中位数，不能一般地把两个中位数直接相加。
运算：ΔT=(0.725500−0.031100) ms=0.694400 ms；时间节约率=ΔT/0.725500 ms=95.713%。
ΔM=177,040−9,936=167,104 bytes；内存节约率=ΔM/177,040=94.388%。
**成本解释：** 本例测得online总成本更低；收益同时包含窗口、Qf/Qe证书和提前拒绝坏模式。这是当前实现/模型的实测，不是对所有系统最坏复杂度下降的证明。

[Offline BTS数据](23TACsecure_fig_2b/offline/bts.json) · [Offline闭环](23TACsecure_fig_2b/closed_loop_system_offline.png) · [Offline supervisor](23TACsecure_fig_2b/supervisor_offline.json) · [逐项测量](23TACsecure_fig_2b/online_offline_comparison.json)
<!-- END-RUN-RESULTS: 23TACsecure_fig_2b -->

### 修改意见（请填写）

<!-- USER-NOTES: 23TACsecure_fig_2b -->
- 需要修改的状态或转移：
- 可观事件调整：
- 可控事件调整：
- 希望保留的闭环或预期行为：
- 其他意见：
<!-- END-USER-NOTES: 23TACsecure_fig_2b -->

## 23TACsecure_fig_3

编号：58。类别：论文自动机。
原始状态数：3；转移数：3；初始状态：`0`。
当前结果：`winning`；所选前视深度：`u=1`。

| 事件属性 | 集合 |
| --- | --- |
| 全部事件 Σ | `{a, u}` |
| 可观事件 Σo | `{a}` |
| 不可观事件 Σuo | `{u}` |
| 可控事件 Σc | `{a, u}` |
| 不可控事件 Σuc | ∅ |

[原始系统图](23TACsecure_fig_3/plant.png) · [原始系统数据](23TACsecure_fig_3/plant.json) · [LL-BTS](23TACsecure_fig_3/ll_bts.png) · [闭环结果](23TACsecure_fig_3/closed_loop.png)

来源：23TACsecure.pdf, Fig. 3, PDF p.5。

模型备注：Verification source has no control partition. For this deadlock-free test only, all events are declared controllable; observation partition and transitions are inherited. No claim of source control reproduction.。

<!-- RUN-RESULTS: 23TACsecure_fig_3 -->
### 运行结果与分析

- 判定：online **winning**，offline **winning**；完整离线结论一致。
- 预处理：Qd=∅；Qf=∅；Qe=`{0, 1, 2}`。
- 深度：草稿阈值=1；最小可判定u=0；恢复offline根极大控制模式的最小u=0；实际采用u=1。
  深度经过逐例扫描标定；草稿阈值本身不等于普遍可解性保证。

| 结构指标 | Online LL-BTS | 传统 Offline BTS |
| --- | ---: | ---: |
| 构建D节点 | 1 | 3 |
| 构建O节点 | 0 | 12 |
| 构建边 | 0 | 17 |
| 全部保留D/O节点 | 1/0 | 3/5 |
| 所选闭环可达状态 | 4 | 4 |
| 所选闭环可达转移 | 4 | 4 |
| 所选控制器记忆状态 | 3 | 3 |

**为什么可解：** 初始估计已完全落在Qe中，允许全部事件即可安全延续。因此online可以在根估计处采用安全终端证书，停止枚举O节点。这不是原始plant只有一个状态；物理闭环仍按实际DFA状态和控制器记忆展开。
**实际控制行为：** 所有导出记忆状态的控制输出均允许全部事件，未禁用任何可控事件。保留的多个估计记忆不表示控制模式一定不同。

**传统BTS初始节点的模式去向（互斥分类）：** 共4个模式，其中UR含plant死锁0个；其余模式直接引入控制死锁2个；局部通过但因后续估计失败而剪除0个；最终保留2个。

| 实测成本 | Online | Offline | 绝对节约（Offline−Online） | 节约率 |
| --- | ---: | ---: | ---: | ---: |
| 总求解时间，含online预处理 / ms | 0.013900 | 0.069300 | 0.055400 | 79.942% |
| Python分配峰值 / KiB | 5.562 | 18.852 | 13.289 | 70.493% |

Online分项中位数：预处理0.011200 ms，求解0.002700 ms。总时间是每次预处理与求解相加后再取中位数，不能一般地把两个中位数直接相加。
运算：ΔT=(0.069300−0.013900) ms=0.055400 ms；时间节约率=ΔT/0.069300 ms=79.942%。
ΔM=19,304−5,696=13,608 bytes；内存节约率=ΔM/19,304=70.493%。
**成本解释：** 本例测得online总成本更低；收益同时包含窗口、Qf/Qe证书和提前拒绝坏模式。这是当前实现/模型的实测，不是对所有系统最坏复杂度下降的证明。

[Offline BTS数据](23TACsecure_fig_3/offline/bts.json) · [Offline闭环](23TACsecure_fig_3/closed_loop_system_offline.png) · [Offline supervisor](23TACsecure_fig_3/supervisor_offline.json) · [逐项测量](23TACsecure_fig_3/online_offline_comparison.json)
<!-- END-RUN-RESULTS: 23TACsecure_fig_3 -->

### 修改意见（请填写）

<!-- USER-NOTES: 23TACsecure_fig_3 -->
- 需要修改的状态或转移：
- 可观事件调整：
- 可控事件调整：
- 希望保留的闭环或预期行为：
- 其他意见：
<!-- END-USER-NOTES: 23TACsecure_fig_3 -->

## 23IFAC-attack_fig_1

编号：59。类别：论文自动机。
原始状态数：5；转移数：5；初始状态：`x0`。
当前结果：`losing`；所选前视深度：`u=2`。

| 事件属性 | 集合 |
| --- | --- |
| 全部事件 Σ | `{a, b, c, d, e}` |
| 可观事件 Σo | `{a, b, c, d, e}` |
| 不可观事件 Σuo | ∅ |
| 可控事件 Σc | `{b, c, d, e}` |
| 不可控事件 Σuc | `{a}` |

[原始系统图](23IFAC-attack_fig_1/plant.png) · [原始系统数据](23IFAC-attack_fig_1/plant.json) · [LL-BTS](23IFAC-attack_fig_1/ll_bts.png) · [闭环结果](23IFAC-attack_fig_1/closed_loop.png)

来源：23IFAC-attack.pdf, Fig. 1, PDF p.4。

模型备注：Full observation from source; attack budget/weights ignored, terminal x4 retained.。

<!-- RUN-RESULTS: 23IFAC-attack_fig_1 -->
### 运行结果与分析

- 判定：online **losing**，offline **losing**；完整离线结论一致。
- 预处理：Qd=`{x4}`；Qf=`{x2, x3}`；Qe=∅。
- 深度：草稿阈值=0；最小可判定u=2；恢复offline根极大控制模式的最小u=2；实际采用u=2。
  深度经过逐例扫描标定；草稿阈值本身不等于普遍可解性保证。

| 结构指标 | Online LL-BTS | 传统 Offline BTS |
| --- | ---: | ---: |
| 构建D节点 | 4 | 5 |
| 构建O节点 | 28 | 80 |
| 构建边 | 60 | 128 |
| 全部保留D/O节点 | 0/0 | 0/0 |

**为什么不可解：** 完整已知系统的offline BTS也将初始决策节点剪除，因此这不是单纯u偏小造成的未判定；当前模型不存在满足本实验无死锁目标的supervisor。
从初始状态可达的原始图无环。有限无环系统的所有执行最终都到达无出边终点，仅通过禁用事件不能产生可持续运行的环。
未将空图或“不可解”提示图当成一个可行闭环，也未给终止状态补自环。

**传统BTS初始节点的模式去向（互斥分类）：** 共16个模式，其中UR含plant死锁0个；其余模式直接引入控制死锁0个；局部通过但因后续估计失败而剪除16个；最终保留0个。

| 实测成本 | Online | Offline | 绝对节约（Offline−Online） | 节约率 |
| --- | ---: | ---: | ---: | ---: |
| 总求解时间，含online预处理 / ms | 0.221400 | 0.348900 | 0.127500 | 36.543% |
| Python分配峰值 / KiB | 50.703 | 110.812 | 60.109 | 54.244% |

Online分项中位数：预处理0.017700 ms，求解0.203700 ms。总时间是每次预处理与求解相加后再取中位数，不能一般地把两个中位数直接相加。
运算：ΔT=(0.348900−0.221400) ms=0.127500 ms；时间节约率=ΔT/0.348900 ms=36.543%。
ΔM=113,472−51,920=61,552 bytes；内存节约率=ΔM/113,472=54.244%。
**成本解释：** 本例测得online总成本更低；收益同时包含窗口、Qf/Qe证书和提前拒绝坏模式。这是当前实现/模型的实测，不是对所有系统最坏复杂度下降的证明。

[Offline BTS数据](23IFAC-attack_fig_1/offline/bts.json) · [Offline闭环](23IFAC-attack_fig_1/closed_loop_system_offline.png) · [Offline supervisor](23IFAC-attack_fig_1/supervisor_offline.json) · [逐项测量](23IFAC-attack_fig_1/online_offline_comparison.json)
<!-- END-RUN-RESULTS: 23IFAC-attack_fig_1 -->

### 修改意见（请填写）

<!-- USER-NOTES: 23IFAC-attack_fig_1 -->
- 需要修改的状态或转移：
- 可观事件调整：
- 可控事件调整：
- 希望保留的闭环或预期行为：
- 其他意见：
<!-- END-USER-NOTES: 23IFAC-attack_fig_1 -->

## 23IFAC-attack_fig_2b

编号：60。类别：论文自动机。
原始状态数：7；转移数：9；初始状态：`x0`。
当前结果：`winning`；所选前视深度：`u=3`。

| 事件属性 | 集合 |
| --- | --- |
| 全部事件 Σ | `{a, b, c, d}` |
| 可观事件 Σo | `{a, b, c, d}` |
| 不可观事件 Σuo | ∅ |
| 可控事件 Σc | `{a, c, d}` |
| 不可控事件 Σuc | `{b}` |

[原始系统图](23IFAC-attack_fig_2b/plant.png) · [原始系统数据](23IFAC-attack_fig_2b/plant.json) · [LL-BTS](23IFAC-attack_fig_2b/ll_bts.png) · [闭环结果](23IFAC-attack_fig_2b/closed_loop.png)

来源：23IFAC-attack.pdf, Fig. 2b, PDF p.5。

模型备注：Robot topology only, full observation; original terminal x6 retained.。

<!-- RUN-RESULTS: 23IFAC-attack_fig_2b -->
### 运行结果与分析

- 判定：online **winning**，offline **winning**；完整离线结论一致。
- 预处理：Qd=`{x6}`；Qf=`{x5}`；Qe=∅。
- 深度：草稿阈值=0；最小可判定u=3；恢复offline根极大控制模式的最小u=3；实际采用u=3。
  深度经过逐例扫描标定；草稿阈值本身不等于普遍可解性保证。

| 结构指标 | Online LL-BTS | 传统 Offline BTS |
| --- | ---: | ---: |
| 构建D节点 | 7 | 7 |
| 构建O节点 | 34 | 56 |
| 构建边 | 78 | 104 |
| 全部保留D/O节点 | 4/20 | 4/20 |
| 所选闭环可达状态 | 4 | 4 |
| 所选闭环可达转移 | 4 | 4 |
| 所选控制器记忆状态 | 4 | 4 |

**为什么可解：** 初始估计不能直接用Qe证书终止，但剪枝后仍有认证控制模式。所选supervisor在每个估计处固定选择一个保留模式，所有可能观测均有认证后续控制，并检查不可观测可达集中的每个实际状态都有可用事件。
**实际控制行为：** 不可控事件始终允许；下表列出选定online supervisor的控制输出。

| 记忆 | 估计 | 允许的可控事件 | 禁用的可控事件 |
| --- | --- | --- | --- |
| C0 | `{x0}` | `{a, c, d}` | ∅ |
| C1 | `{x2}` | `{a, c}` | `{d}` |
| C2 | `{x3}` | `{a, d}` | `{c}` |
| C3 | `{x1}` | `{a, c, d}` | ∅ |

**传统BTS初始节点的模式去向（互斥分类）：** 共8个模式，其中UR含plant死锁0个；其余模式直接引入控制死锁0个；局部通过但因后续估计失败而剪除0个；最终保留8个。

| 实测成本 | Online | Offline | 绝对节约（Offline−Online） | 节约率 |
| --- | ---: | ---: | ---: | ---: |
| 总求解时间，含online预处理 / ms | 0.337300 | 0.348300 | 0.011000 | 3.158% |
| Python分配峰值 / KiB | 56.305 | 75.156 | 18.852 | 25.083% |

Online分项中位数：预处理0.028900 ms，求解0.308100 ms。总时间是每次预处理与求解相加后再取中位数，不能一般地把两个中位数直接相加。
运算：ΔT=(0.348300−0.337300) ms=0.011000 ms；时间节约率=ΔT/0.348300 ms=3.158%。
ΔM=76,960−57,656=19,304 bytes；内存节约率=ΔM/76,960=25.083%。
**成本解释：** 本例测得online总成本更低；收益同时包含窗口、Qf/Qe证书和提前拒绝坏模式。这是当前实现/模型的实测，不是对所有系统最坏复杂度下降的证明。

[Offline BTS数据](23IFAC-attack_fig_2b/offline/bts.json) · [Offline闭环](23IFAC-attack_fig_2b/closed_loop_system_offline.png) · [Offline supervisor](23IFAC-attack_fig_2b/supervisor_offline.json) · [逐项测量](23IFAC-attack_fig_2b/online_offline_comparison.json)
<!-- END-RUN-RESULTS: 23IFAC-attack_fig_2b -->

### 修改意见（请填写）

<!-- USER-NOTES: 23IFAC-attack_fig_2b -->
- 需要修改的状态或转移：
- 可观事件调整：
- 可控事件调整：
- 希望保留的闭环或预期行为：
- 其他意见：
<!-- END-USER-NOTES: 23IFAC-attack_fig_2b -->

## 25LCSSattack_fig_1

编号：61。类别：论文自动机。
原始状态数：5；转移数：8；初始状态：`0`。
当前结果：`winning`；所选前视深度：`u=0`。

| 事件属性 | 集合 |
| --- | --- |
| 全部事件 Σ | `{a, b, c}` |
| 可观事件 Σo | `{a, b, c}` |
| 不可观事件 Σuo | ∅ |
| 可控事件 Σc | `{a, b}` |
| 不可控事件 Σuc | `{c}` |

[原始系统图](25LCSSattack_fig_1/plant.png) · [原始系统数据](25LCSSattack_fig_1/plant.json) · [LL-BTS](25LCSSattack_fig_1/ll_bts.png) · [闭环结果](25LCSSattack_fig_1/closed_loop.png)

来源：25LCSSattack.pdf, Fig. 1, PDF p.3。

模型备注：Full observation; protection, vulnerability, and attacks ignored for this objective.。

<!-- RUN-RESULTS: 25LCSSattack_fig_1 -->
### 运行结果与分析

- 判定：online **winning**，offline **winning**；完整离线结论一致。
- 预处理：Qd=`{3}`；Qf=`{2}`；Qe=∅。
- 深度：草稿阈值=0；最小可判定u=0；恢复offline根极大控制模式的最小u=0；实际采用u=0。
  深度经过逐例扫描标定；草稿阈值本身不等于普遍可解性保证。

| 结构指标 | Online LL-BTS | 传统 Offline BTS |
| --- | ---: | ---: |
| 构建D节点 | 1 | 5 |
| 构建O节点 | 1 | 20 |
| 构建边 | 2 | 40 |
| 全部保留D/O节点 | 1/1 | 1/1 |
| 所选闭环可达状态 | 1 | 1 |
| 所选闭环可达转移 | 1 | 1 |
| 所选控制器记忆状态 | 1 | 1 |

**为什么可解：** 初始估计不能直接用Qe证书终止，但剪枝后仍有认证控制模式。所选supervisor在每个估计处固定选择一个保留模式，所有可能观测均有认证后续控制，并检查不可观测可达集中的每个实际状态都有可用事件。
**实际控制行为：** 不可控事件始终允许；下表列出选定online supervisor的控制输出。

| 记忆 | 估计 | 允许的可控事件 | 禁用的可控事件 |
| --- | --- | --- | --- |
| C0 | `{0}` | ∅ | `{a, b}` |

**传统BTS初始节点的模式去向（互斥分类）：** 共4个模式，其中UR含plant死锁0个；其余模式直接引入控制死锁0个；局部通过但因后续估计失败而剪除3个；最终保留1个。

| 实测成本 | Online | Offline | 绝对节约（Offline−Online） | 节约率 |
| --- | ---: | ---: | ---: | ---: |
| 总求解时间，含online预处理 / ms | 0.057800 | 0.111200 | 0.053400 | 48.022% |
| Python分配峰值 / KiB | 12.859 | 37.789 | 24.930 | 65.971% |

Online分项中位数：预处理0.015400 ms，求解0.042400 ms。总时间是每次预处理与求解相加后再取中位数，不能一般地把两个中位数直接相加。
运算：ΔT=(0.111200−0.057800) ms=0.053400 ms；时间节约率=ΔT/0.111200 ms=48.022%。
ΔM=38,696−13,168=25,528 bytes；内存节约率=ΔM/38,696=65.971%。
**成本解释：** 本例测得online总成本更低；收益同时包含窗口、Qf/Qe证书和提前拒绝坏模式。这是当前实现/模型的实测，不是对所有系统最坏复杂度下降的证明。

[Offline BTS数据](25LCSSattack_fig_1/offline/bts.json) · [Offline闭环](25LCSSattack_fig_1/closed_loop_system_offline.png) · [Offline supervisor](25LCSSattack_fig_1/supervisor_offline.json) · [逐项测量](25LCSSattack_fig_1/online_offline_comparison.json)
<!-- END-RUN-RESULTS: 25LCSSattack_fig_1 -->

### 修改意见（请填写）

<!-- USER-NOTES: 25LCSSattack_fig_1 -->
- 需要修改的状态或转移：
- 可观事件调整：
- 可控事件调整：
- 希望保留的闭环或预期行为：
- 其他意见：
<!-- END-USER-NOTES: 25LCSSattack_fig_1 -->

## structural_01_long_chain_16

编号：62。类别：用户指定结构测试。
原始状态数：16；转移数：15；初始状态：`q0`。
当前结果：`losing`；所选前视深度：`u=2`。

| 事件属性 | 集合 |
| --- | --- |
| 全部事件 Σ | `{h, o}` |
| 可观事件 Σo | `{o}` |
| 不可观事件 Σuo | `{h}` |
| 可控事件 Σc | `{h}` |
| 不可控事件 Σuc | `{o}` |

[原始系统图](structural_01_long_chain_16/plant.png) · [原始系统数据](structural_01_long_chain_16/plant.json) · [LL-BTS](structural_01_long_chain_16/ll_bts.png) · [闭环结果](structural_01_long_chain_16/closed_loop.png)

来源：User-requested synthetic topology。

模型备注：16-state finite single chain q0 -> ... -> q15. q15 has no outgoing edge. No invented terminal self-loop: deadlock-free supervision is impossible.。

<!-- RUN-RESULTS: structural_01_long_chain_16 -->
### 运行结果与分析

- 判定：online **losing**，offline **losing**；完整离线结论一致。
- 预处理：Qd=`{q15}`；Qf=`{q0, q1, q10, q11, q12, q13, q14, q2, q3, q4, q5, q6, q7, q8, q9}`；Qe=∅。
- 深度：草稿阈值=2；最小可判定u=0；恢复offline根极大控制模式的最小u=0；实际采用u=2。
  深度经过逐例扫描标定；草稿阈值本身不等于普遍可解性保证。

| 结构指标 | Online LL-BTS | 传统 Offline BTS |
| --- | ---: | ---: |
| 构建D节点 | 1 | 6 |
| 构建O节点 | 0 | 12 |
| 构建边 | 0 | 17 |
| 全部保留D/O节点 | 0/0 | 0/0 |

**为什么不可解：** 完整已知系统的offline BTS也将初始决策节点剪除，因此这不是单纯u偏小造成的未判定；当前模型不存在满足本实验无死锁目标的supervisor。
初始状态属于Qf：沿单后继状态链必然到达Qd。允许后继会走向死锁，禁用全部后继则直接引入控制死锁。
未将空图或“不可解”提示图当成一个可行闭环，也未给终止状态补自环。

**传统BTS初始节点的模式去向（互斥分类）：** 共2个模式，其中UR含plant死锁0个；其余模式直接引入控制死锁1个；局部通过但因后续估计失败而剪除1个；最终保留0个。

| 实测成本 | Online | Offline | 绝对节约（Offline−Online） | 节约率 |
| --- | ---: | ---: | ---: | ---: |
| 总求解时间，含online预处理 / ms | 0.113500 | 0.174800 | 0.061300 | 35.069% |
| Python分配峰值 / KiB | 16.406 | 21.055 | 4.648 | 22.078% |

Online分项中位数：预处理0.081300 ms，求解0.032200 ms。总时间是每次预处理与求解相加后再取中位数，不能一般地把两个中位数直接相加。
运算：ΔT=(0.174800−0.113500) ms=0.061300 ms；时间节约率=ΔT/0.174800 ms=35.069%。
ΔM=21,560−16,800=4,760 bytes；内存节约率=ΔM/21,560=22.078%。
**成本解释：** 本例测得online总成本更低；收益同时包含窗口、Qf/Qe证书和提前拒绝坏模式。这是当前实现/模型的实测，不是对所有系统最坏复杂度下降的证明。

[Offline BTS数据](structural_01_long_chain_16/offline/bts.json) · [Offline闭环](structural_01_long_chain_16/closed_loop_system_offline.png) · [Offline supervisor](structural_01_long_chain_16/supervisor_offline.json) · [逐项测量](structural_01_long_chain_16/online_offline_comparison.json)
<!-- END-RUN-RESULTS: structural_01_long_chain_16 -->

### 修改意见（请填写）

<!-- USER-NOTES: structural_01_long_chain_16 -->
- 需要修改的状态或转移：
- 可观事件调整：
- 可控事件调整：
- 希望保留的闭环或预期行为：
- 其他意见：
<!-- END-USER-NOTES: structural_01_long_chain_16 -->

## structural_02_chain_cycle_two_tails_15

编号：63。类别：用户指定结构测试。
原始状态数：15；转移数：15；初始状态：`q0`。
当前结果：`winning`；所选前视深度：`u=8`。

| 事件属性 | 集合 |
| --- | --- |
| 全部事件 Σ | `{h, o, x, y}` |
| 可观事件 Σo | `{o, x, y}` |
| 不可观事件 Σuo | `{h}` |
| 可控事件 Σc | `{h, x, y}` |
| 不可控事件 Σuc | `{o}` |

[原始系统图](structural_02_chain_cycle_two_tails_15/plant.png) · [原始系统数据](structural_02_chain_cycle_two_tails_15/plant.json) · [LL-BTS](structural_02_chain_cycle_two_tails_15/ll_bts.png) · [闭环结果](structural_02_chain_cycle_two_tails_15/closed_loop.png)

来源：User-requested synthetic topology。

模型备注：Prefix q0 -> ... -> q5; cycle q5 -> q6 -> q7 -> q8 -> q5; two exit chains q6 -x-> q9 -> q10 -> q11 and q8 -y-> q12 -> q13 -> q14. Terminal q11,q14 are deadlocks; x,y can be disabled to retain the cycle.。

<!-- RUN-RESULTS: structural_02_chain_cycle_two_tails_15 -->
### 运行结果与分析

- 判定：online **winning**，offline **winning**；完整离线结论一致。
- 预处理：Qd=`{q11, q14}`；Qf=`{q10, q12, q13, q9}`；Qe=∅。
- 深度：草稿阈值=1；最小可判定u=8；恢复offline根极大控制模式的最小u=8；实际采用u=8。
  深度经过逐例扫描标定；草稿阈值本身不等于普遍可解性保证。

| 结构指标 | Online LL-BTS | 传统 Offline BTS |
| --- | ---: | ---: |
| 构建D节点 | 4 | 5 |
| 构建O节点 | 10 | 40 |
| 构建边 | 24 | 58 |
| 全部保留D/O节点 | 3/6 | 3/6 |
| 所选闭环可达状态 | 11 | 11 |
| 所选闭环可达转移 | 11 | 11 |
| 所选控制器记忆状态 | 3 | 3 |

**为什么可解：** 初始估计不能直接用Qe证书终止，但剪枝后仍有认证控制模式。所选supervisor在每个估计处固定选择一个保留模式，所有可能观测均有认证后续控制，并检查不可观测可达集中的每个实际状态都有可用事件。
本例的两条出口链分别通向终止状态q11、q14。所选策略在相关记忆处禁止危险出口x或y，保留前缀及 `q5→q6→q7→q8→q5` 的可持续循环。
**实际控制行为：** 不可控事件始终允许；下表列出选定online supervisor的控制输出。

| 记忆 | 估计 | 允许的可控事件 | 禁用的可控事件 |
| --- | --- | --- | --- |
| C0 | `{q0}` | `{h, y}` | `{x}` |
| C1 | `{q7}` | `{h, x}` | `{y}` |
| C2 | `{q5}` | `{h, y}` | `{x}` |

**传统BTS初始节点的模式去向（互斥分类）：** 共8个模式，其中UR含plant死锁0个；其余模式直接引入控制死锁4个；局部通过但因后续估计失败而剪除2个；最终保留2个。

| 实测成本 | Online | Offline | 绝对节约（Offline−Online） | 节约率 |
| --- | ---: | ---: | ---: | ---: |
| 总求解时间，含online预处理 / ms | 0.387100 | 0.489700 | 0.102600 | 20.952% |
| Python分配峰值 / KiB | 24.422 | 50.133 | 25.711 | 51.286% |

Online分项中位数：预处理0.059900 ms，求解0.327200 ms。总时间是每次预处理与求解相加后再取中位数，不能一般地把两个中位数直接相加。
运算：ΔT=(0.489700−0.387100) ms=0.102600 ms；时间节约率=ΔT/0.489700 ms=20.952%。
ΔM=51,336−25,008=26,328 bytes；内存节约率=ΔM/51,336=51.286%。
**成本解释：** 本例测得online总成本更低；收益同时包含窗口、Qf/Qe证书和提前拒绝坏模式。这是当前实现/模型的实测，不是对所有系统最坏复杂度下降的证明。

[Offline BTS数据](structural_02_chain_cycle_two_tails_15/offline/bts.json) · [Offline闭环](structural_02_chain_cycle_two_tails_15/closed_loop_system_offline.png) · [Offline supervisor](structural_02_chain_cycle_two_tails_15/supervisor_offline.json) · [逐项测量](structural_02_chain_cycle_two_tails_15/online_offline_comparison.json)
<!-- END-RUN-RESULTS: structural_02_chain_cycle_two_tails_15 -->

### 修改意见（请填写）

<!-- USER-NOTES: structural_02_chain_cycle_two_tails_15 -->
- 需要修改的状态或转移：
- 可观事件调整：
- 可控事件调整：
- 希望保留的闭环或预期行为：
- 其他意见：
<!-- END-USER-NOTES: structural_02_chain_cycle_two_tails_15 -->

## structural_03_chain_nested_cycles_11

编号：64。类别：用户指定结构测试。
原始状态数：11；转移数：12；初始状态：`q0`。
当前结果：`winning`；所选前视深度：`u=8`。

| 事件属性 | 集合 |
| --- | --- |
| 全部事件 Σ | `{h, j, o}` |
| 可观事件 Σo | `{o}` |
| 不可观事件 Σuo | `{h, j}` |
| 可控事件 Σc | `{h, j}` |
| 不可控事件 Σuc | `{o}` |

[原始系统图](structural_03_chain_nested_cycles_11/plant.png) · [原始系统数据](structural_03_chain_nested_cycles_11/plant.json) · [LL-BTS](structural_03_chain_nested_cycles_11/ll_bts.png) · [闭环结果](structural_03_chain_nested_cycles_11/closed_loop.png)

来源：User-requested synthetic topology。

模型备注：Prefix q0 -> ... -> q5; outer cycle q5 -> q6 -> q7 -> q8 -> q5; inner cycle q6 -> q9 -> q10 -> q6. Both cycles share q6. Hidden inner cycling is permitted by the deadlock-free objective; no fairness, eventual observation or nonblocking objective is imposed.。

<!-- RUN-RESULTS: structural_03_chain_nested_cycles_11 -->
### 运行结果与分析

- 判定：online **winning**，offline **winning**；完整离线结论一致。
- 预处理：Qd=∅；Qf=∅；Qe=`{q0, q1, q10, q2, q3, q4, q5, q6, q7, q8, q9}`。
- 深度：草稿阈值=8；最小可判定u=0；恢复offline根极大控制模式的最小u=0；实际采用u=8。
  深度经过逐例扫描标定；草稿阈值本身不等于普遍可解性保证。

| 结构指标 | Online LL-BTS | 传统 Offline BTS |
| --- | ---: | ---: |
| 构建D节点 | 1 | 3 |
| 构建O节点 | 0 | 12 |
| 构建边 | 0 | 18 |
| 全部保留D/O节点 | 1/0 | 3/6 |
| 所选闭环可达状态 | 15 | 15 |
| 所选闭环可达转移 | 17 | 17 |
| 所选控制器记忆状态 | 3 | 3 |

**为什么可解：** 初始估计已完全落在Qe中，允许全部事件即可安全延续。因此online可以在根估计处采用安全终端证书，停止枚举O节点。这不是原始plant只有一个状态；物理闭环仍按实际DFA状态和控制器记忆展开。
本例没有plant死锁：前缀接外环，q6处另接内环。允许在不可观测内环中持续运行并不违反无死锁目标；这里没有额外要求最终产生观测或退出内环。
**实际控制行为：** 所有导出记忆状态的控制输出均允许全部事件，未禁用任何可控事件。保留的多个估计记忆不表示控制模式一定不同。

**传统BTS初始节点的模式去向（互斥分类）：** 共4个模式，其中UR含plant死锁0个；其余模式直接引入控制死锁2个；局部通过但因后续估计失败而剪除0个；最终保留2个。

| 实测成本 | Online | Offline | 绝对节约（Offline−Online） | 节约率 |
| --- | ---: | ---: | ---: | ---: |
| 总求解时间，含online预处理 / ms | 0.037300 | 0.094800 | 0.057500 | 60.654% |
| Python分配峰值 / KiB | 12.367 | 19.992 | 7.625 | 38.140% |

Online分项中位数：预处理0.034600 ms，求解0.002600 ms。总时间是每次预处理与求解相加后再取中位数，不能一般地把两个中位数直接相加。
运算：ΔT=(0.094800−0.037300) ms=0.057500 ms；时间节约率=ΔT/0.094800 ms=60.654%。
ΔM=20,472−12,664=7,808 bytes；内存节约率=ΔM/20,472=38.140%。
**成本解释：** 本例测得online总成本更低；收益同时包含窗口、Qf/Qe证书和提前拒绝坏模式。这是当前实现/模型的实测，不是对所有系统最坏复杂度下降的证明。

[Offline BTS数据](structural_03_chain_nested_cycles_11/offline/bts.json) · [Offline闭环](structural_03_chain_nested_cycles_11/closed_loop_system_offline.png) · [Offline supervisor](structural_03_chain_nested_cycles_11/supervisor_offline.json) · [逐项测量](structural_03_chain_nested_cycles_11/online_offline_comparison.json)
<!-- END-RUN-RESULTS: structural_03_chain_nested_cycles_11 -->

### 修改意见（请填写）

<!-- USER-NOTES: structural_03_chain_nested_cycles_11 -->
- 需要修改的状态或转移：
- 可观事件调整：
- 可控事件调整：
- 希望保留的闭环或预期行为：
- 其他意见：
<!-- END-USER-NOTES: structural_03_chain_nested_cycles_11 -->


<!-- LARGE-RESULTS: literature_products -->
## 千万状态论文乘积：实际运行结果与分析

本节是额外的两个大乘积，不混入上面64个显式原始模型的计时汇总。它们保留源模型的部分观测/控制属性，使用精确组合式Qe证书；没有逐一展开千万状态，也没有完成传统offline BTS。

| 来源 × 副本 | 实际可达状态 | 实际可达转移 | 结果 | 含组合式预处理综合中位数 / μs | Python峰值 / bytes |
| --- | ---: | ---: | --- | ---: | ---: |
| 21AutomaticaOptimal_fig_2 × 6 | 11,390,625 | 109,350,000 | winning | 31.000 | 7,192 |
| 18TACrange_fig_3a × 7 | 19,487,171 | 173,612,978 | winning | 19.600 | 6,328 |

### literature_product_21AutomaticaOptimal_fig_2_6copy

源例：`21AutomaticaOptimal_fig_2`；15状态 × 6副本；u=12。
| 属性 | 集合 |
| --- | --- |
| 可观事件 Σo | `{o1_0, o1_1, o1_2, o1_3, o1_4, o1_5, o2_0, o2_1, o2_2, o2_3, o2_4, o2_5, o3_0, o3_1, o3_2, o3_3, o3_4, o3_5, o4_0, o4_1, o4_2, o4_3, o4_4, o4_5}` |
| 不可观事件 Σuo | `{a1_0, a1_1, a1_2, a1_3, a1_4, a1_5, a2_0, a2_1, a2_2, a2_3, a2_4, a2_5, a3_0, a3_1, a3_2, a3_3, a3_4, a3_5, a4_0, a4_1, a4_2, a4_3, a4_4, a4_5, b1_0, b1_1, b1_2, b1_3, b1_4, b1_5, b2_0, b2_1, b2_2, b2_3, b2_4, b2_5, c1_0, c1_1, c1_2, c1_3, c1_4, c1_5, c2_0, c2_1, c2_2, c2_3, c2_4, c2_5, c3_0, c3_1, c3_2, c3_3, c3_4, c3_5, c4_0, c4_1, c4_2, c4_3, c4_4, c4_5, c5_0, c5_1, c5_2, c5_3, c5_4, c5_5}` |
| 可控事件 Σc | `{c1_0, c1_1, c1_2, c1_3, c1_4, c1_5, c2_0, c2_1, c2_2, c2_3, c2_4, c2_5, c3_0, c3_1, c3_2, c3_3, c3_4, c3_5, c4_0, c4_1, c4_2, c4_3, c4_4, c4_5, c5_0, c5_1, c5_2, c5_3, c5_4, c5_5}` |
| 不可控事件 Σuc | `{a1_0, a1_1, a1_2, a1_3, a1_4, a1_5, a2_0, a2_1, a2_2, a2_3, a2_4, a2_5, a3_0, a3_1, a3_2, a3_3, a3_4, a3_5, a4_0, a4_1, a4_2, a4_3, a4_4, a4_5, b1_0, b1_1, b1_2, b1_3, b1_4, b1_5, b2_0, b2_1, b2_2, b2_3, b2_4, b2_5, o1_0, o1_1, o1_2, o1_3, o1_4, o1_5, o2_0, o2_1, o2_2, o2_3, o2_4, o2_5, o3_0, o3_1, o3_2, o3_3, o3_4, o3_5, o4_0, o4_1, o4_2, o4_3, o4_4, o4_5}` |

**综合结论与控制行为：** 所有分量状态都有出边，故任意乘积状态都有出边，Qd=Qf=∅、Qe=整个乘积。实际得到一个记忆状态C0、永远允许全部事件的supervisor；S/G=G，所以在无死锁目标下最大宽松。
认证LL-BTS只有1个D节点、0个O节点。这表示组合安全证书提前终止，不表示物理闭环只有一个状态。所有分量状态都有已验证到达词，按坐标交错这些词可构造到任意元组的路径，因此所报规模是真实可达规模。
**实际运行与验证：** 实际运行导出的Python supervisor；每例100条×1000步，共100000步，每步校验完整因子化观测估计包含实际状态，未发现死锁或禁用不可控事件。另对1/2/3副本做全状态/全转移检查，并执行1000个目标元组的构造到达串。大乘积的全状态安全性由组合证明保证，随机运行只是额外测试。
101次新鲜测量：预处理中位数23.900 μs，求解中位数7.100 μs，逐次总时间中位数31.000 μs，Python分配峰值7,192 bytes。预处理是对小分量的真实检查及组合证明，不是显式全乘积扫描；输入/测试/导出不计入该时间。

**Offline估算，不能当作实测：** 初始节点模式数P=1,073,741,824；在目标规模上实测384个逐模式UR/NX记录，单次中位数2.495750 ms。按P×t外推，仅根阶段≈2,679,791.158s≈31.02天；根记录内存外推≈131.28 TiB。
这只针对当前传统逐模式/独立保存UR与NX的实现，未包含后续BTS与剪枝；实际更可能先内存不足，不能写成“offline实测31天”。如果offline也使用组合证书、共享闭包、位集或符号模式族，这个估算就不能直接套用。先前forecast的25.1 μs为较早一轮online测量；本节表格采用最近实际综合运行记录。

**适用范围：** 这两个候选全部安全，适合展示Qe证书收益，不代表任意含危险状态的系统。只保证无死锁，不附带公平性、最终观测、标记非阻塞或原论文收益目标。

[实际综合与验证报告](literature_product_21AutomaticaOptimal_fig_2_6copy/SYNTHESIS_AND_VALIDATION.md) · [可执行supervisor](literature_product_21AutomaticaOptimal_fig_2_6copy/supervisor_online.py) · [完整精确因子化闭环](literature_product_21AutomaticaOptimal_fig_2_6copy/closed_loop_system_online.json) · [闭环图](literature_product_21AutomaticaOptimal_fig_2_6copy/closed_loop_system_online.svg) · [原始实测](literature_product_21AutomaticaOptimal_fig_2_6copy/actual_online_run.json)

#### 修改意见（请填写）

<!-- USER-NOTES: literature_product_21AutomaticaOptimal_fig_2_6copy -->
- 源例或副本数调整：
- 可观/可控事件调整：
- 希望保留的闭环或预期行为：
- 其他意见：
<!-- END-USER-NOTES: literature_product_21AutomaticaOptimal_fig_2_6copy -->

### literature_product_18TACrange_fig_3a_7copy

源例：`18TACrange_fig_3a`；11状态 × 7副本；u=14。
| 属性 | 集合 |
| --- | --- |
| 可观事件 Σo | `{o_0, o_1, o_2, o_3, o_4, o_5, o_6}` |
| 不可观事件 Σuo | `{c1_0, c1_1, c1_2, c1_3, c1_4, c1_5, c1_6, c2_0, c2_1, c2_2, c2_3, c2_4, c2_5, c2_6, u1_0, u1_1, u1_2, u1_3, u1_4, u1_5, u1_6, u2_0, u2_1, u2_2, u2_3, u2_4, u2_5, u2_6}` |
| 可控事件 Σc | `{c1_0, c1_1, c1_2, c1_3, c1_4, c1_5, c1_6, c2_0, c2_1, c2_2, c2_3, c2_4, c2_5, c2_6}` |
| 不可控事件 Σuc | `{o_0, o_1, o_2, o_3, o_4, o_5, o_6, u1_0, u1_1, u1_2, u1_3, u1_4, u1_5, u1_6, u2_0, u2_1, u2_2, u2_3, u2_4, u2_5, u2_6}` |

**综合结论与控制行为：** 所有分量状态都有出边，故任意乘积状态都有出边，Qd=Qf=∅、Qe=整个乘积。实际得到一个记忆状态C0、永远允许全部事件的supervisor；S/G=G，所以在无死锁目标下最大宽松。
认证LL-BTS只有1个D节点、0个O节点。这表示组合安全证书提前终止，不表示物理闭环只有一个状态。所有分量状态都有已验证到达词，按坐标交错这些词可构造到任意元组的路径，因此所报规模是真实可达规模。
**实际运行与验证：** 实际运行导出的Python supervisor；每例100条×1000步，共100000步，每步校验完整因子化观测估计包含实际状态，未发现死锁或禁用不可控事件。另对1/2/3副本做全状态/全转移检查，并执行1000个目标元组的构造到达串。大乘积的全状态安全性由组合证明保证，随机运行只是额外测试。
101次新鲜测量：预处理中位数12.900 μs，求解中位数6.700 μs，逐次总时间中位数19.600 μs，Python分配峰值6,328 bytes。预处理是对小分量的真实检查及组合证明，不是显式全乘积扫描；输入/测试/导出不计入该时间。

**Offline状态：** 未运行完整传统BTS，也未生成可宣称实测的offline耗时/节约率。不能把第一个系统的31天估算套用到本系统。

**适用范围：** 这两个候选全部安全，适合展示Qe证书收益，不代表任意含危险状态的系统。只保证无死锁，不附带公平性、最终观测、标记非阻塞或原论文收益目标。

[实际综合与验证报告](literature_product_18TACrange_fig_3a_7copy/SYNTHESIS_AND_VALIDATION.md) · [可执行supervisor](literature_product_18TACrange_fig_3a_7copy/supervisor_online.py) · [完整精确因子化闭环](literature_product_18TACrange_fig_3a_7copy/closed_loop_system_online.json) · [闭环图](literature_product_18TACrange_fig_3a_7copy/closed_loop_system_online.svg) · [原始实测](literature_product_18TACrange_fig_3a_7copy/actual_online_run.json)

#### 修改意见（请填写）

<!-- USER-NOTES: literature_product_18TACrange_fig_3a_7copy -->
- 源例或副本数调整：
- 可观/可控事件调整：
- 希望保留的闭环或预期行为：
- 其他意见：
<!-- END-USER-NOTES: literature_product_18TACrange_fig_3a_7copy -->
<!-- END-LARGE-RESULTS: literature_products -->
