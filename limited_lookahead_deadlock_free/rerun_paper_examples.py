"""Re-run the manuscript examples, explicitly auditing old figure labels.

python -X utf8 rerun_paper_examples.py
"""

from collections import deque
from dataclasses import asdict, replace
import gc
import hashlib
import json
from pathlib import Path
import shutil
import statistics
from time import perf_counter
import tracemalloc

import matplotlib

matplotlib.use('Agg')
matplotlib.rcParams['pdf.fonttype'] = 42
import matplotlib.pyplot as plt

from certified_benchmark import dump, export_plant, export_bts, trajectory
from compare_online_offline import storage, offline_context
from des_core.automata import DFA
from des_core.asynchronous_product import ImplicitProductDFA
from des_core.certified_lookahead import preprocess, solve_limited_lookahead, solve_offline, validate_policy
from des_core.closed_loop import build_closed_loop
from des_core.implicit_product import benchmark_case1_product
from des_core.offline_bts import construct_offline_bts, BTSBudgetExceeded
from draw_closed_loops import export_graph
from examples.non_deadlock import build_small_cycle_example, build_nested_cycle_deadlock_example
from large_online_offline import product_pre, verify_product_certificates
from paper_example_models import paper_small_figure, archived_component_figure, u5_u6_annotation
from revised_large_products import CONTROLLER, validate_product, certify_component

ROOT = Path('outputs/paper_examples_rerun')


def small_case(example, u):
    folder = ROOT/example.name;folder.mkdir(parents=True, exist_ok=True);export_plant(example, folder)
    times = [];off_times = []

    for repeat in range(11):
        order = ('online', 'offline') if repeat%2 else ('offline', 'online')

        for mode in order:
            start = perf_counter()

            if mode == 'online':pre = preprocess(example.dfa, max_path_visits=2_000_000);r = solve_limited_lookahead(pre, horizon=u);_ = r.maximal_patterns
            else:off = solve_offline(example.dfa);_ = off.maximal_patterns

            (times if mode == 'online' else off_times).append(perf_counter()-start)

    validate_policy(pre, r);validate_policy(pre, off)

    if r.status != 'inconclusive':assert r.status == off.status

    same_patterns = set(r.maximal_patterns) == set(off.maximal_patterns)
    sweep = []

    for depth in range(len(example.dfa.states)):
        checked = solve_limited_lookahead(pre, horizon=depth);validate_policy(pre, checked)
        sweep.append(dict(u=depth, status=checked.status, same_offline_root_patterns=
            (checked.status, set(checked.maximal_patterns)) == (off.status, set(off.maximal_patterns))))

    export_bts(pre, r, folder);baseline = folder/'offline';baseline.mkdir(exist_ok=True)
    export_bts(offline_context(example.dfa), off, baseline, structure='BTS', draw=off.decision_count+off.observation_count <= 65)

    for mode, result, dest in (('online', r, folder), ('offline', off, baseline)):
        graph = (build_closed_loop(pre, result) if result.status != 'inconclusive' else
            dict(status='inconclusive', initial=None, controller_initial=None, controller=[], controller_edges=[], nodes=[], edges=[],
                reason='Requested window is insufficient; this is not an infeasibility proof.'))
        dump(dest/f'closed_loop_system_{mode}.json', graph)
        dump(dest/f'supervisor_{mode}.json', dict(status=graph['status'], initial=graph['controller_initial'],
            memories=graph['controller'], transitions=graph['controller_edges']))

        if result.status != 'inconclusive':export_graph(graph, dest, example.name, u, mode=mode)

        if mode == 'online':closed = graph

    gc.collect();tracemalloc.start();mpre = preprocess(example.dfa);solve_limited_lookahead(mpre, horizon=u)
    on_peak = tracemalloc.get_traced_memory()[1];tracemalloc.stop()
    gc.collect();tracemalloc.start();solve_offline(example.dfa)
    off_peak = tracemalloc.get_traced_memory()[1];tracemalloc.stop()
    row = dict(name=example.name, states=len(example.dfa.states), transitions=len(example.dfa.transitions),
        u=u, draft_u=pre.horizon, status=r.status, offline_status=off.status, same_root_patterns=same_patterns,
        minimal_decisive_u=next(x['u'] for x in sweep if x['status'] != 'inconclusive'),
        minimal_matching_u=next(x['u'] for x in sweep if x['same_offline_root_patterns']),
        online_root_patterns=[sorted(x) for x in r.maximal_patterns], offline_root_patterns=[sorted(x) for x in off.maximal_patterns],
        online=storage(r), offline=storage(off), closed_loop_states=len(closed['nodes']), closed_loop_edges=len(closed['edges']),
        controller_memories=len(closed['controller']), online_total_median_seconds=statistics.median(times),
        offline_median_seconds=statistics.median(off_times), online_peak_python_bytes=on_peak, offline_peak_python_bytes=off_peak,
        plant_sha256=hashlib.sha256((folder/'plant.json').read_bytes()).hexdigest())
    dump(folder/'result.json', row);dump(folder/'u_sweep.json', sweep)
    dump(folder/'timing_samples.json', dict(online_total=times, offline=off_times))
    dump(folder/'trajectory.json', trajectory(pre, u, steps=7))
    print(example.name, row['status'], 'closed', row['closed_loop_states'], row['closed_loop_edges'], flush=True)

    return row


