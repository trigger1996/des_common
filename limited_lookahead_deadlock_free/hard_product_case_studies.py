"""Reproduce less-prunable global and exact 10^6/10^7/10^8 product tests.

python -X utf8 hard_product_case_studies.py
Incomplete global searches are reported as budget-limited, never as losing.
"""

import argparse
from collections import deque
from collections.abc import Set
import hashlib
from itertools import product as tuples
import json
from pathlib import Path
import subprocess
import sys
from time import perf_counter

from des_core.asynchronous_product import ImplicitProductDFA
from des_core.automata import DFA
from des_core.certified_lookahead import (
    Preprocessing, preprocess, solve_limited_lookahead, solve_minimum_lookahead, validate_policy,
)
from des_core.closed_loop import build_closed_loop
from des_core.offline_bts import BTSBudgetExceeded, construct_offline_bts
from global_large_case_studies import build_global_dfa


OUT = Path('outputs/revision_materials/hard_products_20261123')
SECONDS = 15.
WINDOW_LIMIT = 50_000
PATTERN_LIMIT = 20_000


def dump(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2), encoding='utf-8')


class ExactSubset(Set):
    """Exact product subset, with lazy iteration and tuple membership.

    Only membership and length are used in the large online solves. No subset
    is approximated and no component LL-BTS is substituted for a global graph.
    """

    def __init__(self, plant, kind, failures):
        self.plant = plant
        self.kind = kind
        self.failures = failures

    def __contains__(self, q):
        safe = 'q2' in q

        return safe if self.kind == 'safe' else safe or q in self.failures or all(x == 'q9' for x in q)

    def __len__(self):
        n = 10 ** self.plant.copies - 9 ** self.plant.copies

        return n if self.kind == 'safe' else n + len(self.failures) + 1

    def __iter__(self):
        return (q for q in self.plant.states if q in self)


def product_analysis(copies):
    """Exact Algorithm-1 sets derived from the known asynchronous product.

    Qd is the all-q9 tuple. Qf has precisely one non-q9 coordinate, in q3..q8;
    with two nondead coordinates there are two distinct successor states, so
    that tuple cannot enter the paper's single-successor failure-chain class.
    Qe contains exactly the tuples with at least one q2 coordinate. Every
    other coordinate can independently reach q9, whereas q2 is invariant.
    The only hidden transition is q0->q1; it reaches neither a new Qf tuple
    nor a new Qe tuple. Thus bar_u=0, and the extended threshold is copies-1.
    """

    started = perf_counter()
    component = build_global_dfa(10, 3)
    local = preprocess(component)
    assert local.Q_d == frozenset({'q9'})
    assert local.Q_f == frozenset(f'q{i}' for i in range(3, 9))
    assert local.Q_e == frozenset({'q2'})
    plant = ImplicitProductDFA(component, copies)
    dead = frozenset({('q9',) * copies})
    failure = set()

    for index in range(copies):
        for state in local.Q_f:
            q = ['q9'] * copies
            q[index] = state
            failure.add(tuple(q))

    failure = frozenset(failure)
    safe = ExactSubset(plant, 'safe', failure)
    entries = ExactSubset(plant, 'entries', failure)
    pre = Preprocessing(plant, dead, failure, safe, entries, copies - 1, 0, 0,
                        perf_counter() - started)

    return pre


