"""Run Cai-2018, classic LLP-1992, and our LL-BTS on identical example inputs.

python -X utf8 three_method_comparison.py
All three methods receive the same fully observed component models. The two
published methods retain their original marked nonblocking interpretation;
their resulting controls are independently checked for continuing deadlock-free
execution. Failure of one local window is never labeled global losing.
"""

import argparse
from collections import deque
from dataclasses import replace
import gc
import hashlib
import json
from pathlib import Path
import random
from statistics import mean
import subprocess
import sys
from time import perf_counter
import tracemalloc

from des_core.automata import DFA
from des_core.certified_lookahead import preprocess, solve_limited_lookahead, executable_choices
from des_core.classic_llp_1992 import solve_classic_llp
from des_core.resource_monitor import environment_record, process_snapshot, interval_usage
from des_core.warehouse_2018 import solve_warehouse, synchronous_product
from warehouse_2018_case_study import load_product_components, physical_successors, plant_record


ROOT = Path(__file__).resolve().parent
DEFAULT = ROOT / 'outputs/case_studies/three_method_comparison'
METHODS = ('cai2018', 'llp1992', 'ours')
LABELS = dict(cai2018='Cai-2018', llp1992='LLP-1992', ours='Our LL-BTS')
SOURCES = dict(llp1992='https://doi.org/10.1109/9.182478',
               cai2018='https://www.caikai.org/publication/TatsumotoShiraishiCaiLin_18CEP.pdf',
               tutorial='https://arxiv.org/abs/2006.06514')