def draw_component_pdf(component, path):
    pos = {'q_0':(0, 1), 'q_1':(2, 1), 'q_2':(4, 1), 'q_3':(2, -1), 'q_4':(4, -1), 'q_5':(6, -1)}
    from matplotlib.patches import FancyArrowPatch
    import networkx as nx

    graph = nx.DiGraph();graph.add_nodes_from(pos)
    fig, ax = plt.subplots(figsize=(7.2, 3.2))
    nx.draw_networkx_nodes(graph, pos, ax=ax, node_size=1000, node_color='#dce9f4', edgecolors='#276093')
    nx.draw_networkx_labels(graph, pos, labels={q:'$q_{'+q[2:]+'}$' for q in pos}, font_size=13, ax=ax)

    for (q, e), t in component.transitions.items():
        rad = .2 if (t, q) in {(a, b) for (a, event), b in component.transitions.items()} else 0

        if q == 'q_2' and t == 'q_0':rad = .35

        x, y = pos[q];xx, yy = pos[t];dx, dy = xx-x, yy-y
        ax.add_patch(FancyArrowPatch((x, y), (xx, yy), connectionstyle=f'arc3,rad={rad}', arrowstyle='-|>',
            shrinkA=19, shrinkB=19, mutation_scale=16, color='#444'))
        lx = (x+xx)/2+.5*rad*dy;ly = (y+yy)/2-.5*rad*dx
        label = '$o_'+e[1:]+'$' if e.startswith('o') else '$'+e+'$'
        ax.text(lx, ly, label, fontsize=13, ha='center', va='center', bbox=dict(facecolor='white', edgecolor='none', pad=1))

    ax.annotate('', xy=(-.28, 1), xytext=(-.9, 1), arrowprops=dict(arrowstyle='->'))
    ax.set_xlim(-1, 6.6);ax.set_ylim(-1.6, 2.1);ax.axis('off');fig.tight_layout()
    fig.savefig(path);plt.close(fig)


