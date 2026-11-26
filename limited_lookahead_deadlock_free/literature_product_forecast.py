"""Build a >10^7-state genuine literature product and quantify a forecast.

Actual online compositional certification and actual target-size root UR/NX
microbenchmarks are separated from estimated exhaustive offline costs.
"""

from collections import deque
from itertools import product as cartesian
import gc
import hashlib
import json
from pathlib import Path
import random
import shutil
import statistics
from time import perf_counter
import tracemalloc

from certified_benchmark import dump, export_bts
from compare_online_offline import load_plant
from des_core.asynchronous_product import ImplicitProductDFA
from des_core.automata import DFA
from des_core.certified_lookahead import Preprocessing, preprocess, solve_limited_lookahead, solve_offline, validate_policy
from des_core.offline_bts import traditional_ur_nx

ROOT = Path('outputs/expanded_yin_benchmark')
SOURCE = '21AutomaticaOptimal_fig_2'
COPIES = 6
NAME = 'literature_product_21AutomaticaOptimal_fig_2_6copy'


def reach_and_hidden_bound(component):
    """Check the actual component, including reachability and hidden DAG depth."""

    reachable = {component.initial};queue = deque(reachable)

    while queue:
        q = queue.popleft()
        assert component.enabled(q), ('component deadlock', q)

        for _, target in component.enabled(q):
            if target not in reachable:reachable.add(target);queue.append(target)

    assert reachable == component.states
    assert all(component.enabled(q) for q in component.states)
    successors = {q:{t for e, t in component.enabled(q) if e not in component.observable}
                for q in component.states}
    incoming = {q:0 for q in component.states}

    for targets in successors.values():
        for target in targets:incoming[target] += 1

    queue = deque(q for q in component.states if incoming[q] == 0)
    distance = {q:0 for q in component.states};visited = 0

    while queue:
        q = queue.popleft();visited += 1

        for target in successors[q]:
            distance[target] = max(distance[target], distance[q]+1)
            incoming[target] -= 1

            if incoming[target] == 0:queue.append(target)

    assert visited == len(component.states), 'Hidden graph must be acyclic for this depth bound.'

    return reachable, max(distance.values())


def compositional_context(component, product):
    start = perf_counter()
    _, hidden_depth = reach_and_hidden_bound(component)

    # Every product state has outgoing events; Qd=Qf=empty and Qe=all states.
    # Each hidden step changes exactly one coordinate. The DAG depth sum is a
    # sufficient global u, though the Qe root already allows immediate stopping.
    return Preprocessing(product, frozenset(), frozenset(), product.states, frozenset(),
        hidden_depth*product.copies, 0, 0, perf_counter()-start)


def verify_composition_small(component):
    for copies in (1, 2):
        product = ImplicitProductDFA(component, copies)
        states = frozenset(cartesian(component.states, repeat=copies))
        explicit = DFA(states, product.initial, product.events, product.controllable, product.observable,
            {(q, e):t for q in states for e, t in product.enabled(q)})
        pre = preprocess(explicit, max_path_visits=2_000_000)
        symbolic = compositional_context(component, product)
        assert not pre.deadlocks and not pre.failure and pre.safe == states
        assert pre.horizon <= symbolic.horizon
        result = solve_limited_lookahead(symbolic, horizon=max(1, symbolic.horizon), max_window_states=1)
        assert result.status == 'winning' and result.observation_count == 0

    # Also certify the actual source controller rather than merely its name.
    result = solve_offline(component)
    assert result.status == 'winning'
    validate_policy(preprocess(component), result)


def solve_online(component, product):
    start = perf_counter();pre = compositional_context(component, product)
    pre_seconds = perf_counter()-start
    start = perf_counter();result = solve_limited_lookahead(pre, horizon=max(1, pre.horizon), max_window_states=1)
    patterns = result.maximal_patterns;solve_seconds = perf_counter()-start
    assert result.status == 'winning' and patterns == (product.controllable,)
    assert result.decision_count == 1 and result.observation_count == 0

    return pre, result, pre_seconds, solve_seconds


def root_record(product, initial, pattern):
    record = traditional_ur_nx(product, initial, pattern)
    full = pattern|product.uncontrollable
    valid = all(any(e in full for e, t in product.enabled(q)) for q in record.closure)
    assert valid

    return record


def memory_for_records(product, initial, patterns, count):
    gc.collect();tracemalloc.start()
    records = [root_record(product, initial, frozenset(tuple(patterns[i]))) for i in range(count)]
    current, peak = tracemalloc.get_traced_memory();tracemalloc.stop()
    assert len(records) == count
    del records

    return dict(count=count, retained_python_bytes=current, peak_python_bytes=peak)


