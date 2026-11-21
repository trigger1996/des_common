# DFA定义与确定性复核

本轮检查61个当前模型、64个修改前模型：发现0个不符合确定性或数据合法性的模型。
逐条读取原始转移列表后检查，未先转成字典；同时执行原始构造器的重复键断言，避免同事件多后继被覆盖后漏检。

## 使用的定义

本项目采用DES中的部分定义确定自动机：δ: Q×Σ ⇀ Q。每个状态—事件至多一个后继；允许某些事件未定义。
若采用教材中要求δ为全函数的完整DFA定义，当前61例中只有0例完整；其余是部分DFA。
终止状态、无出边状态、同一状态上不同事件的多条边、自环，以及不可达状态，都不违反这里的确定性定义。无死锁可解性是另一项性质。
`eps`在Mealy例子中是显式事件名称，按不可观事件处理，不是无需事件发生的数学ε转移；不能把这些例子描述为含ε转移的普通DFA。

## 已解决的修改意见

`20CDC2_fig_2b`最新意见为添加 `2─b→2`、`6─c→6`，已执行；原有 `2─c→6` 保留。同一状态同一事件仍只有一个后继，当前没有暂缓冲突。
`16WODESmax_fig_3a_Gprime`已按用户后续修正添加c2自环，原有c1出边保留，两种事件不同，无确定性冲突。

| 当前模型 | 部分DFA合法 | 同状态同事件多后继 | 未定义状态—事件对数 | 无出边状态 |
| --- | --- | ---: | ---: | --- |
| yin2016_fig_1a | 是 | 0 | 31 | 无 |
| yin2016_fig_1c | 是 | 0 | 10 | 无 |
| yin2016_fig_3a | 是 | 0 | 32 | 无 |
| yin2016_fig_3b | 是 | 0 | 46 | 5^-1, 5^2 |
| yin2016_fig_3c | 是 | 0 | 46 | 5 |
| 15ACCopac_fig_1 | 是 | 0 | 26 | 6 |
| 15ACCopac_fig_2a | 是 | 0 | 20 | 6 |
| 15ACCopac_fig_2b | 是 | 0 | 9 | 1 |
| 15ACCopac_fig_2c | 是 | 0 | 23 | 1 |
| 16CDC_fig_2a_G | 是 | 0 | 14 | 9 |
| 16CDC_fig_2a_K | 是 | 0 | 14 | 7, 8 |
| 16CDC_fig_2b | 是 | 0 | 6 | 2 |
| 14IFAC_fig_1 | 是 | 0 | 32 | 3, 7, 8 |
| 16WODESmax_fig_1a | 是 | 0 | 14 | 6 |
| 16WODESmax_fig_1b | 是 | 0 | 16 | 7 |
| 16WODESmax_fig_2a | 是 | 0 | 14 | 无 |
| 16WODESmax_fig_3a_Gprime | 是 | 0 | 25 | 7 |
| 17TAC-Range_fig_2a_G | 是 | 0 | 23 | 7 |
| 17TAC-Range_fig_2a_K | 是 | 0 | 20 | 6 |
| 17TAC-Range_fig_4a | 是 | 0 | 6 | 无 |
| 17TAC-Range_fig_4b | 是 | 0 | 16 | 无 |
| 17TAC-Range_fig_4c | 是 | 0 | 18 | 7 |
| 18TACrange_fig_1a | 是 | 0 | 48 | 12, 13 |
| 18TACrange_fig_1b | 是 | 0 | 13 | 5 |
| 18TACrange_fig_3a | 是 | 0 | 41 | 10 |
| 18TACrange_fig_3b | 是 | 0 | 17 | 3, 4 |
| 16TACNB_fig_7a | 是 | 0 | 63 | 10, 9 |
| 22TACopaque_fig_1 | 是 | 0 | 42 | 10, 11, 8, 9 |
| 24TACopa_fig_1a | 是 | 0 | 33 | 6 |
| 24TACopa_fig_1c | 是 | 0 | 24 | 6 |
| 24TACopa_fig_4 | 是 | 0 | 16 | 8 |
| 17Mealy_fig_2a | 是 | 0 | 36 | 3, 4 |
| 17Mealy_fig_2b | 是 | 0 | 28 | 2 |
| 17Mealy_fig_3a | 是 | 0 | 34 | 2, 3 |
| 17Mealy_fig_3b | 是 | 0 | 27 | 2, 3 |
| 22TAConline_fig_2 | 是 | 0 | 67 | 10, 15, 16, 7 |
| 22TAClocal_fig_2 | 是 | 0 | 98 | x2, x5 |
| 24AutoOpt_fig_1 | 是 | 0 | 3 | 无 |
| 24AutoOpt_fig_2 | 是 | 0 | 6 | q4 |
| 24AutoOpt_fig_6b | 是 | 0 | 33 | 无 |
| 24AutoOpt_fig_6d | 是 | 0 | 4 | 无 |
| 21AutomaticaOptimal_fig_2 | 是 | 0 | 201 | 无 |
| 20CDC2_fig_1a | 是 | 0 | 18 | 6 |
| 20CDC2_fig_1b | 是 | 0 | 24 | 6 |
| 20CDC2_fig_2a | 是 | 0 | 52 | 11, 13, 5 |
| 20CDC2_fig_2b | 是 | 0 | 27 | 10, 7 |
| 20IFAC1_fig_1 | 是 | 0 | 20 | 5 |
| 16SEI_fig_1a | 是 | 0 | 26 | 7, 8, 9 |
| 16SEI_fig_1b | 是 | 0 | 21 | 4, 6 |
| 16SEI_fig_4a | 是 | 0 | 35 | 12, 9 |
| 16SEI_fig_4b | 是 | 0 | 31 | 10, 5, 8, 9 |
| 17AutomaticaTW_fig_1a | 是 | 0 | 17 | 无 |
| 23TACsecure_fig_2a | 是 | 0 | 23 | 无 |
| 23TACsecure_fig_2b | 是 | 0 | 21 | 3 |
| 23TACsecure_fig_3 | 是 | 0 | 3 | 无 |
| 23IFAC-attack_fig_1 | 是 | 0 | 20 | x4 |
| 23IFAC-attack_fig_2b | 是 | 0 | 19 | x6 |
| 25LCSSattack_fig_1 | 是 | 0 | 7 | 3 |
| structural_01_long_chain_16 | 是 | 0 | 17 | q15 |
| structural_02_chain_cycle_two_tails_15 | 是 | 0 | 45 | q11, q14 |
| structural_03_chain_nested_cycles_11 | 是 | 0 | 21 | 无 |

索引事件互不共享的异步乘积保持确定性；大系统检查分量及组合规则，不枚举千万状态。
详细逐项数据见 [dfa_definition_audit.json](dfa_definition_audit.json)。