def legacy_run(component, label):
    folder = ROOT/label;folder.mkdir(exist_ok=True)
    result = benchmark_case1_product(component, 8, 50, 3, pattern_mode='factored', cache_size=0)
    dump(folder/'legacy_trajectory.json', asdict(result))
    fig, ax = plt.subplots(figsize=(5.8, 3.2));steps = [s.iteration+1 for s in result.stats]
    ax.plot(steps, [s.local_state_count for s in result.stats], label='Local query states', lw=1.5)
    ax.plot(steps, [s.cumulative_state_count for s in result.stats], label='Cumulative query states', lw=1.5)
    ax.set(xlabel='Historical physical-root query', ylabel='Number of concrete states')
    ax.grid(alpha=.2);ax.legend(fontsize=8);fig.tight_layout()
    fig.savefig(folder/'visited_states_rerun.pdf');fig.savefig(folder/'visited_states_rerun.png', dpi=150);plt.close(fig)
    print(label, 'legacy queries', result.iterations, 'cycle_check', result.cycle_check.ok, flush=True)

    return dict(requested_queries=50, completed_queries=result.iterations, elapsed_seconds=result.elapsed_seconds,
        cumulative_states=result.stats[-1].cumulative_state_count, max_local_states=result.max_local_states,
        stop_reason=result.stop_reason, certified_global_supervisor=False,
        reason='Historical runner resets a physical-state root instead of preserving the full observation estimate.')


def product_attempts(component, label):
    folder = ROOT/label;folder.mkdir(exist_ok=True);p = ImplicitProductDFA(component, 8)
    # Structural formula checked exhaustively for 1/2/3 current-label copies.
    # Same q4->q5 hidden tail holds in the archived figure-label component.
    pre = product_pre(component, 8, p)
    rows = []

    for mode, u in (('online', 3), ('online', pre.horizon), ('offline', None)):
        try:
            start = perf_counter()
            r = (solve_limited_lookahead(pre, horizon=u, max_choices=5000, max_window_states=25000, timeout_seconds=3.)
               if mode == 'online' else construct_offline_bts(p, max_choices=5000, max_decisions=25000, timeout_seconds=3.))
            rows.append(dict(mode=mode, u=u, complete=True, status=r.status, seconds=perf_counter()-start))
        except BTSBudgetExceeded as e:
            record = dict(mode=mode, u=u, status='budget_exceeded', **e.metrics);record['complete'] = False;rows.append(record)

    dump(folder/'certified_attempts.json', rows)

    return rows


def verified_constant_controller(component):
    folder = ROOT/'product_current';p = ImplicitProductDFA(component, 8)
    allowed = p.events-{f'o1_{i}' for i in range(8)}
    assert p.uncontrollable <= allowed
    states = [p.initial];ids = {p.initial:0};edges = []

    for q in states:
        count = 0

        for event, target in p.enabled(q):
            if event not in allowed:continue

            if target not in ids:ids[target] = len(states);states.append(target)

            edges.append([ids[q], event, ids[target]]);count += 1

        assert count == 8 and all(x in ('q_0', 'q_1', 'q_2') for x in q)

    assert len(states) == 3**8 and len(edges) == 8*3**8
    dump(folder/'verified_closed_loop_system.json', dict(initial=0, states=states, transitions=edges,
        supervisor=dict(memory=['C0'], enabled_events=sorted(allowed)), proof='Every reachable state and enabled transition checked; all uncontrollable events retained.',
        maximality='Feasible constant supervisor only; global maximal synthesis not claimed.'))

    return dict(status='verified_feasible', states=len(states), edges=len(edges), disabled_events=[f'o1_{i}' for i in range(8)])


