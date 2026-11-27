# DES limited-lookahead control

## 目录与快速试运行

| 位置 | 用途 |
| --- | --- |
| `des_core/` | DFA、预处理、LL-BTS、传统 BTS、闭环验证等核心实现 |
| `examples/basic/` | 入门示例、动态构建及 Case 1 乘积实验 |
| `examples/benchmarks/` | 文献、随机及结构化模型基准实验 |
| `examples/comparisons/` | 在线/离线、三方法、轨迹和资源开销对比 |
| `examples/large_scale/` | 大规模系统及乘积实验入口，包含原有输入数据 |
| `examples/paper/`、`examples/paper_fig1_r1/` | 论文案例、图示复现和增量合并实验 |
| `examples/warehouse_2018/` | 仓储案例模型和复现入口 |
| `examples/` 下其余模型文件 | 各组实验共用的模型定义 |
| `tests/` | 正确性与回归测试 |
| `scripts/maintenance/` | 数据审计、结果刷新、批量重跑及输出清理 |
| `scripts/reporting/` | 报告、统计分析和绘图工具 |
| `scripts/local/` | 一次性文档生成等本地辅助脚本；Git 忽略 |
| `__ref/local/` | 从根目录归档的三份参考 PDF |
| `docs/local/` | 本地会话记忆、审查指南及历史算法备忘；Git 忽略 |
| `outputs/`、`output/` | 运行生成的图、报告和测量结果 |
| `tmp/` | 临时文件和整理归档 |

在本项目目录执行：

运行工作目录统一为 `limited_lookahead_deadlock_free/`。入口可通过下方脚本路径直接运行，
也可使用模块形式，例如 `python -m examples.comparisons.three_method_comparison --help`。
Python 导入使用分类后的完整包名；原根目录脚本已迁移至上述目录。

```powershell
python -m pip install -r requirements.txt
python -X utf8 -m unittest discover -s tests -v
python -X utf8 examples/paper/print_paper_figure_reference.py --u 5
```

最后一条运行论文小模型，验证策略并打印 LL-BTS，结果写入
`outputs/revision_materials/fig1_r1_20261123/figure_state_transition_u5.txt`。
这是小规模试运行；大规模实验请按下方对应入口单独执行。

本地辅助文档：`CODEX_MEMORY.md` 记录历史会话上下文；`CODE_REVIEW_GUIDE.md`
列出运行和审查步骤；`ON_THE_FLY_NONDEADLOCK_MODIFICATION_MEMO.md` 和
`OPTIMIZATION_AND_CONSISTENCY_NOTES.md` 保存历史修改思路与优化论证。
它们已归入 `docs/local/`，不会随 Git 分发；新克隆可从本 README 开始。
历史备忘可能早于当前实现，应结合代码和测试阅读。

## 同一组例子上的 Cai-2018 / LLP-1992 / 本文方法对比

```powershell
python -X utf8 examples/comparisons/three_method_comparison.py --repetitions 5
```

PyCharm 配置：`Three_Method_Common_Examples`。
这组三方法明确指 **蔡老师2018方法、Chung等1992方法、本文LL-BTS**，不把Full BTS算作其中一个。
5个共同全观测例子 × 3个前视长度（3、8、16）× 3种方法，共45组结果；
输入哈希一致，每组独立进程测量5次root时间，另测Python峰值和CPU/RAM，并穷举检查闭环。
还保存真正逐事件重新计算的50事件上限轨迹。原始部分观测数据不变。

先看 `outputs/case_studies/three_method_comparison/共同例子三方法对比.md`。
方法、输入、计数差异和失败结果的解释见
[examples/three_method_common/README.md](examples/three_method_common/README.md)。
详细结果已加入 `Response/supplementary_material.R1.tex` 第6节。

CPU/RAM另有45组独立长批次，每组至少2秒，避免短计时造成CPU零值或比例失真：

```powershell
python -X utf8 examples/comparisons/three_method_resource_batches.py --minimum-seconds 2
```

PyCharm 配置：`Three_Method_Resource_Batches`。结果在
`outputs/case_studies/three_method_comparison/resource_batches/CPU_RAM长批次结果.md`，
包含每次求解CPU时间、单核/全机归一CPU比例、峰值工作集和提交内存。
原五次wall时间、Python峰值、逐事件/累计时间和失败路径保持独立口径。
探索/剪枝及模式检查计数另用不计时重放获得：
`python -X utf8 examples/comparisons/three_method_construction_counts.py`，数据在同目录 `construction_counts/`。

## 仓储 2018 复现、审稿核对与输出清理

```powershell
python -X utf8 examples/warehouse_2018/warehouse_2018_case_study.py --part all
```

PyCharm 配置：`Warehouse_2018_Case_Study`。输入规则及原始模型见
[examples/warehouse_2018](examples/warehouse_2018/README.md)，本轮结果在
`outputs/case_studies/warehouse_2018/运行结果.md`。
这是独立复现，不是作者源代码。两处控制动作和第二处 68 状态匹配；第一处为 101，
原文为 108，该差异尚未消除。公式解释与组件边界解释分开保存。
这份旧参考实验比较Full BTS、本文LL-BTS与仓储复现；上述新实验才是Cai/LLP-1992/本文三方法直接对比。
两组都使用新增的完全观测副本，原始61/1000输入不变；重规划失败与死锁分别记录。

