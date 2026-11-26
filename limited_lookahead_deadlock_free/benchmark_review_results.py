"""Result-analysis sections for the user-editable benchmark review document."""

import json
from pathlib import Path
import re


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def event_set(values):
    return '`{'+', '.join(sorted(values))+'}`' if values else '∅'


def marked(kind, name, content):
    return f'<!-- {kind}: {name} -->\n{content}\n<!-- END-{kind}: {name} -->'


def replace_marked(text, kind, name, content):
    pattern = rf'<!-- {re.escape(kind)}: {re.escape(name)} -->\n.*?\n<!-- END-{re.escape(kind)}: {re.escape(name)} -->'

    return re.sub(pattern, lambda _:marked(kind, name, content), text, count=1, flags=re.S)


def root_rejections(plant, bts):
    observations = {n['id']:n for n in bts['O']}
    kept = {tuple(e) for e in bts['policy_edges']}
    outgoing = {q:[] for q in plant['states']}

    for q, event, target in plant['transitions']:outgoing[q].append(event)

    uncontrollable = set(plant['events'])-set(plant['controllable'])
    counts = dict(plant_deadlock=0, control_deadlock=0, successor_loss=0, retained=0)

    for source, target, label in bts['edges']:
        if source != bts['initial']:continue

        observation = observations[target];closure = observation['estimate']
        enabled = set(observation['pattern_controllable'])|uncontrollable

        if any(not outgoing[q] for q in closure):counts['plant_deadlock'] += 1
        elif any(not enabled.intersection(outgoing[q]) for q in closure):counts['control_deadlock'] += 1
        elif (source, target, label) not in kept:counts['successor_loss'] += 1
        else:counts['retained'] += 1

    assert sum(counts.values()) == 2**len(plant['controllable'])

    return counts


def reachable_cycle(plant):
    import networkx as nx

    graph = nx.DiGraph();graph.add_nodes_from(plant['states'])
    graph.add_edges_from((q, t) for q, e, t in plant['transitions'])
    reachable = nx.descendants(graph, plant['initial'])|{plant['initial']}

    return not nx.is_directed_acyclic_graph(graph.subgraph(reachable))