def validate_analysis():
    rows = []

    for copies in (1, 2, 3):
        symbolic = product_analysis(copies)
        plant = symbolic.plant
        states = frozenset(plant.states)
        transitions = {(q, event): target for q in states for event, target in plant.enabled(q)}
        explicit = DFA(states, plant.initial, plant.events, plant.controllable,
                       plant.observable, transitions)
        exact = preprocess(explicit)
        assert exact.Q_d == symbolic.Q_d and exact.Q_f == symbolic.Q_f
        assert exact.Q_e == frozenset(symbolic.Q_e)
        assert exact.Q_o_tilde == frozenset(symbolic.Q_o_tilde)
        assert exact.u_f == symbolic.u_f and exact.u == symbolic.u
        reached = {plant.initial}
        queue = deque(reached)

        while queue:
            for _, q in plant.enabled(queue.popleft()):
                if q not in reached:
                    reached.add(q)
                    queue.append(q)

        assert reached == states
        # Check the actual global controlled graph, not a reused component graph.
        controlled = {q for q in states if all(int(x[1:]) < 3 for x in q)}

        for q in controlled:
            edges = [(e, t) for e, t in plant.enabled(q) if e not in plant.controllable]
            assert edges and all(t in controlled for _, t in edges)

        rows.append(dict(copies=copies, all_reachable_states=len(reached),
                         controlled_states=len(controlled), exact_sets_agree=True))

    dump(OUT / 'small_product_validation.json', rows)


def export_controlled_products():
    """Enumerate complete global closed loops for a constant valid policy.

    These are closed-loop DFA states, not completed LL-BTS constructions.
    Disabling every b_i is observation-based and keeps all uncontrollables.
    """

    rows = []

    for copies in (6, 7, 8):
        plant = product_analysis(copies).plant
        states = list(tuples(('q0', 'q1', 'q2'), repeat=copies))
        ids = {q: i for i, q in enumerate(states)}
        edges = []
        adjacency = {i: [] for i in range(len(states))}

        for q in states:
            outgoing = [(e, t) for e, t in plant.enabled(q) if e not in plant.controllable]
            assert outgoing and all(t in ids for _, t in outgoing)

            for event, target in outgoing:
                edges.append([ids[q], event, ids[target]])
                adjacency[ids[q]].append(ids[target])

        initial = ids[plant.initial]
        reached = {initial}
        queue = deque(reached)

        while queue:
            for target in adjacency[queue.popleft()]:
                if target not in reached:
                    reached.add(target)
                    queue.append(target)

        assert len(reached) == 3 ** copies
        assert len(edges) == 4 * copies * 3 ** (copies - 1)
        record = dict(copies=copies, plant_states=10 ** copies,
                      controlled_states=len(states), controlled_transitions=len(edges),
                      all_controlled_states_reachable=True, deadlock_free=True,
                      all_uncontrollables_preserved=True,
                      policy='Constant policy disables all b_i and enables every uncontrollable event.',
                      synthesis_scope='Explicit global closed loop for a valid constant supervisor; '
                          'not the result or node count of a completed global LL-BTS synthesis.')
        dump(OUT / f'P{copies}_closed_loop.json', dict(**record, initial=initial,
             states=states, transitions=edges))
        rows.append(record)

    dump(OUT / 'controlled_product_verification.json', rows)

    return rows


def worker(copies, method):
    path = OUT / f'product_{copies}_{method}.json'
    started = perf_counter()
    pre = product_analysis(copies)
    record = dict(copies=copies, states=10 ** copies, method=method,
                  Q_d=len(pre.Q_d), Q_f=len(pre.Q_f), Q_e=len(pre.Q_e),
                  structural_seconds=pre.seconds, trials=[], complete=False)
    dump(path, record)

    try:
        if method == 'full':
            result = construct_offline_bts(pre.plant, max_choices=PATTERN_LIMIT,
                                           timeout_seconds=SECONDS)
        else:
            for u in range(1, 2 * copies + 2):
                result = solve_limited_lookahead(pre, horizon=u,
                    max_window_states=WINDOW_LIMIT, max_choices=PATTERN_LIMIT,
                    timeout_seconds=max(0., SECONDS - (perf_counter() - started)))
                record['trials'].append(dict(u=u, status=result.status,
                    window=len(result.window), D=result.decision_count, O=result.observation_count))
                record['seconds'] = perf_counter() - started
                dump(path, record)

                if result.status != 'inconclusive':
                    break

        record.update(complete=True, status=result.status, u=result.horizon,
                      D=result.decision_count, O=result.observation_count,
                      nodes=result.decision_count + result.observation_count,
                      seconds=perf_counter() - started)

        if result.status == 'winning':
            record['policy_validation'] = validate_policy(pre, result)

    except BTSBudgetExceeded as error:
        record.update(status='budget limited', metrics=error.metrics,
                      seconds=perf_counter() - started)

    dump(path, record)


