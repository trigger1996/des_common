"""Re-measure revision datasets after the truncated UR/NX implementation change.

Run from the project root: python -X utf8 examples/paper/revision_experiments.py
Saved source plants are inputs. Existing benchmark measurements are preserved.
"""

# Allow direct execution from the project working directory.
if __package__ in (None, ""):
    import sys as _sys
    from pathlib import Path as _Path
    _sys.path.insert(0, str(_Path(__file__).resolve().parents[2]))


from collections import Counter
import gc
import hashlib
import json
from pathlib import Path
import platform
import statistics
import subprocess
import sys
from time import perf_counter
import tracemalloc

from des_core.automata import DFA
from des_core.certified_lookahead import preprocess, solve_limited_lookahead, validate_policy
from des_core.offline_bts import construct_offline_bts
from des_core.closed_loop import build_closed_loop
from examples.comparisons.compare_online_offline import load_plant
from des_core.resource_monitor import process_snapshot, interval_usage
from examples.comparisons.randomized_online_offline import online as adaptive_online

BASE = Path('outputs/expanded_yin_benchmark')
OUT = Path('outputs/revision_materials/experiments')


def dump(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')


def storage(result):
    return dict(D=result.decision_count, O=result.observation_count,
                nodes=result.decision_count + result.observation_count,
                edges=result.edge_count,
                retained_D=len(result.decision_policy),
                retained_O=len({(c.closure, c.pattern) for options in result.policy.values() for c in options}))


def peak(call):
    gc.collect()
    tracemalloc.start()

    try:
        call()

        return tracemalloc.get_traced_memory()[1]
    finally:
        tracemalloc.stop()


def timed_offline(plant):
    started = perf_counter()
    result = construct_offline_bts(plant)
    patterns = result.maximal_patterns

    return result, patterns, perf_counter() - started


def measure(plant, run_online, repetitions, index):
    on_samples, off_samples, pre_samples, solve_samples = [], [], [], []
    resources = {'online': [], 'offline': []}

    for q in plant.states:
        plant.enabled(q)

    for repeat in range(repetitions):
        for mode in (('online', 'offline') if (index + repeat) % 2 else ('offline', 'online')):
            resource_before = process_snapshot()

            if mode == 'online':
                on, patterns, elapsed, pre, attempts = run_online()
                on_samples.append(elapsed)
                pre_samples.append(pre.seconds)
                solve_samples.append(on.seconds)
            else:
                off, off_patterns, elapsed = timed_offline(plant)
                off_samples.append(elapsed)

            resources[mode].append(interval_usage(resource_before, process_snapshot()))

    assert on.status == off.status
    validate_policy(pre, on)
    validate_policy(pre, off)
    row = dict(states=len(plant.states), transitions=len(plant.transitions),
               observable=sorted(plant.observable), controllable=sorted(plant.controllable),
               status=on.status, u=on.horizon, same_decision=True,
               same_root_patterns=set(patterns) == set(off_patterns), attempts=attempts,
               repetitions=repetitions, online_samples=on_samples, offline_samples=off_samples,
               preprocessing_samples=pre_samples, final_solve_samples=solve_samples,
               online_median=statistics.median(on_samples), offline_median=statistics.median(off_samples),
               online_mean=statistics.mean(on_samples), offline_mean=statistics.mean(off_samples),
               online_peak=peak(run_online), offline_peak=peak(lambda: timed_offline(plant)),
               online=storage(on), offline=storage(off))
    row['resource_samples'] = resources
    row['resource_scope'] = 'CPU interval and OS memory snapshots around each timed solve; '
    row['resource_scope'] += 'OS high-water marks are process-wide, not isolated per-case peaks. '
    row['resource_scope'] += 'Separate tracemalloc calls measure per-case Python allocation peaks.'
    p = 2 ** len(plant.controllable)
    row['online_pattern_checks_final_solve'] = p * sum(
        not estimate & (pre.Q_d | pre.Q_f) and estimate not in on.safe_terminals
        for estimate in on.constructed_choices)
    row['offline_pattern_checks'] = off.patterns_tested

    return row, pre, on


def summarize(rows):
    result = dict(models=len(rows), statuses=dict(Counter(r['status'] for r in rows)),
                  decision_agreement=sum(r['same_decision'] for r in rows),
                  root_pattern_agreement=sum(r['same_root_patterns'] for r in rows))

    for field in ('mean', 'median', 'peak'):
        on = statistics.mean(r['online_' + field] for r in rows)
        off = statistics.mean(r['offline_' + field] for r in rows)
        result[field] = dict(online=on, offline=off, difference=off - on,
                            saving=(off - on) / off,
                            negative_cases=sum(r['online_' + field] > r['offline_' + field] for r in rows))

    for field in ('D', 'O', 'nodes', 'edges', 'retained_D', 'retained_O'):
        on = sum(r['online'][field] for r in rows)
        off = sum(r['offline'][field] for r in rows)
        result[field] = dict(online_total=on, offline_total=off,
                            online_mean=on / len(rows), offline_mean=off / len(rows),
                            difference=off - on, saving=(off - on) / off if off else None,
                            negative_cases=sum(r['online'][field] > r['offline'][field] for r in rows))

    result['preprocessing_mean'] = statistics.mean(statistics.mean(r['preprocessing_samples']) for r in rows)
    result['final_solve_mean'] = statistics.mean(statistics.mean(r['final_solve_samples']) for r in rows)

    return result


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    curated, inputs = [], []
    models = json.loads((BASE / 'model_results.json').read_text(encoding='utf-8'))

    for index, model in enumerate(models):
        name = model['name']
        folder = BASE / name
        plant = load_plant(folder)
        inputs.append(json.loads((folder / 'plant.json').read_text(encoding='utf-8')))
        pre = preprocess(plant)
        baseline = construct_offline_bts(plant)
        sweep = [solve_limited_lookahead(pre, horizon=u) for u in range(1, max(2, len(plant.states)))]
        decisive = next(r.horizon for r in sweep if r.status != 'inconclusive')
        matching = next(r.horizon for r in sweep if r.status == baseline.status and
                        set(r.maximal_patterns) == set(baseline.maximal_patterns))
        selected = next(r.horizon for r in sweep if r.horizon >= max(1, pre.lookahead_lower_bound) and
                        r.status == baseline.status and set(r.maximal_patterns) == set(baseline.maximal_patterns))

        def run_online():
            started = perf_counter()
            fresh_pre = preprocess(plant)
            result = solve_limited_lookahead(fresh_pre, horizon=selected)
            patterns = result.maximal_patterns

            return result, patterns, perf_counter() - started, fresh_pre, [dict(u=selected, status=result.status)]

        row, pre, result = measure(plant, run_online, 11, index)
        row.update(name=name, draft_u=pre.lookahead_lower_bound, minimum_decisive_u=decisive,
                   minimum_matching_u=matching, selected_u=selected)
        graph = build_closed_loop(pre, result)
        row['closed_loop'] = dict(states=len(graph['nodes']), edges=len(graph['edges']))
        # This is a controlled ablation, not a reproduction of another paper.
        ablation = solve_limited_lookahead(pre, horizon=selected, certificates=False)
        row['same_u_without_certificates'] = dict(status=ablation.status, **storage(ablation))
        curated.append(row)
        print('curated', index + 1, name, result.status, selected, flush=True)

    dump(OUT / 'curated_inputs.json', inputs)
    dump(OUT / 'curated_results.json', curated)
    plants_path = BASE / 'randomized_comparison/plants.json'
    plants = json.loads(plants_path.read_text(encoding='utf-8'))
    random_rows = []

    for index, item in enumerate(plants):
        plant = DFA(frozenset(item['states']), item['initial'], frozenset(item['events']),
                    frozenset(item['controllable']), frozenset(item['observable']),
                    {(q, e):t for q, e, t in item['transitions']})
        row, _, _ = measure(plant, lambda: adaptive_online(plant, seconds=10.), 5, index)
        row.update(index=item['index'], stratum=item['stratum'])
        random_rows.append(row)

        if (index + 1) % 100 == 0:
            print('random', index + 1, flush=True)

    dump(OUT / 'random_inputs.json', plants)
    dump(OUT / 'random_results.json', random_rows)
    summary = dict(curated=summarize(curated), randomized=summarize(random_rows),
                   random_seed=20261121, generated_automata=len(plants),
                   random_input_sha256=hashlib.sha256(plants_path.read_bytes()).hexdigest(),
                   python=sys.version, platform=platform.platform(), processor=platform.processor(),
                   hardware_threads=__import__('os').cpu_count(),
                   git_base_commit=subprocess.check_output(
                       ['git', '-c', 'safe.directory=D:/__Workspace/Pycharm/des_common', 'rev-parse', 'HEAD'],
                       text=True).strip(),
                   source_sha256={name: hashlib.sha256(Path(name).read_bytes()).hexdigest()
                                  for name in ('examples/paper/revision_experiments.py', 'des_core/certified_lookahead.py',
                                               'des_core/offline_bts.py', 'examples/comparisons/randomized_online_offline.py')},
                   timing_scope='Fresh solving and root maximal-pattern filtering; online includes preprocessing '
                                'and, for random automata, all horizon retries. Common input/index, calibration, '
                                'rendering, validation and serialization excluded.',
                   memory_scope='Independent tracemalloc peak per side, common prebuilt immutable input/index '
                                'excluded; Python allocations, not RSS or C-extension/process memory.',
                   curated_selection='Offline root-pattern equality calibrates u outside timing; this is '
                                      'an oracle-calibrated comparison, not an online horizon-selection rule.',
                   random_selection='Start at computed draft_u and increase only after inconclusive; no offline oracle.')
    dump(OUT / 'summary.json', summary)
    print(json.dumps({k: summary[k] for k in ('curated', 'randomized')}, indent=2))


if __name__ == '__main__':
    main()
