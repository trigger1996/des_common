"""Two completed large known systems plus bounded original-product attempts.

Large array systems use exact singleton UR/NX for full observation and one
uncontrollable event. This is an indexed implementation of a complete BTS,
NOT the original partially observed asynchronous product.
"""

from array import array
from collections import deque
import gc
import hashlib
import json
from pathlib import Path
import statistics
import subprocess
import sys
from time import perf_counter
import tracemalloc

ROOT = Path('outputs/expanded_yin_benchmark/large_systems')


def dump(path, value):path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')


def known_input(n, terminal):
    successor = array('i', range(1, n+1))
    assert successor.itemsize == 4 and sys.byteorder == 'little'
    successor[-1] = -1 if terminal else n-3

    return successor


def indexed_offline_bts(successor):
    """Explicit D/O and edge arrays; UR({q})={q}, NX_o({q})={succ[q]}.

    Every q is reachable from 0 in these two input systems; the ascending loop
    is exactly the BFS discovery order. Both have one admissible full pattern.
    head/link store the full reverse observation-edge relation for count pruning.
    """

    n = len(successor)
    do = array('i', range(n));od = array('i', successor)
    head = array('i', [-1])*n;link = array('i', [-1])*n
    d_ok = bytearray(b'\1')*n;o_ok = bytearray(b'\1')*n
    lost = deque()

    for q in range(n):
        target = od[q]

        if target<0:o_ok[q] = 0;d_ok[q] = 0;lost.append(q)
        else:link[q] = head[target];head[target] = q

    while lost:
        target = lost.popleft();incoming = head[target]

        while incoming >= 0:
            if o_ok[incoming]:
                o_ok[incoming] = 0;d_ok[incoming] = 0;lost.append(incoming)

            incoming = link[incoming]

    return dict(status='winning' if d_ok[0] else 'losing', D=n, O=n,
        edges=n+sum(t >= 0 for t in od), UR_calls=n, NX_calls=n,
        retained_D=sum(d_ok), retained_O=sum(o_ok),
        do=do, od=od, d_ok=d_ok, o_ok=o_ok)


def indexed_online(successor):
    """Same input arrays; full Qd/Qf/Qe scan, then root certificate at u=0.

    Outdegree is <=1 and every event is observable. Reverse adjacency is built
    from the actual input, not assumed from the answer. Longest hidden paths=0.
    """

    n = len(successor);head = array('i', [-1])*n;link = array('i', [-1])*n
    dead = bytearray(n);failure = bytearray(n);removed = bytearray(n);queue = deque()

    for q, target in enumerate(successor):
        if target<0:dead[q] = 1;removed[q] = 1;queue.append(q)
        else:link[q] = head[target];head[target] = q

    while queue:
        target = queue.popleft();q = head[target]

        while q >= 0:
            if not removed[q]:removed[q] = 1;failure[q] = 1;queue.append(q)

            q = link[q]

    safe = bytearray(1-value for value in removed)

    return dict(status='losing' if dead[0] or failure[0] else 'winning',
        u=0, D=1, O=0, edges=0, Qd=sum(dead), Qf=sum(failure), Qe=sum(safe),
        dead=dead, failure=failure, safe=safe)


def peak(call):
    gc.collect();tracemalloc.start();value = call()
    _, value_peak = tracemalloc.get_traced_memory();tracemalloc.stop()
    del value

    return value_peak


