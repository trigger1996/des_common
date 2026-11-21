"""Exact products of certified component supervisors for the reviewed models.

No global product BTS is claimed to have been enumerated. Component LL-BTSs,
controllers and closed loops are factored, and their asynchronous composition
is certified by checking every component closed-loop state and transition.
"""

from collections import deque
import gc
import hashlib
import json
from pathlib import Path
import random
import shutil
import statistics
from time import perf_counter
import tracemalloc

from certified_benchmark import dump
from compare_online_offline import load_plant
from des_core.certified_lookahead import preprocess, solve_limited_lookahead, validate_policy
from des_core.closed_loop import build_closed_loop
from des_core.plot_automaton import render_plant
from draw_closed_loops import export_graph

ROOT = Path('outputs/expanded_yin_benchmark')
CASES = (('21AutomaticaOptimal_fig_2', 6), ('18TACrange_fig_3a', 7))

CONTROLLER = '''"""Factored observation-feedback controller; never reads physical states."""
import json
from pathlib import Path

class Supervisor:
    def __init__(self):
        d=json.loads((Path(__file__).parent/'supervisor_online.json').read_text(encoding='utf-8'))
        self.memory=[d['initial']]*d['copies']
        self.patterns={m['id']:frozenset(m['full_pattern']) for m in d['component_memories']}
        self.observable=frozenset(d['component_observable'])
        self.transitions={(q,e):t for q,e,t in d['component_observable_transitions']}
    def enabled_events(self):
        return frozenset(f'{e}_{i}' for i,m in enumerate(self.memory) for e in self.patterns[m])
    def observe(self,event):
        raw,index=event.rsplit('_',1);index=int(index)
        if raw not in self.observable:raise ValueError('Hidden event is not observed')
        self.memory[index]=self.transitions[self.memory[index],raw]
        return tuple(self.memory)
'''


def certify_component(plant, u):
    started = perf_counter();pre = preprocess(plant, max_path_visits=2_000_000)
    result = solve_limited_lookahead(pre, horizon=u);validate_policy(pre, result)
    graph = build_closed_loop(pre, result)
    assert graph['status'] == 'winning'
    by_memory = {m['id']:m for m in graph['controller']}
    nodes = {n['id']:n for n in graph['nodes']};out = {q:[] for q in nodes}

    for edge in graph['edges']:out[edge['source']].append(edge)

    for q, node in nodes.items():
        assert out[q]
        m = by_memory[node['memory']]
        assert plant.uncontrollable <= set(m['full_pattern'])
        assert node['state'] in m['closure']

        for e, t in plant.enabled(node['state']):
            assert (e in m['full_pattern']) == any(x['event'] == e for x in out[q])

    # Every factor is live, and alphabets are disjoint by coordinate indexing.
    # Thus every tuple has a successor, and local uncontrollable events survive.
    seconds = perf_counter()-started

    return pre, result, graph, seconds


def validate_product(graph, copies):
    adjacency = {n['id']:[] for n in graph['nodes']}

    for e in graph['edges']:adjacency[e['source']].append(e['target'])

    small = []

    for k in (1, 2, 3):
        initial = (graph['initial'],)*k;seen = {initial};queue = deque([initial]);edges = 0

        while queue:
            state = queue.popleft();count = 0

            for i, q in enumerate(state):
                for target in adjacency[q]:
                    t = state[:i]+(target,)+state[i+1:];edges += 1;count += 1

                    if t not in seen:seen.add(t);queue.append(t)

            assert count

        assert len(seen) == len(graph['nodes'])**k
        assert edges == k*len(graph['edges'])*len(graph['nodes'])**(k-1)
        small.append(dict(copies=k, states=len(seen), transitions=edges, deadlocks=0, exhaustive=True))

    return small


