# DES limited-lookahead control

2026-11-21 用户审阅修订：活动基准为 **58个论文改编模型＋3个结构测试，共61例，36例winning、25例losing**。
原始设计快照保存在各例 `plant_original.json/png`；按表修改与去重记录见 `review_modifications.json`。
`16WODESmax_fig_3a_Gprime` 已给6、6′添加c2自环；`20CDC2_fig_2b` 已按最新意见给2添加b自环、给6添加c自环，当前没有暂缓冲突。
`outputs/expanded_yin_benchmark/运行结果.md` 的最上方总表包含状态数、可观/可控事件、最小u及online/offline数值对比。
总表另含BTS/LL-BTS的D/O、构建节点总数及节点节约率；61例为3346→665，减少80.13%。
`COMPLEXITY_AND_MEMORY_CALCULATION.md` 给出时间/空间理论式、逐例参数代入和tracemalloc峰值口径，理论代理值不冒充实测时间或内存。
`python -X utf8 randomized_online_offline.py --samples 1000 --repetitions 5 --seed 20261121` 在 `randomized_comparison/` 保存全部随机输入与原始测量。
这批分层随机分布中平均时间0.523862→0.072462ms（节约86.17%），可解性1000/1000一致、根极大模式991/1000一致；不使用offline结果选择online的u。
两个论文乘积位于 `large_systems/`，使用 `python -X utf8 revised_large_products.py` 复现组合式online综合；
`python -X utf8 refresh_large_catalogue.py` 更新六个大系统的分量图/模板及说明，不执行offline求解。

当前 draft 的实现入口是 `python certified_benchmark.py --samples 600 --seed 20261120`，
或直接 `python des_dfa_on_the_fly.py`。它先完整扫描显式 DFA，计算 `Qd/Qf/Qe/u`，
然后按完整状态估计构建、剪枝 LL-BTS；只有完整 `UR/NX` 和无控制死锁检查通过才返回
`winning`，窗口不足返回 `inconclusive`。`CertifiedController` 保留已经证明的后续控制，
防止重规划窗口变化丢掉原有安全证据。不会依据一个实际物理后继重置部分观测估计。

34 个论文自动机、2 个项目例子、逐例选取的 `u`、LL-BTS 图与 JSON、600 个随机样本的
数据位于 `outputs/certified_yin_benchmark/`，解释和正确性限制见该目录的 `report.txt`。
源论文和官网目录记录位于 `__ref/yin2016/`。
随机实验的 `draft_u` 并非普遍可解性保证；无死锁保证仅适用于已经认证的策略。

2026-11-21 最初扩充至61个论文自动机；本轮去重后 `python -X utf8 expanded_yin_benchmark.py` 测试 **58个论文改编模型**，输出位于 `outputs/expanded_yin_benchmark/`。
每例扫描所有 `u=0..|Q|-1`，分别记录最小可判定深度和恢复离线根极大控制模式的最小深度，
所选深度同时满足草稿阈值与离线根模式一致。每例导出原自动机、认证 LL-BTS、完整离线 BTS、
策略轨迹及来源图号/URL/SHA256。官网222条目录记录和105份相关PDF的文本筛查记录位于
`__ref/yin2016/expanded_inventory.json`；这不等于逐篇全文精读或覆盖官网以外的全部论文。
部分验证类来源需新增控制划分，分散控制来源使用集中式观测并集，均在来源备注中明确区分。
上述 `certified_benchmark.py` 也已接入扩充语料；旧输出中的34例是此前保存的结果。

`python -X utf8 draw_closed_loops.py` 为58个论文模型、3个结构测试及6个项目配置导出闭环系统，
打开 `outputs/closed_loop_systems/index.html` 浏览，或下载 `outputs/closed_loop_systems.zip`。
每个可解例子固定选择一个认证的包含极大控制模式策略，绘制实际DFA状态与控制器记忆的
可达乘积，包含全部允许的事件演化，不可观测事件保持记忆不变。安全证书终端采用允许全部
事件的延续并展开。项目部分观测封装使用 `original_dfa`，不将绘图用observer作为被控对象。
不可解例子仅标记不可解并展示原图。图集不表示所有策略的并，也不模拟逐步重新规划。
论文模型的主输出同时保存在原来的 `outputs/expanded_yin_benchmark/<example>/` 中：
直接读取 `plant.json` 与 `ll_bts.json` 的剪枝保留边，提取 `supervisor.json`，再生成
`closed_loop_system_online.json`、闭环与监督器图。当前基准共61个模型，36个可解例子各选取一个策略，25个不可解例子明确标记。
入口为 `outputs/expanded_yin_benchmark/closed_loop_index.html`，来源SHA256记录在每例JSON中。