审稿意见核对清单在论文目录 `Response/reviewer_gap_audit.md`。仍需处理的问题包括
Problem 1 的全局最大允许性主张、good 观测状态的固定模式活性，以及观测一致性的正式证明；
带有作者保护标记的公式未擅改。

`N_raw` 是剪枝前决策/观测状态总数的理论上界。`O(N_raw)` 是状态计数的空间阶，
不是实测 RAM；实际集合与状态转移的编码开销另计。

旧中间输出已清理，仅保留当前 case study、原始输入与修改意见、资源数据和绘图记录。
清单见 `outputs/revision_materials/pair_states_final_20261123/cleanup_manifest.json`。
以后可先用 `python -X utf8 scripts/maintenance/clean_non_case_outputs.py` 检查，确认清单后用 `--apply` 清理。
后文历史脚本的旧输出可能已删除，命令仍可用于重新生成。

## 成对决策状态修正及全部重跑结果

Full BTS 和 LL-BTS 都实际存储 `(q_hat, x_hat)` 决策状态；不同 `q_hat` 不合并。
同一估计共用控制模式和不可变 UR/NX 计算结果，以保持部分观测控制的一致性。
构建图先记录全部候选模式（包括不安全模式），再记录剪枝；每个 LL 作图目录包含
`construction_steps.jsonl`、逐步 JSON/PNG、`ll_bts_construction.gif` 和最终合并结果。
旧实现确有状态合并问题，因此本轮已重新运行全部当前实验，不是只修改显示标签。

权威数据目录：`outputs/revision_materials/pair_states_final_20261123/`。
其中 `corpus/` 是独立论文比较，`cpu/` 是独立资源批次，`large/` 是八个大系统，
`trajectories/` 是逐观测累计运行，`fig1/` 是论文图。各阶段退出状态在 `stage_profiles/`。

```powershell
python -X utf8 scripts/maintenance/rerun_all_pair_states.py
python -X utf8 examples/paper/print_paper_figure_reference.py --u 5
python -X utf8 examples/paper/print_paper_figure_reference.py --full
```

总入口默认检查并跳过已有成功阶段。需要独立复现时使用新目录，例如
`python -X utf8 scripts/maintenance/rerun_all_pair_states.py --output outputs/pair_states_independent`。
PyCharm 运行同名脚本，Working directory 为本项目目录，Parameters 为上述参数。

当前共 112 项正确性测试通过。1,061 个初次综合的可解性与 Full 完全一致，但根极大模式仅
1,054 例一致，不混淆这两个指标。初次平均时间 Full/LL 为 0.638/0.145 ms；独立的
逐观测累计实验为 0.937/1.266 ms，后者 LL 更慢，负结果保留。
理论证明、资源口径和五组详细实验统一在论文目录的 `Response/supplementary_material.R1.tex`，
由 `Response/LCSS_26-1509_Response_Template.tex` 在回复信后通过 `\input` 引入。

## 当前实现：危险终点检测与观察后重新建窗

`Q_f` 仍不包含 `Q_d`；ReverseDFS 的危险终点改为 `Q_f ∪ Q_d`。代码通过
`pre.lookahead_lower_bound` 获取论文的 `bar_u`，`pre.u_f` 为兼容字段，
`pre.horizon` 也返回该阈值；`pre.u` 只保存含 `Q_e` 的可选扩展对照值。
每个完整决策估计重新计算 `x_L = Post_<=u(x_hat)`。执行前检查完整 UR/NX、
逐状态活性和所有可能观测的保留延续，不能把未知边界当作安全延续。
检测阈值本身不保证固定 u 下必然成功，初始求解仍可返回 inconclusive 并增大 u。

本轮原始15状态论文模型得到 `bar_u=4`，并在 `u=4` 返回 winning；
当前 Fig.1 按参考 PDF 第9页，只增加 `q14--a-->q15--b-->q16`，共17状态，
`Q_f={q14,q15}`、`bar_u=4`；u=4可解，u=5匹配 Full 根极大模式。
此前19状态的长链版本保留存档。输入见 `examples/paper_fig1_r1/plant.json`，
用 `python -X utf8 examples/paper/rebuild_fig1_r1.py` 复现，输出见 `outputs/revision_materials/fig1_r1_20261123/`。

61个审阅模型与1,000个保存的随机模型均已重跑并检查策略。权威新数据在
`outputs/revision_materials/pair_states_final_20261123/`；
逐例 LL-BTS、offline BTS、监督器及闭环已同步到 `outputs/expanded_yin_benchmark/`。
手写修改意见和原始 plant 输入保持原样。

## 当前大规模例子：非零前视阈值与零阈值对照

正文 E/H/P/C 的当前生成与测量入口为 `examples/large_scale/nonzero_lookahead_cases.py`。
它在原生成器之后重标记死锁链末端事件，事件属性集合不变；E/P/C 的末端两条
`a` 转移改为 `u`，H 的末端一条改为 `u`。因此不可观测路径可以进入
`Q_f ∪ Q_d`。仍可禁用可控的分支入口事件 `b`，得到无死锁监督器。
补充材料另列完全不改的 `E4_zero`，说明 `bar_u=0` 时仍从 `u=1` 求解。

