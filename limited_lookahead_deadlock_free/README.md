# DES limited-lookahead control

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