def run_case(source, copies):
    plant = load_plant(ROOT/source)
    reachable = {plant.initial};queue = deque(reachable)

    while queue:
        for event, target in plant.enabled(queue.popleft()):
            if target not in reachable:reachable.add(target);queue.append(target)

    assert reachable == plant.states
    u = json.loads((ROOT/source/'preprocessing.json').read_text(encoding='utf-8'))['selected_u']
    samples = []

    for _ in range(101):pre, result, graph, elapsed = certify_component(plant, u);samples.append(elapsed)

    gc.collect();tracemalloc.start();pre, result, graph, _ = certify_component(plant, u)
    _, peak = tracemalloc.get_traced_memory();tracemalloc.stop()
    name = f'literature_product_{source}_{copies}copy';folder = ROOT/'large_systems'/name
    # Preserve old reports and measurements, which may certify a different model.
    archive = Path('tmp/user_review_revision_20261121/previous_large_products')/name

    for old in (ROOT/name, folder):
        if old.exists():
            archive.parent.mkdir(exist_ok=True, parents=True)
            assert old.resolve().is_relative_to(ROOT.resolve())
            assert archive.resolve().is_relative_to(Path('tmp/user_review_revision_20261121').resolve())
            target = archive;counter = 2

            while target.exists():target = archive.with_name(archive.name+f'_rerun_{counter}');counter += 1

            assert target.resolve().is_relative_to(Path('tmp/user_review_revision_20261121').resolve())
            shutil.move(str(old), str(target))

    folder.mkdir(parents=True)

    for filename in ('plant.json', 'plant.png', 'plant_original.json', 'plant_original.png', 'll_bts.json', 'll_bts.png'):
        src = ROOT/source/filename

        if src.exists():shutil.copy2(src, folder/('component_'+filename))

    dump(folder/'component_closed_loop.json', graph)
    descriptor = dict(name=name, source_model=source, source_file='../../'+source+'/plant.json',
        source_sha256=hashlib.sha256((ROOT/source/'plant.json').read_bytes()).hexdigest(),
        copies=copies, component_states=len(plant.states), reachable_product_states=len(plant.states)**copies,
        product_transitions=copies*len(plant.transitions)*len(plant.states)**(copies-1),
        initial=[plant.initial]*copies, component_events=sorted(plant.events),
        component_controllable=sorted(plant.controllable), component_observable=sorted(plant.observable),
        events=[f'{e}_{i}' for i in range(copies) for e in sorted(plant.events)],
        observable=[f'{e}_{i}' for i in range(copies) for e in sorted(plant.observable)],
        controllable=[f'{e}_{i}' for i in range(copies) for e in sorted(plant.controllable)],
        component_transitions=[[q, e, t] for (q, e), t in sorted(plant.transitions.items())],
        composition='Exact asynchronous product; independent, indexed event alphabets.')
    dump(folder/'plant_product.json', descriptor)
    dump(folder/'supervisor_online.json', dict(status='winning', copies=copies, initial=graph['controller_initial'],
        component_memories=graph['controller'], component_observable=sorted(plant.observable),
        component_observable_transitions=graph['controller_edges'],
        rule='Only the coordinate owning an observable event updates memory; hidden events preserve memory.',
        representation='Asynchronous product of verified component observation-feedback controllers.'))
    (folder/'supervisor_online.py').write_text(CONTROLLER, encoding='utf-8')
    namespace = {'__file__':str((folder/'supervisor_online.py').resolve())}
    exec(compile(CONTROLLER, str(folder/'supervisor_online.py'), 'exec'), namespace)
    memories = {m['id']:m for m in graph['controller']};rng = random.Random(20261121+copies)
    traces = []

    for trial in range(100):
        controller = namespace['Supervisor']();state = [plant.initial]*copies;trace = []

        for step in range(1000):
            enabled = controller.enabled_events()
            assert all(f'{e}_{i}' in enabled for i in range(copies) for e in plant.uncontrollable)
            options = [(i, e, t) for i, q in enumerate(state) for e, t in plant.enabled(q) if f'{e}_{i}' in enabled]
            assert options
            i, e, t = rng.choice(options);state[i] = t

            if e in plant.observable:controller.observe(f'{e}_{i}')

            assert all(q in memories[m]['closure'] for q, m in zip(state, controller.memory))

            if trial<2 and step<50:trace.append(dict(event=f'{e}_{i}', state=list(state), memory=list(controller.memory)))

        if trace:traces.append(trace)

    small = validate_product(graph, copies)
    physical = {n['state'] for n in graph['nodes']}
    row = dict(name='large_systems/'+name, source_model=source, copies=copies, component_states=len(plant.states),
        reachable_product_states=len(plant.states)**copies, reachable_transitions=descriptor['product_transitions'],
        closed_loop_physical_states=len(physical)**copies,
        closed_loop_states=len(graph['nodes'])**copies,
        closed_loop_transitions=copies*len(graph['edges'])*len(graph['nodes'])**(copies-1),
        status='winning', method='compositional_supervisors', component_u=u,
        global_minimal_u=None, component_D=result.decision_count, component_O=result.observation_count,
        total_median_seconds=statistics.median(samples), online_peak_python_bytes=peak,
        timing_scope='One shared component preprocessing + certified LL-BTS solve + closed-loop construction + full component certificate verification; product factors reuse this result. No global BTS enumeration, input/plotting/tests excluded.',
        verification=dict(small_products=small, large_trajectories=100, steps_per_trajectory=1000, total_steps=100000,
            proof='Every reachable local closed-loop state is live and preserves uncontrollable events. Disjoint-alphabet asynchronous products preserve both properties. All local reachable nodes have paths; interleaving paths reaches every tuple.'),
        offline_complete=False, offline_root_patterns=2**(copies*len(plant.controllable)),
        explicit_input_compact_bytes=16*descriptor['product_transitions']+8*len(plant.states)**copies,
        explicit_input_scan_seconds_range=[descriptor['product_transitions']/1e7, descriptor['product_transitions']/1e6])

    # Historical forecast remains applicable only for the unchanged first source.
    if source == '21AutomaticaOptimal_fig_2' and (archive/'forecast.json').exists():
        forecast = json.loads((archive/'forecast.json').read_text(encoding='utf-8'))
        row['offline_root_forecast'] = dict(patterns=forecast['root_control_patterns'],
            sample_median_seconds=forecast['root_record_median_seconds'],
            seconds=forecast['offline_root_stage_estimate_seconds'],
            bytes=forecast['offline_root_records_python_bytes_estimate'], historical_measurement=True)
        shutil.copy2(archive/'forecast.json', folder/'forecast.json')

    dump(folder/'actual_online_run.json', row);dump(folder/'actual_online_timing_samples.json', dict(total_seconds=samples))
    dump(folder/'simulation_samples.json', traces)
    dump(folder/'ll_bts.json', dict(structure='Factored LL-BTS', copies=copies, component_file='component_ll_bts.json',
        global_graph_enumerated=False, component_u=u, global_minimal_u=None, proof=row['verification']['proof']))
    dump(folder/'closed_loop_system_online.json', dict(status='winning', complete_symbolic_description=True,
        explicit_product_enumeration=False, component_file='component_closed_loop.json', copies=copies,
        reachable_states=row['closed_loop_states'], reachable_physical_states=row['closed_loop_physical_states'],
        reachable_transitions=row['closed_loop_transitions'], proof=row['verification']['proof']))
    render_plant(plant, folder, source+f' | asynchronous product x {copies}', pre.deadlocks, pre.safe,
        subtitle=f'Component diagram BEFORE product; full product: {row["reachable_product_states"]:,} states')
    shutil.copy2(folder/'plant.png', folder/'component_product_overview.png')
    export_graph(graph, folder, source+f' | COMPONENT view; product x {copies}', u)
    # export_graph draws one factor; JSON describes the complete exact product.
    report = ['# 修订后的论文乘积与组合式无死锁综合', '',
        f'源例 `{source}`，异步乘积 {copies} 次。源例以本轮修改后的 plant.json 为准。',
        f'完整plant可达状态 {row["reachable_product_states"]:,}；监督后的物理状态 {row["closed_loop_physical_states"]:,}；'
        f'包含控制器记忆的闭环状态 {row["closed_loop_states"]:,}。', '',
        '![乘积之前的分量图与副本数](component_product_overview.png)', '',
        f'Online总时间中位数 {row["total_median_seconds"]*1000:.6f} ms，Python新分配峰值 {peak:,} bytes。',
        '计时包括共享分量的预处理、LL-BTS求解、闭环构建与组合证书检查；没有显式展开全局LL-BTS。',
        f'分量实测所选u={u}；未扫描全局乘积，不能宣称求得全局最小u。',
        '组件间事件不共享；完整检查每个分量闭环无死锁且不禁用不可控事件，因此其异步乘积无死锁。',
        '对1/2/3副本做完整可达检查，并实际执行导出的控制器100条×1000步。',
        '图中闭环展示一个分量；完整乘积见closed_loop_system_online.json和component_closed_loop.json。', '',
        'Offline未求解。理论BTS估计节点最多2^N−1，逐模式UR/NX上界O(2^C·2^N·(N+M))，不是实际节点数预测。',
        f'假设紧凑表示每条转移16 bytes、每状态8 bytes，光显式输入约{row["explicit_input_compact_bytes"]/(1024**3):.3f} GiB；不含BTS、Python对象开销。',
        f'假设处理速度100万～1000万条转移/秒，仅完整扫描输入约{row["explicit_input_scan_seconds_range"][0]:.2f}～{row["explicit_input_scan_seconds_range"][1]:.2f}秒；这是设定吞吐率的粗估，不是实测offline总耗时。',
        '不能把扫描成本、理论最坏界或第一例历史根阶段外推写成完整offline求解时间。',
        '结构优化也可用于offline；这里展示组合结构收益，不宣称online普遍优于所有offline实现。']

    if 'offline_root_forecast' in row:
        f = row['offline_root_forecast']
        report += ['', f'第一例源模型未变，历史逐模式根阶段外推仍为{f["seconds"]/86400:.2f}天、{f["bytes"]/(1024**4):.2f} TiB；未实际跑完整offline，内存更可能先耗尽。']

    (folder/'SYNTHESIS_AND_VALIDATION.md').write_text('\n\n'.join(report)+'\n', encoding='utf-8')
    print(source, copies, 'plant', row['reachable_product_states'], 'closed physical', row['closed_loop_physical_states'], flush=True)

    return row


def main():
    rows = [run_case(source, copies) for source, copies in CASES]
    dump(ROOT/'large_literature_supervisors.json', dict(results=rows, revision='user_review_20261121'))
    (ROOT/'large_literature_supervisors.html').write_text('<!doctype html><meta charset="utf-8"><h1>修订后的千万状态论文乘积</h1>'+''.join(
        '<h2>'+r['source_model']+' × '+str(r['copies'])+'</h2><p><a href="'+r['name']+'/SYNTHESIS_AND_VALIDATION.md">实际结果、组合证书与offline估算</a></p><img style="max-width:100%" src="'+r['name']+'/component_product_overview.png">' for r in rows), encoding='utf-8')


if __name__ == '__main__':main()