```powershell
python -X utf8 examples/large_scale/nonzero_lookahead_cases.py --run
python -X utf8 examples/large_scale/nonzero_lookahead_cases.py --run --cases E4 E4_zero --repetitions 3
```

本次成对状态修正后的权威结果汇总在
`outputs/revision_materials/pair_states_final_20261123/large/combined.json`。
同目录保存八例的 Full/LL 构建、阈值、模式检查和 CPU/RAM 数据；所有运行均已完成。
今后默认输出到 `outputs/revision_materials/nonzero_lookahead_runs/` 下的新时间戳目录，避免覆盖存档。
原始输入保存在 [examples/large_scale](examples/large_scale/README.md)，运行脚本直接读取
其中的基底 JSON 和各系统 `model.json`，不以 `outputs` 中的导出副本作为输入。
其中 `combined.json` 是最新总表，`*_base.json` 保存 E/H/P 基底的全部转移，
`C_model.json` 保存百万状态 C 的精确生成参数，`*_closed_loop.json` 保存闭环。
所有乘积均显式构建全局 DFA 后计算状态子集、阈值和全局 BTS/LL-BTS；
不套用旧生成器的状态数、阈值或内存预测公式。
Full/LL 均用新进程测量并计入输入建立；LL 还计入结构分析和全部初始前视尝试。
策略检查与文件导出不计入计时。当前正文各项均为一次完整测量；
默认运行 E5/H3/P5/C/零阈值对照各一次，可用 `--repetitions 3` 增加产品重复次数。
可在 PyCharm 中运行 `examples/large_scale/nonzero_lookahead_cases.py`，Parameters 填 `--run`，
Working directory 设为本项目目录。

| 系统 | DFA 状态数 | bar_u / 采用 u | Full 状态数 | LL 状态数 | Full/s | LL/s |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| E5 | 100,000 | 10 / 10 | 730,049 | 321,505 | 73.035 | 70.659 |
| H3 | 1,000,000 | 3 / 3 | 8,589,412 | 8,300,166 | 179.448 | 283.543 |
| P5 | 100,000 | 10 / 10 | 1,397,964 | 842,129 | 169.459 | 287.450 |
| C | 1,000,000 | 2 / 2 | 3,000,120 | 509 | 42.587 | 13.856 |
| E4_zero | 10,000 | 0 / 1 | 118,896 | 71,279 | 5.005 | 2.536 |

更大一档的尝试使用独立输出目录，避免覆盖以上数据：

```powershell
python -X utf8 examples/large_scale/nonzero_lookahead_cases.py --run --cases E5 P5 H3 --repetitions 1 --max-memory-gib 20
```

Full/LL 五例可解性和初始包含极大模式均一致，均可综合无死锁监督器。
这里状态数为剪枝前构建数量；E5/H3/P5 的 LL 时间均更长，保留该结果。
P5 完整进程峰值为 Full 8.02 GiB、LL 9.08 GiB，包含后续验证及闭环导出，
不能把其构建状态减少率当作峰值内存节约率。详细口径见当前汇总目录的 `运行结果.md`。

## 先前零阈值模型的测量存档

以下数据对应修改前的 E/H/P/C，并非当前正文中的非零阈值模型。
`scripts/maintenance/rerun_large_recentered.py`、`examples/large_scale/early_stop_products.py`、`examples/large_scale/large_scale_overall.py`
仍保留该旧模型用于复现历史结果，其中的乘积计数和资源公式不能套用到新模型。

| 系统 | 全局 DFA 状态数 | Full 状态数 | LL 状态数 | Full/s | LL/s |
| --- | ---: | ---: | ---: | ---: | ---: |
| E_4 | 10,000 | 114,438 | 71,279 | 3.981 | 3.027 |
| H_2 | 10,000 | 49,200 | 47,451 | 0.843 | 1.434 |
| P_4 | 10,000 | 170,000 | 114,052 | 4.797 | 5.926 |
| C | 1,000,000 | 3,000,000 | 383 | 43.275 | 12.334 |

所有表中状态数均为剪枝前构建数量。E/H 是五次平均时间；P/C 是 overall
脚本的单次完整运行，含两侧的进度跟踪和输入建立，LL 另含结构分析及全部前视重试。
不把这些不同测量口径混成同一个重复实验平均值。所有已完成策略均经过完整检查。

E7/E8/H4/P6/P7/P8 的重新建窗 LL-BTS 必需存储下界分别约为
589.4/10480.0/2254.1/69.7/1414.0/28326.3 GiB（含必需NX项），因此资源检查后未将其当作完成的运行。
这不是 losing 判定。旧的143、273、3639或1007718状态数据只对应旧固定窗口，已从正文比较表移除。

```powershell
python -X utf8 examples/comparisons/compare_deadlock_target_bound.py
python -X utf8 examples/paper/manuscript_case_studies.py --part small --output outputs/recentered_paper
python -X utf8 examples/paper/manuscript_case_studies.py --part corpus --output outputs/recentered_corpus
python -X utf8 scripts/maintenance/refresh_recentered_benchmarks.py
python -X utf8 examples/comparisons/compare_online_offline.py --repetitions 11
python -X utf8 examples/comparisons/randomized_online_offline.py --samples 1000 --repetitions 5 --seed 20261121
python -X utf8 examples/large_scale/early_stop_products.py --case E --copies 4 --max-memory-gib 4
python -X utf8 examples/large_scale/early_stop_products.py --case H --copies 2 --max-memory-gib 4
python -X utf8 examples/large_scale/large_scale_overall.py --run --cases products --copies 4 --methods full ll --max-memory-gib 4
python -X utf8 examples/large_scale/large_scale_overall.py --run --cases chain --methods full ll --max-memory-gib 8
```

