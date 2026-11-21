"""Fair known-system traditional BTS versus certified online LL-BTS comparison.

python -X utf8 compare_online_offline.py --repetitions 11
"""

import argparse
from collections import Counter
import csv
import gc
import hashlib
import json
from pathlib import Path
import shutil
import statistics
from time import perf_counter
import tracemalloc

from certified_benchmark import dump, export_bts
from des_core.automata import DFA
from des_core.certified_lookahead import (Preprocessing, preprocess, solve_limited_lookahead,
    solve_offline, validate_policy)
from des_core.closed_loop import build_closed_loop, restore_certified_result
from draw_closed_loops import export_graph
from graph_size_metrics import graph_size_metrics, aggregate_graph_sizes
from comparison_averages import comparison_averages, decision_metrics

ROOT = Path('outputs/expanded_yin_benchmark')


def load_plant(folder):
    p = json.loads((folder/'plant.json').read_text(encoding='utf-8'))

    return DFA(frozenset(p['states']), p['initial'], frozenset(p['events']),
        frozenset(p['controllable']), frozenset(p['observable']),
        {(q, e):t for q, e, t in p['transitions']})


def offline_context(plant):
    return Preprocessing(plant, frozenset(q for q in plant.states if not plant.enabled(q)),
        frozenset(), frozenset(), frozenset(), 0, 0, 0, 0.)


def execute_online(plant, u):
    start = perf_counter();pre = preprocess(plant, max_path_visits=2_000_000)
    pre_seconds = perf_counter()-start
    start = perf_counter();result = solve_limited_lookahead(pre, horizon=u);patterns = result.maximal_patterns
    online_seconds = perf_counter()-start

    return pre, result, patterns, pre_seconds, online_seconds


def execute_offline(plant):
    start = perf_counter();result = solve_offline(plant);patterns = result.maximal_patterns

    return result, patterns, perf_counter()-start


def allocation_peak(call):
    gc.collect();tracemalloc.start()
    value = call()
    current, peak = tracemalloc.get_traced_memory();tracemalloc.stop()
    del value

    return current, peak


def storage(result):
    observations = {(c.closure, c.pattern) for cs in result.constructed_choices.values() for c in cs}

    return dict(D=result.decision_count, O=result.observation_count, edges=result.edge_count,
        nodes=result.decision_count+result.observation_count,
        choice_records=sum(len(cs) for cs in result.constructed_choices.values()),
        successor_incidences=sum(len(c.successors) for cs in result.constructed_choices.values() for c in cs),
        stored_choice_memberships=sum(len(c.closure)+len(c.pattern)+sum(len(y) for e, y in c.successors)
                                      for cs in result.constructed_choices.values() for c in cs),
        estimate_memberships=sum(map(len, result.constructed_choices))+sum(len(x) for x, p in observations),
        pattern_memberships=sum(len(p) for x, p in observations),
        retained_D=len(result.policy),
        retained_O=len({(c.closure, c.pattern) for cs in result.policy.values() for c in cs}))


def savings(online, offline):
    return (offline-online)/offline if offline else None


