"""Measure revised E/H/P/C examples and one unchanged zero-bound control.

python -X utf8 nonzero_lookahead_cases.py --run
The old generators and measurements remain unchanged. This entry point uses
explicit global DFA analysis, including for products; no old count formulas
or component-controller compositions are used. Timings exclude validation
and export. Each repetition and method starts in a fresh child process.
"""

import argparse
from collections import deque
from datetime import datetime
import gc
import hashlib
import json
from pathlib import Path
import platform
import statistics
import subprocess
import sys
from time import perf_counter, sleep

from des_core.asynchronous_product import ImplicitProductDFA
from des_core.automata import DFA
from des_core.certified_lookahead import preprocess, solve_minimum_lookahead, validate_policy
from des_core.closed_loop import build_closed_loop
from des_core.offline_bts import construct_offline_bts
from early_stop_products import component
from global_large_case_studies import build_global_dfa
from large_scale_overall import dump, working_set
from des_core.resource_monitor import process_snapshot, interval_usage, environment_record


CASES = {'E4': ('E', 10, 4, 2), 'H2': ('H', 100, 2, 1),
         'P4': ('P', 10, 4, 2), 'C': ('C', 1_000_000, 1, 2),
         'E4_zero': ('E', 10, 4, 0), 'E5': ('E', 10, 5, 2),
         'H3': ('H', 100, 3, 1), 'P5': ('P', 10, 5, 2)}
INPUTS = Path(__file__).resolve().parent / 'examples/large_scale'
DEFAULT_OUTPUT = Path('outputs/revision_materials/nonzero_lookahead_runs') / datetime.now().strftime('%Y%m%d_%H%M%S')


class MeasurementMemoryLimit(MemoryError):
    def __init__(self, record):
        self.record = record
        super().__init__(f'{record["case"]} {record["method"]}: memory guard stopped the measurement')


def base_model(kind, n, hidden_steps):
    """Relabel terminal failure transitions; retain the event partition."""

    base = component(kind, n) if kind in ('E', 'H') else build_global_dfa(n, 3 if kind == 'P' else 128)
    transitions = dict(base.transitions)

    for i in range(n - 1 - hidden_steps, n - 1):
        target = transitions.pop((f'q{i}', 'a'))
        assert (f'q{i}', 'u') not in transitions
        transitions[f'q{i}', 'u'] = target

    return DFA(base.states, base.initial, base.events, base.controllable,
               base.observable, transitions)


def global_model(case):
    kind, n, copies, hidden_steps = CASES[case]
    recipe = json.loads((INPUTS / case / 'model.json').read_text(encoding='utf-8'))
    assert (recipe['kind'], recipe['component_states'], recipe['copies'], recipe['terminal_hidden_steps']) == CASES[case]
    model_path = INPUTS / case / recipe['component_file']

    if kind == 'C':
        record = json.loads(model_path.read_text(encoding='utf-8'))
        original = build_global_dfa(record['states'], record['safe_spine_states'])
        transitions = dict(original.transitions)

        for q, previous_event, event, target in record['relabeled_transitions']:
            assert transitions.pop((q, previous_event)) == target
            assert (q, event) not in transitions
            transitions[q, event] = target

        base = DFA(original.states, record['initial'], frozenset(record['events']),
                   frozenset(record['controllable']), frozenset(record['observable']), transitions)
    else:
        record = json.loads(model_path.read_text(encoding='utf-8'))
        base = DFA(frozenset(record['states']), record['initial'], frozenset(record['events']),
                   frozenset(record['controllable']), frozenset(record['observable']),
                   {(q, event): target for q, event, target in record['transitions']})

    assert len(base.states) == n

    if copies == 1:
        return base, base

    product = ImplicitProductDFA(base, copies)
    states = frozenset(product.states)
    transitions = {(q, event): target for q in states for event, target in product.enabled(q)}
    plant = DFA(states, product.initial, product.events, product.controllable,
                product.observable, transitions)

    return base, plant


def model_record(plant):
    return dict(states=sorted(plant.states), initial=plant.initial,
                events=sorted(plant.events), observable=sorted(plant.observable),
                controllable=sorted(plant.controllable),
                transitions=[[q, event, target] for (q, event), target in sorted(plant.transitions.items())])


