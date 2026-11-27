# 2018 仓储在线监督控制的独立复现

论文：Y. Tatsumoto, M. Shiraishi, K. Cai, Z. Lin,
Application of online supervisory control of discrete-event systems to multi-robot warehouse automation,
Control Engineering Practice 81 (2018), 97–104。

原文：https://www.caikai.org/publication/TatsumotoShiraishiCaiLin_18CEP.pdf

DOI：https://doi.org/10.1016/j.conengprac.2018.09.003

这是根据论文公式和图生成的独立实现，未找到或冒充作者源代码。
`models.py` 根据 Fig.3 的网格、式 (1)–(3) 的最短路径规则和 Fig.6 任务生成输入；
三个机器人分别为 34、25、25 状态，全部事件可观且可控。
任务 `(start, item, goal)` 为 `(7,32,70)`、`(4,18,64)`、`(1,38,67)`。

## 运行

在项目根目录运行：

```powershell
python -X utf8 examples/warehouse_2018/warehouse_2018_case_study.py --part all
python -X utf8 examples/warehouse_2018/warehouse_2018_case_study.py --part paper
python -X utf8 examples/warehouse_2018/warehouse_2018_case_study.py --part comparison --repetitions 5
python -X utf8 examples/warehouse_2018/warehouse_2018_case_study.py --part horizons
```

PyCharm 配置：`Warehouse_2018_Case_Study`。
或手动运行 `examples/warehouse_2018/warehouse_2018_case_study.py`，Parameters 填 `--part all`，
Working directory 设为项目根目录。

输出：`outputs/case_studies/warehouse_2018/`。
`paper/` 为原文数值核对和 50 事件任务轨迹，`comparison/` 为独立全观测对照，
`horizons/` 为前视长度与重规划可持续性检查。

## 必须保留的复现差异

- 原文打印公式：每个组件先截断，再组合，组合后再按全局 N 步截断，标记长度 N 的终点。
  对应 `interpretation='equations'`，是默认的公式解释。
- 另存的组件边界解释：保留组件截断的组合，并将各组件的边界/任务终点组合成标记集合。
  对应 `interpretation='component-frontiers'`。
  它能得到原文两处控制动作，第二处也得到原文的 68 个监督器状态。
- 第一处在组件边界解释下有 101 个可达保留状态，未复现原文的 108；
  不能把另一种解释或未核实状态数写成原算法已经精确复现。
- 公式解释第一处还允许事件 17，组件边界解释则禁用 17。两种结果均保留。

`des_core/warehouse_2018.py` 不调用本文的 BTS/LL-BTS、Q_f/Q_e、活性校验或安全延续判断。
nonblocking 的任务终点可以没有后续事件，因此不能直接当成本文的无限运行无死锁条件。

## 三方法比较的口径

Full BTS、本文 LL-BTS 和仓储复现只在新增的完全观测产品副本上比较；原始 61/1000 输入不变。
从相同的组件输入开始计时，Full/LL 包含全局组合，LL 还包含结构分析和初始前视扫描；
仓储方法只构建其所需局部组合。Python 分配峰值单独测量，验证和导出不混入根求解时间。
单进程的 Windows 工作集高水位可能继承前面的方法，不能据此直接比较方法峰值 RAM；
正式小例内存比较使用独立 tracemalloc 峰值，旧大型案例另有独立进程 RAM 记录。

每个仓储根模式还需在实际逐事件重建中独立验证。遇到空的局部监督器就记录
`replanning_failure` 并停止该分支，不伪造一个空模式继续执行，也不标记全局不可解。
验证不会替仓储方法修改控制模式。短窗口较快但无法持续执行时，不报告为同等保证下的加速。
