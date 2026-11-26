"""Reproducible paper corpus, u sweep, offline comparison and random experiment.

Run: python certified_benchmark.py --samples 600 --seed 20261120
"""

from __future__ import annotations
import argparse
from collections import Counter
import csv
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import platform
import random
import statistics
import sys
from time import perf_counter
import tracemalloc

from des_core.automata import DFA, DESExample
from des_core.certified_lookahead import (preprocess, solve_limited_lookahead, solve_offline,
                                         validate_policy, executable_choices, Limited_Lookahead_Controller)
from examples.yin_literature import build_yin_literature_examples
from examples.non_deadlock import build_small_cycle_example, build_nested_cycle_deadlock_example


def dump(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')


def export_plant(example, folder):
    p = example.dfa
    dump(folder/'plant.json', {'name':example.name, 'source':example.source_name,
         'notes':example.description, 'states':sorted(p.states), 'initial':p.initial,
         'events':sorted(p.events), 'controllable':sorted(p.controllable),
         'observable':sorted(p.observable),
         'transitions':[[q, e, t] for (q, e), t in sorted(p.transitions.items())]})


def export_bts(pre, result, folder, *, draw=True, structure='LL-BTS'):
    """Export actual pair-valued states; record construction before pruning."""

    from des_core.bipartite_export import graph_record, write_dot, render_record, export_recorded_steps
    from des_core.bipartite_graph import attach_pair_graph
    import shutil

    if structure not in ('LL-BTS', 'BTS'):
        raise ValueError(structure)

    folder.mkdir(parents=True, exist_ok=True)

    if not result.decision_states:
        attach_pair_graph(result)

    if draw and structure == 'LL-BTS' and not result.construction_steps:
        recorded = solve_limited_lookahead(pre, estimate=result.initial,
            horizon=result.horizon, full=result.horizon is None,
            analysis_state=result.initial_decision[0], record_steps=True)
        assert recorded.status == result.status
        assert recorded.decision_states == result.decision_states
        assert recorded.decision_policy == result.decision_policy
        result = recorded

    stem = 'bts' if structure == 'BTS' else 'll_bts'
    record, ids, oids = graph_record(pre, result, structure)
    dump(folder / (stem + '.json'), record)
    write_dot(record, folder / (stem + '.dot'))
    write_dot(record, folder / (stem + '_retained.dot'), retained=True)

    if not draw:
        return

    render_record(record, folder / (stem + '.png'))
    render_record(record, folder / (stem + '_retained.png'), retained=True)
    render_record(record, folder / (stem + '_retained.pdf'), retained=True)

    if structure == 'LL-BTS':
        record['recorded_steps'] = export_recorded_steps(result, record, ids, oids, folder)
        dump(folder / (stem + '.json'), record)
        dump(folder / (stem + '_merged.json'), record)
        shutil.copy2(folder / (stem + '.png'), folder / (stem + '_merged.png'))


def summary_row(name, pre, result, baseline, selected_u, u_seconds):
    return {'name':name, 'states':len(pre.plant.states), 'transitions':len(pre.plant.transitions),
            'Qc':len(pre.plant.controllable), 'Qo':len(pre.plant.observable),
            'Qd':len(pre.deadlocks), 'Qf':len(pre.failure), 'Qe':len(pre.safe),
            'draft_u':pre.horizon, 'selected_u':selected_u, 'path_visits':pre.path_visits,
            'status':result.status, 'offline_status':baseline.status,
            'pre_seconds':pre.seconds, 'online_seconds':result.seconds,
            'total_seconds':pre.seconds+result.seconds, 'offline_seconds':baseline.seconds,
            'calibration_seconds_excluded':u_seconds,
            'D':result.decision_count, 'O':result.observation_count, 'edges':result.edge_count,
            'offline_D':baseline.decision_count, 'offline_O':baseline.observation_count,
            'maximal_patterns':[sorted(p) for p in result.maximal_patterns],
            'same_maximal_patterns':set(result.maximal_patterns) == set(baseline.maximal_patterns)}


def random_plant(rng, index):
    n = rng.randint(4, 12)
    states = [str(i) for i in range(n)]
    events = ('a', 'b', 'c', 'o')
    mode = index%3
    controls = frozenset(e for e in events if rng.random()<.55)
    observable = frozenset(e for e in events if rng.random()<.55)
    # Both partitions nontrivial; no all-observable substitution.
    observable = (observable|{'o'})-{'a'}
    transitions = {}
    probability = (.7, .45, .3)[mode]

    for q in states:
        if mode != 0 and rng.random()<.18:
            continue

        for e in events:
            if rng.random()<probability:
                transitions[q, e] = rng.choice(states)

        if mode == 0 and not any(s == q for s, e in transitions):
            transitions[q, rng.choice(events)] = rng.choice(states)

    return DFA(frozenset(states), '0', frozenset(events), controls, observable, transitions)


def trajectory(pre, u, steps=12):
    controller = Limited_Lookahead_Controller(pre, u)
    rows = []

    for k in range(steps):
        belief = controller.estimate
        result, fresh, fallback = controller.solve()
        validate_policy(pre, result)
        row = {'step':k, 'estimate':sorted(belief), 'seconds':fresh.seconds, 'status':result.status,
             'fresh_status':fresh.status, 'used_certified_continuation':fallback}
        rows.append(row)

        if result.status != 'winning': break

        options = executable_choices(pre, result, belief)
        pattern = result.maximal_patterns[-1]
        choice = next(c for c in options if c.pattern == pattern)
        row['pattern'] = sorted(pattern)

        if not choice.successors:
            row['stop'] = 'no observable event; hidden continuation certified'

            break

        event, _ = choice.successors[k%len(choice.successors)]
        belief = controller.observe(pattern, event)
        row['observation'] = event; row['next_estimate'] = sorted(belief)

    return rows


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--samples', type=int, default=600)
    parser.add_argument('--seed', type=int, default=20261120)
    parser.add_argument('--output', type=Path, default=Path('outputs/certified_yin_benchmark'))
    parser.add_argument('--no-plots', action='store_true')
    args = parser.parse_args(argv)
    out = args.output; out.mkdir(parents=True, exist_ok=True)
    corpus = build_yin_literature_examples()
    paper_rows = []; sweeps = {}; traces = {}

    for e in corpus + (build_small_cycle_example(), build_nested_cycle_deadlock_example()):
        folder = out/e.name; folder.mkdir(exist_ok=True)
        export_plant(e, folder)
        pre = preprocess(e.dfa, max_path_visits=2_000_000)
        baseline = solve_offline(e.dfa)
        validate_policy(pre, baseline)
        sweep = []; selected = None
        started = perf_counter()

        for u in range(1, max(2, len(e.dfa.states))):
            r = solve_limited_lookahead(pre, horizon=u)
            validate_policy(pre, r)
            sweep.append({'u':u, 'status':r.status, 'D':r.decision_count, 'O':r.observation_count,
                          'seconds':r.seconds, 'maximal_patterns':[sorted(p) for p in r.maximal_patterns]})

            if selected is None and r.status != 'inconclusive': selected = u

        calibration = perf_counter()-started
        assert selected is not None
        chosen = max(selected, pre.horizon)
        # selected is minimal decisive at the initial belief; chosen respects
        # the draft threshold. Calibration is experimental, not part of theorem.
        r = solve_limited_lookahead(pre, horizon=chosen)
        assert r.status == baseline.status, (e.name, r.status, baseline.status)
        validate_policy(pre, r)
        row = summary_row(e.name, pre, r, baseline, chosen, calibration)
        row['minimal_decisive_u'] = selected
        row['source'] = e.source_name
        paper_rows.append(row); sweeps[e.name] = sweep
        dump(folder/'preprocessing.json', {'Qd':sorted(pre.deadlocks), 'Qf':sorted(pre.failure),
             'Qe':sorted(pre.safe), 'entries':sorted(pre.entries), 'draft_u':pre.horizon,
             'selected_u':chosen, 'minimal_decisive_u':selected})

        if not args.no_plots: export_bts(pre, r, folder)

        traces[e.name] = trajectory(pre, chosen)
        print(e.name, 'u', pre.horizon, '->', chosen, r.status, flush=True)

    rng = random.Random(args.seed); random_rows = []; budget_exceeded = []

    for i in range(args.samples):
        p = random_plant(rng, i)

        try: pre = preprocess(p, max_path_visits=2_000_000)
        except RuntimeError:
            budget_exceeded.append(i); continue

        baseline = solve_offline(p)
        r = solve_limited_lookahead(pre)
        validate_policy(pre, baseline); validate_policy(pre, r)

        if r.status == 'winning': assert baseline.status == 'winning'

        if r.status == 'losing': assert baseline.status == 'losing'

        full = solve_limited_lookahead(pre, full=True)
        validate_policy(pre, full)
        assert (full.status, set(full.maximal_patterns)) == (baseline.status, set(baseline.maximal_patterns))
        row = summary_row('random_%04d'%i, pre, r, baseline, r.horizon, 0.)
        row['full_certificate_seconds'] = full.seconds
        row['full_certificate_D'] = full.decision_count;row['full_certificate_O'] = full.observation_count
        row['stratum'] = ('live', 'mixed', 'sparse')[i%3]

        if i<30:
            # Allocation peak measured separately, never mix traced timings into
            # the ordinary elapsed-time comparison. Input DFA already exists.
            tracemalloc.start(); solve_offline(p)
            row['offline_peak_python_bytes'] = tracemalloc.get_traced_memory()[1];tracemalloc.stop()
            tracemalloc.start(); mpre = preprocess(p); solve_limited_lookahead(mpre)
            row['pre_plus_online_peak_python_bytes'] = tracemalloc.get_traced_memory()[1];tracemalloc.stop()

        random_rows.append(row)

        if i%100 == 0: print('random', i, flush=True)

    dump(out/'paper_results.json', paper_rows); dump(out/'u_sweeps.json', sweeps)
    dump(out/'trajectories.json', traces); dump(out/'random_results.json', random_rows)
    keys = [k for k in paper_rows[0] if k != 'maximal_patterns']

    with (out/'paper_results.csv').open('w', newline='', encoding='utf-8-sig') as f:
        w = csv.DictWriter(f, fieldnames=keys, extrasaction='ignore');w.writeheader();w.writerows(paper_rows)

    summary = {'seed':args.seed, 'requested_random_samples':args.samples, 'completed_random_samples':len(random_rows),
             'preprocessing_budget_exceeded':budget_exceeded, 'paper_models':len(corpus),
             'project_models':2, 'random_statuses':dict(Counter(r['status'] for r in random_rows)),
             'offline_statuses':dict(Counter(r['offline_status'] for r in random_rows)),
             'machine':platform.platform(), 'python':sys.version,
             'semantics':'deadlock-free only, same count-pruning for both baselines; no result caching',
             'timing':'single fresh solve per random instance; population means, not worst-case guarantees; u sweep excluded'}

    for group in ['all', 'live', 'mixed', 'sparse']:
        rows = [r for r in random_rows if group == 'all' or r['stratum'] == group]

        if not rows:continue

        summary[group] = {'n':len(rows), 'decisive':sum(r['status'] != 'inconclusive' for r in rows)}

        for key in ('pre_seconds', 'online_seconds', 'total_seconds', 'offline_seconds', 'full_certificate_seconds'):
            values = [r[key] for r in rows]
            summary[group][key] = {'mean':statistics.mean(values), 'median':statistics.median(values),
                                 'max':max(values), 'sum':sum(values)}

    originals = {str(p):hashlib.sha256(p.read_bytes()).hexdigest()
               for p in Path('.').rglob('*original*') if p.is_file()
               and p.name != 'original_hashes_after.json'}
    dump(out/'original_hashes_after.json', originals)
    dump(out/'summary.json', summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == '__main__': main()