完整大系统复现入口为 `python -X utf8 scripts/maintenance/rerun_large_recentered.py`。

Full 时间外推仍可用 `examples/large_scale/estimate_full_runtime.py`，但当前正文表格只保留新版本实际完成的测量。
历史外推和固定窗口测量保存在原目录，不能替代新实现的 LL 结果。

## PyCharm 启动方式

项目已增加以下运行配置，打开本项目后可从右上角运行配置列表或 **Run → Edit Configurations** 中选择并运行：

| 配置名 | 执行内容 |
| --- | --- |
| `E_self_products_1e7_1e8` | E 的七重、八重自乘积 |
| `H_self_product_1e8` | H 的四重自乘积 |
| `LL_P7_P8` | 原 P7/P8 的 LL 资源检查及条件运行 |

配置文件在 `.idea/runConfigurations/`，使用项目模块的 Python SDK，工作目录为项目根目录。E/H 的启动文件也可直接在 PyCharm 中右键 **Run**；若打开的是上一级 `des_common` 项目，可直接右键这些启动文件，无需改动现有项目。启动文件会定位到本目录，避免相对路径错误。

P7/P8 配置等价于下面的命令，`ll` 是两个小写字母 L，不是数字 `11`：

```powershell
python -X utf8 examples/large_scale/large_scale_overall.py --run --cases products --copies 7 8 --methods ll --max-memory-gib 10
# 也可右键运行下列启动文件
python -X utf8 examples/large_scale/run_P7_P8_LL.py
```

该配置会分别检查 Full/LL 中所选方法的资源需求；当前仅请求 LL。本机无法容纳 P7/P8 的 LL 必需存储，因此会正常提示跳过，而非绕过内存检查。E/H 是新设计的、更早进入安全延续的自乘积，不等同于原 P7/P8。

## 大规模总体运行（无固定时间预算）

在 Windows 项目目录运行 [examples/large_scale/large_scale_overall.py](examples/large_scale/large_scale_overall.py)。默认只估算 Full 和 LL 的节点、时间与内存；`--run` 才执行综合。该入口没有默认的时间、模式数或窗口状态上限，与 `examples/large_scale/hard_product_case_studies.py` 的短预算测试分开。

```powershell
python -X utf8 examples/large_scale/large_scale_overall.py --estimate-only
python -X utf8 examples/large_scale/large_scale_overall.py --run --cases products --copies 6 --methods ll --max-memory-gib 10
```

第二条命令从正整数前视开始扫描，直到得到明确结果，并验证保留策略。`--max-memory-gib 10` 只限制子进程工作集内存，不限制运行时间。默认输出目录带时间戳，位于 `outputs/revision_materials/large_scale_overall_*/`；结果 JSON 每约五秒保存一次进度摘要。摘要不是可恢复的搜索快照，Ctrl+C 停止后重跑会重新计算。

```powershell
# 同时检查 Full 与 LL；逐方法跳过内存无法容纳的构建，另一方法仍可执行。
python -X utf8 examples/large_scale/large_scale_overall.py --run --cases products --copies 6 --methods full ll

# 单独重跑百万状态链式系统，不设置固定时间上限。
python -X utf8 examples/large_scale/large_scale_overall.py --run --cases chain --methods full ll --max-memory-gib 10
```

要在自己的机器上标定 LL 时间与内存，可先跑一个小乘积，再传入标定结果：

```powershell
python -X utf8 examples/large_scale/large_scale_overall.py --run --cases products --copies 5 --methods ll --final-window-only --output outputs/my_product5
python -X utf8 examples/large_scale/large_scale_overall.py --estimate-only --calibration outputs/my_product5/products_5_ll.json
```

`--final-window-only` 用于乘积的已知最小成功前视 `u = k+1`，不计初始逐深度扫描；使用它得到的时间不能冒充完整前视搜索时间。`--export-closed-loop` 可在策略验证后额外枚举闭环。Full 的 UR/NX 抽样外推只估计这一阶段，不是完整综合总耗时；LL 的时间和峰值外推使用已完成的小乘积标定，并明确记录外推口径。

当前机器约31.76 GiB RAM；新的乘积存储下界及资源检查见上表与补充材料。不要使用旧固定窗口的P6/P7/P8存储值推断新实现能否完成。历史运行保留在原目录。

### 前视阈值、观察后重新建窗与无死锁保证

当前实现从Q_f并Q_d执行反向DFS求检测阈值，并在每个完整决策估计处重新建窗。Q_f仍只包含非死锁的单后继链状态，不将Q_d混入Q_f。

原始15状态系统的Q_f为空，但Q_d非空，新阈值bar_u=4；u=4返回winning。初始选择允许{a,o2}、禁用b，UR={q0,q1,q2,q3}，观察o1后NX={q6}，随后从{q6}重新建窗，保留q6-a-q7-u-q6的安全循环。

