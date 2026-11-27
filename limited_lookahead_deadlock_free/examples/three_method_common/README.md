# 三种方法使用同一组输入的直接比较

这组比较的三种方法是 **Cai-2018、LLP-1992、本文 LL-BTS**。Full BTS 不占这三行。

```powershell
python -X utf8 examples/comparisons/three_method_comparison.py --repetitions 5
```

PyCharm 配置：`Three_Method_Common_Examples`。
输出目录：`outputs/case_studies/three_method_comparison/`。
先看其中的 `共同例子三方法对比.md`，每个例子和每个 N 都对应三行。

## 共同例子

- Ring2-FO：两个三状态环，共享可控 fail 事件通向共同死锁，10 个可达 plant 状态。
- Ring3-FO：三个四状态环，65 个可达 plant 状态。
- Fig1-FO：论文 17 状态例子的全观测副本。
- E2-FO、P2-FO：原有两个 10 状态分量的自乘积，全观测副本，各 100 个可达状态。

每个例子在 N=3、8、16 下运行三种方法。相同例子的模型哈希和可控事件一致，所有事件均可观；
原始部分观测实验不变。每个分量全部状态作为标记状态，排除 plant 死锁作为共同物理约束。

## 方法来源与实现

1. Cai-2018：Tatsumoto、Shiraishi、Cai、Lin，
   *Application of online supervisory control of discrete-event systems to multi-robot warehouse automation*，2018。
   https://www.caikai.org/publication/TatsumotoShiraishiCaiLin_18CEP.pdf
   使用 `des_core/warehouse_2018.py` 的 `interpretation='equations'`，按原文公式执行组件截断、组合和全局截断。
   原有 `component-frontiers` 解释仅作为另一个复现诊断保留，不作为这组主表的默认方法。
2. LLP-1992：Chung、Lafortune、Lin，
   *Limited lookahead policies in supervisory control of discrete event systems*，1992，非 1998。
   https://doi.org/10.1109/9.182478
   独立实现 `des_core/classic_llp_1992.py`，使用乐观边界，再做可控性/到标记状态的反向递推。
   对相同物理状态和相同深度共享结果，不跨深度合并；对本组状态型安全约束等价于完整前缀树。
   另用完整前缀树验证 640 个随机小窗口组合，覆盖两种边界态度。
   算法说明另参考：https://arxiv.org/abs/2006.06514
3. 本文：`des_core/certified_lookahead.py`，固定与其他两者相同的 N，包含一次完整结构分析。

三种方法都从同一组件输入开始，各自计算所需产品/窗口。N 的数值相同，但 Cai 的组件先截断与
经典方法的全局 N 步投影并不构成相同的物理状态集合；这正是两种算法的构造差异。

## 比较什么

每种方法、例子、N 在新进程中运行，初次求解时间取五次均值；Python 分配峰值在独立调用中测量。
OS CPU 时间、峰值工作集和提交内存来自该独立进程的初次求解批次，在 tracemalloc/闭环验证之前读取。
状态数分别是物理窗口状态、经典分层投影状态、LL-BTS 信息状态，保留结构类型说明，不计算相互节约率。

`*_validation.json` 对各方法自己的全部可达闭环分支进行穷举检查，保存控制、事件转移、CPU/RAM 和失败路径。
`*_trajectory.json` 是真正逐事件重新求解的一条采样轨迹，至多 50 个事件，固定种子 199212。
三种方法控制不同时轨迹可以不同；提前失败的短轨迹不能仅因累计时间较短而称为更快。

原文的 nonblocking 允许在标记状态停止，与本文要求每个可达状态均有允许事件的 deadlock-free 不同。
本实验不改写已发表方法去加入我们的活性检查，统一检查的是它们实际输出在共同例子上能否持续运行。
Ring 例子的所有合法状态都有不可控事件，因此三者可以共同满足这一持续运行条件。
Fig1-FO 用于呈现标记终止与持续运行要求的差异，不把这种差异说成原论文算法错误。
replanning_failure 仅表示可达状态上的局部求解失败，不是原系统全局不可解的证明。

输入和源码哈希、环境、重复次数、完整样本和单位定义均在 `manifest.json` 与各方法结果中。
旧的 Full/LL/Cai 实验仍保留，但它不能替代本组明确的 Cai/LLP-1992/LL-BTS 直接比较。

## CPU/RAM长批次补测

```powershell
python -X utf8 examples/comparisons/three_method_resource_batches.py --minimum-seconds 2
```

PyCharm：`Three_Method_Resource_Batches`。
45个方法/例子/N组合各使用一个新进程，预热一次后计时重复至少2秒，本次保存的补测累计237,528次根求解。
结果在 `outputs/case_studies/three_method_comparison/resource_batches/`，
先看 `CPU_RAM长批次结果.md`。这是独立资源批次，不替换五次初算wall均值。

- CPU时间为user+kernel；单次CPU时间=批次CPU时间÷完成次数。
- 单核比例=100×CPU时间÷wall时间，全机归一比例再除以16，不是整机其他程序的总CPU负载。
- RAM为进程峰值工作集（物理驻留内存），Commit为进程提交内存，MiB均按2^20换算。
- 进程内存包括解释器、共同输入、预热和求解，不包含后续验证/绘图/tracemalloc。
- 原短批次的零值或超过100%的CPU记录不删掉，以长批次数据作为稳定比例说明。
- 不保存随重复次数增长的结果列表，避免更快的方法因重复次数多而产生额外存储峰值。

补充材料还给出E2在(q9,q0)处是否允许b1的实测对照及失败路径，并明确本文u=3使用完整结构分析，
不能解释为只用同样的未来3步信息就比其他方法安全。Fig1的标记终止目标差异单独解释。

## 探索、剪枝和模式检查数

```powershell
python -X utf8 examples/comparisons/three_method_construction_counts.py
```

这是45次不计时构建重放，不改原求解器及已保存性能数据。结果在 `construction_counts/summary.json`。
保存raw/retained/removed状态和转移、可控分支、本文D/O细分及实际UR/NX模式检查数。
经典方法从实际计算结束时的投影读取计数，没有另造一个求解过程来代替原结果。
两种已发表方法从状态值计算控制事件集合，不枚举控制模式；其模式检查数为不适用，不能填写成0。
对于本文，分支是D→O控制模式转移；对于另两种方法，分支是可控事件转移，定义不同，不能直接计算相互节约率。
