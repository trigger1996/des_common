"""Reproducible random-DFA comparison against independent traditional BTS.

Primary comparison: existence of a deadlock-free supervisor, not equality of
all maximally permissive policies. Online chooses u without consulting offline.
"""

import argparse
import csv
import gc
import json
from pathlib import Path
import random
import statistics
from time import perf_counter
import tracemalloc
from collections import Counter

from certified_benchmark import dump, random_plant
from compare_online_offline import storage
from des_core.certified_lookahead import preprocess, solve_limited_lookahead, validate_policy
from des_core.offline_bts import construct_offline_bts, BTSBudgetExceeded
from graph_size_metrics import graph_size_metrics, aggregate_graph_sizes

ROOT = Path('outputs/expanded_yin_benchmark/randomized_comparison')


def online(plant, *, seconds=1.):
    start = perf_counter();pre = preprocess(plant, max_path_visits=200000)
    attempts = []

    # This rule consults only the online status, never the offline result.
    for u in range(pre.horizon, len(plant.states)):
        remaining = seconds-(perf_counter()-start)

        if remaining <= 0:raise RuntimeError('online total time budget exceeded')

        r = solve_limited_lookahead(pre, horizon=u, max_choices=50000, max_window_states=20000, timeout_seconds=remaining)
        attempts.append(dict(u=u, status=r.status))

        if r.status != 'inconclusive':break

    assert r.status != 'inconclusive'
    patterns = r.maximal_patterns

    return r, patterns, perf_counter()-start, pre, attempts


def offline(plant, *, seconds=1.):
    start = perf_counter()
    r = construct_offline_bts(plant, max_choices=50000, max_decisions=20000, timeout_seconds=seconds)
    patterns = r.maximal_patterns

    return r, patterns, perf_counter()-start


def memory_peak(call):
    gc.collect();tracemalloc.start()

    try:
        value = call();_, peak = tracemalloc.get_traced_memory()

        return peak, None
    except (RuntimeError, BTSBudgetExceeded) as e:return None, str(e)
    finally:tracemalloc.stop()


def distribution(values):
    values = sorted(values)

    return dict(mean=statistics.mean(values), median=statistics.median(values),
        p90=values[int(.90*(len(values)-1))], minimum=values[0], maximum=values[-1])


def summarize(rows, seed, repetitions):
    completed = [r for r in rows if r['complete']]
    memory = [r for r in completed if r['online_peak_python_bytes'] is not None and r['offline_peak_python_bytes'] is not None]

    def summary(rs):
        if not rs:return dict(count=0)

        on = statistics.mean(r['online_mean_seconds'] for r in rs)
        off = statistics.mean(r['offline_mean_seconds'] for r in rs)

        return dict(count=len(rs), online_mean_seconds=on, offline_mean_seconds=off,
            mean_time_saved_seconds=off-on, time_saving=(off-on)/off, speedup=off/on,
            online_distribution=distribution([r['online_mean_seconds'] for r in rs]),
            offline_distribution=distribution([r['offline_mean_seconds'] for r in rs]),
            models_faster_online=sum(r['online_mean_seconds']<r['offline_mean_seconds'] for r in rs))

    totals = summary(completed)
    totals.update(seed=seed, repetitions=repetitions, generated=len(rows),
        incomplete=len(rows)-len(completed), incomplete_ids=[r['index'] for r in rows if not r['complete']],
        statuses=dict(Counter(r['status'] for r in completed)),
        root_patterns_equal=sum(r['same_root_patterns'] for r in completed),
        timing_scope='Arithmetic mean over all fresh runs of each model, then equal-weight mean over models; identical repetitions per completed model. Online includes preprocessing and inconclusive-window retries. Model generation/input indexing, validation, export and memory profiling excluded.',
        objective='Same deadlock-free existence decision; root maximal patterns equality reported separately, not forced by an offline oracle.',
        generator='certified_benchmark.random_plant; n=4..12, Sigma={a,b,c,o}; controls sampled independently p=.55, observability sampled p=.55 then force o observable/a hidden. Index modulo3 selects density .70/.45/.30; dense family ensures >=1 outgoing edge per state; other families may force deadlock states with p=.18. This is an explicit stratified distribution, not all possible automata.',
        strata={str(k):summary([r for r in completed if r['stratum'] == k]) for k in range(3)},
        graph_size_comparison=aggregate_graph_sizes(completed) if completed else {},
        memory_completed=len(memory))
    totals['negative_savings'] = dict(time=sum(r['offline_mean_seconds']<r['online_mean_seconds'] for r in completed),
        memory=sum(r['offline_peak_python_bytes']<r['online_peak_python_bytes'] for r in memory),
        nodes=sum(r['node_saving']<0 for r in completed))

    if memory:
        on = statistics.mean(r['online_peak_python_bytes'] for r in memory);off = statistics.mean(r['offline_peak_python_bytes'] for r in memory)
        totals.update(online_mean_peak_python_bytes=on, offline_mean_peak_python_bytes=off,
            mean_memory_saved_bytes=off-on, memory_saving=(off-on)/off)

    if completed:
        rng = random.Random(seed+1);deltas = []
        differences = [r['offline_mean_seconds']-r['online_mean_seconds'] for r in completed]

        for _ in range(2000):deltas.append(statistics.mean(rng.choices(differences, k=len(differences))))

        deltas.sort();totals['paired_mean_time_saving_bootstrap_95_seconds'] = [deltas[49], deltas[1949]]

    return totals