历史四状态长链的19状态版本得到bar_u=6：q6-a-q7-b-q15-u-q16-u-q17-u-q18-u-q12共六步。该版本u=4已可得到安全但较保守的初始模式{a,o2}，u=5恢复offline初始极大模式{a,b,o2}；默认从bar_u开始时采用u=6。

旧实现所有内部后继共用初始窗口，因此曾记录u=5/6的差异；这些旧数值不能继续描述重新建窗后的实现。当前每个保留模式都通过完整UR/NX、逐状态活性及后继一致性检查，不是先执行模式、再假定下一次重新求解必然成功。

bar_u是危险状态检测的充分阈值，不单独等于最小成功前视，也不单独证明综合可解。即使覆盖Q_f并Q_d，安全不可观测环的完整UR仍可能需要更大的窗口；程序在尚不能建立完整延续时返回inconclusive并增大实际u。


## 代码模块与审阅入口

先阅读 [CODE_REVIEW_GUIDE.md](docs/local/CODE_REVIEW_GUIDE.md)，再按“模型→预处理→LL-BTS→传统BTS对照→闭环→实验统计”的顺序检查。
[代码审阅快照](outputs/code_review/code_review_bundle.zip) 包含当前源码、测试、依赖清单和文件哈希；不包含虚拟环境、论文PDF及运行输出数据。

| 模块 | 职责与关键入口 |
| --- | --- |
| [des_core/automata.py](des_core/automata.py) | 部分定义DFA和DESExample数据结构；转移映射不可变 |
| [examples/non_deadlock.py](examples/non_deadlock.py) | 项目原有例子及论文分量的当前代码版本 |
| [examples/yin_literature.py](examples/yin_literature.py)、[review_amendments.py](examples/review_amendments.py) | 论文原始转录、逐例修改和去重；amended=False读取修改前设计 |
| [des_core/certified_lookahead.py](des_core/certified_lookahead.py) | preprocess计算Qd/Qf/Qe及深度；limited_ur/limited_nx按论文公式截断；limited_choice构建局部分支；complete_choice独立检查完整物理行为；solve_limited_lookahead构建、剪枝认证LL-BTS；Limited_Lookahead_Controller保留完整观测估计 |
| [des_core/offline_bts.py](des_core/offline_bts.py) | 独立传统BTS；traditional_ur走零步或多步不可观事件，traditional_nx针对一个可观事件走一步；traditional_ur_nx保留批量单事件NX的组合接口 |
| [des_core/closed_loop.py](des_core/closed_loop.py) | 恢复保留策略，提取观测反馈supervisor，构建实际状态×控制器记忆的可达闭环 |
| [des_core/asynchronous_product.py](des_core/asynchronous_product.py) | 隐式异步乘积；事件带副本下标，继承各分量的控制/观测属性 |
| [examples/large_scale/large_scale_overall.py](examples/large_scale/large_scale_overall.py) | Full/LL资源估算和无固定时间预算的总体运行；进度日志、可选内存保护、完整策略验证 |
| [examples/large_scale/nonzero_lookahead_cases.py](examples/large_scale/nonzero_lookahead_cases.py) | 当前正文非零阈值 E/H/P/C 与补充材料零阈值对照；显式全局结构分析、独立 Full/LL 测量、闭环与原始数据导出 |
| [examples/paper/rebuild_fig1_r1.py](examples/paper/rebuild_fig1_r1.py) | 按参考 PDF 第9页重建17状态 Fig.1，重新生成LL-BTS并逐模式核对第10页 |
| [examples/large_scale/early_stop_products.py](examples/large_scale/early_stop_products.py) | 当前 E/H 基底、自乘积、精确全局子集与实际全局 LL-BTS；小乘积对照、五次计时及图结构导出 |
| [examples/benchmarks/expanded_yin_benchmark.py](examples/benchmarks/expanded_yin_benchmark.py)、[examples/benchmarks/structural_benchmark.py](examples/benchmarks/structural_benchmark.py) | 构建当前61例，扫描u并导出LL-BTS/BTS及模型数据 |
| [examples/comparisons/compare_online_offline.py](examples/comparisons/compare_online_offline.py) | 11次交替新鲜测量、独立内存峰值、根模式与可解性对照；--refresh-report只刷新已有数据 |
| [examples/comparisons/randomized_online_offline.py](examples/comparisons/randomized_online_offline.py) | 固定种子的随机实验；online只依自身判定加深，不用offline结果选择u |
| [des_core/graph_size_metrics.py](des_core/graph_size_metrics.py)、[des_core/comparison_averages.py](des_core/comparison_averages.py) | 构建/保留节点计数、均值、负节约及结果一致性 |
| [scripts/reporting/complexity_memory_report.py](scripts/reporting/complexity_memory_report.py) | 理论时空公式、参数代入、抽象成本代理与实际Python峰值的区分 |
| [scripts/reporting/draw_closed_loops.py](scripts/reporting/draw_closed_loops.py)、[des_core/plot_automaton.py](des_core/plot_automaton.py) | 策略与完整闭环图、避免经过无关节点的plant连线 |
| [scripts/local/write_benchmark_review.py](scripts/local/write_benchmark_review.py)、[scripts/reporting/benchmark_review_results.py](scripts/reporting/benchmark_review_results.py) | 事件审阅文档、双语总表、均值与逐例分析；保留修改意见 |
| [examples/large_scale/revised_large_products.py](examples/large_scale/revised_large_products.py) | 认证分量supervisor的精确组合证明；不把分量节点数冒充全局BTS节点数 |
| [examples/paper/rerun_paper_examples.py](examples/paper/rerun_paper_examples.py)、[examples/paper/paper_example_models.py](examples/paper/paper_example_models.py) | 论文图与当前代码版本分开重跑、标签差异检查、完整可行闭环及组合式supervisor验证 |
| [scripts/maintenance/sync_paper_example_results.py](scripts/maintenance/sync_paper_example_results.py) | 备份后同步活动论文的case study和新图，保留原始tex与归档 |
| [tests/](tests/) | 认证正确性、独立offline、闭环、指标口径与模型修改的回归检查 |