def run_indexed_case(n, terminal):
    name = ('large_finite_chain_' if terminal else 'large_chain_cycle_')+str(n)
    folder = ROOT/name;folder.mkdir(parents=True, exist_ok=True)
    materialize_start = perf_counter();successor = known_input(n, terminal)
    input_seconds = perf_counter()-materialize_start

    with (folder/'plant_successors_i32.bin').open('wb') as f:successor.tofile(f)

    digest = hashlib.sha256((folder/'plant_successors_i32.bin').read_bytes()).hexdigest()
    dump(folder/'plant.json', dict(name=name, representation='Explicit indexed transition table',
        states=dict(start=0, stop=n), initial=0, events=['o'], observable=['o'], controllable=[],
        successors_file='plant_successors_i32.bin', dtype='native signed int32, little endian on this host',
        terminal_sentinel=-1, sha256=digest, terminal=terminal,
        topology='0 -> ... -> n-1 -> terminal' if terminal else '0 -> ... -> n-1 -> n-3 (three-state cycle)',
        scope='Synthetic fully observed benchmark, NOT a relabeling of the original case-1 product.'))
    off_times = [];on_times = []

    for repeat in range(7):
        for kind in (('online', 'offline') if repeat%2 else ('offline', 'online')):
            start = perf_counter()
            result = indexed_online(successor) if kind == 'online' else indexed_offline_bts(successor)
            elapsed = perf_counter()-start
            (on_times if kind == 'online' else off_times).append(elapsed)
            del result

    print(name, 'timing complete', flush=True)
    on_peak = peak(lambda:indexed_online(successor))
    print(name, 'online memory complete', flush=True)
    off_peak = peak(lambda:indexed_offline_bts(successor))
    offline = indexed_offline_bts(successor);online = indexed_online(successor)
    assert offline['status'] == online['status']
    baseline = folder/'offline';baseline.mkdir(exist_ok=True)

    for key in ('do', 'od', 'd_ok', 'o_ok'):
        value = offline[key]

        if isinstance(value, array):
            with (baseline/(key+'_i32.bin')).open('wb') as f:value.tofile(f)
        else:(baseline/(key+'_u8.bin')).write_bytes(value)

    dump(baseline/'bts.json', dict(structure='BTS', status=offline['status'],
        D=dict(start=0, stop=n), O=dict(start=0, stop=n), edges=offline['edges'],
        D_to_O='do_i32.bin (source index q, target O index value)',
        O_to_D='od_i32.bin (source O index q, observation o, target D index value; -1 absent)',
        retained_D='d_ok_u8.bin', retained_O='o_ok_u8.bin', UR_calls=n, NX_calls=n,
        certificates=False, horizon=None, complete=True))
    dump(folder/'ll_bts.json', dict(structure='LL-BTS', status=online['status'], u=0, D=1, O=0, edges=0,
        root_certificate='Qf' if terminal else 'Qe: enable all events',
        preprocessing=dict(Qd=online['Qd'], Qf=online['Qf'], Qe=online['Qe'])))

    for mode in ('offline', 'online'):
        dump(folder/('supervisor_'+mode+'.json'), dict(status=online['status'],
            states=[] if terminal else [dict(id='C0', full_pattern=['o'])],
            observable_transitions=[] if terminal else [['C0', 'o', 'C0']],
            source='offline/bts.json' if mode == 'offline' else 'll_bts.json'))
        destination = folder/'offline' if mode == 'offline' else folder
        destination.mkdir(exist_ok=True)
        dump(destination/('closed_loop_system_'+mode+'.json'), dict(status=online['status'],
            complete=True, states=0 if terminal else dict(start=0, stop=n),
            controller_memory=None if terminal else 'C0',
            edges=None if terminal else dict(file=('../' if mode == 'offline' else '')+'plant_successors_i32.bin', event='o', source='array index', target='int32 value'),
            reason='No deadlock-free supervisor exists.' if terminal else
                   'All reachable closed-loop transitions stored in the indexed table; not a sampled trajectory.'))

    row = dict(name=name, states=n, events=1, controllable_events=0, observable_events=1,
        status=online['status'], complete=True, representation='indexed complete BTS; full observation',
        input_materialization_seconds=input_seconds, input_bytes=len(successor)*successor.itemsize,
        offline_seconds=statistics.median(off_times), online_total_seconds=statistics.median(on_times),
        offline_peak_python_bytes=off_peak, online_peak_python_bytes=on_peak,
        time_saving=(statistics.median(off_times)-statistics.median(on_times))/statistics.median(off_times),
        memory_saving=(off_peak-on_peak)/off_peak, offline_D=n, offline_O=n, offline_edges=offline['edges'],
        online_D=1, online_O=0, online_edges=0, repetitions=7,
        timing_scope='Shared explicit successor table excluded on both sides; online includes complete preprocessing; no rendering/export.',
        memory_scope='Separate tracemalloc peak Python allocations, excluding common input; same indexed representation strategy on both sides.',
        limitation='All events observable, one uncontrollable event, one control pattern. Does not measure partial-observation or control-pattern explosion.')
    dump(folder/'comparison.json', row)
    print(name, 'COMPLETE', row['time_saving'], row['memory_saving'], flush=True)

    return row


