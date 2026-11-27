"""True self-products for the revised E/H large-scale examples.

python -X utf8 examples/large_scale/early_stop_products.py --case E H
python -X utf8 examples/large_scale/early_stop_products.py --case E --copies 7 8
python -X utf8 examples/large_scale/early_stop_products.py --case H --copies 4

The default components have 10 (E) and 100 (H) states. No component LL-BTS
is reused: the standard solver constructs a global product LL-BTS. There is
no fixed time/pattern/window budget; the optional working-set guard defaults
to 10 GiB. Full counts are structural predictions, not completed full runs.
"""

# Allow direct execution from the project working directory.
if __package__ in (None, ""):
    import sys as _sys
    from pathlib import Path as _Path
    _sys.path.insert(0, str(_Path(__file__).resolve().parents[2]))


import argparse
from collections import deque
from collections.abc import Set
from datetime import datetime
import hashlib
import json
from pathlib import Path
import signal
import statistics
import subprocess
import sys
from time import perf_counter, sleep

from des_core.asynchronous_product import ImplicitProductDFA
from des_core.automata import DFA
from des_core.certified_lookahead import Choice, Preprocessing, preprocess, solve_minimum_lookahead, validate_policy
from des_core.offline_bts import construct_offline_bts
from examples.large_scale.large_scale_overall import dump, memory_status, working_set


def component(kind, n):
    if n < 6:
        raise ValueError('Use at least six component states')

    safe = (1, 2) if kind == 'E' else (2, 3)
    failure_start = 3 if kind == 'E' else 4
    transitions = {('q0', 'a'): 'q1', ('q0', 'b'): f'q{failure_start}'}

    if kind == 'H':
        transitions['q1', 'a'] = 'q2'
        transitions['q1', 'b'] = 'q4'

    first, hidden = (f'q{i}' for i in safe)
    transitions[first, 'a'] = first
    transitions[first, 'u'] = hidden
    transitions[hidden, 'a'] = first

    for i in range(failure_start, n - 1):
        transitions[f'q{i}', 'a'] = f'q{i + 1}'

    return DFA(frozenset(f'q{i}' for i in range(n)), 'q0',
               frozenset({'a', 'b', 'u'}), frozenset({'b'}),
               frozenset({'a', 'b'}), transitions)


class ProductSubset(Set):
    def __init__(self, plant, safe, failure, kind):
        self.plant = plant
        self.safe = safe
        self.failure = failure
        self.kind = kind
        self.hidden_target = max(safe, key=lambda q: int(q[1:]))

    def __contains__(self, q):
        is_safe = any(state in self.safe for state in q)

        if self.kind == 'safe':
            return is_safe

        is_entry = (q == self.plant.initial or
                    any(state not in ('q0', self.hidden_target) for state in q))

        return is_entry and (is_safe or q in self.failure or not self.plant.enabled(q))

    def __len__(self):
        n, k = len(self.plant.component.states), self.plant.copies
        size = n ** k - (n - len(self.safe)) ** k

        return size if self.kind == 'safe' else size + len(self.failure) + 1 - (2 ** k - 1)

    def __iter__(self):
        return (q for q in self.plant.states if q in self)


def analyze(kind, n, copies):
    started = perf_counter()
    base = component(kind, n)
    local = preprocess(base)
    plant = ImplicitProductDFA(base, copies)
    dead_state = next(iter(local.Q_d))
    dead = frozenset({(dead_state,) * copies})
    failure = set()

    for i in range(copies):
        for q in local.Q_f:
            state = [dead_state] * copies
            state[i] = q
            failure.add(tuple(state))

    failure = frozenset(failure)
    safe = ProductSubset(plant, local.Q_e, failure, 'safe')
    entries = ProductSubset(plant, local.Q_e, failure, 'entries')

    # Hidden transitions move only within the invariant local safe subset.
    # Their global maximum simple length is k; no hidden path enters Qf.
    return Preprocessing(plant, dead, failure, safe, entries, copies, 0, 0,
                         perf_counter() - started)


def full_counts(n, copies):
    closure_types = (n - 1) ** copies
    decisions = n ** copies - 3 ** copies + copies * n ** (copies - 1) + 1
    observations = closure_types * 2 ** copies
    minimum_record = (sys.getsizeof(Choice(frozenset(), frozenset(), ()))
                      + 3 * sys.getsizeof(frozenset({'q'}))
                      + sys.getsizeof((None,)) + sys.getsizeof((None, None)))

    return dict(D=decisions, O=observations, nodes=decisions + observations,
                status='structural count; global full BTS not run',
                minimum_record_bytes=(observations - 2 ** copies) * minimum_record)