def main():
    component = load_plant(ROOT/SOURCE)
    verify_composition_small(component)
    product = ImplicitProductDFA(component, COPIES)
    folder = ROOT/NAME;folder.mkdir(exist_ok=True)
    reachable, hidden_depth = reach_and_hidden_bound(component)

    for attr in ('states', 'events', 'controllable', 'observable', 'uncontrollable'):getattr(product, attr)

    n = len(reachable)**COPIES
    patterns_count = 2**len(product.controllable)
    assert n >= 10**7 and len(component.states)**(COPIES-1)<10**7
    local_root = traditional_ur_nx(component, frozenset((component.initial,)), frozenset())
    # No controllable event can occur before the first observation, hence ALL
    # root control patterns share the same complete UR and NX. The classical
    # explicit BTS still has a distinct O node for each (UR, pattern) pair.
    assert all(e not in component.controllable for q in local_root.closure for e, t in component.enabled(q))
    controls = tuple(sorted(product.controllable));rng = random.Random(20261121)
    patterns = []

    for i in range(128):
        size = i%(len(controls)+1)
        patterns.append(frozenset(rng.sample(controls, size)))

    initial = frozenset((product.initial,))
    warm = root_record(product, initial, product.controllable)
    closure_size = len(local_root.closure)**COPIES
    successors_count = COPIES*len(local_root.successors)
    successor_members = sum(len(x)*len(local_root.closure)**(COPIES-1)
                          for e, x in local_root.successors)*COPIES
    assert len(warm.closure) == closure_size
    assert len(warm.successors) == successors_count
    assert sum(len(x) for e, x in warm.successors) == successor_members
    reference = (warm.closure, warm.successors)
    root_samples = []

    for repeat in range(3):
        for pattern in patterns:
            start = perf_counter();record = root_record(product, initial, pattern)
            root_samples.append(perf_counter()-start)
            assert (record.closure, record.successors) == reference

    print('Target-size root microbenchmarks complete:', len(root_samples), flush=True)
    memory_small = memory_for_records(product, initial, patterns, 8)
    memory_large = memory_for_records(product, initial, patterns, 24)
    memory_per_record = (memory_large['retained_python_bytes']-memory_small['retained_python_bytes'])/16
    pre_samples = [];online_samples = [];totals = []

    for _ in range(101):
        pre, result, pt, st = solve_online(component, product)
        pre_samples.append(pt);online_samples.append(st);totals.append(pt+st)

    gc.collect();tracemalloc.start();pre, result, _, _ = solve_online(component, product)
    _, online_peak = tracemalloc.get_traced_memory();tracemalloc.stop()
    pre, result, _, _ = solve_online(component, product)
    export_bts(pre, result, folder, draw=False)
    ll = json.loads((folder/'ll_bts.json').read_text(encoding='utf-8'))
    ll.update(window_construction='Skipped after exact root Qe certificate, before Post_<=u enumeration.',
              preprocessing='Compositional all-live certificate; hidden DAG depth sum; no product-table materialization.')
    dump(folder/'ll_bts.json', ll)
    source_hash = hashlib.sha256((ROOT/SOURCE/'plant.json').read_bytes()).hexdigest()
    descriptor = dict(name=NAME, source_model=SOURCE, source_file='../'+SOURCE+'/plant.json',
        source_sha256=source_hash, copies=COPIES, component_states=len(component.states),
        reachable_component_states=len(reachable), reachable_product_states=n,
        product_transitions=COPIES*len(component.transitions)*len(component.states)**(COPIES-1),
        initial=product.initial, events=sorted(product.events), controllable=sorted(product.controllable),
        observable=sorted(product.observable), uncontrollable=sorted(product.uncontrollable),
        composition='Exact asynchronous product: event e_i updates coordinate i only. Partitions inherited.',
        component_transitions=[[q, e, t] for (q, e), t in sorted(component.transitions.items())],
        representation='Factored exact transition function; full reachable state count proved from component reachability.')
    dump(folder/'plant_product.json', descriptor)
    shutil.copy2(ROOT/SOURCE/'plant.png', folder/'component_plant.png')
    dump(folder/'supervisor_online.json', dict(status='winning', initial='C0', states=['C0'],
        full_pattern=sorted(product.events), controllable_pattern=sorted(product.controllable),
        rule='Enable every event forever; memory remains C0 on every observation and hidden event.',
        source='ll_bts.json, Qe safe terminal', guarantee='Every component state has an outgoing transition; so does every product state.'))
    dump(folder/'closed_loop_system_online.json', dict(status='winning', complete_symbolic_description=True,
        explicit_state_enumeration_performed=False, reachable_states=n,
        reachable_transitions=descriptor['product_transitions'], controller_memory='C0',
        representation='Exact same asynchronous product as plant_product.json: supervisor enables all events.',
        proof='All component states are reachable. Interleave their reaching strings to reach any tuple. '
              'Every component state has an outgoing event, so every product tuple is nondeadlocked.',
        source_model_sha256=source_hash))
    sorted_times = sorted(root_samples)
    per_pattern = statistics.median(root_samples)
    low = sorted_times[len(sorted_times)//10];high = sorted_times[len(sorted_times)*9//10]
    forecast = dict(name=NAME, source_model=SOURCE, copies=COPIES, reachable_states=n,
        controllable_events=len(product.controllable), observable_events=len(product.observable),
        total_events=len(product.events), u=pre.horizon,
        online_status='winning', online_measurement_repetitions=101,
        online_pre_median_seconds=statistics.median(pre_samples),
        online_solve_median_seconds=statistics.median(online_samples),
        online_total_median_seconds=statistics.median(totals), online_peak_python_bytes=online_peak,
        online_D=1, online_O=0, online_preprocessing='Exact compositional Qe certificate, not explicit scan of all product states.',
        offline_complete=False, offline_total_measured_seconds=None,
        root_control_patterns=patterns_count, root_explicit_O_nodes_required=patterns_count,
        root_UR_cardinality=closure_size, root_observable_successors=successors_count,
        root_successor_estimate_memberships=successor_members,
        root_record_timing_samples=len(root_samples), root_record_median_seconds=per_pattern,
        offline_root_stage_estimate_seconds=patterns_count*per_pattern,
        offline_root_stage_scenario_seconds=[patterns_count*low, patterns_count*high],
        scenario_note='10th/90th empirical per-record times times pattern count; scenario range, NOT a confidence interval or full-run measurement.',
        sampled_record_memory=[memory_small, memory_large], root_record_retained_python_bytes_estimate=memory_per_record,
        offline_root_records_python_bytes_estimate=patterns_count*memory_per_record,
        separate_set_membership_reference_bytes=patterns_count*(closure_size+successor_members)*8,
        estimated_root_stage_time_saved_seconds=patterns_count*per_pattern-statistics.median(totals),
        root_stage_to_online_speedup_estimate=patterns_count*per_pattern/statistics.median(totals),
        limitations=[
            'Root-stage projection for the current pattern-wise complete UR/NX implementation; complete offline construction/pruning was not run.',
            'Different caching, bitsets, symbolic pattern families or compositional offline synthesis can change the forecast substantially.',
            'A memory-capacity failure is likely before exhaustive offline completion; no fake completion time is reported.',
            'This all-live paper model demonstrates Qe certificate benefits; not representative of arbitrary mixed-risk products.',
            'No event observability or controllability was changed.'])
    dump(folder/'forecast.json', forecast)
    dump(folder/'root_timing_samples.json', dict(seed=20261121, seconds=root_samples,
        component_closure=sorted(local_root.closure), component_successors=[(e, sorted(x)) for e, x in local_root.successors],
        sample_patterns=[sorted(p) for p in patterns], warm_input_index=True, result_cache=False))
    dump(folder/'online_timing_samples.json', dict(pre_seconds=pre_samples, solve_seconds=online_samples, total_seconds=totals))
    (folder/'offline').mkdir(exist_ok=True)
    dump(folder/'offline/closed_loop_system_offline.json', dict(status='not_computed', complete=False,
        reason='Only mandatory target-size root UR/NX work was sampled; full exhaustive offline BTS exceeds practical memory estimates.',
        estimate_file='../forecast.json'))
    write_report(folder, forecast, descriptor)
    render_overview(folder, forecast)
    print(json.dumps(forecast, ensure_ascii=False, indent=2))


def write_report(folder, r, descriptor):
    seconds = r['offline_root_stage_estimate_seconds'];memory = r['offline_root_records_python_bytes_estimate']
    lines = ['# 论文自动机六副本乘积：千万状态与耗时估算', '',
        f'来源：`{SOURCE}`，15状态、24条转移，原始 partial observation 与 controllability 均继承。'
        '该源例已通过完整 offline BTS 得到可行闭环。源图见 [component_plant.png](component_plant.png)。', '',
        '## 系统及可解性', '',
        f'- 最少需要6副本：15^5={15**5:,}<10^7，15^6={15**6:,}≥10^7。',
        f'- 实际可达状态 {r["reachable_states"]:,}；转移 {descriptor["product_transitions"]:,}。'
        '每个分量的15个状态都可达，异步交错可到达任意状态元组，故不是仅报笛卡尔积名义规模。',
        f'- 事件共 {r["total_events"]}，其中可控{r["controllable_events"]}、可观{r["observable_events"]}；没有改成全可观/全不可控。',
        '- 每个分量状态均有出边，因此整个乘积 Qd=Qf=∅、Qe=Q。采用“永远允许全部事件”的一个状态监督器即可无死锁。',
        '- 乘积未逐状态展开，`plant_product.json` 与 `closed_loop_system_online.json` 给出完整精确因子化转移描述及可达性/无死锁证明。',
        f'- 局部不可观测图是DAG，最长隐藏路径为2；乘积取充分上界u=2×6={r["u"]}。'
        '根估计已获Qe证书，先终止再展开窗口，避免无必要地枚举 Post_<=u。', '',
        '## 实测 online（包含本例的组合式预处理）', '',
        f'101次新鲜求解：预处理中位数 {r["online_pre_median_seconds"]:.9f}s；'
        f'求解中位数 {r["online_solve_median_seconds"]:.9f}s；逐次总时间中位数 {r["online_total_median_seconds"]:.9f}s。',
        f'Python分配峰值 {r["online_peak_python_bytes"]:,} bytes '
        f'({r["online_peak_python_bytes"]/1024:.3f} KiB)。LL-BTS为1个D节点、0个O节点。',
        '预处理检查15状态分量的真实转移/可达性与隐藏DAG，推出乘积Qe证书；不是声称显式扫描了一千多万状态。'
        '输入模型/公共索引、导出不计时；此结构优化已与1/2副本的显式预处理及源例offline策略核对。', '',
        '## Offline：目标规模上的实测单步，外推初始节点枚举成本', '',
        f'每个估计处有 P=2^30={r["root_control_patterns"]:,} 个模式。初始隐藏可达集大小为3^6={r["root_UR_cardinality"]}；'
        f'有{r["root_observable_successors"]}个可观后继，每个后继486状态，合计{r["root_successor_estimate_memberships"]}个集合成员。',
        '初始隐藏可达集上没有任何可控事件可执行，因此所有模式的UR/NX集合相同；但传统显式BTS的O节点含控制模式，'
        '模式不同仍为不同O节点。仅初始D节点就要求10.7亿个O节点，而非仅仅10.7亿次可能无效的候选检查。',
        f'在真实六副本乘积上测{r["root_record_timing_samples"]}次完整UR/NX与局部无死锁检查，'
        f'单记录中位数 t={r["root_record_median_seconds"]:.9f}s。没有用小规模状态数直接乘比例冒充实测。', '',
        f'当前逐模式实现的根阶段估算：`T_root≈P×t` = {r["root_control_patterns"]:,} × '
        f'{r["root_record_median_seconds"]:.9f} = {seconds:,.3f}s = {seconds/3600:,.2f}小时 = {seconds/86400:,.2f}天。',
        f'按样本10%/90%分位单步耗时作情景外推：{r["offline_root_stage_scenario_seconds"][0]/86400:.2f}～'
        f'{r["offline_root_stage_scenario_seconds"][1]/86400:.2f}天。这不是置信区间，也不是完整offline实测。',
        f'估算时间差（仅根阶段）`P×t−T_online` = {r["estimated_root_stage_time_saved_seconds"]:,.3f}s；'
        f'估算比值 `P×t/T_online` = {r["root_stage_to_online_speedup_estimate"]:,.0f}。'
        '这是实测online对比估算offline根阶段，不应标为完成实验的加速比。', '',
        '## 内存估算及适用范围', '',
        f'分别保留8与24份根记录，按 `(M24−M8)/16` 得每记录约 '
        f'{r["root_record_retained_python_bytes_estimate"]:,.1f} bytes。'
        f'根阶段记录估算 `P×m_record`={memory:,.0f} bytes={memory/(1024**4):,.2f} TiB。',
        f'仅按现有“每模式独立保存UR/NX集合”的成员引用，每份({r["root_UR_cardinality"]}+'
        f'{r["root_successor_estimate_memberships"]})×8 bytes，合计 '
        f'{r["separate_set_membership_reference_bytes"]/(1024**4):.2f} TiB（尚未计集合哈希表/对象/模式）。',
        '所以通常首先遇到内存容量限制，不能承诺传统实现实际能运行到所估算天数。'
        '缓存共享闭包、位集、控制模式族或组合式offline都可能显著改变成本；上述估算只针对当前传统显式逐模式基线。'
        '完整后续BTS、剪枝、根极大模式筛选均未计入根阶段估算，也未报告伪造的完整offline时间。',
        '该候选适合展示Qe证书的巨大收益；不能据此推断任意含危险状态系统也有同样收益。', '',
        '数据：[forecast.json](forecast.json)、[原始计时样本](root_timing_samples.json)、'
        '[online样本](online_timing_samples.json)、[可执行监督器](supervisor_online.json)。']
    (folder/'PRODUCT_FORECAST.md').write_text('\n'.join(lines)+'\n', encoding='utf-8')


def render_overview(folder, r):
    import matplotlib

    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.patches import FancyBboxPatch

    fig, ax = plt.subplots(figsize=(11, 4.5));ax.axis('off')
    ax.add_patch(FancyBboxPatch((.31, .30), .38, .35, boxstyle='round,pad=.03',
        facecolor='#c1e2cb', edgecolor='#32704c', transform=ax.transAxes))
    ax.text(.5, .475, 'D0: {initial product tuple}\nQe certificate: enable all events\nNo O-node expansion needed',
        ha='center', va='center', fontsize=13, transform=ax.transAxes)
    ax.annotate('', xy=(.28, .475), xytext=(.12, .475), xycoords='axes fraction',
                arrowprops=dict(arrowstyle='->', lw=1.5))
    ax.set_title(f'Certified LL-BTS | u={r["u"]}\n1 decision node, 0 observation nodes; compositional safety proof', fontsize=13)
    fig.tight_layout();fig.savefig(folder/'ll_bts.png', dpi=150);fig.savefig(folder/'ll_bts.svg');plt.close(fig)
    fig, ax = plt.subplots(figsize=(14, 5.5));ax.axis('off')

    for i in range(6):
        x = .04+i*.155
        ax.add_patch(FancyBboxPatch((x, .43), .125, .23, boxstyle='round,pad=.012',
            facecolor='#c9dff0', edgecolor='#3c6586', transform=ax.transAxes))
        ax.text(x+.0625, .545, f'G{i+1}\n15 reachable states', ha='center', va='center', fontsize=10, transform=ax.transAxes)

        if i<5:ax.text(x+.14, .54, '×', ha='center', va='center', fontsize=16, transform=ax.transAxes)

    ax.text(.5, .25, f'Supervisor C0: allow all {r["total_events"]} events forever\n'
        f'Closed-loop reachable states = 15^6 = {r["reachable_states"]:,}\n'
        'Exact factored diagram; full product is not individually drawn or enumerated.',
        ha='center', va='center', fontsize=13, transform=ax.transAxes)
    ax.set_title('21AutomaticaOptimal Fig.2 | Asynchronous closed-loop product\n'
                 'Original controllability and partial observability retained', fontsize=14)
    fig.tight_layout();fig.savefig(folder/'closed_loop_system_online.png', dpi=150)
    fig.savefig(folder/'closed_loop_system_online.svg');plt.close(fig)
    (folder/'index.html').write_text('<!doctype html><meta charset="utf-8"><title>千万状态论文乘积</title>'
        '<style>body{font:16px system-ui;max-width:1200px;margin:30px auto}img{max-width:100%}</style>'
        '<h1>论文自动机六副本：11,390,625 个可达状态</h1>'
        '<p>来源21AutomaticaOptimal_fig_2；保留原部分观测/控制划分。当前模型全部状态可安全运行，'
        '组合式Qe证书使LL-BTS直接终止。该例专门展示证书收益，不代表任意危险混合系统。</p>'
        f'<p>实测online（含组合式预处理）：{r["online_total_median_seconds"]*1e6:.3f} µs；'
        f'Python峰值 {r["online_peak_python_bytes"]:,} bytes。'
        f'传统逐模式根阶段估算约{r["offline_root_stage_estimate_seconds"]/86400:.2f}天，'
        f'记录内存约{r["offline_root_records_python_bytes_estimate"]/(1024**4):.2f} TiB。'
        'Offline完整综合未运行，估算不是完整实测，通常会先内存不足。</p>'
        '<p><a href="PRODUCT_FORECAST.md">方法、运算、假设与限制</a> · <a href="forecast.json">完整数值</a> · '
        '<a href="root_timing_samples.json">目标规模抽样</a> · <a href="supervisor_online.json">可执行监督器</a> · '
        '<a href="closed_loop_system_online.json">精确因子化闭环</a></p>'
        '<h2>源分量</h2><img src="component_plant.png"><h2>认证LL-BTS</h2><img src="ll_bts.png">'
        '<h2>乘积闭环</h2><img src="closed_loop_system_online.png">', encoding='utf-8')


if __name__ == '__main__':main()