def model_analysis(root, row, plant, bts, closed):
    name = row['name'];folder = root/name
    pre = read(folder/'preprocessing.json')
    comparison = read(folder/'online_offline_comparison.json')
    offline_bts = read(folder/'offline/bts.json')
    offline_closed = read(folder/'offline/closed_loop_system_offline.json')
    on = comparison['online_storage'];off = comparison['offline_storage']
    rejected = root_rejections(plant, offline_bts)
    lines = ['### 运行结果与分析', '',
        f'- 判定：online **{bts["status"]}**，offline **{offline_bts["status"]}**；完整离线结论一致。',
        f'- 预处理：Qd={event_set(pre["Qd"])}；Qf={event_set(pre["Qf"])}；Qe={event_set(pre["Qe"])}。',
        f'- 深度：草稿阈值={pre["draft_u"]}；最小可判定u={pre["minimal_decisive_u"]}；'
        f'恢复offline根极大控制模式的最小u={pre["minimal_matching_u"]}；实际采用u={pre["selected_u"]}。',
        '  深度经过逐例扫描标定；草稿阈值本身不等于普遍可解性保证。', '',
        '| 结构指标 | Online LL-BTS | 传统 Offline BTS |',
        '| --- | ---: | ---: |',
        f'| 构建D节点 | {on["D"]} | {off["D"]} |',
        f'| 构建O节点 | {on["O"]} | {off["O"]} |',
        f'| 构建总节点D+O | {on["nodes"]} | {off["nodes"]} |',
        f'| 构建边 | {on["edges"]} | {off["edges"]} |',
        f'| 剪枝后保留D/O节点 | {on["retained_D"]}/{on["retained_O"]} | {off["retained_D"]}/{off["retained_O"]} |',
        f'| 剪枝后保留总节点 | {on["retained_D"]+on["retained_O"]} | {off["retained_D"]+off["retained_O"]} |']

    if bts['status'] == 'winning':
        assert closed and offline_closed['status'] == 'winning'
        lines += [f'| 所选闭环可达状态 | {len(closed["nodes"])} | {len(offline_closed["nodes"])} |',
            f'| 所选闭环可达转移 | {len(closed["edges"])} | {len(offline_closed["edges"])} |',
            f'| 所选控制器记忆状态 | {len(closed["controller"])} | {len(offline_closed["controller"])} |', '']

        if plant['initial'] in pre['Qe']:
            lines += ['**为什么可解：** 初始估计已完全落在Qe中，允许全部事件即可安全延续。'
                '因此online可以在根估计处采用安全终端证书，停止枚举O节点。'
                '这不是原始plant只有一个状态；物理闭环仍按实际DFA状态和控制器记忆展开。']
        else:
            lines += ['**为什么可解：** 初始估计不能直接用Qe证书终止，但剪枝后仍有认证控制模式。'
                '所选supervisor在每个估计处固定选择一个保留模式，所有可能观测均有认证后续控制，'
                '并检查不可观测可达集中的每个实际状态都有可用事件。']

        if name == 'structural_02_chain_cycle_two_tails_15':
            lines += ['本例的两条出口链分别通向终止状态q11、q14。'
                '所选策略在相关记忆处禁止危险出口x或y，保留前缀及 `q5→q6→q7→q8→q5` 的可持续循环。']

        if name == 'structural_03_chain_nested_cycles_11':
            lines += ['本例没有plant死锁：前缀接外环，q6处另接内环。'
                '允许在不可观测内环中持续运行并不违反无死锁目标；这里没有额外要求最终产生观测或退出内环。']

        memories = closed['controller'];controls = set(plant['controllable'])

        if all(set(m['controllable_pattern']) == controls for m in memories):
            lines += ['**实际控制行为：** 所有导出记忆状态的控制输出均允许全部事件，未禁用任何可控事件。'
                '保留的多个估计记忆不表示控制模式一定不同。']
        else:
            lines += ['**实际控制行为：** 不可控事件始终允许；下表列出选定online supervisor的控制输出。', '',
                '| 记忆 | 估计 | 允许的可控事件 | 禁用的可控事件 |',
                '| --- | --- | --- | --- |']

            for memory in memories:
                lines.append(f'| {memory["id"]} | {event_set(memory["estimate"])} | '
                    f'{event_set(memory["controllable_pattern"])} | '
                    f'{event_set(controls-set(memory["controllable_pattern"]))} |')

        if (len(closed['nodes']), len(closed['edges'])) != (len(offline_closed['nodes']), len(offline_closed['edges'])):
            lines += ['', '两侧所选闭环的节点/边数不同，说明所选策略或记忆图不同。'
                '当前只核对了根极大模式集合一致，并分别验证了闭环无死锁；不据此宣称两个完整闭环语言相同。']
    else:
        lines += ['', '**为什么不可解：** 完整已知系统的offline BTS也将初始决策节点剪除，'
            '因此这不是单纯u偏小造成的未判定；当前模型不存在满足本实验无死锁目标的supervisor。']

        if plant['initial'] in pre['Qd']:
            lines += ['初始状态本身没有任何出边，已经是plant死锁；控制只能删边，不能创造新出边。']
        elif plant['initial'] in pre['Qf']:
            lines += ['初始状态属于Qf：沿单后继状态链必然到达Qd。允许后继会走向死锁，'
                '禁用全部后继则直接引入控制死锁。']
        elif not reachable_cycle(plant):
            lines += ['从初始状态可达的原始图无环。有限无环系统的所有执行最终都到达无出边终点，'
                '仅通过禁用事件不能产生可持续运行的环。']

        if name == '14IFAC_fig_1':
            lines += ['本例虽有 `1 —b→ 2 —o→ 4 —c→ 1`，但b不可观测。'
                '到达1与隐藏到达2的观测历史相同，不能分别禁止/允许o。允许o会同时开放 `1 —o→ 5`，'
                '5允许a则到7死锁，禁用a则停在5；禁止o又使2无法安全继续，所以不能只保留期望的环。']

        if name == '16SEI_fig_4b':
            lines += ['**初始状态1与Qf：** 1沿a可到4、沿b可到2、沿o可到5；所有分支最终只能到无出边终点。'
                '因此1属于完整综合的必败状态集合。当前预处理Qf只收录单一后继链通往死锁的充分判据，'
                '1有多个不同后继，故不在当前定义的Qf中；不能把完整必败集合与局部Qf混同。当前通过正整数前视、完整UR/NX及后继检查证明losing。']

        lines += ['空图或“不可解”提示图仅说明判定，不作为可行闭环；模型新增边只来自明确的修改指令。']

    lines += ['', f'**构建节点节约：** ΔN={off["nodes"]}−{on["nodes"]}={comparison["nodes_saved"]}，'
        f'节点节约率={comparison["nodes_saved"]}/{off["nodes"]}={comparison["node_saving"]:.3%}。'
        '这统计构建过的逻辑信息节点，不能与剪枝后保留数、Plant状态数或实际内存峰值混同。',
        '', '**传统BTS初始节点的模式去向（互斥分类）：** '
        f'共{sum(rejected.values())}个模式，其中UR含plant死锁{rejected["plant_deadlock"]}个；'
        f'其余模式直接引入控制死锁{rejected["control_deadlock"]}个；'
        f'局部通过但因后续估计失败而剪除{rejected["successor_loss"]}个；最终保留{rejected["retained"]}个。', '',
        '| 实测成本 | Online | Offline | 绝对节约（Offline−Online） | 节约率 |',
        '| --- | ---: | ---: | ---: | ---: |',
        f'| 总求解时间，含online预处理 / ms | {comparison["online_total_median_seconds"]*1000:.6f} | '
        f'{comparison["offline_median_seconds"]*1000:.6f} | {comparison["time_saved_ms"]:.6f} | '
        f'{comparison["time_saving_including_pre"]:.3%} |',
        f'| Python分配峰值 / KiB | {comparison["online_peak_python_bytes"]/1024:.3f} | '
        f'{comparison["offline_peak_python_bytes"]/1024:.3f} | {comparison["memory_saved_KiB"]:.3f} | '
        f'{comparison["peak_memory_saving"]:.3%} |', '',
        f'Online分项中位数：预处理{comparison["pre_median_seconds"]*1000:.6f} ms，'
        f'求解{comparison["online_solve_median_seconds"]*1000:.6f} ms。'
        '总时间是每次预处理与求解相加后再取中位数，不能一般地把两个中位数直接相加。',
        f'运算：ΔT=({comparison["offline_median_seconds"]*1000:.6f}−'
        f'{comparison["online_total_median_seconds"]*1000:.6f}) ms={comparison["time_saved_ms"]:.6f} ms；'
        f'时间节约率=ΔT/{comparison["offline_median_seconds"]*1000:.6f} ms={comparison["time_saving_including_pre"]:.3%}。',
        f'ΔM={comparison["offline_peak_python_bytes"]:,}−{comparison["online_peak_python_bytes"]:,}'
        f'={comparison["memory_saved_bytes"]:,} bytes；内存节约率=ΔM/'
        f'{comparison["offline_peak_python_bytes"]:,}={comparison["peak_memory_saving"]:.3%}。']

    if comparison['time_saving_including_pre']<0:
        lines += ['**成本解释：** 本例online含预处理的总时间反而更高，已保留负节约率。'
            '减少图规模不保证抵消预处理成本；小模型的微秒级时间也易受解释器及调度影响。']
    else:
        lines += ['**成本解释：** 本例测得online总成本更低；收益同时包含窗口、Qf/Qe证书和提前拒绝坏模式。'
            '这是当前实现/模型的实测，不是对所有系统最坏复杂度下降的证明。']

    lines += ['', f'[Offline BTS数据]({name}/offline/bts.json) · [Offline闭环]({name}/offline/closed_loop_system_offline.png) · '
        f'[Offline supervisor]({name}/supervisor_offline.json) · [逐项测量]({name}/online_offline_comparison.json)']

    return '\n'.join(lines)