def recentered_counts(kind, n, copies):
    """Exact constructed counts for copies >= 2, with one-step local windows."""

    if copies < 2:
        return {}

    r = n - 2
    failure = n - (4 if kind == 'E' else 5)
    decisions = r ** copies - 1 + copies * r ** (copies - 1)
    observations = 2 ** copies * (r ** copies - 1 - copies * failure)
    record_floor = sys.getsizeof(Choice(frozenset(), frozenset(), ())) + 2 * sys.getsizeof(frozenset()) + sys.getsizeof(())
    healthy = 1 if kind == 'E' else 2
    modes = 2 ** copies
    successor_pairs = (modes * copies * (r - 1) * r ** (copies - 1)
                       + modes // 2 * copies * healthy * r ** (copies - 1)
                       - modes * copies * failure)
    successor_floor = (sys.getsizeof((None, None)) + sys.getsizeof(frozenset())
                       + sys.getsizeof((None,)) - sys.getsizeof(()))

    return dict(D=decisions, O=observations, states=decisions + observations,
                horizon=1, bar_u=0, successor_pairs=successor_pairs,
                minimum_payload_bytes=observations * record_floor + successor_pairs * successor_floor,
                memory_scope='Choice, separate pattern/closure frozensets, successor tuple and every '
                    'nonempty NX pair/frozenset/reference; excludes state tuples, transitions, maps and pruning.')


def validate_small():
    records = []

    for kind in ('E', 'H'):
        for copies in (1, 2, 3):
            pre = analyze(kind, 6, copies)
            plant = pre.plant
            states = frozenset(plant.states)
            transitions = {(q, e): t for q in states for e, t in plant.enabled(q)}
            explicit = DFA(states, plant.initial, plant.events, plant.controllable,
                           plant.observable, transitions)
            reference = preprocess(explicit)
            assert reference.Q_d == pre.Q_d and reference.Q_f == pre.Q_f
            assert reference.Q_e == frozenset(pre.Q_e)
            assert reference.Q_o_tilde == frozenset(pre.Q_o_tilde)
            assert (reference.u, reference.u_f) == (pre.u, pre.u_f)
            full = construct_offline_bts(explicit)
            predicted = full_counts(6, copies)
            assert (full.decision_count, full.observation_count) == (predicted['D'], predicted['O'])
            result = solve_minimum_lookahead(pre)
            assert result.status == full.status == 'winning'
            assert result.horizon == 1

            if copies >= 2:
                counts = recentered_counts(kind, 6, copies)
                assert (result.decision_count, result.observation_count) == (counts['D'], counts['O'])
                assert sum(len(c.successors) for cs in result.constructed_choices.values() for c in cs) == counts['successor_pairs']

            validation = validate_policy(pre, result)
            reached = {plant.initial}
            queue = deque(reached)

            while queue:
                for _, q in plant.enabled(queue.popleft()):
                    if q not in reached:
                        reached.add(q)
                        queue.append(q)

            assert reached == states
            records.append(dict(kind=kind, copies=copies, explicit_states=len(states),
                                global_sets_match=True, full_counts_match=True,
                                horizon=result.horizon, policy_validation=validation))

    return records


def export_bts(result, path):
    dump(path, dict(status=result.status, horizon=result.horizon,
        initial_estimate=sorted(result.initial), window=sorted(result.window),
        maximal_root_patterns=[sorted(p) for p in result.maximal_patterns],
        nodes_counted_before_pruning=result.decision_count + result.observation_count,
        decision_states=[dict(estimate=sorted(x), retained=x in result.policy,
            safe_terminal=x in result.safe_terminals,
            choices=[dict(pattern=sorted(c.pattern), retained=c in result.policy.get(x, ()), closure=sorted(c.closure),
                successors=[dict(event=e, estimate=sorted(y)) for e, y in c.successors]) for c in choices])
            for x, choices in result.constructed_choices.items()]))


