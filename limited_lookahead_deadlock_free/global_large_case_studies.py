"""Global DFA/LL-BTS stress tests, without component-controller composition.

python -X utf8 global_large_case_studies.py
All declared DFA states are reachable before control. The full baseline uses
the same explicit DFA and event partition as the limited-lookahead solver.
"""

import gc
import hashlib
import json
from pathlib import Path
import statistics
from time import perf_counter

from des_core.automata import DFA
from des_core.certified_lookahead import preprocess, solve_minimum_lookahead, validate_policy
from des_core.closed_loop import build_closed_loop
from des_core.offline_bts import BTSBudgetExceeded, construct_offline_bts


OUT = Path('outputs/revision_materials/global_case_studies_20261123')


def build_global_dfa(n, length):
    """A safe observable spine and a long controllable failure branch.

    q0 --u--> q1 is unobservable; a advances along the safe spine, whose
    last state has an a self-loop. At every earlier spine state, b enters
    the same failure chain. Only b is controllable. Every failure-chain
    state has a single a successor and eventually reaches the sole deadlock.
    """

    states = frozenset(f'q{i}' for i in range(n))
    transitions = {('q0', 'u'): 'q1'}

    for i in range(length):
        transitions[(f'q{i}', 'a')] = f'q{min(i + 1, length - 1)}'

        if i < length - 1:
            transitions[(f'q{i}', 'b')] = f'q{length}'

    for i in range(length, n - 1):
        transitions[(f'q{i}', 'a')] = f'q{i + 1}'

    return DFA(states, 'q0', frozenset({'a', 'b', 'u'}),
               frozenset({'b'}), frozenset({'a', 'b'}), transitions)


def run_case(n, length):
    plant = build_global_dfa(n, length)
    # Both solvers share immutable input and its outgoing-transition index.
    plant.enabled(plant.initial)
    times = []
    analysis_times = []

    for _ in range(3):
        gc.collect()
        started = perf_counter()
        pre = preprocess(plant, max_path_visits=2_000_000)
        analysis_times.append(perf_counter() - started)
        result = solve_minimum_lookahead(pre, timeout_seconds=30.)
        result.maximal_patterns
        times.append(perf_counter() - started)
        del pre

    pre = preprocess(plant, max_path_visits=2_000_000)
    assert len(pre.Q_d) == 1 and len(pre.Q_f) == n - length - 1
    assert pre.Q_e == frozenset({f'q{length - 1}'})
    assert result.status == 'winning' and result.maximal_patterns == (frozenset(),)
    validation = validate_policy(pre, result)
    graph = build_closed_loop(pre, result)
    assert len(graph['nodes']) == 2 * length - 1
    assert result.horizon == length - 1
    assert len(result.window) == length + result.horizon
    ll_nodes = result.decision_count + result.observation_count
    del pre
    gc.collect()
    started = perf_counter()

    try:
        full = construct_offline_bts(plant, max_decisions=150_000,
                                     timeout_seconds=30.)
        full_time = perf_counter() - started
        assert full.status == result.status
        full_record = dict(complete=True, seconds=full_time, status=full.status,
                           nodes=full.decision_count + full.observation_count,
                           decisions=full.decision_count, observations=full.observation_count)
        assert full.decision_count == n and full_record['nodes'] == 3 * n
    except BTSBudgetExceeded as error:
        full_record = dict(complete=False, seconds=perf_counter() - started,
                           status='budget exceeded', metrics=error.metrics)

    row = dict(states=n, transitions=len(plant.transitions), safe_spine_states=length,
               observable=sorted(plant.observable), controllable=sorted(plant.controllable),
               admissible_patterns=2, Q_d=1, Q_f=n - length - 1, Q_e=1, bar_u=0,
               selected_u=result.horizon, window_states=len(result.window),
               LL_decisions=result.decision_count, LL_observations=result.observation_count,
               LL_nodes=ll_nodes, LL_seconds=times, LL_mean_seconds=statistics.mean(times),
               structural_analysis_seconds=analysis_times, full=full_record,
               closed_loop_states=len(graph['nodes']), closed_loop_edges=len(graph['edges']),
               validation=validation,
               full_node_count_exact=3 * n,
               full_node_count_basis='There are n reachable decision estimates (singleton or adjacent pairs). '
                   'Each has two distinct (UR closure, control pattern) observation states.')
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / f'n{n}.json').write_text(json.dumps(row, indent=2), encoding='utf-8')
    (OUT / f'n{n}_closed_loop.json').write_text(json.dumps(graph, indent=2), encoding='utf-8')
    print(n, 'LL', ll_nodes, 'u', result.horizon, 'seconds', row['LL_mean_seconds'],
          'full', full_record, flush=True)

    return row


def main():
    rows = [run_case(n, length) for n, length in ((10_000, 32), (100_000, 64), (1_000_000, 128))]
    reference = rows[1]

    if reference['full']['complete']:
        rows[-1]['full_estimate_seconds'] = reference['full']['seconds'] * 10
        rows[-1]['full_estimate_basis'] = ('Linear extrapolation from the completed 100000-state '
            'run, with the same two control patterns per decision estimate; not measured total runtime.')

    record = dict(results=rows, repeats=3, seed=None,
                  design='Deterministic explicit global DFAs; no factorized LL-BTS or component reuse.',
                  timing='Shared warm immutable DFA input/index excluded. LL includes fresh structural '
                      'analysis and every positive-horizon trial; independent full BTS uses complete UR/NX.',
                  source_sha256={f: hashlib.sha256(Path(f).read_bytes()).hexdigest() for f in
                      ('global_large_case_studies.py', 'des_core/certified_lookahead.py', 'des_core/offline_bts.py')})
    (OUT / 'results.json').write_text(json.dumps(record, indent=2), encoding='utf-8')


if __name__ == '__main__':
    main()