历史实现 `des_core/ll_bts.py`、`ll_bts_synthesis.py`、`factored_synthesis.py`、`implicit_product.py` 以及 `examples/basic/case1_product_benchmark.py` 用于复现旧图和物理根查询。其轨迹完成次数不能直接作为当前部分观测认证supervisor的证明。

当前局部算子为 `x = UR_gamma(x_hat) ∩ x_L`、`x_hat_next = NX_sigma(x) ∩ x_L`；局部结果与完整物理后继不一致时，作为未认证边界处理。这里的交集限制终点，不限制路径中间状态，因此精确UR仍可能访问窗口外状态，不能声称UR计算成本完全局限在窗口内。[本次正确性验证](outputs/limited_lookahead_correctness/validation.json) 覆盖61例与固定种子20261121的1,000个已保存随机系统。当前61例和1,000个随机例子均已按观察后重新建窗的实现重测，具体数据以本轮目录为准。

当前论文图和结果见 `outputs/revision_materials/pair_states_final_20261123/`。旧 `outputs/paper_examples_rerun/` 中的固定窗口性能是历史记录；组合式可行监督器仍须与全局显式BTS综合区分。

2026-11-21 用户审阅修订：活动基准为 **58个论文改编模型＋3个结构测试，共61例，36例winning、25例losing**。
原始设计快照保存在各例 `plant_original.json/png`；按表修改与去重记录见 `review_modifications.json`。
`16WODESmax_fig_3a_Gprime` 已给6、6′添加c2自环；`20CDC2_fig_2b` 已按最新意见给2添加b自环、给6添加c自环，当前没有暂缓冲突。
`outputs/expanded_yin_benchmark/运行结果.md` 的最上方总表包含状态数、可观/可控事件、最小u及online/offline数值对比。
总表另含BTS/LL-BTS的D/O、构建节点总数及节点节约率；61例为3346→830，减少75.19%。
`COMPLEXITY_AND_MEMORY_CALCULATION.md` 给出时间/空间理论式、逐例参数代入和tracemalloc峰值口径，理论代理值不冒充实测时间或内存。
`python -X utf8 examples/comparisons/randomized_online_offline.py --samples 1000 --repetitions 5 --seed 20261121` 在 `randomized_comparison/` 保存全部随机输入与原始测量。
这批分层随机分布中平均时间0.523862→0.072462ms（节约86.17%），可解性1000/1000一致、根极大模式991/1000一致；不使用offline结果选择online的u。
两个论文乘积位于 `large_systems/`，使用 `python -X utf8 examples/large_scale/revised_large_products.py` 复现组合式online综合；
`python -X utf8 scripts/maintenance/refresh_large_catalogue.py` 更新六个大系统的分量图/模板及说明，不执行offline求解。

当前 draft 的实现入口是 `python examples/benchmarks/certified_benchmark.py --samples 600 --seed 20261120`，
或直接 `python examples/basic/des_dfa_on_the_fly.py`。它先完整扫描显式 DFA，计算 `Qd/Qf/Qe/u`，
然后按完整状态估计构建、剪枝 LL-BTS；只有完整 `UR/NX` 和无控制死锁检查通过才返回
`winning`，窗口不足返回 `inconclusive`。`Limited_Lookahead_Controller` 保留已经证明的后续控制，
防止重规划窗口变化丢掉原有安全证据。不会依据一个实际物理后继重置部分观测估计。

34 个论文自动机、2 个项目例子、逐例选取的 `u`、LL-BTS 图与 JSON、600 个随机样本的
数据位于 `outputs/certified_yin_benchmark/`，解释和正确性限制见该目录的 `report.txt`。
源论文和官网目录记录位于 `__ref/yin2016/`。
随机实验的 `draft_u` 并非普遍可解性保证；无死锁保证仅适用于已经认证的策略。

2026-11-21 最初扩充至61个论文自动机；本轮去重后 `python -X utf8 examples/benchmarks/expanded_yin_benchmark.py` 测试 **58个论文改编模型**，输出位于 `outputs/expanded_yin_benchmark/`。
每例扫描所有 `u=0..|Q|-1`，分别记录最小可判定深度和恢复离线根极大控制模式的最小深度，
所选深度同时满足草稿阈值与离线根模式一致。每例导出原自动机、认证 LL-BTS、完整离线 BTS、
策略轨迹及来源图号/URL/SHA256。官网222条目录记录和105份相关PDF的文本筛查记录位于
`__ref/yin2016/expanded_inventory.json`；这不等于逐篇全文精读或覆盖官网以外的全部论文。
部分验证类来源需新增控制划分，分散控制来源使用集中式观测并集，均在来源备注中明确区分。
上述 `examples/benchmarks/certified_benchmark.py` 也已接入扩充语料；旧输出中的34例是此前保存的结果。