def overview(root, models):
    summary = read(root/'online_offline_summary.json')
    lines = ['## 运行结果总览与阅读口径', '',
        f'本文件逐例整理{len(models)}个当前模型（{sum(r.get("group")!="structural" for r,p,b,c in models)}个论文模型、3个结构测试）：'
        f'**{summary["statuses"]["winning"]}个winning，{summary["statuses"]["losing"]}个losing**。'
        '后面另列两个实际综合成功的千万状态论文乘积。', '',
        '- Offline以完整已知DFA计算UR/NX，先构建传统BTS再剪枝；不用前视或Qf/Qe证书。',
        '- Online采用认证LL-BTS；只返回已证明winning/losing的结果，窗口不足应为inconclusive。',
        '- 原始DFA状态、D/O信息状态、supervisor记忆、物理闭环状态是不同对象。'
        '闭环节点按（实际DFA状态，控制器记忆）计数，不能把单节点证书当成单状态plant。',
        '- 两侧初始根极大模式集合均已核对；各自选定闭环分别验证，不自动等于两套完整闭环语言一致。',
        '- 原论文的标记非阻塞、保密性、攻击/时延、收益等目标未在本实验中复现；这里只验证无死锁。', '',
        '### 时间、内存与计算公式', '',
        f'{len(models)}个当前模型各做11次交替顺序新鲜求解，取中位数。Online总时间包含预处理；'
        '公共输入模型/索引、u的实验标定、验证和绘图导出不计入求解时间。'
        'u标定借助offline根模式对照，因此不是无offline先验的完整部署耗时。',
        '`ΔT=T_off−T_on`；`时间节约率=ΔT/T_off×100%`；`速度倍数=T_off/T_on`。'
        '`ΔM=M_off−M_on`；`内存节约率=ΔM/M_off×100%`。'
        '1 ms=0.001 s；1 KiB=1024 bytes；1 MiB=1048576 bytes。',
        '内存是另行测量的Python新分配峰值，不是进程RSS；共同输入模型不重复计入。'
        '负差值/负节约率保留。逐例峰值之和只是工作负载统计，不是同时运行的内存峰值。',
        f'{len(models)}例总时间中位数之和：offline={summary["sum_offline_medians"]:.9f}s，'
        f'online含预处理={summary["sum_online_total_medians"]:.9f}s，'
        f'绝对差={summary["time_saved_seconds"]:.9f}s，节约率={summary["aggregate_time_saving"]:.3%}。',
        f'逐例峰值之和：offline={summary["summed_offline_peak_bytes"]:,} bytes，'
        f'online={summary["summed_online_peak_bytes"]:,} bytes，'
        f'绝对差={summary["summed_peak_saved_bytes"]:,} bytes，节约率={summary["aggregate_peak_saving"]:.3%}。',
        f'有{summary["models_with_positive_total_time_saving"]}例总时间节约为正，'
        f'{summary["models_with_positive_peak_memory_saving"]}例Python峰值节约为正。', '',
        '### 理论复杂度与实测结果分开', '',
        '令n=|Q|、m=|δ|、c=|Σc|、o=|Σo|、P=2^c。传统BTS的D≤2^n−1、O≤PD；'
        '逐模式UR/NX构建为O(PD(n+m))。当前按估计—模式记录计数剪枝，若A是记录数、H是观测后继关联数，'
        '成本为O(D+A+H)，不能直接用逻辑合并图的O(V+E)替代。'
        '存储还包含估计/模式集合及重复关联，不能只数节点。',
        'Online需额外计预处理，最长不可观测简单路径存在阶乘级最坏情形；完整UR/NX也可能走出窗口。'
        '因此节约百分比不是普遍的时间/空间复杂度降阶结论。', '',
        '[Online/offline并排图集](online_offline_index.html) · '
        '[完整对比报告](ONLINE_OFFLINE_COMPARISON.md) · '
        '[逐例数值CSV](online_offline_comparison.csv) · '
        '[两个大乘积实际综合](large_literature_supervisors.html)']
    table_start = len(lines)
    lines += ['', '## Online / Offline 运行结果总表 / Online/Offline Results Summary', '',
        '“最小u”分为最小可判定值与恢复offline根极大模式的最小值；“采用u”另满足草稿阈值。Δ均为Offline−Online，节约率为Δ÷Offline；时间包含online预处理，负值原样保留。'
        '这里比较的是实测工作量与资源，理论复杂度上界见上文，不能把节约率当成渐近复杂度降阶。', '',
        '| 系统 | 状态数（Plant） | 可观事件 Σo | 可控事件 Σc | 结果 | 结果一致性（Online/Offline） | 最小u：判定/匹配 | 采用u | LL-BTS D/O | BTS D/O | LL-BTS节点数 | BTS节点数 | Δ节点数 | 节点节约率 | Online/ms | Offline/ms | ΔT/ms | 时间节约 | Online/KiB | Offline/KiB | ΔM/KiB | 内存节约 |',
        '| --- | ---: | --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |',
        '| **System** | **Plant states** | **Observable events Σo** | **Controllable events Σc** | **Result** | **Decision agreement (Online/Offline)** | **Minimum u: decision/pattern match** | **Selected u** | **LL-BTS D/O** | **BTS D/O** | **LL-BTS nodes** | **BTS nodes** | **Nodes saved** | **Node saving rate** | **Online/ms** | **Offline/ms** | **Time saved/ms** | **Time saving rate** | **Online/KiB** | **Offline/KiB** | **Memory saved/KiB** | **Memory saving rate** |']

    for row, p, b, c in models:
        name = row['name'];d = read(root/name/'online_offline_comparison.json');u = read(root/name/'preprocessing.json')
        agreement = ('一致' if d['same_solvability_result'] else '不一致' if d['decision_comparison_complete'] else '未完成')+f'（{d["online_status"]}/{d["offline_status"]}）'
        lines.append(f'| [{name}](#{name.lower()}) | {len(p["states"])} | {event_set(p["observable"])} | {event_set(p["controllable"])} | {b["status"]} | {agreement} | {u["minimal_decisive_u"]}/{u["minimal_matching_u"]} | {u["selected_u"]} | '
            f'{d["online_D"]}/{d["online_O"]} | {d["offline_D"]}/{d["offline_O"]} | {d["online_nodes"]} | {d["offline_nodes"]} | {d["nodes_saved"]} | {d["node_saving"]:.2%} | '
            f'{d["online_total_median_seconds"]*1000:.6f} | {d["offline_median_seconds"]*1000:.6f} | {d["time_saved_ms"]:.6f} | {d["time_saving_including_pre"]:.2%} | '
            f'{d["online_peak_python_bytes"]/1024:.3f} | {d["offline_peak_python_bytes"]/1024:.3f} | {d["memory_saved_KiB"]:.3f} | {d["peak_memory_saving"]:.2%} |')

    table = lines[table_start:]
    from complexity_memory_report import methodology

    g = summary['graph_size_comparison']
    node_summary = (f'{len(models)}例构建节点合计：LL-BTS={g["online_nodes"]:,}（D={g["online_D"]:,},O={g["online_O"]:,}），'
        f'BTS={g["offline_nodes"]:,}（D={g["offline_D"]:,},O={g["offline_O"]:,}），减少{g["nodes_saved"]:,}，节约率{g["node_saving"]:.3%}。'
        '合计节约率用总数相除，不对逐例百分比取平均。'
        f'剪枝后保留节点另计：LL-BTS={g["online_retained_nodes"]:,}，BTS={g["offline_retained_nodes"]:,}。')
    a = summary['arithmetic_means'];neg = summary['negative_savings']['counts'];agree = summary['decision_agreement']
    random_path = root/'randomized_comparison/summary.json'
    random_summary = read(random_path) if random_path.exists() else None
    average_lines = [f'### {len(models)}例时间、空间平均值与结果一致性 / Mean Time, Memory, and Decision Agreement across {len(models)} Examples', '',
        '下表第一行是主表61个单例中位耗时的算术平均（先每例11次取中位数，再对61例取均值）；第二行直接对保存的全部重复耗时取算术平均。'
        '内存按61个单独测量的峰值取均值，不是某一时刻同时运行的平均内存，也不是理论空间复杂度的平均。', '',
        '| 平均指标 | Online LL-BTS | Offline BTS | 平均绝对节约 | 节约率 |',
        '| --- | ---: | ---: | ---: | ---: |',
        f'| 单例中位耗时均值/ms | {a["online_mean_model_median_seconds"]*1000:.6f} | {a["offline_mean_model_median_seconds"]*1000:.6f} | {a["mean_model_median_time_saved_seconds"]*1000:.6f} | {a["mean_model_median_time_saving"]:.3%} |',
        f'| 全部{a["raw_repetitions_per_side"]}次耗时算术平均/ms | {a["online_raw_mean_seconds"]*1000:.6f} | {a["offline_raw_mean_seconds"]*1000:.6f} | {a["raw_mean_time_saved_seconds"]*1000:.6f} | {a["raw_mean_time_saving"]:.3%} |',
        f'| 单例Python峰值均值/KiB | {a["online_mean_peak_python_bytes"]/1024:.3f} | {a["offline_mean_peak_python_bytes"]/1024:.3f} | {a["mean_peak_saved_bytes"]/1024:.3f} | {a["mean_peak_saving"]:.3%} |',
        f'| 单例构建节点均值D+O | {a["online_mean_nodes"]:.3f} | {a["offline_mean_nodes"]:.3f} | {a["offline_mean_nodes"]-a["online_mean_nodes"]:.3f} | {g["node_saving"]:.3%} |', '',
        '计算：平均时间=时间合计÷61；平均峰值=峰值合计÷61；平均差值=Offline均值−Online均值，节约率=平均差值÷Offline均值。不是逐例节约百分比的平均。',
        f'**可解性一致性：{agree["equal_decisions"]}/{agree["models"]}例一致。** Offline已证明losing的{agree["offline_losing_count"]}例中，online也losing的有{agree["offline_losing_online_losing_count"]}例。'
        '`losing`指已证明不存在无死锁supervisor；超时、内存不足、budget_exceeded或inconclusive只表示尚未完成证明，不能据此要求online也无解。',
        f'**负节约说明：** 当前{len(models)}例中，时间负节约{neg["time"]}例，内存和节点负节约分别为{neg["memory"]}例、{neg["nodes"]}例。'
        +(f'但随机实验中有{random_summary["negative_savings"]["memory"]}例内存负节约，说明空间收益也可能为负。' if random_summary else '')
        +'负的是节约差值或比例，不是复杂度本身。', '']
    random_lines = []

    if random_path.exists():
        s = read(random_path)
        random_lines = [f'## {s["generated"]:,}个随机自动机的平均性能验证 / Average Performance Validation on {s["generated"]:,} Random Automata', '',
            f'**随机种子：`{s["seed"]}`；样本数：`{s["generated"]}`；每例重复：`{s["repetitions"]}`次。**', '',
            '- 实验入口：[randomized_online_offline.py](../../randomized_online_offline.py)。',
            '- 随机自动机生成器：[certified_benchmark.py](../../certified_benchmark.py) 中的 `random_plant(rng, index)`；入口用 `random.Random(seed)` 初始化。',
            '- Online实现：[des_core/certified_lookahead.py](../../des_core/certified_lookahead.py)；传统Offline BTS实现：[des_core/offline_bts.py](../../des_core/offline_bts.py)。',
            '- 运行目录：项目的 `limited_lookahead_deadlock_free/`；复现使用上述本地代码。[本次GitHub仓库核对记录](github_repository_check.json)显示，新增实验脚本尚未被Git跟踪。', '',
            '```powershell',
            f'python -X utf8 randomized_online_offline.py --samples {s["generated"]} --repetitions {s["repetitions"]} --seed {s["seed"]}',
            '```', '',
            f'固定种子{s["seed"]}，每例交替运行{s["repetitions"]}次；成对完成{s["count"]}/{s["generated"]}例，未完成{s["incomplete"]}例。'
            'Online从草稿u开始，仅在inconclusive时加深，预处理及全部窗口重试计入；不使用offline结果选择u。比较无死锁可解性，不能把这组平均值当作理论最坏界。', '',
            '| 随机样本平均指标 | Online LL-BTS | Offline BTS | 绝对节约 | 节约率 |',
            '| --- | ---: | ---: | ---: | ---: |',
            f'| 平均总时间/ms | {s["online_mean_seconds"]*1000:.6f} | {s["offline_mean_seconds"]*1000:.6f} | {s["mean_time_saved_seconds"]*1000:.6f} | {s["time_saving"]:.3%} |',
            f'| 平均Python峰值/KiB | {s["online_mean_peak_python_bytes"]/1024:.3f} | {s["offline_mean_peak_python_bytes"]/1024:.3f} | {s["mean_memory_saved_bytes"]/1024:.3f} | {s["memory_saving"]:.3%} |',
            f'| 构建节点总数D+O | {s["graph_size_comparison"]["online_nodes"]:,} | {s["graph_size_comparison"]["offline_nodes"]:,} | {s["graph_size_comparison"]["nodes_saved"]:,} | {s["graph_size_comparison"]["node_saving"]:.3%} |', '',
            f'全部完成例子可解性判定一致；根极大模式集合有{s["root_patterns_equal"]}/{s["count"]}例一致，未强制用offline模式作online标定。'
            f'Online更快{s["models_faster_online"]}例，其他例子也保留。',
            f'随机逐例数据中：时间负节约{s["negative_savings"]["time"]}例、内存峰值负节约{s["negative_savings"]["memory"]}例、节点负节约{s["negative_savings"]["nodes"]}例；均未删除。',
            '随机分布分为密度0.70/0.45/0.30三层，稠密层保证每状态有出边；这是特定分层分布，不能泛化成所有随机分布都同样受益。'
            '[生成分布、分层均值、分布区间、全部输入与原始计时](randomized_comparison/RANDOMIZED_COMPARISON.md)。', '']

    paper_lines = []
    paper_summary = root.parent/'paper_examples_rerun/summary.json'

    if paper_summary.exists():
        from paper_example_models import u5_u6_annotation

        ps = read(paper_summary);pr = {r['name']:r for r in ps['small_models']}
        paper_lines = ['## 论文例子重新运行 / Manuscript Example Reruns', '',
            '本节单独核对论文例子与当前代码标签，不计入前述61例或1000个随机模型的均值。'
            '[重跑报告与原始数据](../paper_examples_rerun/PAPER_EXAMPLES_RERUN.md) · '
            '[更新后的论文PDF](../paper_examples_rerun/paper_examples_updated.pdf)。', '',
            u5_u6_annotation(), '']
        composition = ps['products']['product_current'].get('compositional_supervisor')

        if composition:
            paper_lines += [f'八副本继续计算得到组合式认证supervisor：可达物理状态{composition["reachable_physical_states"]:,}，'
                f'含记忆闭环状态对{composition["reachable_closed_loop_states"]:,}。完整全局BTS仍未显式构造，不声称全局最大宽松；'
                '证明、分量穷举与100000步运行见重跑报告。', '']

    return '\n'.join([table[1], '', *table[5:], '', node_summary, '', *average_lines, methodology(root), '', *random_lines, *paper_lines, *lines[:table_start]])


