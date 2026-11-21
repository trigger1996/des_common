# 原始系统事件属性与修改意见

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

## 快速索引

| 序号 | 系统 | 原始状态数 | 可观事件 Σo | 可控事件 Σc | 当前结果 |
| --- | --- | ---: | --- | --- | --- |
| 1 | [yin2016_fig_1a](#yin2016_fig_1a) | 7 | `{o1, o2}` | `{a, b, c}` | winning |
| 2 | [yin2016_fig_1b](#yin2016_fig_1b) | 5 | `{o1, o2}` | `{a, b, c}` | winning |
| 3 | [yin2016_fig_1c](#yin2016_fig_1c) | 2 | `{o1, o2}` | `{a, b, c}` | winning |
| 4 | [yin2016_fig_3a](#yin2016_fig_3a) | 6 | `{a, c, d, o}` | `{b, o}` | winning |
| 5 | [yin2016_fig_3b](#yin2016_fig_3b) | 8 | `{a, c, d, o}` | `{b, o}` | winning |
| 6 | [yin2016_fig_3c](#yin2016_fig_3c) | 8 | `{a, c, d, o}` | `{b, o}` | winning |
| 7 | [15ACCopac_fig_1](#15accopac_fig_1) | 7 | `{o1, o2}` | `{a, b, c}` | winning |
| 8 | [15ACCopac_fig_2a](#15accopac_fig_2a) | 5 | `{o1, o2}` | `{a, b, c}` | winning |
| 9 | [15ACCopac_fig_2b](#15accopac_fig_2b) | 2 | `{o1, o2}` | `{a, b, c}` | losing |
| 10 | [15ACCopac_fig_2c](#15accopac_fig_2c) | 6 | `{o1, o2}` | `{a, b, c}` | winning |
| 11 | [16CDC_fig_2a_G](#16cdc_fig_2a_g) | 9 | `{o}` | `{c1, c2}` | losing |
| 12 | [16CDC_fig_2a_K](#16cdc_fig_2a_k) | 8 | `{o}` | `{c1, c2}` | losing |
| 13 | [16CDC_fig_2b](#16cdc_fig_2b) | 3 | `{o}` | `{c1, c2}` | losing |
| 14 | [14IFAC_fig_1](#14ifac_fig_1) | 8 | `{o, uc}` | `{a, b, c, o}` | losing |
| 15 | [16WODESmax_fig_1a](#16wodesmax_fig_1a) | 6 | `{a, b}` | `{c1, c2}` | losing |
| 16 | [16WODESmax_fig_1b](#16wodesmax_fig_1b) | 7 | `{a, b}` | `{c1, c2}` | losing |
| 17 | [16WODESmax_fig_2a](#16wodesmax_fig_2a) | 5 | `{a, b}` | `{c1, c2}` | losing |
| 18 | [16WODESmax_fig_3a_Gprime](#16wodesmax_fig_3a_gprime) | 11 | `{a, b}` | `{c1, c2}` | losing |
| 19 | [17TAC-Range_fig_2a_G](#17tac-range_fig_2a_g) | 7 | `{a, b}` | `{c1, c2}` | losing |
| 20 | [17TAC-Range_fig_2a_K](#17tac-range_fig_2a_k) | 6 | `{a, b}` | `{c1, c2}` | losing |
| 21 | [17TAC-Range_fig_2c](#17tac-range_fig_2c) | 5 | `{a, b}` | `{c1, c2}` | losing |
| 22 | [17TAC-Range_fig_4a](#17tac-range_fig_4a) | 2 | `{a, b, v}` | `{v, w}` | winning |
| 23 | [17TAC-Range_fig_4b](#17tac-range_fig_4b) | 6 | `{a, b, v}` | `{v, w}` | winning |
| 24 | [17TAC-Range_fig_4c](#17tac-range_fig_4c) | 7 | `{a, b, v}` | `{v, w}` | winning |
| 25 | [18TACrange_fig_1a](#18tacrange_fig_1a) | 13 | `{o}` | `{c1, c2}` | winning |
| 26 | [18TACrange_fig_1b](#18tacrange_fig_1b) | 3 | `{o}` | `{c1, c2}` | losing |
| 27 | [18TACrange_fig_3a](#18tacrange_fig_3a) | 11 | `{o}` | `{c1, c2}` | winning |
| 28 | [18TACrange_fig_3b](#18tacrange_fig_3b) | 4 | `{o}` | `{c1, c2}` | losing |
| 29 | [16TACNB_fig_7a](#16tacnb_fig_7a) | 11 | `{o}` | `{c1, c2}` | winning |
| 30 | [22TACopaque_fig_1](#22tacopaque_fig_1) | 12 | `{o1, o2, o3}` | `{c1, c2}` | losing |
| 31 | [24TACopa_fig_1a](#24tacopa_fig_1a) | 9 | `{o1, o2}` | `{a, b, c}` | losing |
| 32 | [24TACopa_fig_1b](#24tacopa_fig_1b) | 2 | `{o1, o2}` | `{a, b, c}` | losing |
| 33 | [24TACopa_fig_1c](#24tacopa_fig_1c) | 6 | `{o1, o2}` | `{a, b, c}` | losing |
| 34 | [24TACopa_fig_4](#24tacopa_fig_4) | 9 | `{o1, o2}` | `{a}` | losing |
| 35 | [17Mealy_fig_2a](#17mealy_fig_2a) | 10 | `{d1, d2}` | `{s1, s2}` | losing |
| 36 | [17Mealy_fig_2b](#17mealy_fig_2b) | 8 | `{d1, d2}` | `{s1, s2}` | losing |
| 37 | [17Mealy_fig_3a](#17mealy_fig_3a) | 9 | `{d1, d2}` | `{s1, s2}` | losing |
| 38 | [17Mealy_fig_3b](#17mealy_fig_3b) | 7 | `{d1, d2}` | `{s1, s2}` | losing |
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

### 修改意见（请填写）

<!-- USER-NOTES: structural_03_chain_nested_cycles_11 -->
- 需要修改的状态或转移：
- 可观事件调整：
- 可控事件调整：
- 希望保留的闭环或预期行为：
- 其他意见：
<!-- END-USER-NOTES: structural_03_chain_nested_cycles_11 -->
