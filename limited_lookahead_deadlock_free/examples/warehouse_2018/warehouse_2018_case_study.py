"""Reproduce the 2018 warehouse algorithm and a fully observed comparison.

python -X utf8 examples/warehouse_2018/warehouse_2018_case_study.py --part all
This is an independent implementation, not author-supplied code. Both the
displayed equations and the component-frontier interpretation are reported.
"""

# Allow direct execution from the project working directory.
if __package__ in (None, ""):
    import sys as _sys
    from pathlib import Path as _Path
    _sys.path.insert(0, str(_Path(__file__).resolve().parents[2]))


import argparse
from collections import deque
from dataclasses import replace
import hashlib
import json
from pathlib import Path
from statistics import mean
from time import perf_counter
import tracemalloc

from des_core.automata import DFA
from des_core.certified_lookahead import preprocess, solve_minimum_lookahead, validate_policy
from des_core.closed_loop import build_closed_loop
from des_core.offline_bts import construct_offline_bts
from des_core.resource_monitor import environment_record, process_snapshot, interval_usage
from des_core.warehouse_2018 import solve_warehouse, synchronous_product, WarehouseBudgetExceeded
from examples.warehouse_2018.models import paper_components, collision_free, TASKS


SOURCE = 'https://www.caikai.org/publication/TatsumotoShiraishiCaiLin_18CEP.pdf'
DEFAULT = Path('outputs/case_studies/warehouse_2018')