def report(rows, summary):
    s = summary
    lines = ['# 随机自动机：传统BTS与在线LL-BTS平均性能', '',
        f'**随机种子：`{s["seed"]}`；样本数：`{s["generated"]}`；每例重复：`{s["repetitions"]}`次。**', '',
        '实验入口：[randomized_online_offline.py](../../../randomized_online_offline.py)；生成器：[certified_benchmark.py](../../../certified_benchmark.py) 的 `random_plant(rng,index)`。',
        'Online算法：[des_core/certified_lookahead.py](../../../des_core/certified_lookahead.py)；Offline算法：[des_core/offline_bts.py](../../../des_core/offline_bts.py)。',
        '在 `limited_lookahead_deadlock_free/` 目录运行；使用上述本地代码。[本次仓库核对记录](../github_repository_check.json)显示，新增实验脚本尚未被Git跟踪。', '',
        '```powershell',
        f'python -X utf8 randomized_online_offline.py --samples {s["generated"]} --repetitions {s["repetitions"]} --seed {s["seed"]}',
        '```', '',
        f'固定种子{s["seed"]}，生成{s["generated"]}个部分观测DFA，每例交替顺序运行{s["repetitions"]}次。'
        f'成对完成{s["count"]}例，未完成{s["incomplete"]}例；所有成对完成模型的无死锁可解性判定一致。',
        'Online先执行真实预处理，从草稿u开始；只有结果inconclusive才逐步加深，重试时间全部计入。'
        '不使用offline结果挑选u；完整UR/NX与证书不变。Offline完整已知系统逐模式UR/NX构建BTS再剪枝。',
        '比较任务是是否存在无死锁supervisor，不要求两者全部极大根模式相同；完整模式相同的例数另报。', '',
        '## 生成分布与限制', '',
        '使用既有random_plant生成器：状态数均匀取4～12，事件集{a,b,c,o}；每个事件以0.55概率独立设为可控。'
        '观测集也按0.55概率生成，随后固定o可观、a不可观。按编号模3分为转移密度0.70/0.45/0.30三层；'
        '稠密层保证每状态至少有出边，另外两层以0.18概率将某状态设为无出边。每条定义的状态—事件转移只取一个随机后继，因此保持确定性。',
        '这是明确指定的三层分布，包含较容易全部安全的稠密层。不能由其平均值推断所有分布均受益。'
        '未按耗时或结论筛选模型；预算未完成项保留，不当作不可解或悄悄纳入成功耗时平均。',
        '计时每次上限1秒、模式记录50000、估计/窗口20000；预处理精确路径访问上限200000。'
        '内存复测另给5秒，失败时留空并单独报告覆盖数。公共输入索引、验证、绘图不计时。', '',
        '## 平均值如何计算', '',
        '对模型i，t_i=(t_i1+…+t_ir)/r；总体平均T=(t_1+…+t_N)/N。所有完成例子重复数相同，等价于对全部重复运行取算术平均。'
        'ΔT=平均T_off−平均T_on，节约率=ΔT/平均T_off；不是逐例百分比的平均。',
        '内存对每例分别测tracemalloc新分配峰值M_i，再取共同完成子集的平均；ΔM=平均M_off−平均M_on。'
        'Online包含预处理与窗口重试；共同输入已建、Python外部/C内存不计。', '',
        '| 指标 | Online LL-BTS | Offline BTS | 绝对节约 | 节约率 |',
        '| --- | ---: | ---: | ---: | ---: |',
        f'| 平均总时间/ms | {s["online_mean_seconds"]*1000:.6f} | {s["offline_mean_seconds"]*1000:.6f} | {s["mean_time_saved_seconds"]*1000:.6f} | {s["time_saving"]:.3%} |']

    if s['memory_completed']:
        lines.append(f'| 平均Python峰值/KiB | {s["online_mean_peak_python_bytes"]/1024:.3f} | {s["offline_mean_peak_python_bytes"]/1024:.3f} | {s["mean_memory_saved_bytes"]/1024:.3f} | {s["memory_saving"]:.3%} |')

    g = s['graph_size_comparison']
    lines += [f'| 构建信息节点合计D+O | {g["online_nodes"]:,} | {g["offline_nodes"]:,} | {g["nodes_saved"]:,} | {g["node_saving"]:.3%} |', '',
        f'Online更快的模型：{s["models_faster_online"]}/{s["count"]}；根极大模式集合相同：{s["root_patterns_equal"]}/{s["count"]}；内存成对完成：{s["memory_completed"]}。',
        f'逐例负节约：时间{s["negative_savings"]["time"]}例、Python峰值{s["negative_savings"]["memory"]}例、节点{s["negative_savings"]["nodes"]}例。'
        '负节约表示online实测成本更高，均保留；空间也可能负节约，不是只有时间。复杂度函数本身不存在负值。',
        f'成对模型平均时间差的bootstrap 95%区间/ms：{[round(x*1000,6) for x in s["paired_mean_time_saving_bootstrap_95_seconds"]]}。'
        '按模型重采样2000次；只描述该抽样分布，不能代替理论最坏界。', '',
        '| 随机层 | 完成例数 | Online平均/ms | Offline平均/ms | 时间节约率 |',
        '| --- | ---: | ---: | ---: | ---: |']

    for k, d in s['strata'].items():
        if d['count']:lines.append(f'| 密度层{k} | {d["count"]} | {d["online_mean_seconds"]*1000:.6f} | {d["offline_mean_seconds"]*1000:.6f} | {d["time_saving"]:.3%} |')

    lines += ['', '[逐例结果与全部计时样本](results.json) · [汇总原始数据](summary.json) · [全部输入模型](plants.json) · [数值CSV](results.csv)',
        '理论复杂度及本项目论文例子的规模代入另见 [复杂度与内存计算方法](../COMPLEXITY_AND_MEMORY_CALCULATION.md)。']
    render_distribution(rows, summary)
    lines += ['', '![全部1000例时间分布与分层均值](average_performance.png)']
    (ROOT/'RANDOMIZED_COMPARISON.md').write_text('\n'.join(lines)+'\n', encoding='utf-8')