def absolute_metrics(row):
    off = row['offline_median_seconds'];on = row['online_total_median_seconds']
    off_mem = row['offline_peak_python_bytes'];on_mem = row['online_peak_python_bytes']

    return dict(time_saved_seconds=off-on, time_saved_ms=(off-on)*1000,
        time_speedup=off/on if on else None, memory_saved_bytes=off_mem-on_mem,
        memory_saved_KiB=(off_mem-on_mem)/1024, memory_saved_MiB=(off_mem-on_mem)/(1024**2),
        online_peak_MiB=on_mem/(1024**2), offline_peak_MiB=off_mem/(1024**2),
        nodes_saved=row['offline_nodes']-row['online_nodes'],
        edges_saved=row['offline_edges']-row['online_edges'])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repetitions', type=int, default=11)
    parser.add_argument('--only', help='Re-time/export one amended model; preserve other saved model measurements')
    parser.add_argument('--refresh-report', action='store_true', help='Refresh metadata/report from saved measurements, without re-timing or re-rendering')
    args = parser.parse_args()
    assert args.repetitions >= 3
    models = json.loads((ROOT/'model_results.json').read_text(encoding='utf-8'))
    rows = json.loads((ROOT/'online_offline_comparison.json').read_text(encoding='utf-8')) if args.refresh_report or args.only else []

    if args.only:
        assert any(m['name'] == args.only for m in models), args.only
        assert not args.refresh_report
        models = [m for m in models if m['name'] == args.only]

    if args.refresh_report:
        for row in rows:
            folder = ROOT/row['name'];plant = load_plant(folder);pre = preprocess(plant)
            online = restore_certified_result(pre, json.loads((folder/'ll_bts.json').read_text(encoding='utf-8')))
            offline = restore_certified_result(offline_context(plant), json.loads((folder/'offline/bts.json').read_text(encoding='utf-8')))
            detail = json.loads((folder/'online_offline_comparison.json').read_text(encoding='utf-8'))
            detail.update(online_storage=storage(online), offline_storage=storage(offline))
            dump(folder/'online_offline_comparison.json', detail)

    for model in ([] if args.refresh_report else models):
        name = model['name'];folder = ROOT/name;plant = load_plant(folder)

        # The immutable transition index is common input, warmed for BOTH sides.
        # Neither solver has a result cache. Rendering/export/validation excluded.
        for q in plant.states:plant.enabled(q)

        u = json.loads((folder/'preprocessing.json').read_text(encoding='utf-8'))['selected_u']
        pre, online, patterns, _, _ = execute_online(plant, u)
        offline, off_patterns, _ = execute_offline(plant)
        assert (online.status, set(patterns)) == (offline.status, set(off_patterns)), name
        validate_policy(pre, online)
        off_pre = offline_context(plant);validate_policy(off_pre, offline)
        on_samples = [];pre_samples = [];off_samples = []

        for repeat in range(args.repetitions):
            if repeat%2:
                _, _, _, pt, ot = execute_online(plant, u)
                off_samples.append(execute_offline(plant)[2])
            else:
                off_samples.append(execute_offline(plant)[2])
                _, _, _, pt, ot = execute_online(plant, u)

            on_samples.append(ot);pre_samples.append(pt)

        _, on_peak = allocation_peak(lambda:execute_online(plant, u))
        _, off_peak = allocation_peak(lambda:execute_offline(plant))
        totals = [a+b for a, b in zip(pre_samples, on_samples)]
        on_stats = storage(online);off_stats = storage(offline)
        row = dict(name=name, status=online.status, u=u, states=len(plant.states),
            transitions=len(plant.transitions), control_patterns=2**len(plant.controllable),
            pre_median_seconds=statistics.median(pre_samples),
            online_solve_median_seconds=statistics.median(on_samples),
            online_total_median_seconds=statistics.median(totals),
            offline_median_seconds=statistics.median(off_samples),
            time_saving_including_pre=savings(statistics.median(totals), statistics.median(off_samples)),
            time_saving_online_only=savings(statistics.median(on_samples), statistics.median(off_samples)),
            online_peak_python_bytes=on_peak, offline_peak_python_bytes=off_peak,
            peak_memory_saving=savings(on_peak, off_peak),
            online_nodes=on_stats['nodes'], offline_nodes=off_stats['nodes'],
            node_saving=savings(on_stats['nodes'], off_stats['nodes']),
            online_edges=on_stats['edges'], offline_edges=off_stats['edges'],
            same_root_maximal_patterns=True)

        if args.only:
            rows = [row if previous['name'] == name else previous for previous in rows]
        else:rows.append(row)

        details = dict(**row, repetitions=args.repetitions, online_storage=on_stats, offline_storage=off_stats,
            samples=dict(pre_seconds=pre_samples, online_seconds=on_samples, offline_seconds=off_samples),
            timing_scope='Fresh solve plus root maximal-pattern filtering. Online total includes preprocessing. '
                         'Same warmed immutable input index; no synthesis cache; alternating order; no rendering/validation.',
            memory_scope='Separate tracemalloc peaks: preprocessing+online versus offline BTS construction/pruning. '
                         'Common already-built input DFA/index excluded. Python allocations only, not RSS/C allocations.',
            baseline='Known complete DFA; enumerate all admissible controls; full UR/NX builds BTS first, '
                     'including unsafe branches, then count-prune. No horizon/Qf/Qe certificates.')
        dump(folder/'online_offline_comparison.json', details)
        baseline = folder/'offline';baseline.mkdir(exist_ok=True)
        export_bts(off_pre, offline, baseline, structure='BTS',
                   draw=offline.decision_count+offline.observation_count <= 65)
        saved = json.loads((baseline/'bts.json').read_text(encoding='utf-8'))
        restored = restore_certified_result(off_pre, saved)
        graph = build_closed_loop(off_pre, restored)

        if graph['status'] != 'winning':
            for filename in ('supervisor_offline.png', 'supervisor_offline.svg', 'supervisor_offline_memory.csv'):
                path = folder/filename

                if path.exists():path.unlink()

        graph.update(name=name, u=None, structure='offline BTS',
            source_artifacts_sha256={str(Path('offline')/'bts.json'):hashlib.sha256((baseline/'bts.json').read_bytes()).hexdigest(),
                                     'plant.json':hashlib.sha256((folder/'plant.json').read_bytes()).hexdigest()})
        dump(baseline/'closed_loop_system_offline.json', graph)
        dump(folder/'supervisor_offline.json', dict(status=graph['status'], initial=graph['controller_initial'],
            states=graph['controller'], observable_transitions=graph['controller_edges'],
            hidden_event_rule='Memory unchanged on hidden events.', source='offline/bts.json',
            source_artifacts_sha256=graph['source_artifacts_sha256']))
        export_graph(graph, baseline, name, None, mode='offline')

        for source, target in [('supervisor.png', 'supervisor_offline.png'),
                              ('supervisor.svg', 'supervisor_offline.svg'),
                              ('supervisor_memory.csv', 'supervisor_offline_memory.csv')]:
            if (baseline/source).exists():
                shutil.move(str(baseline/source), str(folder/target))

        print(name, 'offline BTS', off_stats['nodes'], 'vs online', on_stats['nodes'], flush=True)

    dump(ROOT/'online_offline_comparison.json', rows)

    with (ROOT/'online_offline_comparison.csv').open('w', encoding='utf-8-sig', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)

    summary = dict(models=len(rows), repetitions=args.repetitions,
        statuses=dict(Counter(r['status'] for r in rows)),
        sum_online_total_medians=sum(r['online_total_median_seconds'] for r in rows),
        sum_offline_medians=sum(r['offline_median_seconds'] for r in rows),
        summed_online_peak_bytes=sum(r['online_peak_python_bytes'] for r in rows),
        summed_offline_peak_bytes=sum(r['offline_peak_python_bytes'] for r in rows),
        models_with_positive_total_time_saving=sum(r['time_saving_including_pre']>0 for r in rows),
        models_with_positive_peak_memory_saving=sum(r['peak_memory_saving']>0 for r in rows))
    summary['aggregate_time_saving'] = savings(summary['sum_online_total_medians'], summary['sum_offline_medians'])
    summary['aggregate_peak_saving'] = savings(summary['summed_online_peak_bytes'], summary['summed_offline_peak_bytes'])
    summary['peak_aggregation_note'] = 'Sum of separately measured per-model peaks is a workload statistic, not simultaneous process memory.'
    summary.update(time_saved_seconds=summary['sum_offline_medians']-summary['sum_online_total_medians'],
        time_speedup=summary['sum_offline_medians']/summary['sum_online_total_medians'],
        summed_peak_saved_bytes=summary['summed_offline_peak_bytes']-summary['summed_online_peak_bytes'])

    for row in rows:
        row.update(absolute_metrics(row))
        path = ROOT/row['name']/'online_offline_comparison.json'
        detail = json.loads(path.read_text(encoding='utf-8'));detail.update(absolute_metrics(row))
        metrics = graph_size_metrics(detail['online_storage'], detail['offline_storage'])
        row.update(metrics);detail.update(metrics)
        online_saved = json.loads((ROOT/row['name']/'ll_bts.json').read_text(encoding='utf-8'))
        offline_saved = json.loads((ROOT/row['name']/'offline/bts.json').read_text(encoding='utf-8'))
        decisions = decision_metrics(online_saved['status'], offline_saved['status'])
        row.update(decisions);detail.update(decisions)
        detail['formulas'] = dict(time_saved='T_off - T_on', time_saving='(T_off - T_on)/T_off',
            speedup='T_off/T_on', memory_saved='M_off - M_on', memory_saving='(M_off - M_on)/M_off',
            nodes='N = D + O; constructed logical information nodes, before pruning',
            nodes_saved='N_off - N_on', node_saving='(N_off - N_on)/N_off',
            retained_nodes='Retained_D + Retained_O; counted separately from constructed nodes',
            units='T in seconds; M in bytes; 1 ms=0.001 s; 1 KiB=1024 bytes; 1 MiB=1048576 bytes')
        dump(path, detail)

    dump(ROOT/'online_offline_comparison.json', rows)

    with (ROOT/'online_offline_comparison.csv').open('w', encoding='utf-8-sig', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)

    summary['graph_size_comparison'] = aggregate_graph_sizes(rows)
    summary.update(comparison_averages(rows, {r['name']:json.loads((ROOT/r['name']/'online_offline_comparison.json').read_text(encoding='utf-8')) for r in rows}))
    dump(ROOT/'online_offline_summary.json', summary)
    # Replace older baseline timing/node fields so no row silently continues to
    # describe the former early-pruned shared solver as the traditional baseline.
    by_name = {r['name']:r for r in rows}
    details_by = {r['name']:json.loads((ROOT/r['name']/'online_offline_comparison.json').read_text(encoding='utf-8'))
                for r in rows}
    combined = []

    for filename in ('paper_results.json', 'structural_results.json'):
        old_rows = json.loads((ROOT/filename).read_text(encoding='utf-8'))

        for old in old_rows:
            r = by_name[old['name']];stats = details_by[old['name']]['offline_storage']
            old.update(pre_seconds=r['pre_median_seconds'], online_seconds=r['online_solve_median_seconds'],
                total_seconds=r['online_total_median_seconds'], offline_seconds=r['offline_median_seconds'],
                offline_D=stats['D'], offline_O=stats['O'], offline_edges=stats['edges'],
                offline_baseline='Traditional BTS: complete UR/NX construction, then pruning; no Qf/Qe/window.',
                timing_protocol='11 alternating fresh solves; medians; u calibration excluded.'
                                if args.repetitions == 11 else f'{args.repetitions} alternating fresh solves; medians; u calibration excluded.')

        dump(ROOT/filename, old_rows);combined.extend(old_rows)

        if filename == 'paper_results.json':
            with (ROOT/'paper_results.csv').open('w', encoding='utf-8-sig', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=list(old_rows[0]));writer.writeheader();writer.writerows(old_rows)

    dump(ROOT/'model_results.json', combined)
    dump(ROOT/'model_summary.json', dict(literature_models=len(combined)-3, structural_models=3,
        total_models=len(combined), statuses=dict(Counter(r['status'] for r in combined))))

    if (ROOT/'summary.json').exists():
        corpus = json.loads((ROOT/'summary.json').read_text(encoding='utf-8'))
        paper = [r for r in combined if not r['name'].startswith('structural_')]
        corpus.update(paper_models=len(paper), statuses=dict(Counter(r['status'] for r in paper)))
        dump(ROOT/'summary.json', corpus)

    write_report(rows, summary)