def large_analyses(root, existing):
    revision_note = ('> 以下大乘积条目保留历史组合式/预算实验，不计入本轮重新建窗版本的性能平均。'
        '当前全局乘积、百万状态模型及资源检查见'
        '[本轮重跑报告](../revision_materials/recentered_deadlock_targets_20261123/RERUN_REPORT.md)。\n\n')
    path = root/'large_literature_supervisors.json'

    if not path.exists():return ''

    rows = read(path)['results']

    if rows and rows[0].get('method') == 'compositional_supervisors':
        from review_large_analyses import format_large_analyses

        return revision_note + format_large_analyses(root, rows, existing)

    lines = [revision_note, '## 千万状态论文乘积：历史运行结果与分析', '',
        '本节是额外的两个大乘积，不混入上面64个显式原始模型的计时汇总。'
        '它们保留源模型的部分观测/控制属性，使用精确组合式Qe证书；'
        '没有逐一展开千万状态，也没有完成传统offline BTS。', '',
        '| 来源 × 副本 | 实际可达状态 | 实际可达转移 | 结果 | 含组合式预处理综合中位数 / μs | Python峰值 / bytes |',
        '| --- | ---: | ---: | --- | ---: | ---: |']

    for r in rows:
        lines.append(f'| {r["source_model"]} × {r["copies"]} | {r["reachable_product_states"]:,} | '
            f'{r["reachable_transitions"]:,} | winning | {r["total_median_seconds"]*1e6:.3f} | '
            f'{r["online_peak_python_bytes"]:,} |')

    for r in rows:
        name = r['name'];descriptor = read(root/name/'plant_product.json')
        events = set(descriptor['events']);observed = set(descriptor['observable']);controls = set(descriptor['controllable'])
        lines += ['', f'### {name}', '',
            f'源例：`{r["source_model"]}`；{r["component_states"]}状态 × {r["copies"]}副本；u={r["u"]}。',
            '| 属性 | 集合 |', '| --- | --- |',
            '| 可观事件 Σo | '+event_set(observed)+' |',
            '| 不可观事件 Σuo | '+event_set(events-observed)+' |',
            '| 可控事件 Σc | '+event_set(controls)+' |',
            '| 不可控事件 Σuc | '+event_set(events-controls)+' |', '',
            '**综合结论与控制行为：** 所有分量状态都有出边，故任意乘积状态都有出边，Qd=Qf=∅、Qe=整个乘积。'
            '实际得到一个记忆状态C0、永远允许全部事件的supervisor；S/G=G，所以在无死锁目标下最大宽松。',
            f'认证LL-BTS只有{r["D"]}个D节点、{r["O"]}个O节点。'
            '这表示组合安全证书提前终止，不表示物理闭环只有一个状态。'
            '所有分量状态都有已验证到达词，按坐标交错这些词可构造到任意元组的路径，因此所报规模是真实可达规模。',
            '**实际运行与验证：** 实际运行导出的Python supervisor；每例100条×1000步，共100000步，'
            '每步校验完整因子化观测估计包含实际状态，未发现死锁或禁用不可控事件。'
            '另对1/2/3副本做全状态/全转移检查，并执行1000个目标元组的构造到达串。'
            '大乘积的全状态安全性由组合证明保证，随机运行只是额外测试。',
            f'101次新鲜测量：预处理中位数{r["pre_median_seconds"]*1e6:.3f} μs，'
            f'求解中位数{r["solve_median_seconds"]*1e6:.3f} μs，'
            f'逐次总时间中位数{r["total_median_seconds"]*1e6:.3f} μs，'
            f'Python分配峰值{r["online_peak_python_bytes"]:,} bytes。'
            '预处理是对小分量的真实检查及组合证明，不是显式全乘积扫描；输入/测试/导出不计入该时间。']
        forecast_path = root/name/'forecast.json'

        if forecast_path.exists():
            f = read(forecast_path)
            lines += ['', '**Offline估算，不能当作实测：** '
                f'初始节点模式数P={f["root_control_patterns"]:,}；在目标规模上实测'
                f'{f["root_record_timing_samples"]}个逐模式UR/NX记录，单次中位数'
                f'{f["root_record_median_seconds"]*1000:.6f} ms。'
                f'按P×t外推，仅根阶段≈{f["offline_root_stage_estimate_seconds"]:,.3f}s'
                f'≈{f["offline_root_stage_estimate_seconds"]/86400:.2f}天；'
                f'根记录内存外推≈{f["offline_root_records_python_bytes_estimate"]/(1024**4):.2f} TiB。',
                '这只针对当前传统逐模式/独立保存UR与NX的实现，未包含后续BTS与剪枝；'
                '实际更可能先内存不足，不能写成“offline实测31天”。'
                '如果offline也使用组合证书、共享闭包、位集或符号模式族，这个估算就不能直接套用。'
                '先前forecast的25.1 μs为较早一轮online测量；本节表格采用最近实际综合运行记录。']
        else:
            lines += ['', '**Offline状态：** 未运行完整传统BTS，也未生成可宣称实测的offline耗时/节约率。'
                '不能把第一个系统的31天估算套用到本系统。']

        lines += ['', '**适用范围：** 这两个候选全部安全，适合展示Qe证书收益，不代表任意含危险状态的系统。'
            '只保证无死锁，不附带公平性、最终观测、标记非阻塞或原论文收益目标。', '',
            f'[实际综合与验证报告]({name}/SYNTHESIS_AND_VALIDATION.md) · '
            f'[可执行supervisor]({name}/supervisor_online.py) · '
            f'[完整精确因子化闭环]({name}/closed_loop_system_online.json) · '
            f'[闭环图]({name}/closed_loop_system_online.svg) · [原始实测]({name}/actual_online_run.json)', '',
            '#### 修改意见（请填写）', '',
            marked('USER-NOTES', name, existing.get(name,
                '- 源例或副本数调整：\n- 可观/可控事件调整：\n- 希望保留的闭环或预期行为：\n- 其他意见：'))]

    return '\n'.join(lines)