def render_distribution(rows, summary):
    import matplotlib

    matplotlib.use('Agg')
    import matplotlib.pyplot as plt

    completed = [r for r in rows if r['complete']]
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.8))
    colors = ('#386cb0', '#e49c35', '#39926c')

    for k in range(3):
        cases = [r for r in completed if r['stratum'] == k]
        axes[0].scatter([r['offline_mean_seconds']*1000 for r in cases],
            [r['online_mean_seconds']*1000 for r in cases], s=12, alpha=.55, color=colors[k], label=f'Stratum {k}')

    values = [r[key]*1000 for r in completed for key in ('online_mean_seconds', 'offline_mean_seconds')]
    low = min(values)*.8;high = max(values)*1.2
    axes[0].plot([low, high], [low, high], 'k--', lw=1, label='Equal time')
    axes[0].set(xscale='log', yscale='log', xlim=(low, high), ylim=(low, high),
        xlabel='Offline mean time per model (ms)', ylabel='Online total mean time per model (ms)',
        title=f'All {len(completed)} models; below line = faster online')
    axes[0].legend(fontsize=8)

    for mode, offset, color in (('online', -.18, '#318765'), ('offline', .18, '#577eb0')):
        axes[1].bar([i+offset for i in range(3)],
            [summary['strata'][str(i)][mode+'_mean_seconds']*1000 for i in range(3)],
            width=.35, label=mode, color=color)

    axes[1].set(xticks=[0, 1, 2], xticklabels=['0.70; all states live', '0.45; mixed', '0.30; mixed'],
        ylabel='Arithmetic mean time (ms)', title='Prespecified strata; preprocessing included online')
    axes[1].legend();axes[1].grid(axis='y', alpha=.2);axes[1].set_axisbelow(True)
    fig.suptitle(f'Fixed seed {summary["seed"]} | {summary["repetitions"]} fresh alternating solves per DFA | incomplete: {summary["incomplete"]}')
    fig.tight_layout();fig.savefig(ROOT/'average_performance.png', dpi=150)
    fig.savefig(ROOT/'average_performance.svg');plt.close(fig)