def reachable_count(plant):
    seen = {plant.initial}
    queue = deque(seen)

    while queue:
        for _, target in plant.enabled(queue.popleft()):
            if target not in seen:
                seen.add(target)
                queue.append(target)

    return len(seen)


def worker(case, method, destination):
    gc.collect()
    resource_before = process_snapshot()
    started = perf_counter()
    base, plant = global_model(case)
    setup_seconds = perf_counter() - started
    analysis_seconds = 0.
    pre = None

    if method == 'll':
        pre = preprocess(plant)
        analysis_seconds = perf_counter() - started - setup_seconds
        dump(destination.with_suffix('.analysis.json'), dict(case=case,
             states=len(plant.states), Q_d=len(pre.Q_d), Q_f=len(pre.Q_f), Q_e=len(pre.Q_e),
             bar_u=pre.lookahead_lower_bound, seconds=analysis_seconds,
             path_visits=pre.path_visits, complete=True))
        print(case, 'structural analysis: bar_u =', pre.lookahead_lower_bound, flush=True)
        result = solve_minimum_lookahead(pre)
    else:
        result = construct_offline_bts(plant)

    patterns = result.maximal_patterns
    seconds = perf_counter() - started
    construction_resources = interval_usage(resource_before, process_snapshot())
    record = dict(case=case, method=method, complete=True, seconds=seconds,
                  setup_seconds=setup_seconds, analysis_seconds=analysis_seconds,
                  states=len(plant.states), transitions=len(plant.transitions),
                  D=result.decision_count, O=result.observation_count,
                  constructed_states=result.decision_count + result.observation_count,
                  status=result.status, root_patterns=[sorted(p) for p in patterns],
                  component_states=len(base.states), copies=CASES[case][2],
                  construction_resources=construction_resources,
                  retained_D=len(result.decision_policy),
                  retained_O=len({(c.closure, c.pattern) for cs in result.decision_policy.values() for c in cs}),
                  patterns_tested=result.patterns_tested, horizon_trials=result.horizon_trials,
                  terminal_hidden_steps=CASES[case][3],
                  timing='Input construction, structural analysis (LL only), all horizon trials, '
                         'BTS/LL-BTS construction, pruning and root pattern filtering. '
                         'Validation and export excluded.')
    assert result.status == 'winning'
    dump(destination.with_suffix('.construction.json'), dict(record, validation_complete=False))

    if pre is not None:
        record.update(bar_u=pre.lookahead_lower_bound, u=result.horizon,
                      Q_d=len(pre.Q_d), Q_f=len(pre.Q_f), Q_e=len(pre.Q_e),
                      path_visits=pre.path_visits)
        assert (pre.lookahead_lower_bound > 0) == (CASES[case][3] > 0)
        record['validation'] = validate_policy(pre, result)
        dump(destination.with_suffix('.validation.json'), dict(record, validation_complete=True))
        graph = build_closed_loop(pre, result)
        sources = {e['source'] for e in graph['edges']}
        assert graph['nodes'] and all(q['id'] in sources for q in graph['nodes'])
        record['closed_loop_states'] = len(graph['nodes'])
        dump(destination.parent / (case + '_closed_loop.json'), graph)

        if case != 'C':
            dump(destination.parent / (case + '_base.json'), model_record(base))
        else:
            dump(destination.parent / 'C_model.json', dict(generator='base_model',
                 arguments=['C', 1_000_000, 2], initial='q0', states=1_000_000,
                 observable=sorted(base.observable), controllable=sorted(base.controllable),
                 relabeled_transitions=[['q999997', 'u', 'q999998'], ['q999998', 'u', 'q999999']]))

        record['reachable_states'] = reachable_count(plant)
        assert record['reachable_states'] == len(plant.states)

    dump(destination, record)
    print(case, method, record['constructed_states'], round(seconds, 4),
          'bar_u', record.get('bar_u'), 'u', record.get('u'), flush=True)