def enrich_review(text, root, models, existing):
    text = re.sub(r'<!-- LARGE-EVENTS: literature_products -->\n.*?\n<!-- END-LARGE-EVENTS: literature_products -->', '', text, flags=re.S)
    text = re.sub(r'^# .*', '# 系统事件属性与运行结果与修改意见', text, count=1)
    top = overview(root, models)

    if '<!-- RUN-OVERVIEW: benchmark -->' in text:
        text = replace_marked(text, 'RUN-OVERVIEW', 'benchmark', top)
    else:
        text = text.replace('## 快速索引', marked('RUN-OVERVIEW', 'benchmark', top)+'\n\n## 快速索引', 1)

    for row, plant, bts, closed in models:
        name = row['name'];analysis = model_analysis(root, row, plant, bts, closed)
        pattern = rf'(^## {re.escape(name)}\n)(.*?)(?=^## |\Z)'

        def update(match):
            body = match[2]

            if f'<!-- RUN-RESULTS: {name} -->' in body:
                body = replace_marked(body, 'RUN-RESULTS', name, analysis)
            else:
                assert '### 修改意见（请填写）' in body, name
                body = body.replace('### 修改意见（请填写）',
                    marked('RUN-RESULTS', name, analysis)+'\n\n### 修改意见（请填写）', 1)

            return match[1]+body

        text, count = re.subn(pattern, update, text, count=1, flags=re.S|re.M)
        assert count == 1, name

    large = large_analyses(root, existing)

    if large:
        if '<!-- LARGE-RESULTS: literature_products -->' in text:
            text = replace_marked(text, 'LARGE-RESULTS', 'literature_products', large)
        else:text += '\n\n'+marked('LARGE-RESULTS', 'literature_products', large)+'\n'

    return text