def main():
    parser = argparse.ArgumentParser();parser.add_argument('--samples', type=int, default=1000)
    parser.add_argument('--repetitions', type=int, default=5);parser.add_argument('--seed', type=int, default=20261121)
    args = parser.parse_args();assert args.samples>0 and args.repetitions >= 3
    ROOT.mkdir(exist_ok=True, parents=True);rng = random.Random(args.seed);plants = [];rows = []

    for index in range(args.samples):
        p = random_plant(rng, index)
        plants.append(dict(index=index, stratum=index%3, states=sorted(p.states), initial=p.initial,
            events=sorted(p.events), controllable=sorted(p.controllable), observable=sorted(p.observable),
            transitions=[[q, e, t] for (q, e), t in sorted(p.transitions.items())]))

        for q in p.states:p.enabled(q)  # same warmed immutable input for both solvers

        row = dict(index=index, stratum=index%3, states=len(p.states), transitions=len(p.transitions), complete=False)
        samples = {'online':[], 'offline':[]};error = None;results = {}

        for repeat in range(args.repetitions):
            for mode in (('online', 'offline') if (index+repeat)%2 else ('offline', 'online')):
                try:
                    value = online(p) if mode == 'online' else offline(p)
                    results[mode] = value;samples[mode].append(value[2])
                except (RuntimeError, BTSBudgetExceeded) as exc:
                    error = dict(mode=mode, repeat=repeat, reason=str(exc));break

            if error:break

        row.update(samples_seconds=samples, error=error)

        if not error:
            on, off = results['online'], results['offline']
            assert on[0].status == off[0].status, (index, on[0].status, off[0].status)
            validate_policy(on[3], on[0]);validate_policy(on[3], off[0])
            on_peak, on_error = memory_peak(lambda:online(p, seconds=5.))
            off_peak, off_error = memory_peak(lambda:offline(p, seconds=5.))
            row.update(complete=True, status=on[0].status, selected_u=on[0].horizon,
                attempts=on[4], same_root_patterns=set(on[1]) == set(off[1]),
                online_mean_seconds=statistics.mean(samples['online']), offline_mean_seconds=statistics.mean(samples['offline']),
                online_median_seconds=statistics.median(samples['online']), offline_median_seconds=statistics.median(samples['offline']),
                online_peak_python_bytes=on_peak, offline_peak_python_bytes=off_peak, memory_errors=[on_error, off_error],
                **graph_size_metrics(storage(on[0]), storage(off[0])))

        rows.append(row)

        if (index+1)%100 == 0:
            dump(ROOT/'results.json', rows);dump(ROOT/'plants.json', plants)
            print('random completed', index+1, '/', args.samples, flush=True)

    summary = summarize(rows, args.seed, args.repetitions)
    dump(ROOT/'results.json', rows);dump(ROOT/'plants.json', plants);dump(ROOT/'summary.json', summary)
    fields = ['index', 'stratum', 'states', 'transitions', 'complete', 'status', 'selected_u', 'online_mean_seconds', 'offline_mean_seconds',
        'online_peak_python_bytes', 'offline_peak_python_bytes', 'online_D', 'online_O', 'offline_D', 'offline_O',
        'online_nodes', 'offline_nodes', 'nodes_saved', 'node_saving', 'same_root_patterns', 'error']

    with (ROOT/'results.csv').open('w', encoding='utf-8-sig', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction='ignore');writer.writeheader();writer.writerows(rows)

    report(rows, summary);print(json.dumps(summary, ensure_ascii=False), flush=True)


if __name__ == '__main__':main()