def dump(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')


def components_for(name):
    if name.startswith('Ring'):
        copies = int(name[4:-3])
        size = copies + 1
        components = []

        for index in range(copies):
            states = frozenset([str(q) for q in range(size)] + ['dead'])
            step = f'step_{index}'
            events = frozenset({step, 'fail'})
            transitions = {(str(q), step): str((q + 1) % size) for q in range(size)}
            transitions.update({(str(q), 'fail'): 'dead' for q in range(size)})
            model = DFA(states, '0', events, frozenset({'fail'}), events, transitions)
            components.append((model, states))

        return components

    if name == 'Fig1-FO':
        record = json.loads((ROOT / 'examples/paper_fig1_r1/plant.json').read_text(encoding='utf-8'))
        events = frozenset(record['events'])
        plant = DFA(frozenset(record['states']), record['initial'], events,
                    frozenset(record['controllable']), events,
                    {(q, event): target for q, event, target in record['transitions']})

        return [(plant, plant.states)]

    return load_product_components(name[0], int(name[1:-3]))


def input_record(components):
    return [plant_record(plant, marked) for plant, marked in components]


def input_hash(components):
    return hashlib.sha256(json.dumps(input_record(components), sort_keys=True).encode('utf-8')).hexdigest()


def legal_function(components):
    # Same physical constraint for all methods: do not enter a DFA deadlock.
    return lambda q: any(plant.enabled(q[i]) for i, (plant, _) in enumerate(components))


def calculate(method, components, horizon, *, interpretation='equations'):
    started = perf_counter()
    legal = legal_function(components)

    if method == 'cai2018':
        result = solve_warehouse(components, horizon=horizon, legal=legal,
                                 interpretation=interpretation, max_states=200_000)
        metrics = dict(root_status=result.status, constructed_states=len(result.window.states),
                       constructed_transitions=result.window_transitions,
                       state_type='physical states of the local component product',
                       root_gamma_c=sorted(result.gamma_c), adopted_horizon=horizon,
                       component_product_states=result.component_product_states,
                       interpretation=interpretation)
    else:
        plant, marked = synchronous_product(components, max_states=200_000)

        if method == 'llp1992':
            result = solve_classic_llp(plant, horizon=horizon, legal=legal, marked=marked)
            metrics = dict(root_status=result.status, constructed_states=result.stored_states,
                           constructed_transitions=result.stored_transitions,
                           state_type='distinct (physical state, depth) projection occurrences',
                           root_gamma_c=sorted(result.gamma_c), adopted_horizon=horizon,
                           interpretation='optimistic, exact same-depth sharing')
        else:
            pre = preprocess(plant)
            result = solve_limited_lookahead(pre, horizon=horizon)
            metrics = dict(root_status=result.status,
                           constructed_states=result.decision_count + result.observation_count,
                           constructed_transitions=result.edge_count,
                           state_type='decision/observation information states',
                           root_gamma_c=[sorted(pattern) for pattern in result.maximal_patterns],
                           adopted_horizon=result.horizon, bar_u=pre.lookahead_lower_bound,
                           interpretation='fixed common horizon; structural analysis included')

    metrics['seconds'] = perf_counter() - started

    return metrics


def decision_at(method, components, plant, marked, pre, q, horizon, interpretation):
    legal = legal_function(components)

    if method == 'cai2018':
        current = [(replace(component, initial=q[i]), goals)
                   for i, (component, goals) in enumerate(components)]
        result = solve_warehouse(current, horizon=horizon, legal=legal,
                                 interpretation=interpretation)

        return result.gamma_c, result.status, len(result.window.states), None

    if method == 'llp1992':
        result = solve_classic_llp(plant, initial=q, horizon=horizon, legal=legal, marked=marked)

        return result.gamma_c, result.status, result.stored_states, result.stored_transitions

    if q in pre.Q_e:
        return plant.controllable, 'winning', 0, 0

    estimate = frozenset({q})
    result = solve_limited_lookahead(pre, estimate=estimate, horizon=horizon)
    options = executable_choices(pre, result, estimate) if result.status == 'winning' else ()
    selected = max(options, key=lambda choice: (len(choice.pattern), tuple(sorted(choice.pattern)))) if options else None

    return (selected.pattern if selected else frozenset(), result.status,
            result.decision_count + result.observation_count, result.patterns_tested)


def sample_trajectory(method, components, horizon, *, cap=50, seed=199212, interpretation='equations'):
    """Actual observation-triggered solves, with model setup charged once."""

    started = perf_counter()
    plant, marked = synchronous_product(components) if method != 'cai2018' else (None, None)
    pre = preprocess(plant) if method == 'ours' else None
    setup_seconds = perf_counter() - started
    q = tuple(component.initial for component, _ in components)
    uncontrollable = frozenset().union(*(component.uncontrollable for component, _ in components))
    rng = random.Random(seed)
    steps = []
    stop = 'observation_cap'
    total = setup_seconds

    for index in range(cap):
        before = process_snapshot()
        tick = perf_counter()
        gamma_c, status, size, checks = decision_at(method, components, plant, marked, pre,
                                                    q, horizon, interpretation)
        seconds = perf_counter() - tick
        total += seconds
        row = dict(k=index, q=q, status=status, gamma_c=sorted(gamma_c), seconds=seconds,
                   cumulative_seconds=total, stored_states=size, checks=checks,
                   resources=interval_usage(before, process_snapshot()))
        steps.append(row)

        if status not in ('local_supervisor', 'winning'):
            stop = 'local_replanning_failure'

            break

        gamma = gamma_c | uncontrollable
        outcomes = sorted((event, target) for event, target in physical_successors(components, q) if event in gamma)

        if not outcomes:
            stop = 'deadlocking'

            break

        event, target = rng.choice(outcomes)
        row.update(event=event, target=target)
        q = target

    return dict(seed=seed, cap=cap, setup_seconds=setup_seconds, steps=steps,
                executed_events=sum('event' in row for row in steps), stop=stop,
                cumulative_solve_seconds=total,
                scope='One seeded trajectory under this method; same scheduler seed, possibly different controls/traces. '
                      'Input/global composition/analysis charged once where required. No reuse of sampled solve times.')


def validate_execution(method, components, horizon, *, interpretation='equations'):
    """Enumerate all executions of each method's own receding policy.

    Full observation, deterministic state-based specifications, and fixed N
    make a physical state sufficient memory here. Repeated states share the
    same residual decision problem. All enabled outcomes are checked, rather
    than choosing a single favorable scheduler. Validation is outside timing.
    """

    started = perf_counter()
    plant, marked = synchronous_product(components, max_states=200_000)
    pre = preprocess(plant) if method == 'ours' else None
    legal = legal_function(components)
    queue = deque([plant.initial])
    visited = {plant.initial}
    parent = {plant.initial: None}
    controls = []
    edges = []
    failures = []
    deadlocks = []
    unsafe = []

    while queue:
        q = queue.popleft()
        before = process_snapshot()
        tick = perf_counter()

        gamma_c, local_status, size, checks = decision_at(method, components, plant, marked, pre,
                                                         q, horizon, interpretation)

        seconds = perf_counter() - tick
        controls.append(dict(q=q, gamma_c=sorted(gamma_c), status=local_status,
                             solve_seconds=seconds, stored_states=size, checks=checks,
                             resources=interval_usage(before, process_snapshot())))

        if local_status not in ('local_supervisor', 'winning'):
            failures.append(q)

            continue

        gamma = gamma_c | plant.uncontrollable
        outcomes = [(event, target) for event, target in physical_successors(components, q) if event in gamma]

        if not outcomes:
            deadlocks.append(q)

        for event, target in outcomes:
            edges.append([q, event, target])

            if not legal(target):
                unsafe.append(target)

            if target not in visited:
                visited.add(target)
                parent[target] = q, event
                queue.append(target)

    witnesses = []

    for category, candidates in (('local_replanning_failure', failures), ('deadlock', deadlocks), ('illegal', unsafe)):
        if not candidates:
            continue

        target = candidates[0]
        q = target
        trace = []

        while parent[q] is not None:
            source, event = parent[q]
            trace.append([source, event, q])
            q = source

        witnesses.append(dict(category=category, target=target, transitions=trace[::-1]))

    outcome = 'replanning_failure' if failures else 'deadlocking' if deadlocks else 'unsafe' if unsafe else 'deadlock_free'

    return dict(complete=True, outcome=outcome, deadlock_free=not (failures or deadlocks or unsafe),
                plant_states=len(plant.states),
                visited_states=len(visited), transitions=edges, controls=controls,
                local_failures=failures, deadlocks=deadlocks, illegal_states=unsafe,
                witnesses=witnesses, exhaustive_check_seconds=perf_counter() - started,
                sum_unique_state_solve_seconds=sum(row['solve_seconds'] for row in controls),
                scope='All enabled outcomes of this method; finite-state receding controller, fixed horizon and full observation. '
                      'Sum over distinct states is exhaustive checking work, not a single-trajectory cumulative time.')


def worker(args):
    components = components_for(args.case)

    for plant, _ in components:
        plant.enabled(plant.initial)

    baseline = process_snapshot()
    samples = []

    for _ in range(args.repetitions):
        samples.append(calculate(args.method, components, args.horizon))

    root_resources = interval_usage(baseline, process_snapshot())
    gc.collect()
    tracemalloc.start()

    try:
        calculate(args.method, components, args.horizon)
        peak = tracemalloc.get_traced_memory()[1]
    finally:
        tracemalloc.stop()

    validation = validate_execution(args.method, components, args.horizon)
    trajectory = sample_trajectory(args.method, components, args.horizon)
    row = dict(case=args.case, method=LABELS[args.method], method_key=args.method,
               horizon=args.horizon, mean_seconds=mean(row['seconds'] for row in samples),
               samples=samples, peak_python_bytes=peak, root_batch_resources=root_resources,
               constructed_states=samples[-1]['constructed_states'],
               constructed_transitions=samples[-1]['constructed_transitions'],
               state_type=samples[-1]['state_type'], root_status=samples[-1]['root_status'],
               root_gamma_c=samples[-1]['root_gamma_c'],
               input_sha256=input_hash(components), outcome=validation['outcome'],
               deadlock_free=validation['deadlock_free'], closed_loop_states=validation['visited_states'],
               plant_states=validation['plant_states'],
               trajectory_events=trajectory['executed_events'], trajectory_stop=trajectory['stop'],
               trajectory_seconds=trajectory['cumulative_solve_seconds'])
    folder = args.output / args.case / f'N{args.horizon}'
    dump(folder / f'{args.method}_validation.json', validation)
    dump(folder / f'{args.method}_trajectory.json', trajectory)
    dump(folder / f'{args.method}.json', row)
    print(args.case, args.horizon, LABELS[args.method], f"{1000 * row['mean_seconds']:.3f} ms", row['outcome'], flush=True)


def write_readable(output, rows):
    lines = ['# 三种方法在同一组例子上的比较', '',
             '三种方法分别为 Cai-2018（论文公式解释）、LLP-1992（乐观边界）和本文 LL-BTS。',
             '同一例子的输入哈希、可控事件和完整观测属性完全相同；所有标记状态均取组件全部状态。',
             '共同物理约束是避开 plant 死锁；对各方法输出统一穷举检查持续闭环无死锁。',
             '已发表方法保留其 nonblocking 目标，不加入本文的活性判定；因此局部成功不自动代表闭环无死锁。', '',
             'root 时间包含本方法从组件输入开始的组合/窗口计算；本文还包含结构分析，采用相同固定 N，未用 offline 选择 N。',
             'Python 峰值单独测量。状态数是各方法实际存储结构，类型不同，不据此计算跨方法状态节约率。', '',
             '| 共同例子 | N | 方法 | 存储状态 | Root/ms | Python/KiB | 闭环状态 | 穷举结果 | 采样事件数 | 采样累计/ms |',
             '| --- | ---: | --- | ---: | ---: | ---: | ---: | --- | ---: | ---: |']

    for row in rows:
        lines.append(f"| {row['case']} | {row['horizon']} | {row['method']} | {row['constructed_states']} | "
                     f"{1000 * row['mean_seconds']:.3f} | {row['peak_python_bytes'] / 1024:.3f} | "
                     f"{row['closed_loop_states']} | {row['outcome']} | {row['trajectory_events']} | "
                     f"{row['trajectory_seconds'] * 1000:.3f} |")

    lines += ['', 'replanning_failure 表示某个可达状态没有局部监督器，不等于证明原系统全局不可解。',
              'deadlocking 表示算法返回局部监督器，但它允许的控制在某状态没有事件可执行。',
              'deadlock_free 表示对该方法全部可达闭环分支的检查通过，不是只抽取一条成功轨迹。', '',
              '每个 case/N 目录下的 *_validation.json 给出全部控制模式、转移、逐状态 CPU/RAM 和失败路径。',
              '*_trajectory.json 是实际逐事件重新求解的一条50事件上限轨迹，种子相同；若控制不同，物理轨迹可能不同。',
              '采样轨迹跑满50次不能替代穷举检查；提前失败的短轨迹累计时间不能和跑满50次者直接比较速度。',
              '原始部分观测输入未修改。Fig1-FO 是17状态论文例子的全观测副本；E2-FO、P2-FO 是两分量自乘积的全观测副本。',
              'Ring2-FO/Ring3-FO 为2个三状态环/3个四状态环的同步乘积，共享可控 fail 事件让全部分量进入死锁，step_i 不可控。',
              'Ring 系列每个合法物理状态都有不可控 step_i，因此合法可控运行不会因禁用全部事件而死锁。', '',
              'LLP-1992 对相同物理状态和深度共享计算，与完整事件前缀树的根结果一致，测试覆盖两种边界态度。',
              'Cai-2018 主表严格使用 equations；此前 component-frontiers 解释与原文101/108差异仍单独披露。']
    (output / '共同例子三方法对比.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=DEFAULT)
    parser.add_argument('--cases', nargs='+', default=['Ring2-FO', 'Ring3-FO', 'Fig1-FO', 'E2-FO', 'P2-FO'])
    parser.add_argument('--horizons', type=int, nargs='+', default=[3, 8, 16])
    parser.add_argument('--repetitions', type=int, default=5)
    parser.add_argument('--worker', action='store_true', help=argparse.SUPPRESS)
    parser.add_argument('--case', help=argparse.SUPPRESS)
    parser.add_argument('--method', choices=METHODS, help=argparse.SUPPRESS)
    parser.add_argument('--horizon', type=int, help=argparse.SUPPRESS)
    args = parser.parse_args()
    args.output = args.output.resolve()
    args.output.mkdir(parents=True, exist_ok=True)

    if args.worker:
        worker(args)

        return

    source_files = [Path(__file__), ROOT / 'des_core/classic_llp_1992.py', ROOT / 'des_core/warehouse_2018.py',
                    ROOT / 'des_core/certified_lookahead.py', ROOT / 'examples/paper_fig1_r1/plant.json',
                    ROOT / 'examples/large_scale/E_component.json', ROOT / 'examples/large_scale/P_component.json']
    source_files.append(ROOT / 'examples/three_method_common/ring_family.json')
    hashes = {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest() for path in source_files}
    dump(args.output / 'manifest.json', dict(sources=SOURCES, environment=environment_record(),
        methods=LABELS, cases=args.cases, horizons=args.horizons, repetitions=args.repetitions,
        source_sha256=hashes, warehouse_interpretation='equations', classic_attitude='optimistic',
        observation='same fully observed comparison inputs for all three methods',
        timing_scope='Warm loaded component input, root setup/composition and synthesis included. '
                     'Validation/export excluded. No offline answer or horizon calibration.',
        memory_scope='Independent tracemalloc peak; root-batch OS peak from a fresh method/case/horizon worker before '
                     'allocation tracing or validation. Runtime/input included in OS peak.'))
    rows = []

    for case in args.cases:
        components = components_for(case)
        dump(args.output / case / 'inputs.json', dict(components=input_record(components),
             input_sha256=input_hash(components), observation='full in all three methods',
             physical_legal='at least one plant event exists', marked='all component states'))

        for horizon in args.horizons:
            group = []

            for method in METHODS:
                command = [sys.executable, '-X', 'utf8', str(Path(__file__)), '--worker',
                           '--case', case, '--method', method, '--horizon', str(horizon),
                           '--repetitions', str(args.repetitions), '--output', str(args.output)]
                subprocess.run(command, cwd=ROOT, check=True)
                row = json.loads((args.output / case / f'N{horizon}' / f'{method}.json').read_text(encoding='utf-8'))
                group.append(row)

            assert len({row['input_sha256'] for row in group}) == 1
            rows.extend(group)
            dump(args.output / 'summary.json', rows)
            write_readable(args.output, rows)

    assert all(hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == digest for name, digest in hashes.items())
    print('Three-method comparison completed:', args.output, flush=True)


if __name__ == '__main__':
    main()