def write_report(rows, summary):
    lines = ['# Online LL-BTS 与传统 Offline BTS 对比', '',
        'Offline 直接将完整 DFA 视为已知，对每个可达估计和每个可容许控制模式计算完整 UR、NX，先建立 BTS，再剪枝。'
        '不使用前视窗口、Qf/Qe 证书或提前终止。Online 使用当前保存的 u 和认证 LL-BTS。两者采用相同的无死锁目标和计数剪枝。', '',
        'Offline 导出为 `offline/bts.json`、`offline/bts.dot`（小图另有 `bts.png`），'
        '对应 `supervisor_offline.json`、`offline/closed_loop_system_offline.json/png/svg`。'
        '不可解模型提供明确状态说明，不伪造闭环。Online 对应 `closed_loop_system_online.*`。', '',
        '## 时间和空间的口径', '',
        f'每例 {summary["repetitions"]} 次交替顺序的新鲜求解，取中位数。计时包含根极大控制模式筛选；'
        '分别列出 online-only 和 preprocessing+online，公平的一次性总成本比较采用后者。'
        '输入 DFA 及其公共不可变转移索引已建立；模型读取、参数 u 的实验标定、图形/导出、策略验证不计入求解计时。'
        'u 标定使用 offline 解作实验对照，因此当前结果不是无离线先验的端到端部署计时。', '',
        '内存另行通过 tracemalloc 测 Python 新分配峰值，online 计入预处理，双方排除同一输入模型。'
        '这不是进程 RSS，也不覆盖所有 C 扩展内存。另提供真实构建节点数、边数、集合成员数。'
        '节约率 = (offline − online) / offline；负值表示 online 更贵，均原样保留。'
        '小模型耗时很短，计时比例易受解释器/调度影响，应与结构计数一起看。', '',
        '## 复杂度：不能把实测节约率当作最坏阶下降', '',
        '令 n=|Q|，m=|δ|，c=|Σc|，o=|Σo|，P=2^c；传统 BTS 的逻辑图规模为 D、O、E。'
        '令 A 为实际存储的估计—控制模式记录数，H 为这些记录的观测后继关联总数；同一 O 节点可被不同 D 复用。',
        '- D ≤ 2^n−1，O ≤ P·D，E ≤ P·D + o·O。',
        '- 完整 UR/NX 构建为 O(P·D·(n+m))；当前按估计—模式记录计数的剪枝为 O(D+A+H)，'
        '其中 A=P·D、H≤oA。根极大模式比较保守为 O(P²(c+1))。若另实现共享 O 节点的显式图剪枝才可直接写 O(D+O+E)。',
        '- 逻辑图的显式集合/模式编码存储为 O(nD+(n+c)O+E)。当前 Python 实现还保存 A 份记录及 H 份后继估计关联，'
        '保守额外计 O((n+c)A+nH)；另加共同输入 O(n+m)。峰值实测涵盖这些记录、反向索引及临时集合。'
        '不能只把每个集合视为一个字节常数，也不能用逻辑节点数冒充实际内存。',
        '- Online 构建相应的 D_L、O_L、E_L，但完整 UR/NX 可能走出窗口，单次处理成本仍可能达到 O(n+m)。',
        '- Online 总成本还需加预处理；最长不可观测简单路径预处理存在阶乘级最坏情形。因此没有普遍更低时间阶或普遍正节约率的结论。',
        '- 下表的时间/内存百分比是当前模型上的测量结果；节点/边削减来自窗口、证书及提前拒绝坏模式。', '',
        '## 汇总', '',
        '### 具体数值与运算', '',
        '`T_on=T_pre+T_solve`：每次运行先相加，再对总时间取中位数；不一定等于两个中位数之和。'
        '`T_off` 是传统 BTS 总求解时间的中位数。', '',
        '- 时间绝对节约 `ΔT=T_off−T_on`（秒）；乘1000得到毫秒。',
        '- 时间节约率 `ΔT/T_off×100%`；速度倍数 `T_off/T_on`。',
        '- 内存绝对节约 `ΔM=M_off−M_on`（bytes）；内存节约率 `ΔM/M_off×100%`。',
        '- `KiB=bytes/1024`，`MiB=bytes/1048576`；比较各自运行的峰值，不是同一时刻内存差。',
        '- 节点/边绝对削减分别为 `V_off−V_on`、`E_off−E_on`；负差值原样保留。', '',
        f'模型数：{summary["models"]}；所有模型的根极大控制模式与 offline 一致。',
        f'逐例总时间中位数之和：online（含预处理）={summary["sum_online_total_medians"]:.6f}s，'
        f'offline={summary["sum_offline_medians"]:.6f}s；工作负载合计节约率={summary["aggregate_time_saving"]:.2%}。',
        f'逐例 Python 峰值之和的节约率={summary["aggregate_peak_saving"]:.2%}；这是工作负载统计，不是同时运行的内存峰值。', '',
        f'时间绝对差 = {summary["sum_offline_medians"]:.9f} − {summary["sum_online_total_medians"]:.9f}'
        f' = {summary["time_saved_seconds"]:.9f}s；速度倍数={summary["time_speedup"]:.3f}。',
        f'逐例峰值之和绝对差 = {summary["summed_offline_peak_bytes"]} − {summary["summed_online_peak_bytes"]}'
        f' = {summary["summed_peak_saved_bytes"]} bytes。', '',
        '| 模型 | u | online总时间/ms | offline/ms | 时间绝对差/ms | 时间节约 | online峰值/KiB | offline峰值/KiB | 峰值绝对差/KiB | 峰值节约 |',
        '| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |']
    lines += [f'| [{r["name"]}]({r["name"]}/online_offline_comparison.json) | {r["u"]} | '
        f'{r["online_total_median_seconds"]*1000:.4f} | {r["offline_median_seconds"]*1000:.4f} | '
        f'{r["time_saved_ms"]:.4f} | {r["time_saving_including_pre"]:.1%} | '
        f'{r["online_peak_python_bytes"]/1024:.3f} | {r["offline_peak_python_bytes"]/1024:.3f} | '
        f'{r["memory_saved_KiB"]:.3f} | {r["peak_memory_saving"]:.1%} |' for r in rows]
    g = summary['graph_size_comparison']
    avg = summary['arithmetic_means'];neg = summary['negative_savings']['counts'];agree = summary['decision_agreement']
    lines += ['', '## 时间、空间平均值及判定一致性', '',
        f'可解性判定一致{agree["equal_decisions"]}/{agree["models"]}例；offline已证明losing的{agree["offline_losing_count"]}例，online也全部losing。'
        '超时、预算不足或内存不足是未完成，不能当成losing。', '',
        '| 平均指标 | Online | Offline | 平均绝对节约 | 节约率 |',
        '| --- | ---: | ---: | ---: | ---: |',
        f'| 单例中位耗时的均值/ms | {avg["online_mean_model_median_seconds"]*1000:.6f} | {avg["offline_mean_model_median_seconds"]*1000:.6f} | {avg["mean_model_median_time_saved_seconds"]*1000:.6f} | {avg["mean_model_median_time_saving"]:.3%} |',
        f'| 全部{avg["raw_repetitions_per_side"]}次耗时算术平均/ms | {avg["online_raw_mean_seconds"]*1000:.6f} | {avg["offline_raw_mean_seconds"]*1000:.6f} | {avg["raw_mean_time_saved_seconds"]*1000:.6f} | {avg["raw_mean_time_saving"]:.3%} |',
        f'| 单例Python峰值均值/KiB | {avg["online_mean_peak_python_bytes"]/1024:.3f} | {avg["offline_mean_peak_python_bytes"]/1024:.3f} | {avg["mean_peak_saved_bytes"]/1024:.3f} | {avg["mean_peak_saving"]:.3%} |', '',
        f'总表负节约值：时间{neg["time"]}例、Python峰值{neg["memory"]}例、构建节点{neg["nodes"]}例。'
        '负值表示online实测成本更高，不是时间/空间复杂度函数为负。理论上内存也可能出现负节约，未将其截断。']
    lines += ['', '## BTS与LL-BTS信息节点数对比', '',
        'N=D+O。D为决策估计节点，O为估计/控制模式节点；均按构建过的逻辑节点计数。ΔN=N_BTS−N_LL-BTS，节约率=ΔN/N_BTS。'
        '剪枝后保留节点另计；节点节约率不等于实际内存节约率。',
        f'合计：BTS {g["offline_nodes"]:,}，LL-BTS {g["online_nodes"]:,}，减少{g["nodes_saved"]:,}，节约率{g["node_saving"]:.3%}；按总数相除，不取各例百分比平均。', '',
        '| 模型 | LL-BTS D/O | BTS D/O | LL-BTS节点 | BTS节点 | 减少节点 | 节点节约率 | 剪枝后LL-BTS节点 | 剪枝后BTS节点 |',
        '| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |']
    lines += [f'| {r["name"]} | {r["online_D"]}/{r["online_O"]} | {r["offline_D"]}/{r["offline_O"]} | '
        f'{r["online_nodes"]} | {r["offline_nodes"]} | {r["nodes_saved"]} | {r["node_saving"]:.3%} | '
        f'{r["online_retained_nodes"]} | {r["offline_retained_nodes"]} |' for r in rows]
    (ROOT/'ONLINE_OFFLINE_COMPARISON.md').write_text('\n'.join(lines)+'\n', encoding='utf-8')


if __name__ == '__main__':main()