def composed_certified_controller(component):
    """Synthesize local certified policy, then prove its entire exact product."""

    folder = ROOT/'product_current/compositional';folder.mkdir(parents=True, exist_ok=True)
    times = []

    for _ in range(101):
        pre, r, graph, seconds = certify_component(component, 2);times.append(seconds)

    gc.collect();tracemalloc.start();pre, r, graph, _ = certify_component(component, 2)
    peak = tracemalloc.get_traced_memory()[1];tracemalloc.stop()
    assert r.maximal_patterns == (component.controllable,)
    small = validate_product(graph, 8)
    data = dict(status='winning', copies=8, initial=graph['controller_initial'], component_memories=graph['controller'],
        component_observable=sorted(component.observable), component_observable_transitions=graph['controller_edges'])
    dump(folder/'supervisor_online.json', data);dump(folder/'component_closed_loop.json', graph)
    (folder/'supervisor_online.py').write_text(CONTROLLER, encoding='utf-8')
    namespace = {'__file__':str((folder/'supervisor_online.py').resolve())}
    exec(compile(CONTROLLER, str(folder/'supervisor_online.py'), 'exec'), namespace)
    import random

    rng = random.Random(20261121);memories = {m['id']:m for m in graph['controller']}

    for trial in range(100):
        supervisor = namespace['Supervisor']();state = [component.initial]*8

        for step in range(1000):
            enabled = supervisor.enabled_events()
            assert all(f'{e}_{i}' in enabled for i in range(8) for e in component.uncontrollable)
            options = [(i, e, t) for i, q in enumerate(state) for e, t in component.enabled(q) if f'{e}_{i}' in enabled]
            assert options
            i, e, t = rng.choice(options);state[i] = t

            if e in component.observable:supervisor.observe(f'{e}_{i}')

            assert all(q in memories[m]['closure'] for q, m in zip(state, supervisor.memory))

    row = dict(status='winning', method='Exact product of certified component supervisors', copies=8, component_u=2,
        global_minimum_u=None, plant_states=6**8, reachable_physical_states=len({n['state'] for n in graph['nodes']})**8,
        reachable_closed_loop_states=len(graph['nodes'])**8,
        reachable_closed_loop_transitions=8*len(graph['edges'])*len(graph['nodes'])**7,
        controller_memory_configurations=len(graph['controller'])**8,
        component_closed_loop_states=len(graph['nodes']), component_closed_loop_transitions=len(graph['edges']),
        full_global_BTS_constructed=False, global_maximal_supervisor_claimed=False,
        root_pattern='All24 controllable indexed events are enabled initially; hence this root pattern is inclusion-maximal.',
        synthesis_total_median_seconds=statistics.median(times), python_peak_bytes=peak,
        verification=dict(exhaustive_small_products=small, trajectory_steps=100000, seed=20261121,
            proof='Each reachable component state/memory pair is live and preserves uncontrollable events. With disjoint indexed alphabets, every tuple has a permitted successor. Interleaved component reachability words reach every tuple.'))
    dump(folder/'closed_loop_system_online.json', row);dump(folder/'timing_samples.json', times)
    print('Eight-copy compositional supervisor:', row['reachable_physical_states'], 'physical states', row['reachable_closed_loop_states'], 'state/memory pairs', flush=True)

    return row