`python -X utf8 scripts/reporting/draw_closed_loops.py` 为58个论文模型、3个结构测试及6个项目配置导出闭环系统，
打开 `outputs/closed_loop_systems/index.html` 浏览，或下载 `outputs/closed_loop_systems.zip`。
每个可解例子固定选择一个认证的包含极大控制模式策略，绘制实际DFA状态与控制器记忆的
可达乘积，包含全部允许的事件演化，不可观测事件保持记忆不变。安全证书终端采用允许全部
事件的延续并展开。项目部分观测封装使用 `original_dfa`，不将绘图用observer作为被控对象。
不可解例子仅标记不可解并展示原图。图集不表示所有策略的并，也不模拟逐步重新规划。
论文模型的主输出同时保存在原来的 `outputs/expanded_yin_benchmark/<example>/` 中：
直接读取 `plant.json` 与 `ll_bts.json` 的剪枝保留边，提取 `supervisor.json`，再生成
`closed_loop_system_online.json`、闭环与监督器图。当前基准共61个模型，36个可解例子各选取一个策略，25个不可解例子明确标记。
入口为 `outputs/expanded_yin_benchmark/closed_loop_index.html`，来源SHA256记录在每例JSON中。

`python -X utf8 examples/benchmarks/structural_benchmark.py` 新增16状态长单链、15状态链接环再接两条出口链、
11状态链接内外嵌套环三个合成模型，单独记录在 `structural_results.json`，不计入论文模型数量。
运行后执行 `python -X utf8 scripts/reporting/draw_closed_loops.py` 生成监督器与闭环。
`python -X utf8 scripts/local/write_benchmark_review.py` 生成基准目录中的两个 Markdown 文件：
`系统事件属性与修改意见.md` 保留事件划分及逐例修改意见；`运行结果.md` 记录可解性及剪枝原因、
online/offline图规模、监督器行为、闭环、时间/内存数值与运算，以及两个千万状态乘积的实际验证及估算限制。
原有修改意见和生成分析区外的手写内容保留；两个文件提供互相跳转链接。
`single_state_plant_audit.json` 按原始plant状态数检查单状态例子；当前没有此类plant，无需删除。

`python -X utf8 examples/comparisons/compare_online_offline.py --repetitions 11` 为61个模型生成独立传统offline BTS：
完整已知系统上枚举控制模式并计算UR/NX，先建BTS再剪枝，不用窗口或Qf/Qe证书。
每例新增 `offline/bts.*`、`supervisor_offline.*`、`offline/closed_loop_system_offline.*` 和
`online_offline_comparison.json`。旧的不合要求的 `offline/ll_bts.*` 已删除，清单另存。
汇总见 `ONLINE_OFFLINE_COMPARISON.md` 和 `online_offline_comparison.csv`，包含预处理、
交替顺序重复计时、独立Python内存峰值、真实节点/边数及理论复杂度的适用范围。
打开 `online_offline_index.html` 可逐例并排查看online/offline闭环及对应BTS、监督器和测量。
`python -X utf8 examples/large_scale/large_online_offline.py` 在 `large_systems/` 中运行两个完整的大型索引系统
（279936状态长链、1679616状态链加环，均完全观测/单不可控事件），并预算内尝试原7/8副本
部分观测产品；后者未完成BTS综合，不计算节约率，另提供完整验证过的可行常量策略。
不能把新结构化系统的成功测量或该候选策略冒充原产品的完整最大宽松综合。

对比JSON/CSV/HTML还提供时间秒/ms、内存bytes/KiB/MiB、绝对差、速度倍数与百分比公式。
历史实验 `examples/large_scale/literature_product_forecast.py` 从已可解的论文例子 `21AutomaticaOptimal_fig_2`
构造原属性不变的六副本异步乘积：15^6=11390625个可达状态。该全部安全的例子使用精确组合式
Qe证书，在窗口展开前终止；实际online计时包含这一步结构预处理，不能冒充显式扫描千万状态。
传统逐模式BTS的根阶段用目标规模实际UR/NX抽样估算；完整offline未运行，不能把估算当作实测。
旧报告与原始样本已归档在 `tmp/user_review_revision_20261121/previous_large_products/`，新结果使用 `large_systems/`。

`python -X utf8 examples/large_scale/revised_large_products.py` 实际综合并验证两个修订后的论文大乘积：
`21AutomaticaOptimal_fig_2` 六副本（11390625状态）和 `18TACrange_fig_3a` 七副本（19487171状态）。
均保留当前部分观测/控制划分，组合式分量supervisor证明覆盖完整闭环；每例另执行100000步真实闭环运行，
并对1/2/3副本做全可达状态/全转移验证。修改后的18TACrange不能再使用旧的全Qe/全部允许证书。
结果入口为 `large_literature_supervisors.html`。每例有可执行 `supervisor_online.py`、监督器JSON、
精确因子化闭环、分量LL-BTS图、实际计时样本和 `SYNTHESIS_AND_VALIDATION.md`。未测全局最小u。
未逐一展开千万状态，未运行完整offline BTS；随机测试不是安全性证明的替代。

