"""Conditional Full BTS runtime estimates from complete smaller runs.

python -X utf8 estimate_full_runtime.py
Targets are not run: their storage exceeds local RAM. Estimates assume enough
RAM and no paging. Complete pilot phase times, uniformly sampled target
decision estimates, work counts, and model errors are saved for review.
"""

import argparse
import gc
import hashlib
import inspect
from itertools import combinations, product
import json
from pathlib import Path
import random
import statistics
import subprocess
import sys
from time import perf_counter

import numpy as np

from des_core.asynchronous_product import ImplicitProductDFA
import des_core.offline_bts as offline
from early_stop_products import component, full_counts
from global_large_case_studies import build_global_dfa
from large_scale_overall import dump, memory_status


OUT = Path('outputs/revision_materials/full_runtime_estimates_20261123')


def make_plant(kind, n, k):
    base = build_global_dfa(n, 3) if kind == 'P' else component(kind, n)

    return ImplicitProductDFA(base, k)


def totals(kind, n, k):
    if kind == 'P':
        d, o = n ** k, 2 ** k * n ** k
    else:
        count = full_counts(n, k)
        d, o = count['D'], count['O']

    f = n - (4 if kind == 'H' else 3)
    healthy = 1 if kind == 'E' else 2
    p = 2 ** k
    lost = f ** k
    last_healthy = (p // 2) * healthy * k * f ** (k - 1)

    return dict(D=d, O=o, M=d * p, Q=n ** k,
                lost_D=lost, removed_patterns=p * lost + last_healthy,
                prune_links=p * k * (f - 1) * f ** (k - 1) + last_healthy)


def sampled_estimates(kind, n, k, count, rng):
    if kind == 'P':
        factors = [('q0', 'q1'), ('q1', 'q2'), ('q2',)] + [(f'q{i}',) for i in range(3, n)]

        for _ in range(count):
            indices = [rng.randrange(n) for _ in range(k)]
            yield (frozenset({('q0',) * k}) if not any(indices)
                   else frozenset(product(*(factors[i] for i in indices))))

        return

    safe = ('q1', 'q2') if kind == 'E' else ('q2', 'q3')
    start = 3 if kind == 'E' else 4
    factors = [('q0',)] + ([('q1',)] if kind == 'H' else [])
    factors += [(f'q{i}',) for i in range(start, n)] + [safe]
    r = len(factors)
    d0 = r ** k - 2 ** k
    d = d0 + 1 + k * r ** (k - 1)

    for _ in range(count):
        group = rng.randrange(d)

        if group == 0:
            yield frozenset({('q0',) * k})

            continue

        indices = [rng.randrange(r) for _ in range(k)]

        if group <= d0:
            while all(i in (0, r - 1) for i in indices):
                indices = [rng.randrange(r) for _ in range(k)]

            selected = [factors[i] for i in indices]
        else:
            selected = [factors[i] for i in indices]
            selected[rng.randrange(k)] = (safe[0],)

        yield frozenset(product(*selected))


def sample_work(kind, n, k, count=128):
    plant = make_plant(kind, n, k)
    seed = 20261123 + ord(kind) * 1000 + n * 10 + k
    rng = random.Random(seed)
    controls = sorted(plant.controllable)
    records = []
    seconds = 0.

    for estimate in sampled_estimates(kind, n, k, count, rng):
        options, flags, seen, queue = [], [], set(), []
        started = perf_counter()

        for size in range(k + 1):
            for combo in combinations(controls, size):
                pattern = frozenset(combo)
                choice = offline.traditional_ur_nx(plant, estimate, pattern)
                enabled = pattern | plant.uncontrollable
                flags.append(all(any(e in enabled for e, _ in plant.enabled(q)) for q in choice.closure))
                options.append(choice)

                for _, target in choice.successors:
                    if target not in seen:
                        seen.add(target)
                        queue.append(target)

        seconds += perf_counter() - started
        records.extend(options)

    checks = len(records)

    return dict(seed=seed, sampled_decisions=count, pattern_checks=checks,
                enumeration_seconds_per_check=seconds / checks,
                mean_A=sum(len(c.successors) for c in records) / checks,
                mean_U=sum(len({y for _, y in c.successors}) for c in records) / checks,
                mean_C=sum(len(c.closure) for c in records) / checks,
                mean_Y=sum(len(y) for c in records for _, y in c.successors) / checks,
                sampling='Uniform over reachable global decision estimates, then all modes in each block. '
                    'Includes UR/NX, liveness, mode allocation and local queue bookkeeping.')


def profiled_builder():
    source = inspect.getsource(offline.construct_offline_bts)
    source = source.replace('def construct_offline_bts(', 'def profiled(')
    replacements = [
        ('    incoming = defaultdict(list);',
         "    _phase['enumeration'] = perf_counter() - started\n    _mark = perf_counter()\n    incoming = defaultdict(list);"),
        ('    while queue:\n        target = queue.popleft()',
         "    _phase['index'] = perf_counter() - _mark\n    _mark = perf_counter()\n    while queue:\n        target = queue.popleft()"),
        ('    policy = {x:',
         "    _phase['pruning'] = perf_counter() - _mark\n    _mark = perf_counter()\n    policy = {x:"),
        ('    observations = {',
         "    _phase['policy'] = perf_counter() - _mark\n    _mark = perf_counter()\n    observations = {"),
        ('    return Bipartitle_System(',
         "    _phase['graph_sets'] = perf_counter() - _mark\n    _phase['_return_start'] = perf_counter()\n    return Bipartitle_System("),
    ]

    for old, new in replacements:
        assert source.count(old) == 1, old
        source = source.replace(old, new)

    namespace = dict(offline.construct_offline_bts.__globals__)
    namespace['_phase'] = {}
    exec(compile(source, '<phase-only Full instrumentation>', 'exec'), namespace)

    return namespace['profiled'], namespace['_phase']


def pilot(kind, n, k, repetitions=3):
    measured = []
    feature = None

    for _ in range(repetitions):
        gc.collect()
        plant = make_plant(kind, n, k)
        builder, phases = profiled_builder()
        result = builder(plant)
        phases['materialization'] = perf_counter() - phases.pop('_return_start')
        phases['total'] = result.seconds
        assert result.status == 'winning'
        count = totals(kind, n, k)
        assert (result.decision_count, result.observation_count) == (count['D'], count['O'])
        measured.append(dict(phases))

        if feature is None:
            cs = result.constructed_choices
            a = sum(len(c.successors) for options in cs.values() for c in options)
            u = sum(len({y for _, y in c.successors}) for options in cs.values() for c in options)
            c_size = sum(len(c.closure) for options in cs.values() for c in options)
            lost = set(cs) - set(result.policy)
            links = sum(y in lost for options in cs.values() for c in options
                        for y in {target for _, target in c.successors})
            removed = sum(map(len, cs.values())) - sum(map(len, result.policy.values()))
            assert (len(lost), links, removed) == (count['lost_D'], count['prune_links'], count['removed_patterns'])
            d_edges = sum(map(len, cs.values()))
            feature = dict(**count, A=a, U=u, C=c_size, OD_edges=result.edge_count - d_edges)

        del result, builder, phases, plant

    sampling = sample_work(kind, n, k, 64)
    record = dict(kind=kind, component_states=n, copies=k, features=feature,
                  repetitions=measured, median={p: statistics.median(r[p] for r in measured) for p in measured[0]},
                  sampling=sampling)
    dump(OUT / f'pilot_{kind}_{n}_{k}.json', record)
    print('pilot', kind, n, k, 'complete', round(record['median']['total'], 4), 's', flush=True)


def phase_vector(phase, f):
    if phase == 'index':
        return [f['M'], f['U']]

    if phase == 'pruning':
        return [f['prune_links'], f['removed_patterns']]

    if phase == 'policy':
        return [f['M'], f['D']]

    return [f['M'] + f['A'] + f['C'], f['M'] + f['O'] + f['OD_edges']]


def fit_nonnegative(x, y):
    x, y = np.asarray(x, dtype=float), np.asarray(y, dtype=float)
    scale = np.maximum(x.max(axis=0), 1.)
    weights = 1. / np.maximum(y, 1e-6)
    a = (x / scale) * weights[:, None]
    b = y * weights
    candidates = [np.zeros(x.shape[1])]

    for mask in ((0,), (1,), (0, 1)):
        c = np.zeros(x.shape[1])
        c[list(mask)] = np.linalg.lstsq(a[:, mask], b, rcond=None)[0]

        if np.all(c >= 0):
            candidates.append(c)

    coefficient = min(candidates, key=lambda c: np.sum((a @ c - b) ** 2)) / scale

    return coefficient.tolist()


def estimate(pilots, kind, n, k):
    samples = [sample_work(kind, n, k, 256) for _ in range(5)]
    sample = dict(samples[0])
    sample['timing_repetitions'] = [r['enumeration_seconds_per_check'] for r in samples]
    sample['enumeration_seconds_per_check'] = statistics.median(sample['timing_repetitions'])
    f = totals(kind, n, k)
    f.update(A=f['M'] * sample['mean_A'], U=f['M'] * sample['mean_U'],
             C=f['M'] * sample['mean_C'])
    # Estimate unique O-D edges using the decision sample, correcting closure
    # aliases by the ratio observed in completed pilot graph counts.
    edge_ratios = [r['features']['OD_edges'] / max(1., r['features']['O'] * r['sampling']['mean_A'])
                   for r in pilots if r['kind'] == kind]
    f['OD_edges'] = f['O'] * sample['mean_A'] * statistics.median(edge_ratios)
    group = [r for r in pilots if r['kind'] == kind]
    ratios = [r['median']['enumeration'] /
              (r['features']['M'] * r['sampling']['enumeration_seconds_per_check']) for r in group]
    phases = dict(enumeration=f['M'] * sample['enumeration_seconds_per_check'] * statistics.median(ratios))
    models = {}

    for phase in ('index', 'pruning', 'policy', 'graph_sets'):
        coefficient = fit_nonnegative([phase_vector(phase, r['features']) for r in pilots],
                                      [r['median'][phase] for r in pilots])
        phases[phase] = float(np.dot(coefficient, phase_vector(phase, f)))
        models[phase] = coefficient

    per_state = statistics.median(r['median']['materialization'] /
                                 (r['features']['Q'] * r['copies']) for r in pilots)
    phases['materialization'] = per_state * f['Q'] * k
    total = sum(phases.values())
    record = dict(kind=kind, component_states=n, copies=k, features=f, sampling=sample,
                  conditional_seconds=total, conditional_hours=total / 3600,
                  planning_range_seconds=[total * .5, total * 3.], phases_seconds=phases,
                  phase_coefficients=models,
                  enumeration_correction=statistics.median(ratios),
                  condition='Sufficient RAM, same implementation/CPU and no paging. '
                      'Not a measured full run or an achievable completion time on this RAM-limited PC.',
                  range_scope='Engineering sensitivity range, not a statistical confidence interval.')
    dump(OUT / f'target_{kind}_{n}_{k}.json', record)

    return record


def validate(pilots):
    rows = []

    for held in pilots:
        train = [r for r in pilots if r is not held]
        f = held['features']
        group = [r for r in train if r['kind'] == held['kind']]
        correction = statistics.median(r['median']['enumeration'] /
            (r['features']['M'] * r['sampling']['enumeration_seconds_per_check']) for r in group)
        seconds = f['M'] * held['sampling']['enumeration_seconds_per_check'] * correction

        for phase in ('index', 'pruning', 'policy', 'graph_sets'):
            coef = fit_nonnegative([phase_vector(phase, r['features']) for r in train],
                                  [r['median'][phase] for r in train])
            seconds += float(np.dot(coef, phase_vector(phase, f)))

        seconds += f['Q'] * held['copies'] * statistics.median(
            r['median']['materialization'] / (r['features']['Q'] * r['copies']) for r in train)
        actual = held['median']['total']
        rows.append(dict(kind=held['kind'], component_states=held['component_states'],
            copies=held['copies'], measured_seconds=actual, predicted_seconds=seconds,
            relative_error=(seconds - actual) / actual))

    return dict(method='Leave one completed pilot out; use its independently sampled UR/NX work '
                'and exact graph counts, fit phase rates on the other pilots.',
                rows=rows, median_absolute_relative_error=statistics.median(
                    abs(r['relative_error']) for r in rows),
                maximum_absolute_relative_error=max(abs(r['relative_error']) for r in rows),
                limitation='Pilot-scale validation does not bound errors at the large targets.')


def main():
    global OUT
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=OUT)
    parser.add_argument('--pilot', nargs=3)
    parser.add_argument('--reuse-pilots', action='store_true')
    args = parser.parse_args()
    OUT = args.output
    OUT.mkdir(parents=True, exist_ok=True)

    if args.pilot:
        kind, n, k = args.pilot
        pilot(kind, int(n), int(k))

        return

    specs = [('E', 6, 3), ('E', 8, 3), ('E', 6, 4), ('E', 8, 4), ('E', 6, 5),
             ('H', 6, 3), ('H', 8, 3), ('H', 8, 4), ('H', 12, 4),
             ('P', 6, 3), ('P', 8, 3), ('P', 6, 4), ('P', 8, 4), ('P', 6, 5)]

    for kind, n, k in specs:
        if args.reuse_pilots:
            continue

        child = subprocess.run([sys.executable, '-X', 'utf8', __file__, '--output', str(OUT),
                                '--pilot', kind, str(n), str(k)])

        if child.returncode:
            raise RuntimeError(f'Pilot failed: {kind}/{n}/{k}')

    pilots = [json.loads((OUT / f'pilot_{kind}_{n}_{k}.json').read_text()) for kind, n, k in specs]
    validation = validate(pilots)
    targets = [estimate(pilots, *spec) for spec in [('E', 10, 7), ('H', 100, 4), ('P', 10, 6)]]
    dump(OUT / 'summary.json', dict(hardware=memory_status(), python=sys.version,
        targets=targets, pilots=specs, validation=validation,
        source_sha256={f: hashlib.sha256(Path(f).read_bytes()).hexdigest() for f in
            ('estimate_full_runtime.py', 'des_core/offline_bts.py', 'early_stop_products.py')},
        baseline='Unmodified full-BTS algorithm with six phase timers inserted; no per-operation tracing.',
        use='Conditional compute-time forecasts only; do not use as measured speedups.'))

    for row in targets:
        print('FORECAST', row['kind'], row['copies'], round(row['conditional_seconds']), 's',
              round(row['conditional_hours'], 2), 'h', row['phases_seconds'], flush=True)


if __name__ == '__main__':
    main()