def main():
    ROOT.mkdir(parents=True, exist_ok=True)
    small = paper_small_figure()
    current = replace(build_nested_cycle_deadlock_example(), name='small_current_code')
    comp = replace(build_small_cycle_example(), name='component_current_code')
    old = archived_component_figure()
    rows = [small_case(small, 5), small_case(replace(small, name='paper_small_figure_u6'), 6),
        small_case(current, 5), small_case(comp, 2), small_case(old, 2), small_case(replace(old, name='archived_component_figure_u5'), 5)]
    verify_product_certificates()
    large = {}

    for example, label in ((comp, 'product_current'), (old, 'product_archived_figure')):
        large[label] = dict(plant_states=6**8, legacy=legacy_run(example.dfa, label), certified_attempts=product_attempts(example.dfa, label))

    large['product_current']['verified_controller'] = verified_constant_controller(comp.dfa)
    large['product_current']['compositional_supervisor'] = composed_certified_controller(comp.dfa)
    draw_component_pdf(comp.dfa, ROOT/'component_current_code/component_current.pdf')
    dump(ROOT/'summary.json', dict(small_models=rows, products=large,
        label_audit=dict(small='Manuscript q10-o2->q6; current code q10-o1->q6. Both run separately.',
            component='Archived figure q2-o1->q0 is losing as a standalone component. User-corrected code q2-a->q0 is winning.'),
        timing_scope='Small examples: 11 alternating fresh solves including online preprocessing. Large legacy timings are trajectory-query timings, not certified-global-synthesis timings.'))
    lines = ['# 论文例子重新运行与图文核对', '',
        '入口：`python -X utf8 rerun_paper_examples.py`。论文主文为 `[paper]Limited Lookadhead Deadlock-free/main.tex`。'
        '当前项目模型保持不变；按原论文图的标签另建独立变体重跑。', '',
        '| 例子 | u | online/offline | 根极大模式一致 | 最小判定/匹配u | LL-BTS D/O | BTS D/O | 闭环状态/边 |',
        '| --- | ---: | --- | --- | ---: | ---: | ---: | ---: |']

    for r in rows:
        lines.append(f'| [{r["name"]}]({r["name"]}/result.json) | {r["u"]} | {r["status"]}/{r["offline_status"]} | {r["same_root_patterns"]} | '
            f'{r["minimal_decisive_u"]}/{r["minimal_matching_u"]} | '
            f'{r["online"]["D"]}/{r["online"]["O"]} | {r["offline"]["D"]}/{r["offline"]["O"]} | {r["closed_loop_states"]}/{r["closed_loop_edges"]} |')

    lines += ['', '## 标签差异与八副本乘积', '',
        '论文图的小例子u=5可认证winning，但根极大控制模式比完整offline更保守；u=6才恢复完整offline根极大模式。两种深度均已实际重跑，未把可解性一致写成最大宽松性一致。',
        '小例子旧图q10→q6为o2、当前代码为o1，两版都重新运行。分量旧图q2→q0为o1，而用户此前已将代码改为a；旧图分量本身判定losing，修正分量判定winning。',
        '两版八副本均重新运行原u=3、50次物理根查询；此历史运行器在每步使用具体物理状态作为根，不保留完整观测估计，不能据此证明部分观测无死锁supervisor。',
        '两版也分别按当前认证算法运行u=3与结构阈值u=7，并独立尝试完整传统BTS；均设置5000模式、25000窗口/估计、3秒预算，预算截断不是不可解证明。',
        '修正分量八副本另外得到完整验证的常量策略：禁用所有o1_i，闭环保留3^8=6561状态和52488条边；所有可达状态与转移均检查。'
        '这是可行策略，不是已完成全局最大宽松BTS综合。', '']

    for label, d in large.items():
        lines += [f'### {label}', '', f'历史查询：{d["legacy"]["completed_queries"]}/50；耗时{d["legacy"]["elapsed_seconds"]:.6f}s；未认证全局supervisor。',
            f'[完整认证求解尝试]({label}/certified_attempts.json) · [历史查询原始数据]({label}/legacy_trajectory.json)', '',
            '```json', json.dumps(d['certified_attempts'], ensure_ascii=False, indent=2), '```', '']

    lines += ['[修正模型完整可行闭环](product_current/verified_closed_loop_system.json)', '',
        '## 继续计算：组合式认证supervisor', '',
        '独立综合并完整验证分量supervisor，然后按索引字母表做异步组合。该方法得到全乘积的可执行无死锁supervisor，但不枚举完整全局BTS，也不声称全局最大宽松。',
        f'监督后可达物理状态={large["product_current"]["compositional_supervisor"]["reachable_physical_states"]:,}；含控制器记忆的闭环状态={large["product_current"]["compositional_supervisor"]["reachable_closed_loop_states"]:,}。',
        '[完整组合式闭环及验证](product_current/compositional/closed_loop_system_online.json) · [可执行supervisor](product_current/compositional/supervisor_online.py)', '',
        u5_u6_annotation(), '',
        '现有原始论文图、原始tex和技术草稿不在此脚本中覆盖；同步论文时先备份，再根据本报告注明图/代码版本及验证范围。']
    (ROOT/'PAPER_EXAMPLES_RERUN.md').write_text('\n'.join(lines)+'\n', encoding='utf-8')
    print('Paper examples rerun complete:', ROOT, flush=True)


if __name__ == '__main__':main()