def dump(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')


def plant_record(plant, marked):
    return dict(states=sorted(plant.states), initial=plant.initial, events=sorted(plant.events),
                controllable=sorted(plant.controllable), observable=sorted(plant.observable),
                marked=sorted(marked), transitions=[[q, event, target] for (q, event), target in sorted(plant.transitions.items())])


def result_record(result):
    return dict(status=result.status, horizon=result.horizon, interpretation=result.interpretation,
                attitude=result.attitude, initial=result.initial, local_state_counts=result.local_state_counts,
                component_product_states=result.component_product_states,
                window_states=len(result.window.states), window_transitions=result.window_transitions,
                retained_states=len(result.retained_states), retained_transitions=result.retained_transitions,
                removed_states=result.removed_states, gamma_c=sorted(result.gamma_c), seconds=result.seconds)


def paper_cases(output, repetitions):
    rows = []
    cases = [('fig8', (7, 4, 1), (7, 4, 7), 108, ['15', '23', '33', '35']),
             ('fig9', (22, 27, 26), (4, 8, 4), 68, ['15', '25'])]

    for name, current, local_sizes, published_states, published_gamma in cases:
        components = paper_components(current)
        assert [len(plant.states) for plant, _ in components] == [34, 25, 25]
        dump(output / 'paper' / (name + '_inputs.json'), dict(
            source=SOURCE, tasks=TASKS, current=current,
            components=[plant_record(plant, marked) for plant, marked in components]))

        for interpretation in ('equations', 'component-frontiers'):
            samples = []

            for _ in range(repetitions):
                before = process_snapshot()
                started = perf_counter()
                result = solve_warehouse(components, horizon=3, legal=collision_free,
                                         interpretation=interpretation)
                seconds = perf_counter() - started
                samples.append(dict(seconds=seconds, resources=interval_usage(before, process_snapshot())))

            row = dict(case=name, **result_record(result), samples=samples,
                       mean_seconds=mean(sample['seconds'] for sample in samples),
                       published_local_sizes=local_sizes, published_retained_states=published_states,
                       published_gamma_c=published_gamma,
                       matches_local_sizes=tuple(local_sizes) == result.local_state_counts,
                       matches_retained_states=published_states == len(result.retained_states),
                       matches_gamma=published_gamma == sorted(result.gamma_c))
            assert row['matches_local_sizes']
            rows.append(row)
            dump(output / 'paper' / f'{name}_{interpretation}.json', row)
            dump(output / 'paper' / f'{name}_{interpretation}_supervisor.json', dict(
                initial=result.initial, states=sorted(result.retained_states), marked=sorted(result.retained_marked),
                transitions=[[q, event, target] for (q, event), target in result.window.transitions.items()
                             if q in result.retained_states and target in result.retained_states]))

    dump(output / 'paper/summary.json', rows)

    return rows


def paper_execution(output, cap=200):
    q = ('7', '4', '1')
    steps = []
    next_robot = 0

    for k in range(cap):
        if all(cell == '71' for cell in q):
            break

        result = solve_warehouse(paper_components(q), legal=collision_free,
                                 interpretation='component-frontiers')
        events = sorted(result.gamma_c)

        if not events:
            break

        event = min(events, key=lambda value: ((int(value) // 10 - 1 - next_robot) % 3, int(value)))
        actor = int(event) // 10 - 1
        components = paper_components(q)
        target = list(q)
        target[actor] = components[actor][0].transitions[q[actor], event]
        target = tuple(target)
        assert collision_free(target)
        steps.append(dict(k=k, q=q, gamma_c=events, event=event, target=target,
                          window_states=len(result.window.states), retained_states=len(result.retained_states),
                          solve_seconds=result.seconds))
        q = target
        next_robot = (actor + 1) % 3

    record = dict(complete=all(cell == '71' for cell in q), final=q, steps=steps,
                  total_solve_seconds=sum(row['solve_seconds'] for row in steps),
                  interpretation='component-frontiers', scheduler='round-robin robot, then smallest event',
                  scope='One sampled task trajectory; successful termination is not a proof for all executions.')
    dump(output / 'paper/execution.json', record)
    print('Warehouse task execution:', len(steps), 'events; finished:', record['complete'], flush=True)


def horizon_cases(output, max_states):
    rows = []

    for kind in ('E', 'P'):
        components = load_product_components(kind, 2)

        for horizon in (1, 2, 3, 5, 8, 10):
            result = validate_warehouse_execution(components, horizon,
                interpretation='component-frontiers', max_states=max_states)
            row = dict(case=kind + '2', horizon=horizon, complete=result['complete'],
                       deadlock_free=result.get('deadlock_free'), visited=result.get('visited'),
                       empty_local_states=len(result.get('empty_local_states', [])), seconds=result['seconds'])
            rows.append(row)
            dump(output / 'horizons' / f'{kind}2_N{horizon}.json', dict(summary=row, execution=result))

    dump(output / 'horizons/summary.json', rows)
    print('Warehouse horizon sensitivity completed.', flush=True)


def load_product_components(kind, copies):
    path = Path('examples/large_scale') / (kind + '_component.json')
    record = json.loads(path.read_text(encoding='utf-8'))
    components = []

    for index in range(copies):
        event_name = lambda event: event + '_' + str(index)
        events = frozenset(event_name(event) for event in record['events'])
        plant = DFA(frozenset(record['states']), record['initial'], events,
                    frozenset(event_name(event) for event in record['controllable']), events,
                    {(q, event_name(event)): target for q, event, target in record['transitions']})
        # Shared safety specification: exclude physical global deadlock states.
        # Marking all component states does not add our liveness test to LLP.
        components.append((plant, plant.states))

    return components


def physical_successors(components, q):
    # The comparison products use disjoint indexed alphabets.
    for index, (plant, _) in enumerate(components):
        for event, target in plant.enabled(q[index]):
            successor = list(q)
            successor[index] = target
            yield event, tuple(successor)


def validate_warehouse_execution(components, horizon, *, interpretation, max_states):
    """Exhaustively check receding execution, outside root timing/memory runs.

    This validator does not alter the paper's control pattern. It enforces
    physical uncontrollability and records any resulting deadlock or unsafe
    state. An empty local solve is not called global nonexistence.
    """

    initial = tuple(plant.initial for plant, _ in components)
    uncontrollable = frozenset().union(*(plant.uncontrollable for plant, _ in components))
    queue = deque([initial])
    seen = {initial}
    parent = {initial: None}
    transitions = []
    patterns = []
    deadlocks = []
    empty = []
    started = perf_counter()

    def legal(q):
        return any(plant.enabled(q[i]) for i, (plant, _) in enumerate(components))

    while queue:
        q = queue.popleft()
        current = [(replace(plant, initial=q[i]), marked) for i, (plant, marked) in enumerate(components)]
        result = solve_warehouse(current, horizon=horizon, legal=legal,
                                 interpretation=interpretation, max_states=max_states)
        patterns.append(dict(q=q, gamma_c=sorted(result.gamma_c), status=result.status,
                             window_states=len(result.window.states), solve_seconds=result.seconds))

        if result.status != 'local_supervisor':
            empty.append(q)

            # The paper has no control to execute here. Do not invent an empty
            # fallback mode or propagate it as if it were an actual supervisor.
            continue

        gamma = result.gamma_c | uncontrollable
        enabled = [(event, target) for event, target in physical_successors(components, q) if event in gamma]

        if not enabled:
            deadlocks.append(q)

        for event, target in enabled:
            transitions.append([q, event, target])

            if target not in seen:
                seen.add(target)
                parent[target] = (q, event)

                if len(seen) > max_states:
                    return dict(complete=False, reason='validation state budget',
                                visited=len(seen), seconds=perf_counter() - started)

                queue.append(target)

    witnesses = []

    for target in (empty[:1] + deadlocks[:1]):
        path = []
        q = target

        while parent[q] is not None:
            source, event = parent[q]
            path.append([source, event, q])
            q = source

        witnesses.append(dict(target=target, transitions=path[::-1]))

    outcome = 'replanning_failure' if empty else 'deadlocking' if deadlocks else 'deadlock_free'

    return dict(complete=True, deadlock_free=None if empty else not deadlocks,
                execution_outcome=outcome, visited=len(seen), witnesses=witnesses,
                transitions=transitions, patterns=patterns, deadlocks=deadlocks,
                empty_local_states=empty, seconds=perf_counter() - started)


def measure(method, components, horizon, max_states):
    started = perf_counter()

    if method == 'Warehouse-2018':
        def legal(q):
            return any(plant.enabled(q[i]) for i, (plant, _) in enumerate(components))

        result = solve_warehouse(components, horizon=horizon, legal=legal,
                                 interpretation='component-frontiers', max_states=max_states)
        metrics = result_record(result)
    else:
        plant, _ = synchronous_product(components, max_states=max_states)

        if method == 'Full-BTS':
            result = construct_offline_bts(plant, timeout_seconds=60)
        else:
            result = solve_minimum_lookahead(preprocess(plant), timeout_seconds=60)

        metrics = dict(status=result.status, D=result.decision_count, O=result.observation_count,
                       constructed_states=result.decision_count + result.observation_count,
                       retained_D=len(result.decision_policy), horizon=result.horizon,
                       patterns_tested=result.patterns_tested,
                       gamma_c=[sorted(pattern) for pattern in result.maximal_patterns])

    seconds = perf_counter() - started

    return metrics, seconds, result


def comparison_cases(output, repetitions, horizon, max_states):
    rows = []

    for kind, copies in [('E', 2), ('E', 3), ('H', 2), ('P', 2), ('P', 3)]:
        name = kind + str(copies)
        components = load_product_components(kind, copies)
        dump(output / 'comparison' / name / 'inputs.json', dict(
            original_component=str(Path('examples/large_scale') / (kind + '_component.json')),
            copies=copies, observation='all events observable in all three comparison methods',
            components=[plant_record(plant, marked) for plant, marked in components]))

        for method in ('Full-BTS', 'LL-BTS', 'Warehouse-2018'):
            samples = []

            for _ in range(repetitions):
                before = process_snapshot()
                metrics, seconds, result = measure(method, components, horizon, max_states)
                samples.append(dict(seconds=seconds, resources=interval_usage(before, process_snapshot())))

            tracemalloc.start()

            try:
                measure(method, components, horizon, max_states)
                peak = tracemalloc.get_traced_memory()[1]
            finally:
                tracemalloc.stop()

            if method == 'Warehouse-2018':
                validation = validate_warehouse_execution(components, horizon,
                    interpretation='component-frontiers', max_states=max_states)
            else:
                plant, _ = synchronous_product(components, max_states=max_states)
                pre = preprocess(plant)
                validate_policy(pre, result)
                graph = build_closed_loop(pre, result)
                outgoing = {edge['source'] for edge in graph['edges']}
                validation = dict(complete=True, deadlock_free=all(node['id'] in outgoing for node in graph['nodes']),
                                  visited=len(graph['nodes']), transitions=len(graph['edges']))
                dump(output / 'comparison' / name / (method + '_closed_loop.json'), graph)

            dump(output / 'comparison' / name / (method + '_validation.json'), validation)
            row = dict(case=name, method=method, plant_states=len(components[0][0].states) ** copies,
                       **metrics, samples=samples, mean_seconds=mean(sample['seconds'] for sample in samples),
                       peak_python_bytes=peak, validation_complete=validation['complete'],
                       execution_outcome=validation.get('execution_outcome', 'deadlock_free'),
                       closed_loop_deadlock_free=validation.get('deadlock_free'),
                       closed_loop_states=validation.get('visited'))
            rows.append(row)
            dump(output / 'comparison' / name / (method + '.json'), row)
            print(name, method, f"{row['mean_seconds']:.6f}s", 'closed-loop',
                  row['closed_loop_deadlock_free'], flush=True)

    dump(output / 'comparison/summary.json', rows)

    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--part', choices=['paper', 'comparison', 'horizons', 'all'], default='all')
    parser.add_argument('--output', type=Path, default=DEFAULT)
    parser.add_argument('--repetitions', type=int, default=5)
    parser.add_argument('--horizon', type=int, default=3)
    parser.add_argument('--max-product-states', type=int, default=200_000)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    dump(args.output / 'manifest.json', dict(source_url=SOURCE,
        source_doi='10.1016/j.conengprac.2018.09.003',
        implementation='Independent reimplementation, not the authors original code',
        environment=environment_record(), repetitions=args.repetitions, horizon=args.horizon,
        measurement='Root calculation from component models; includes global product for Full/LL. '
                    'Rendering, validation and resource snapshots excluded from wall time; '
                    'allocation peaks measured in separate calls. State structures differ by method.',
        validation='Exhaustive receding execution checked separately; no additional safety check changes warehouse modes.',
        source_sha256={str(path): hashlib.sha256(path.read_bytes()).hexdigest() for path in
                       [Path(__file__), Path('des_core/warehouse_2018.py'), Path('examples/warehouse_2018/models.py')]}))

    if args.part in ('paper', 'all'):
        paper_cases(args.output, args.repetitions)
        paper_execution(args.output)

    if args.part in ('comparison', 'all'):
        comparison_cases(args.output, args.repetitions, args.horizon, args.max_product_states)

    if args.part in ('horizons', 'all'):
        horizon_cases(args.output, args.max_product_states)

    print('Warehouse replication finished:', args.output, flush=True)


if __name__ == '__main__':
    main()