def product_pre(component, copies, product):
    from des_core.certified_lookahead import Preprocessing

    # Exact case-1 structural certificates: all component states can reach q5;
    # a global deadlock is all q5. Single-successor failure states have exactly
    # one q4 and all other coordinates q5. Hidden predecessors of these targets
    # only change other q4 coordinates to q5, giving longest hidden depth k-1.
    assert set(component.states) == {'q_'+str(i) for i in range(6)}
    dead = frozenset((tuple('q_5' for _ in range(copies)),))
    failure = frozenset(tuple('q_4' if j == i else 'q_5' for j in range(copies)) for i in range(copies))

    return Preprocessing(product, dead, failure, frozenset(), frozenset(), copies-1, copies-1, 0, 0.)


def verify_product_certificates():
    from itertools import product as cartesian
    from des_core.automata import DFA
    from des_core.asynchronous_product import ImplicitProductDFA
    from des_core.certified_lookahead import preprocess
    from examples.non_deadlock import build_small_cycle_example

    component = build_small_cycle_example().dfa

    for copies in (1, 2, 3):
        product = ImplicitProductDFA(component, copies)
        states = frozenset(cartesian(component.states, repeat=copies))
        plant = DFA(states, product.initial, product.events, product.controllable, product.observable,
                  {(q, e):t for q in states for e, t in product.enabled(q)})
        explicit = preprocess(plant);symbolic = product_pre(component, copies, product)
        assert (explicit.deadlocks, explicit.failure, explicit.safe, explicit.horizon) == (
            symbolic.deadlocks, symbolic.failure, symbolic.safe, symbolic.horizon)


def run_product(copies):
    from des_core.asynchronous_product import ImplicitProductDFA
    from des_core.certified_lookahead import solve_limited_lookahead
    from des_core.offline_bts import construct_offline_bts, BTSBudgetExceeded
    from examples.non_deadlock import build_small_cycle_example

    component = build_small_cycle_example().dfa
    product = ImplicitProductDFA(component, copies)
    folder = ROOT/('original_case1_product_'+str(copies));folder.mkdir(parents=True, exist_ok=True)
    dump(folder/'plant_product.json', dict(copies=copies, global_states=6**copies,
        component_states=sorted(component.states), initial=product.initial,
        component_transitions=[[q, e, t] for (q, e), t in component.transitions.items()],
        controllable=sorted(product.controllable), observable=sorted(product.observable),
        events=sorted(product.events), control_patterns=2**len(product.controllable),
        semantics='Fully known asynchronous product transition function; no event partition changes. '
                  'Product table not materialized; UR/NX use the exact known transition function.'))
    row = dict(name=folder.name, states=6**copies, copies=copies, control_patterns=2**len(product.controllable),
             choice_budget=5000, window_state_budget=25000, time_budget_seconds=15.)

    for mode in ('offline', 'online'):
        try:
            if mode == 'offline':
                result = construct_offline_bts(product, max_choices=5000, max_decisions=25000, timeout_seconds=15.)
            else:
                pre = product_pre(component, copies, product)
                result = solve_limited_lookahead(pre, horizon=copies-1, max_choices=5000, max_window_states=25000, timeout_seconds=15.)

            row[mode] = dict(complete=True, status=result.status, seconds=result.seconds)
        except BTSBudgetExceeded as exc:
            row[mode] = dict(status='budget_exceeded', **exc.metrics)
            destination = folder/'offline' if mode == 'offline' else folder
            destination.mkdir(exist_ok=True)
            dump(destination/('closed_loop_system_'+mode+'.json'), dict(status='not_computed', complete=False,
                reason='Synthesis budget exceeded; not an unsolvability proof and not a completed closed loop.'))

        print(folder.name, mode, row[mode], flush=True)

    # Also provide a fully checked feasible constant supervisor, explicitly NOT
    # presented as a completed maximal online/offline BTS synthesis.
    allowed = product.events-{f'o1_{i}' for i in range(copies)}
    assert product.uncontrollable <= allowed
    queue = deque((product.initial,));ids = {product.initial:0};states = [];edges = []

    while queue:
        state = queue.popleft();source = ids[state];states.append(state);out = 0
        assert all(q in ('q_0', 'q_1', 'q_2') for q in state)

        for event, target in product.enabled(state):
            if event not in allowed:continue

            if target not in ids:ids[target] = len(ids);queue.append(target)

            edges.append([source, event, ids[target]]);out += 1

        assert out == copies

    assert len(states) == 3**copies
    dump(folder/'verified_feasible_closed_loop.json', dict(
        status='feasible_constant_supervisor_verified', BTS_synthesis_complete=False,
        controller=dict(states=['C0'], full_pattern=sorted(allowed),
                        rule='Disable every o1_i; memory never changes.'),
        initial=0, states=states, transitions=edges,
        guarantee='All reachable states and enabled transitions enumerated; all uncontrollable events enabled; no deadlocks.',
        limitation='A verified candidate, not a claimed maximal supervisor extracted from a completed BTS.'))
    row['verified_feasible_closed_loop_states'] = len(states)
    row['verified_feasible_closed_loop_edges'] = len(edges)
    row['time_or_space_saving'] = None
    row['comparison_note'] = 'Incomplete synthesis runs are excluded from savings comparisons.'
    dump(folder/'comparison.json', row)

    return row