def hard_case():
    plant = build_global_dfa(1000, 800)
    started = perf_counter()
    pre = preprocess(plant)
    result = solve_minimum_lookahead(pre, timeout_seconds=60.)
    ll_seconds = perf_counter() - started
    assert result.status == 'winning'
    validate_policy(pre, result)
    graph = build_closed_loop(pre, result)
    started = perf_counter()
    full = construct_offline_bts(plant)
    full_seconds = perf_counter() - started
    assert full.status == result.status
    row = dict(states=1000, safe_spine=800, Q_d=len(pre.Q_d), Q_f=len(pre.Q_f),
               Q_e=len(pre.Q_e), u=result.horizon, LL_D=result.decision_count,
               LL_O=result.observation_count, LL_nodes=result.decision_count + result.observation_count,
               Full_D=full.decision_count, Full_O=full.observation_count,
               Full_nodes=full.decision_count + full.observation_count,
               LL_seconds=ll_seconds, Full_seconds=full_seconds,
               closed_loop_states=len(graph['nodes']), closed_loop_edges=len(graph['edges']))
    dump(OUT / 'less_prunable.json', row)
    dump(OUT / 'less_prunable_closed_loop.json', graph)
    print('Less-prunable global case:', row, flush=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--worker', choices=('full', 'll'))
    parser.add_argument('--copies', type=int)
    parser.add_argument('--verify-only', action='store_true')
    args = parser.parse_args()

    if args.worker:
        worker(args.copies, args.worker)

        return

    if args.verify_only:
        validate_analysis()
        print(export_controlled_products(), flush=True)

        return

    validate_analysis()
    hard_case()
    rows = []

    for copies in (6, 7, 8):
        row = dict(copies=copies, states=10 ** copies, patterns=2 ** copies,
                   Q_d=1, Q_f=6 * copies, Q_e=10 ** copies - 9 ** copies,
                   feasible=True, deadlock_reachable_before_control=True,
                   controlled_physical_states=3 ** copies,
                   feasible_policy='Disable every b_i; every coordinate stays in {q0,q1,q2} '
                       'and has an uncontrollable a_i transition. This proves feasibility, '
                       'not completion of either global synthesis algorithm.')

        for method in ('full', 'll'):
            print('Starting', copies, method, flush=True)
            path = OUT / f'product_{copies}_{method}.json'
            process = subprocess.Popen([sys.executable, '-X', 'utf8', __file__, '--worker', method,
                                        '--copies', str(copies)])
            terminated = False

            try:
                process.wait(timeout=SECONDS + 5.)
            except subprocess.TimeoutExpired:
                terminated = True
                process.kill()
                process.wait()
                record = json.loads(path.read_text())
                record.update(complete=False, status='external wall-clock budget',
                              wall_clock_limit=SECONDS + 5.)
                dump(path, record)

            if process.returncode and not terminated:
                raise RuntimeError('Worker failed; partial output is not a benchmark result')

            row[method] = json.loads(path.read_text())
            print('Finished', copies, method, row[method].get('status'),
                  row[method].get('nodes'), row[method].get('seconds'), flush=True)

        rows.append(row)
        dump(OUT / 'products.json', rows)

    export_controlled_products()

    dump(OUT / 'manifest.json', dict(seed=None, seconds_per_method=SECONDS,
        window_limit=WINDOW_LIMIT, pattern_limit=PATTERN_LIMIT,
        source_sha256={f: hashlib.sha256(Path(f).read_bytes()).hexdigest() for f in
            ('hard_product_case_studies.py', 'global_large_case_studies.py',
             'des_core/certified_lookahead.py', 'des_core/offline_bts.py')},
        counts='Only completed global LL-BTS/BTS constructions receive final node counts. '
            'Incomplete trials retain their status and work metrics, not a fabricated completed count.'))


if __name__ == '__main__':
    main()