下面的历史绘图函数和 `examples/basic/case1_product_benchmark.py` 仍使用旧版乐观窗口算法，供复现旧图。
其中的 `pending`、计时和隐式乘积结果不能作为新版推论的正确性或性能证据。

离散事件系统（DFA）的局部无死锁监督控制：固定窗口
`x_L = Post_<=u(q)`，构造 LL-BTS，再由 Algorithm 2 剪枝并选择包含关系极大的控制模式。
这里的目标是 **deadlock-free**，不是带标记状态的 nonblocking。

## 安装与运行

在项目根目录执行，安装依赖时使用与运行相同的 Python：

```powershell
python -m pip install -r requirements.txt
```

常用运行命令：

```powershell
python -c "from examples.basic.des_dfa_on_the_fly import main_example2_partial; main_example2_partial()"
python .\examples/basic/case1_product_benchmark.py --copies 8 --iterations 100 -u 3
```

第一条生成 Example 2 的原图、各物理分支的 LL-BTS 动画和逐帧转移报告；
`python examples/basic/des_dfa_on_the_fly.py` 也运行该例。
第二条运行 Example 1 的八副本异步积（1,679,616 个可达产品状态），
前视窗口为 3，最多执行 100 次在线控制综合。

较小规模的四副本命令也可使用：

```powershell
python .\examples/basic/case1_product_benchmark.py --copies 4 --iterations 20 -u 3
```

六位数状态的 Example 1 n-copy（也是基准程序的默认配置）：

```powershell
python examples/basic/case1_product_benchmark.py --copies 7 --iterations 20 -u 2
```

单个 Example 1 有 6 个可达状态，7-copy 有 **279,936 个可达产品状态**。
每个事件只更新一个副本；`a_i,b_i,o1_i` 可控，`o2_i,u_i` 不可控，
只有 `o1_i,o2_i` 可观测。保持原模型的事件属性，不构造完整产品图。
产品总状态数与实际访问数分别报告，不能把 279,936 当作已访问状态数。

默认每一步重新执行构造和综合，不使用跨步结果缓存；按保留的可观测后继轮转推进。
性能验收看 `step_seconds`，目标是每一步实际求解在一分钟以内。
窗口变大仍可能产生很大的信息状态空间，不能由产品状态数单独预测耗时。

历史实测（下述数据早于本次边标签修改，不代表当前模型）：7-copy、`u=2` 共完成 15 次实际求解，最慢一步 5.29 秒，
随后以 `empty_synthesis` 正常结束；累计访问 497 个具体状态。
原有 4-copy、`u=3` 命令完成全部 20 步，最慢一步 8.43 秒。
7-copy、`u=3` 的试跑首步超过一分钟，尚不属于已验证的达标配置。

当前 Example 1 的主循环为 `q0 --o2--> q1 --b--> q2 --a--> q0`。
已有基准输出属于旧标签模型；需重新运行才能获得当前模型的结果。

常用参数：

- `--quiet`：关闭进度显示；`--extra-plots`：额外生成 PNG 曲线。
- `--pattern-mode explicit`：完整枚举，适合小模型核对。
- `--pattern-mode factored`：默认，精确表示控制模式族；最终极大控制和后继与完整枚举一致。
- `--cache-size 32`：可选的相同根状态结果缓存；默认 0，计时验收关闭。

若综合结果为空或没有可用可观测后继，程序正常提前结束并记录 `stop_reason`。
这不等于真实系统已到达死锁，也不会强行走到指定迭代数。

## 输出

- 小例子：`outputs/example2_nested_cycles_deadlock_full_partial_observation/`。
  `ll_bts/branch_XXX/` 包含 GIF、PNG 和 TXT；同级的
  `物理分支选择记忆.json` 只影响绘图路径，删除它可重置历史。
- 产品例子：`outputs/case1_product_<n>copy_u<u>_<k>iter_<mode>_<policy>_uncached/`。
  `benchmark.txt` 是摘要，`benchmark.json` 保存每一步计时、访问量和后继，
  `visited_states_paper.pdf` 是曲线，`original_system.png` 是六状态组件图。

`factored` 的 O 节点数表示控制模式族，不是完整枚举的 O 节点数；
它还提前剪去已知不一致分支，因此具体状态访问量可能小于完整枚举。
实际控制必须取自 Algorithm 2 的输出，
不能直接执行尚未剪枝的模式族上界。

## 代码与验证

- `des_core/ll_bts.py`：局部构造；`ll_bts_synthesis.py`：Algorithm 2 入口。
- `control_reduction.py`、`factored_synthesis.py`：精确控制族压缩与反向剪枝。
- `asynchronous_product.py`、`implicit_product.py`：隐式异步积及在线基准。

```powershell
python -m unittest discover -s tests -v
```

优化依据、等价性论证和论文草稿中需作者核对的公式差异，见
[OPTIMIZATION_AND_CONSISTENCY_NOTES.md](docs/local/OPTIMIZATION_AND_CONSISTENCY_NOTES.md)。