def report(completed, products):
    for r in completed:
        r.update(time_saved_seconds=r['offline_seconds']-r['online_total_seconds'],
            time_speedup=r['offline_seconds']/r['online_total_seconds'],
            memory_saved_bytes=r['offline_peak_python_bytes']-r['online_peak_python_bytes'],
            memory_saved_MiB=(r['offline_peak_python_bytes']-r['online_peak_python_bytes'])/(1024**2),
            online_peak_MiB=r['online_peak_python_bytes']/(1024**2),
            offline_peak_MiB=r['offline_peak_python_bytes']/(1024**2))
        dump(ROOT/r['name']/'comparison.json', r)

    lines = ['# 大系统 online/offline 实验', '',
        '## 两个完整完成的结构化系统', '',
        '这两个系统分别有 6^7=279936 和 6^8=1679616 个实际可达状态，但拓扑是新构造的链/链加环，'
        '不是原 case-1 异步乘积。均为完全观测、单个不可控事件 o。传统 BTS 确实为每个可达状态建立 D/O 节点、'
        '计算完整 UR/NX 并完成剪枝；利用单元素估计的索引编码避免数百万 Python 小集合的额外成本。'
        '二者都使用索引数组实现，不能将这组数字与小模型的 Python 集合实现混作同一性能基线。', '',
        '原始转移表完整保存在 plant_successors_i32.bin；offline/ 下的 BTS 边及保留标记数组均实际构建并写盘。'
        '闭环 JSON 的索引表示引用完整转移表，未以缩略图或一次运行轨迹代替完整闭环。',
        '在线时间包含全图预处理，公共输入表构建费用单列；内存为分别测量的 Python 分配峰值，不是进程RSS。', '',
        '| 系统 | 状态数 | 结果 | offline秒 | online含预处理秒 | 绝对节约/秒 | 时间节约 | offline峰值/MiB | online峰值/MiB | 峰值绝对节约/MiB | 峰值节约 |',
        '| --- | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |']

    for r in completed:
        lines.append(f'| [{r["name"]}]({r["name"]}/comparison.json) | {r["states"]} | {r["status"]} | '
            f'{r["offline_seconds"]:.6f} | {r["online_total_seconds"]:.6f} | {r["time_saved_seconds"]:.6f} | {r["time_saving"]:.2%} | '
            f'{r["offline_peak_MiB"]:.6f} | {r["online_peak_MiB"]:.6f} | {r["memory_saved_MiB"]:.6f} | {r["memory_saving"]:.2%} |')

    worked = completed[-1]
    lines += ['', '### 数值如何计算', '',
        '时间绝对节约 `ΔT=T_off−T_on`，节约率 `ΔT/T_off×100%`；速度倍数 `T_off/T_on`。'
        '内存绝对节约 `ΔM=M_off−M_on`，节约率 `ΔM/M_off×100%`；MiB=bytes/1048576。',
        f'以 {worked["name"]} 为例：',
        f'- ΔT={worked["offline_seconds"]:.9f}−{worked["online_total_seconds"]:.9f}'
        f'={worked["time_saved_seconds"]:.9f}s；{worked["time_saved_seconds"]:.9f}/'
        f'{worked["offline_seconds"]:.9f}×100%={worked["time_saving"]:.4%}。',
        f'- ΔM={worked["offline_peak_python_bytes"]:,}−{worked["online_peak_python_bytes"]:,}'
        f'={worked["memory_saved_bytes"]:,} bytes={worked["memory_saved_MiB"]:.6f} MiB；'
        f'{worked["memory_saved_bytes"]:,}/{worked["offline_peak_python_bytes"]:,}×100%={worked["memory_saving"]:.4%}。']
    lines += ['', '这两个系统的构建/预处理均为线性阶，在线证书求解本身为常数阶。'
        '数组图存储 offline 为线性阶，online 的预处理存储也为线性阶；不能声称总复杂度阶普遍降低。',
        '', '## 原七、八副本异步乘积：实际预算内尝试', '',
        '保留原分量的控制/观测属性。完整产品转移函数已知，传统 BTS 按实际完整 UR/NX 展开，'
        '不是把所有事件改成不可控/可观，也没有用旧乐观 LL-BTS 计时充当认证结果。'
        '每次最多5000个模式、25000窗口状态、15秒；截断不等于不可解。',
        'Online 的产品 Qd/Qf/Qe 与 u 使用可证明的结构公式，已与1/2/3副本的显式全图预处理逐项核对。'
        '该结构预处理是针对 case-1 的精确扩展，不是声称原显式扫描器已遍历百万状态。', '']

    for r in products:
        lines += [f'### {r["name"]}',
            f'- 原始可达状态数 {r["states"]}，每个估计处的控制模式数 {r["control_patterns"]}。',
            '- Offline: '+json.dumps(r['offline'], ensure_ascii=False),
            '- Online: '+json.dumps(r['online'], ensure_ascii=False),
            f'- 另提供验证过的常量可行策略：禁用所有 o1_i；完整可达闭环为 '
            f'{r["verified_feasible_closed_loop_states"]} 状态、{r["verified_feasible_closed_loop_edges"]} 转移。'
            '此候选不是未完成 BTS 的最大宽松综合结果。',
            '- 未完成综合，不计算 online/offline 节约率。', '']

    (ROOT/'LARGE_SYSTEM_COMPARISON.md').write_text('\n'.join(lines)+'\n', encoding='utf-8')
    dump(ROOT/'summary.json', dict(completed_indexed_systems=completed, original_products=products))


def main():
    ROOT.mkdir(parents=True, exist_ok=True)
    verify_product_certificates()
    products = [run_product(copies) for copies in (7, 8)]
    completed = []

    for n, terminal in ((6**7, True), (6**8, False)):
        # Isolate each large run so input/temporary arrays are released reliably.
        child = subprocess.run([sys.executable, '-X', 'utf8', __file__, 'worker', str(n), str(int(terminal))],
            timeout=240, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))

        if child.returncode:raise RuntimeError('Large worker failed')

        name = ('large_finite_chain_' if terminal else 'large_chain_cycle_')+str(n)
        completed.append(json.loads((ROOT/name/'comparison.json').read_text(encoding='utf-8')))

    report(completed, products)


if __name__ == '__main__':
    if len(sys.argv)>1 and sys.argv[1] == 'worker':run_indexed_case(int(sys.argv[2]), bool(int(sys.argv[3])))
    else:main()