def worker(args):
    path = args.output / f'{args.kind}{args.copies}.json'
    row = dict(kind=args.kind, component_states=args.states, copies=args.copies,
               plant_states=args.states ** args.copies, complete=False, phase='starting',
               input_representation='Implicit asynchronous self-product with indexed alphabets; '
                   'exact product state subsets; global LL-BTS explicitly constructed.',
               full=full_counts(args.states, args.copies), runs=[])
    dump(path, row)
    base = component(args.kind, args.states)
    dump(path.with_name(path.stem + '_component.json'), dict(
        states=sorted(base.states), initial=base.initial, events=sorted(base.events),
        observable=sorted(base.observable), controllable=sorted(base.controllable),
        transitions=[[q, e, t] for (q, e), t in sorted(base.transitions.items())]))

    def stop(signum, frame):
        raise KeyboardInterrupt

    if hasattr(signal, 'SIGBREAK'):
        signal.signal(signal.SIGBREAK, stop)

    try:
        for repeat in range(args.repetitions):
            started = perf_counter()
            pre = analyze(args.kind, args.states, args.copies)
            result = solve_minimum_lookahead(pre)
            result.maximal_patterns
            seconds = perf_counter() - started
            assert result.status == 'winning'
            assert result.horizon == 1
            validation = validate_policy(pre, result)
            row['runs'].append(dict(seconds=seconds, structural_seconds=pre.seconds,
                                   horizon=result.horizon, D=result.decision_count,
                                   O=result.observation_count, validation=validation))
            row.update(phase='completed repetition', repetitions_completed=repeat + 1,
                       Q_d=len(pre.Q_d), Q_f=len(pre.Q_f), Q_e=len(pre.Q_e),
                       bar_u=pre.lookahead_lower_bound,
                       admissible_patterns=2 ** args.copies,
                       peak_working_set_bytes=working_set(-1, peak=True))
            dump(path, row)

        row.update(complete=True, phase='finished', status=result.status, horizon=result.horizon,
                   LL_D=result.decision_count, LL_O=result.observation_count,
                   LL_nodes=result.decision_count + result.observation_count,
                   retained_D=len(result.policy),
                   retained_O=len({(c.closure, c.pattern) for cs in result.policy.values() for c in cs}),
                   mean_seconds=statistics.mean(r['seconds'] for r in row['runs']))

        if row['LL_nodes'] <= 200000:
            export_bts(result, path.with_name(path.stem + '_global_ll_bts.json'))
        else:
            row['global_bts_export'] = 'Omitted to avoid materializing a second large graph during JSON export; '
            row['global_bts_export'] += 'completed counts and exhaustive policy validation are recorded.'

        dump(path, row)
    except KeyboardInterrupt:
        row.update(phase='interrupted', complete=False)
        dump(path, row)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--case', nargs='+', choices=('E', 'H'), default=['E', 'H'])
    parser.add_argument('--copies', nargs='+', type=int)
    parser.add_argument('--component-states', type=int)
    parser.add_argument('--repetitions', type=int, default=5)
    parser.add_argument('--max-memory-gib', type=float, default=10.)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--worker', action='store_true', help=argparse.SUPPRESS)
    parser.add_argument('--kind', help=argparse.SUPPRESS)
    parser.add_argument('--states', type=int, help=argparse.SUPPRESS)
    args = parser.parse_args()

    if args.worker:
        args.copies = args.copies[0]
        worker(args)

        return

    args.output = (args.output or Path('outputs/revision_materials') /
        ('early_stop_products_' + datetime.now().strftime('%Y%m%d_%H%M%S'))).resolve()
    dump(args.output / 'small_validation.json', validate_small())
    hardware = memory_status()
    rows = []

    for kind in args.case:
        n = args.component_states or (10 if kind == 'E' else 100)
        copies_list = args.copies or ([7, 8] if kind == 'E' else [4])

        for copies in copies_list:
            print(kind, 'component/copies/product:', n, copies, n ** copies,
                  'full structural counts:', full_counts(n, copies), flush=True)
            predicted = recentered_counts(kind, n, copies)
            allowance = min(hardware['available_bytes'], args.max_memory_gib * 2 ** 30)

            if predicted and predicted['minimum_payload_bytes'] > allowance:
                row = dict(kind=kind, component_states=n, copies=copies, plant_states=n ** copies,
                           complete=False, status='not_run_memory_lower_bound', predicted=predicted,
                           full=full_counts(n, copies), available_bytes=hardware['available_bytes'],
                           reason='Mandatory recentered LL-BTS payload exceeds available RAM or memory guard.')
                dump(args.output / f'{kind}{copies}.json', row)
                rows.append(row)
                dump(args.output / 'results.json', rows)
                print('Skipped by exact resource lower bound:', kind, copies, predicted, flush=True)

                continue

            command = [sys.executable, '-X', 'utf8', str(Path(__file__).resolve()),
                '--worker', '--kind', kind, '--states', str(n), '--copies', str(copies),
                '--repetitions', str(args.repetitions), '--output', str(args.output)]
            child = subprocess.Popen(command, creationflags=subprocess.CREATE_NEW_PROCESS_GROUP)
            stopped = False

            try:
                while child.poll() is None:
                    try:
                        rss = working_set(child._handle)
                    except OSError:
                        if child.poll() is not None:
                            break

                        raise

                    if rss > args.max_memory_gib * 2 ** 30:
                        stopped = True
                        child.send_signal(signal.CTRL_BREAK_EVENT)

                        break

                    sleep(.25)
            except KeyboardInterrupt:
                child.send_signal(signal.CTRL_BREAK_EVENT)
                child.wait()

                raise

            child.wait()

            if child.returncode:
                raise RuntimeError(f'{kind}{copies} worker exited with {child.returncode}')

            row = json.loads((args.output / f'{kind}{copies}.json').read_text())

            if stopped:
                row['stop_reason'] = 'memory guard'

            rows.append(row)
            dump(args.output / 'results.json', rows)
            print('Result:', kind, copies, row.get('status'), 'LL nodes', row.get('LL_nodes'),
                  'mean seconds', row.get('mean_seconds'), flush=True)

    dump(args.output / 'manifest.json', dict(hardware=hardware, python=sys.version, seed=None,
        repetitions=args.repetitions, time_limit=None, pattern_limit=None, window_limit=None,
        memory_guard_gib=args.max_memory_gib,
        source_sha256={f: hashlib.sha256(Path(f).read_bytes()).hexdigest() for f in
            ('examples/large_scale/early_stop_products.py', 'des_core/certified_lookahead.py',
             'des_core/offline_bts.py', 'des_core/asynchronous_product.py')},
        timing='Fresh component structural analysis + exact product subset derivation + '
            'all initial horizon trials + initial maximal-pattern filtering; validation/export excluded.'))


if __name__ == '__main__':
    main()