def split_review(text):
    """Separate generated analysis from the editable event catalogue."""

    results = ['# 运行结果', '']

    def move_overview(match):
        results.append(match[1])
        results.extend(['', '[系统事件属性与修改意见](系统事件属性与修改意见.md)', ''])

        return '[详细运行结果与分析](运行结果.md)'

    text = re.sub(r'<!-- RUN-OVERVIEW: benchmark -->\n(.*?)\n<!-- END-RUN-OVERVIEW: benchmark -->', move_overview, text, flags=re.S)

    def move_case(match):
        name, body = match[1], match[2]
        results.extend(['', f'## {name}', '', f'[事件属性与修改意见](系统事件属性与修改意见.md#{name.lower()})', '', body])

        return ''

    text = re.sub(r'<!-- RUN-RESULTS: (.*?) -->\n(.*?)\n<!-- END-RUN-RESULTS: .*? -->', move_case, text, flags=re.S)

    def move_large(match):
        body = match[1]
        # Keep each product's event partitions and editable notes in the catalogue.
        catalogue = ['## 千万状态论文乘积：事件属性与修改意见', '', '[运行结果与分析](运行结果.md#千万状态论文乘积实际运行结果与分析)']

        for section in re.split(r'(?=^### literature_product_)', body, flags=re.M)[1:]:
            properties = section.split('**综合结论与控制行为：**', 1)[0].rstrip()
            notes = re.search(r'<!-- USER-NOTES: .*? -->\n.*?\n<!-- END-USER-NOTES: .*? -->', section, re.S)
            assert notes
            catalogue.extend(['', properties, '', '#### 修改意见（请填写）', '', notes[0]])

        body = re.sub(r'#### 修改意见（请填写）\n\n<!-- USER-NOTES: .*? -->\n.*?\n<!-- END-USER-NOTES: .*? -->', '', body, flags=re.S)
        results.extend(['', body.rstrip()])

        return marked('LARGE-EVENTS', 'literature_products', '\n'.join(catalogue))

    text = re.sub(r'<!-- LARGE-RESULTS: literature_products -->\n(.*?)\n<!-- END-LARGE-RESULTS: literature_products -->', move_large, text, flags=re.S)
    text = re.sub(r'^# .*', '# 系统事件属性与修改意见', text, count=1)
    # Repeated generation reinserts the overview at the index.
    text = text.replace('[详细运行结果与分析](运行结果.md)\n\n', '')
    text = text.replace('## 快速索引', '[详细运行结果与分析](运行结果.md)\n\n## 快速索引', 1)

    return re.sub(r'\n{4,}', '\n\n\n', text).strip()+'\n', '\n'.join(results).strip()+'\n'