def run_child(case, method, destination, max_memory_gib):
    command = [sys.executable, '-X', 'utf8', str(Path(__file__).resolve()),
               '--worker', case, method, '--output', str(destination)]
    child = subprocess.Popen(command)
    peak = 0
    started = reported = perf_counter()

    try:
        while child.poll() is None:
            if sys.platform == 'win32':
                try:
                    peak = max(peak, working_set(child._handle))
                except OSError:
                    pass

            if max_memory_gib and peak > max_memory_gib * 2 ** 30:
                child.terminate()
                child.wait()

                record = dict(case=case, method=method, complete=False,
                    status='memory guard; not a losing result', elapsed_seconds=perf_counter() - started,
                    sampled_peak_working_set_bytes=peak, max_memory_gib=max_memory_gib,
                    construction_complete=destination.with_suffix('.construction.json').exists(),
                    validation_complete=destination.with_suffix('.validation.json').exists())
                dump(destination, record)

                raise MeasurementMemoryLimit(record)

            if perf_counter() - reported >= 15:
                reported = perf_counter()
                dump(destination.with_suffix('.progress.json'), dict(case=case, method=method,
                     complete=False, elapsed_seconds=reported - started,
                     sampled_peak_working_set_bytes=peak))
                print(case, method, 'running', round(reported - started), 's, peak',
                      round(peak / 2 ** 30, 2), 'GiB', flush=True)

            sleep(.2)
    except BaseException:
        if child.poll() is None:
            child.terminate()
            child.wait()

        raise

    if child.returncode:
        raise subprocess.CalledProcessError(child.returncode, command)

    record = json.loads(destination.read_text(encoding='utf-8'))
    record['sampled_peak_working_set_bytes'] = peak
    dump(destination, record)

    return record


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', action='store_true')
    parser.add_argument('--cases', nargs='+', choices=CASES, default=['E5', 'H3', 'P5', 'C', 'E4_zero'])
    parser.add_argument('--repetitions', type=int, default=1)
    parser.add_argument('--max-memory-gib', type=float, default=20.)
    parser.add_argument('--output', type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument('--worker', nargs=2)
    args = parser.parse_args()

    if args.worker:
        worker(*args.worker, args.output)

        return

    if not args.run:
        parser.error('Use --run to measure the revised examples')

    args.output.mkdir(parents=True, exist_ok=True)
    combined = []

    for case in args.cases:
        row = dict(case=case)

        for method in ('full', 'll'):
            try:
                samples = [run_child(case, method, args.output / f'{case}_{method}_{i}.json',
                                     args.max_memory_gib)
                           for i in range(1 if case in ('C', 'E4_zero') else args.repetitions)]
            except MeasurementMemoryLimit as error:
                row[method] = error.record
                print(case, method, 'incomplete: memory guard', flush=True)

                continue

            assert all((r['D'], r['O'], r['status']) ==
                       (samples[0]['D'], samples[0]['O'], samples[0]['status']) for r in samples)
            row[method] = dict(samples[0], mean_seconds=statistics.mean(r['seconds'] for r in samples),
                               repetitions=len(samples), samples_seconds=[r['seconds'] for r in samples])

        if row['full']['complete'] and row['ll']['complete']:
            assert row['full']['status'] == row['ll']['status']
            row['root_pattern_agreement'] = row['full']['root_patterns'] == row['ll']['root_patterns']

        combined.append(row)
        dump(args.output / 'combined.json', combined)

    sources = [__file__, 'early_stop_products.py', 'global_large_case_studies.py',
               'des_core/certified_lookahead.py', 'des_core/offline_bts.py',
               'des_core/bipartite_graph.py', 'des_core/resource_monitor.py']
    dump(args.output / 'manifest.json', dict(python=sys.version, platform=platform.platform(),
         environment=environment_record(), representation='explicit (q_hat, x_hat) decision states',
         command=sys.argv, model_revision='terminal failure transitions relabeled a to u',
         source_sha256={str(p): hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in sources},
         input_sha256={str(p.relative_to(INPUTS)): hashlib.sha256(p.read_bytes()).hexdigest() for p in INPUTS.rglob('*.json')}))


if __name__ == '__main__':
    main()