`python -X utf8 structural_benchmark.py` 新增16状态长单链、15状态链接环再接两条出口链、
11状态链接内外嵌套环三个合成模型，单独记录在 `structural_results.json`，不计入论文模型数量。
运行后执行 `python -X utf8 draw_closed_loops.py` 生成监督器与闭环。
`python -X utf8 write_benchmark_review.py` 生成基准目录中的两个 Markdown 文件：
`系统事件属性与修改意见.md` 保留事件划分及逐例修改意见；`运行结果.md` 记录可解性及剪枝原因、
online/offline图规模、监督器行为、闭环、时间/内存数值与运算，以及两个千万状态乘积的实际验证及估算限制。
原有修改意见和生成分析区外的手写内容保留；两个文件提供互相跳转链接。
`single_state_plant_audit.json` 按原始plant状态数检查单状态例子；当前没有此类plant，无需删除。

`python -X utf8 compare_online_offline.py --repetitions 11` 为61个模型生成独立传统offline BTS：
完整已知系统上枚举控制模式并计算UR/NX，先建BTS再剪枝，不用窗口或Qf/Qe证书。
每例新增 `offline/bts.*`、`supervisor_offline.*`、`offline/closed_loop_system_offline.*` 和
`online_offline_comparison.json`。旧的不合要求的 `offline/ll_bts.*` 已删除，清单另存。
汇总见 `ONLINE_OFFLINE_COMPARISON.md` 和 `online_offline_comparison.csv`，包含预处理、
交替顺序重复计时、独立Python内存峰值、真实节点/边数及理论复杂度的适用范围。
打开 `online_offline_index.html` 可逐例并排查看online/offline闭环及对应BTS、监督器和测量。
`python -X utf8 large_online_offline.py` 在 `large_systems/` 中运行两个完整的大型索引系统
（279936状态长链、1679616状态链加环，均完全观测/单不可控事件），并预算内尝试原7/8副本
部分观测产品；后者未完成BTS综合，不计算节约率，另提供完整验证过的可行常量策略。
不能把新结构化系统的成功测量或该候选策略冒充原产品的完整最大宽松综合。

对比JSON/CSV/HTML还提供时间秒/ms、内存bytes/KiB/MiB、绝对差、速度倍数与百分比公式。
历史实验 `literature_product_forecast.py` 从已可解的论文例子 `21AutomaticaOptimal_fig_2`
构造原属性不变的六副本异步乘积：15^6=11390625个可达状态。该全部安全的例子使用精确组合式
Qe证书，在窗口展开前终止；实际online计时包含这一步结构预处理，不能冒充显式扫描千万状态。
传统逐模式BTS的根阶段用目标规模实际UR/NX抽样估算；完整offline未运行，不能把估算当作实测。
旧报告与原始样本已归档在 `tmp/user_review_revision_20261121/previous_large_products/`，新结果使用 `large_systems/`。

`python -X utf8 revised_large_products.py` 实际综合并验证两个修订后的论文大乘积：
`21AutomaticaOptimal_fig_2` 六副本（11390625状态）和 `18TACrange_fig_3a` 七副本（19487171状态）。
均保留当前部分观测/控制划分，组合式分量supervisor证明覆盖完整闭环；每例另执行100000步真实闭环运行，
并对1/2/3副本做全可达状态/全转移验证。修改后的18TACrange不能再使用旧的全Qe/全部允许证书。
结果入口为 `large_literature_supervisors.html`。每例有可执行 `supervisor_online.py`、监督器JSON、
精确因子化闭环、分量LL-BTS图、实际计时样本和 `SYNTHESIS_AND_VALIDATION.md`。未测全局最小u。
未逐一展开千万状态，未运行完整offline BTS；随机测试不是安全性证明的替代。

下面的历史绘图函数和 `case1_product_benchmark.py` 仍使用旧版乐观窗口算法，供复现旧图。
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
python -c "from des_dfa_on_the_fly import main_example2_partial; main_example2_partial()"
python .\case1_product_benchmark.py --copies 8 --iterations 100 -u 3
```

第一条生成 Example 2 的原图、各物理分支的 LL-BTS 动画和逐帧转移报告；
`python des_dfa_on_the_fly.py` 也运行该例。
第二条运行 Example 1 的八副本异步积（1,679,616 个可达产品状态），
前视窗口为 3，最多执行 100 次在线控制综合。

较小规模的四副本命令也可使用：

```powershell
python .\case1_product_benchmark.py --copies 4 --iterations 20 -u 3
```

六位数状态的 Example 1 n-copy（也是基准程序的默认配置）：

```powershell
python case1_product_benchmark.py --copies 7 --iterations 20 -u 2
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
[OPTIMIZATION_AND_CONSISTENCY_NOTES.md](OPTIMIZATION_AND_CONSISTENCY_NOTES.md)。
