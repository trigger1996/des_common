"""Reproduce the manuscript case studies outside the legacy result directories.

python -X utf8 examples/paper/manuscript_case_studies.py --part all
The random input DFAs were generated with seed 20261121. Timings include
fresh structural analysis and every initial positive-horizon trial.
"""

# Allow direct execution from the project working directory.
if __package__ in (None, ""):
    import sys as _sys
    from pathlib import Path as _Path
    _sys.path.insert(0, str(_Path(__file__).resolve().parents[2]))


import argparse
from collections import deque
import gc
import hashlib
import json
import os
from pathlib import Path
import platform
import random
import shutil
import statistics
import subprocess
import sys
from time import perf_counter
import tracemalloc

from examples.comparisons.compare_online_offline import load_plant
from des_core.asynchronous_product import ImplicitProductDFA
from des_core.automata import DFA
from des_core.certified_lookahead import (
    Limited_Lookahead_Controller, preprocess, solve_limited_lookahead,
    solve_minimum_lookahead, solve_offline, validate_policy,
)
from des_core.closed_loop import build_closed_loop
from des_core.offline_bts import BTSBudgetExceeded, construct_offline_bts, traditional_ur_nx
from examples.non_deadlock import build_small_cycle_example
from examples.paper.paper_example_models import paper_small_figure
from examples.large_scale.revised_large_products import validate_product
from examples.paper.revision_experiments import measure, summarize


ROOT = Path('outputs/expanded_yin_benchmark')
OUT = Path('outputs/revision_materials/case_studies_20261122')
SEED = 20261121


def dump(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')


def plant_record(plant):
    return dict(states=sorted(plant.states), initial=plant.initial,
                events=sorted(plant.events), observable=sorted(plant.observable),
                controllable=sorted(plant.controllable),
                transitions=[[q, e, t] for (q, e), t in sorted(plant.transitions.items())])


def restore_plant(record):
    return DFA(frozenset(record['states']), record['initial'],
               frozenset(record['events']), frozenset(record['controllable']),
               frozenset(record['observable']),
               {(q, e): t for q, e, t in record['transitions']})


def online(plant):
    started = perf_counter()
    pre = preprocess(plant, max_path_visits=2_000_000)
    result = solve_minimum_lookahead(pre, timeout_seconds=10.)
    patterns = result.maximal_patterns
    attempts = dict(first_u=max(1, pre.u_f), selected_u=result.horizon,
                    constructions=result.horizon - max(1, pre.u_f) + 1)

    return result, patterns, perf_counter() - started, pre, attempts


def plot_small_ll_bts(result, target, pre):
    """Render stored (q_hat, x_hat) states without selecting a representative."""

    from des_core.bipartite_export import graph_record, render_record, write_dot
    from examples.benchmarks.certified_benchmark import export_bts

    trace_folder = target.parent if (target.parent / 'll_bts.json').exists() else target.parent / f'u{result.horizon}'

    if not (trace_folder / 'construction_steps.jsonl').exists():
        export_bts(pre, result, trace_folder, draw=True)

    record, _, _ = graph_record(pre, result, 'LL-BTS')
    render_record(record, target, retained=True)
    render_record(record, target.with_suffix('.png'), retained=True)
    write_dot(record, target.with_suffix('.dot'), retained=True)


def plot_small_ll_bts_fixed_window_archive(result, target):
    import matplotlib

    matplotlib.use('Agg')
    import matplotlib.pyplot as plt

    plt.rcParams['pdf.fonttype'] = 42
    estimates = [result.initial] + sorted(
        (x for x in result.policy if x != result.initial), key=lambda x: sorted(x))
    assert len(estimates) == 2
    fig, ax = plt.subplots(figsize=(3.5, 3.1))
    positions = {estimates[0]: (0, 3.3), estimates[1]: (0, 1.4)}

    def states(values):
        return r'\{' + ','.join('q_{' + q.split('_')[-1] + '}' for q in sorted(values)) + r'\}'

    for estimate in estimates:
        x, y = positions[estimate]
        q = next(iter(estimate))
        ax.text(x, y, '$(' + 'q_{' + q.split('_')[-1] + '},' + states(estimate) + ')$',
                ha='center', va='center', fontsize=9,
                bbox=dict(boxstyle='round,pad=0.28', facecolor='#e7f0fa', edgecolor='#305d8a'))
        options = sorted(result.policy[estimate], key=lambda c: (len(c.pattern), sorted(c.pattern)))
        assert len(options) == 2

        for index, choice in enumerate(options):
            xx, yy = (-1.05 if index == 0 else 1.05), y - 0.85
            events = ','.join('o_2' if e == 'o2' else e for e in sorted(choice.pattern))
            label = '$x=' + states(choice.closure) + '$\n' + r'$\gamma_c=\{' + events + r'\}$'
            ax.text(xx, yy, label, ha='center', va='center', fontsize=8,
                    bbox=dict(boxstyle='round,pad=0.25', facecolor='#fff1cf', edgecolor='#8a6927'))
            ax.annotate('', xy=(xx, yy + 0.19), xytext=(x, y - 0.13),
                        arrowprops=dict(arrowstyle='->', lw=0.9))

            for event, successor in choice.successors:
                tx, ty = positions[successor]
                ax.annotate('', xy=(tx, ty + 0.14), xytext=(xx, yy - 0.2),
                            arrowprops=dict(arrowstyle='->', lw=0.9))
                ax.text((xx + tx) / 2, (yy + ty) / 2 - 0.05,
                        '$o_1$' if event == 'o1' else event, fontsize=8, ha='center')

    ax.annotate('', xy=(0, 3.47), xytext=(0, 3.78), arrowprops=dict(arrowstyle='->', lw=0.9))
    ax.set_xlim(-2, 2)
    ax.set_ylim(-0.05, 3.9)
    ax.axis('off')
    fig.tight_layout(pad=0.2)
    fig.savefig(target, bbox_inches='tight')
    plt.close(fig)


def plot_paper_dfa(example, target):
    import matplotlib

    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.patches import Circle, FancyArrowPatch
    from math import hypot

    plant = example.dfa
    pre = preprocess(plant)
    pos = example.layout
    fig, ax = plt.subplots(figsize=(3.7, 2.1))
    labels = []
    routes = []

    for (q, event), target_state in sorted(plant.transitions.items()):
        x, y = pos[q]
        xx, yy = pos[target_state]
        dx, dy = xx - x, yy - y
        reciprocal = any(t == q for _, t in plant.enabled(target_state))
        preferred = .22 if reciprocal else 0.

        def score(rad, label_t):
            cx, cy = (x + xx) / 2 + rad * dy, (y + yy) / 2 - rad * dx
            clearance = min((hypot((1 - t) ** 2 * x + 2 * (1 - t) * t * cx + t * t * xx - px,
                                   (1 - t) ** 2 * y + 2 * (1 - t) * t * cy + t * t * yy - py)
                for state, (px, py) in pos.items() if state not in (q, target_state)
                for t in (i / 30 for i in range(1, 30))), default=10.)
            lx = (1 - label_t) ** 2 * x + 2 * (1 - label_t) * label_t * cx + label_t ** 2 * xx
            ly = (1 - label_t) ** 2 * y + 2 * (1 - label_t) * label_t * cy + label_t ** 2 * yy
            label_gap = min((hypot(lx - px, ly - py) for px, py in labels), default=10.)
            node_gap = min(hypot(lx - px, ly - py) for px, py in pos.values())

            return (100 * max(0., .55 - clearance) + 30 * max(0., .8 - label_gap)
                    + 100 * max(0., .75 - node_gap) + abs(rad - preferred) + abs(label_t - .5) * .3)

        rad, label_t = min(((r, t) for r in (preferred, 0., .22, -.22, .4, -.4, .65, -.65, 1., -1.)
                           for t in (.3, .4, .5, .6, .7)), key=lambda pair: score(*pair))
        ax.add_patch(FancyArrowPatch((x, y), (xx, yy), connectionstyle=f'arc3,rad={rad}',
            arrowstyle='-|>', shrinkA=6.8, shrinkB=6.8, mutation_scale=7., lw=.65, color='#333333', zorder=1))
        cx, cy = (x + xx) / 2 + rad * dy, (y + yy) / 2 - rad * dx
        lx = (1 - label_t) ** 2 * x + 2 * (1 - label_t) * label_t * cx + label_t ** 2 * xx
        ly = (1 - label_t) ** 2 * y + 2 * (1 - label_t) * label_t * cy + label_t ** 2 * yy
        labels.append((lx, ly))
        event_label = r'$o_1$' if event == 'o1' else r'$o_2$' if event == 'o2' else '$' + event + '$'
        ax.text(lx, ly, event_label, ha='center', va='center', fontsize=7.6,
                bbox=dict(facecolor='white', edgecolor='none', pad=.2), zorder=5)
        routes.append(dict(source=q, event=event, target=target_state,
                           curvature=rad, label_position=[lx, ly]))

    for q, (x, y) in pos.items():
        color = '#f5b6b0' if q in pre.Q_d else '#ffe3a3' if q in pre.Q_f else 'white'
        ax.add_patch(Circle((x, y), .42, facecolor=color, edgecolor='#333333', lw=.7, zorder=3))
        ax.text(x, y, '$q_{' + q.split('_')[-1] + '}$', ha='center', va='center', fontsize=8.2, zorder=4)

    initial_x, initial_y = pos[plant.initial]
    ax.annotate('', xy=(initial_x - .42, initial_y), xytext=(initial_x - 1.3, initial_y),
                arrowprops=dict(arrowstyle='->', lw=.7))
    ax.set_xlim(min(x for x, _ in pos.values()) - 1.5, max(x for x, _ in pos.values()) + .6)
    ax.set_ylim(min(y for _, y in pos.values()) - .9, max(y for _, y in pos.values()) + .9)
    ax.set_aspect('equal')
    ax.axis('off')
    fig.tight_layout(pad=.15)
    fig.savefig(target, bbox_inches='tight')
    fig.savefig(target.with_suffix('.png'), bbox_inches='tight', dpi=220)
    plt.close(fig)
    dump(target.with_suffix('.routes.json'), routes)


def small_case():
    example = paper_small_figure()
    plant = example.dfa
    (OUT / 'small').mkdir(parents=True, exist_ok=True)
    generated_figure = OUT / 'small/dfa_r1.pdf'
    plot_paper_dfa(example, generated_figure)
    figure = Path('[paper]Limited Lookadhead Deadlock-free/Figs/dfa_example_2_r1.pdf')
    shutil.copy2(generated_figure, figure)
    pre = preprocess(plant)
    baseline = solve_offline(plant)
    sweep = []
    results = {}

    for u in range(1, len(plant.states)):
        result = solve_limited_lookahead(pre, horizon=u)
        validate_policy(pre, result)
        sweep.append(dict(u=u, status=result.status,
                          controllable_patterns=[sorted(p) for p in result.maximal_patterns],
                          same_offline_patterns=set(result.maximal_patterns) == set(baseline.maximal_patterns)))
        results[u] = result

    rows = []

    for u in sorted({4, 5, max(1, pre.lookahead_lower_bound)}):
        result = results[u]
        graph = build_closed_loop(pre, result)
        assert graph['status'] == 'winning'
        assert all(any(e['source'] == n['id'] for e in graph['edges']) for n in graph['nodes'])
        dump(OUT / 'small' / ('closed_loop_u' + str(u) + '.json'), graph)
        from des_core.bipartite_export import graph_record

        record, _, _ = graph_record(pre, result, 'LL-BTS')
        dump(OUT / 'small' / ('ll_bts_u' + str(u) + '.json'), record)
        rows.append(dict(u=u, D=result.decision_count, O=result.observation_count,
                         retained_D=len(result.decision_policy),
                         retained_O=len({(c.closure, c.pattern) for v in result.policy.values() for c in v}),
                         closed_states=len(graph['nodes']), closed_edges=len(graph['edges'])))

    controller = Limited_Lookahead_Controller(pre, minimum_horizon=True)
    proof, _, _ = controller.solve()
    assert controller.horizon == max(1, pre.lookahead_lower_bound)
    assert proof.maximal_patterns == results[controller.horizon].maximal_patterns
    pattern = proof.maximal_patterns[-1]
    controller.observe(pattern, 'o1')
    proof, _, fallback = controller.solve()
    validate_policy(pre, proof)
    result = dict(plant=plant_record(plant), figure_sha256=hashlib.sha256(figure.read_bytes()).hexdigest(),
                  figure_file=figure.name,
                  model_revision='Reference page 9: only q14-a-q15-b-q16 added, 2026-11-23',
                  structural_analysis={k: sorted(getattr(pre, k)) for k in ('Q_d', 'Q_f', 'Q_e')},
                  Q_o=sorted(pre.Q_o_tilde), bar_u=pre.u_f,
                  minimum_decisive_u=next(x['u'] for x in sweep if x['status'] != 'inconclusive'),
                  minimum_matching_u=next(x['u'] for x in sweep if x['same_offline_patterns']),
                  cases=rows, sweep=sweep,
                  observed_estimate=sorted(controller.estimate),
                  observation_fallback=fallback,
                  offline=dict(D=baseline.decision_count, O=baseline.observation_count,
                               patterns=[sorted(p) for p in baseline.maximal_patterns]))
    dump(OUT / 'small' / 'result.json', result)
    plot_small_ll_bts(results[max(1, pre.lookahead_lower_bound)], OUT / 'small' / 'll_bts_verified.pdf', pre)

    for horizon in (4, 5):
        diagram = OUT / 'small' / f'll_bts_r1_u{horizon}.pdf'
        plot_small_ll_bts(results[horizon], diagram, pre)
        shutil.copy2(diagram, Path('[paper]Limited Lookadhead Deadlock-free/Figs') / diagram.name)

    print('small verified: recentered windows; closed-loop states', [r['closed_states'] for r in rows], flush=True)


def corpus_cases():
    curated = []
    inputs = []
    models = json.loads((ROOT / 'model_results.json').read_text(encoding='utf-8'))

    for index, model in enumerate(models):
        plant = load_plant(ROOT / model['name'])
        inputs.append(dict(name=model['name'], **plant_record(plant)))
        row, pre, result = measure(plant, lambda: online(plant), 11, index)
        graph = build_closed_loop(pre, result)
        row.update(name=model['name'], bar_u=pre.u_f,
                   closed_loop_states=len(graph['nodes']), closed_loop_edges=len(graph['edges']))
        curated.append(row)

        if (index + 1) % 15 == 0:
            print('curated', index + 1, '/', len(models), flush=True)

    dump(OUT / 'curated_inputs.json', inputs)
    dump(OUT / 'curated_results.json', curated)
    source = ROOT / 'randomized_comparison' / 'plants.json'
    plants = json.loads(source.read_text(encoding='utf-8'))
    random_rows = []

    for index, record in enumerate(plants):
        plant = restore_plant(record)
        row, _, _ = measure(plant, lambda: online(plant), 5, index)
        row.update(index=record['index'], stratum=record['stratum'])
        random_rows.append(row)

        if (index + 1) % 100 == 0:
            dump(OUT / 'random_results_partial.json', random_rows)
            print('random', index + 1, '/', len(plants), flush=True)

    dump(OUT / 'random_inputs.json', plants)
    dump(OUT / 'random_results.json', random_rows)
    groups = []

    for label, rows in (('Curated', curated), ('Random', random_rows)):
        for status in ('winning', 'losing'):
            selected = [r for r in rows if r['status'] == status]
            groups.append(dict(group=label, status=status, **summarize(selected)))

    groups.append(dict(group='All', status='mixed', **summarize(curated + random_rows)))
    dump(OUT / 'summary.json', dict(curated=summarize(curated), random=summarize(random_rows),
         all=summarize(curated + random_rows), groups=groups, seed=SEED,
         random_input_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
         timing='Fresh structural analysis + all initial positive-horizon trials + root pattern filtering. '
                'Common warm DFA/index, validation, rendering and serialization excluded.',
         space='Separate tracemalloc peaks for each side, including LL structural analysis and retries; '
               'common input/index excluded. Node counts describe the final constructed graph.',
         aggregation='Mean per instance over 11 curated / 5 random repeats, then equal weight per instance.'))
    print('corpus complete:', len(curated), '+', len(random_rows), flush=True)


def component_computation(plant, copies):
    started = perf_counter()
    pre = preprocess(plant, max_path_visits=2_000_000)
    result = solve_minimum_lookahead(pre, timeout_seconds=10.)
    assert result.status == 'winning'
    graph = build_closed_loop(pre, result)
    validate_policy(pre, result)
    assert all(any(e['source'] == n['id'] for e in graph['edges']) for n in graph['nodes'])
    descriptor = dict(copies=copies, component_nodes=result.decision_count + result.observation_count,
                      initial=[graph['controller_initial']] * copies,
                      component_memories=graph['controller'], component_edges=graph['controller_edges'])

    return pre, result, graph, descriptor, perf_counter() - started


def sampled_root_time(plant, copies, seed, samples=256):
    product = ImplicitProductDFA(plant, copies)
    controls = sorted(product.controllable)
    count = 2 ** len(controls)
    rng = random.Random(seed)
    masks = rng.sample(range(count), min(samples, count))
    times = []
    sizes = []

    for mask in masks:
        pattern = frozenset(e for i, e in enumerate(controls) if mask & (1 << i))
        traditional_ur_nx(product, frozenset({product.initial}), pattern)
        started = perf_counter()
        choice = traditional_ur_nx(product, frozenset({product.initial}), pattern)
        gamma = pattern | product.uncontrollable
        live = all(any(e in gamma for e, _ in product.enabled(q)) for q in choice.closure)
        times.append(perf_counter() - started)
        sizes.append(dict(UR=len(choice.closure), NX=sum(len(x) for _, x in choice.successors), live=live))

    return dict(patterns=count, required_root_nodes=count + 1, sample_count=len(times),
                seed=seed, seconds_per_pattern=times,
                mean_seconds_per_pattern=statistics.mean(times),
                estimated_root_seconds=count * statistics.mean(times), sizes=sizes,
                scope='Target-size product root UR/NX and liveness checks only, using uniform sampled '
                      'control patterns and warmed transition lookup; no UR/NX result cache. '
                      'No complete global offline solve or root maximal-pattern filtering was timed.')


def bounded_offline_attempt(plant, copies):
    product = ImplicitProductDFA(plant, copies)

    try:
        result = construct_offline_bts(product, max_choices=256,
                                       max_decisions=20000, timeout_seconds=2.)
    except BTSBudgetExceeded as error:
        record = dict(error.metrics)
        record.update(complete=False, status='budget_exceeded', reason=str(error))

        return record

    return dict(complete=True, status=result.status, seconds=result.seconds)


def large_cases_compositional_archive():
    cases = [('Cycle6', build_small_cycle_example().dfa, 8),
             ('Auto15', load_plant(ROOT / '21AutomaticaOptimal_fig_2'), 6),
             ('Range11', load_plant(ROOT / '18TACrange_fig_3a'), 7)]
    rows = []

    for index, (name, plant, copies) in enumerate(cases):
        reachable, work = {plant.initial}, deque([plant.initial])

        while work:
            for _, target in plant.enabled(work.popleft()):
                if target not in reachable:
                    reachable.add(target)
                    work.append(target)

        assert reachable == plant.states
        samples = []

        for _ in range(51):
            pre, result, graph, descriptor, elapsed = component_computation(plant, copies)
            samples.append(elapsed)

        gc.collect()
        tracemalloc.start()
        component_computation(plant, copies)
        peak = tracemalloc.get_traced_memory()[1]
        tracemalloc.stop()
        validation = validate_product(graph, copies)
        forecast = sampled_root_time(plant, copies, SEED + index)
        offline_attempt = bounded_offline_attempt(plant, copies)
        row = dict(name=name, copies=copies, component=plant_record(plant),
                   source_model={'Cycle6': 'examples.non_deadlock.build_small_cycle_example',
                                 'Auto15': '21AutomaticaOptimal_fig_2',
                                 'Range11': '18TACrange_fig_3a'}[name],
                   product_states=len(plant.states) ** copies,
                   product_edges=copies * len(plant.transitions) * len(plant.states) ** (copies - 1),
                   status='winning', component_u=result.horizon,
                   LL_D=result.decision_count, LL_O=result.observation_count,
                   stored_LL_nodes=result.decision_count + result.observation_count,
                   closed_loop_states=len(graph['nodes']) ** copies,
                   component_closed_loop=graph, supervisor=descriptor,
                   online_samples=samples, online_mean=statistics.mean(samples),
                   online_median=statistics.median(samples), online_peak=peak,
                   small_explicit_product_checks=validation, forecast=forecast,
                   bounded_offline_attempt=offline_attempt,
                   method='LL-BTS synthesis and full closed-loop verification on one shared component, '
                          'followed by exact asynchronous composition of independent indexed controllers. '
                          'No explicit global LL-BTS/BTS construction.',
                   offline_complete=False)
        rows.append(row)
        dump(OUT / 'large' / (name + '.json'), row)
        print('large', name, 'states', row['product_states'], 'LL nodes', row['stored_LL_nodes'],
              'ms', row['online_mean'] * 1000, 'estimated root s', forecast['estimated_root_seconds'], flush=True)

    dump(OUT / 'large_results.json', rows)


def large_cases():
    """Current global product and million-state tests; no component graph reuse."""

    subprocess.run([sys.executable, '-X', 'utf8', str(Path('examples/large_scale/nonzero_lookahead_cases.py')),
                    '--run', '--output', str((OUT / 'large').resolve())], check=True)


def manifest():
    sources = ['examples/paper/manuscript_case_studies.py', 'examples/paper/revision_experiments.py', 'examples/paper/paper_example_models.py',
               'des_core/certified_lookahead.py', 'des_core/offline_bts.py', 'des_core/closed_loop.py',
               'examples/large_scale/nonzero_lookahead_cases.py', 'des_core/bipartite_graph.py',
               'des_core/bipartite_export.py', 'des_core/resource_monitor.py']
    figure = Path('[paper]Limited Lookadhead Deadlock-free/Figs/dfa_example_2_r1.pdf')
    commit = subprocess.run(['git', '-c', 'safe.directory=' + str(Path('..').resolve()),
                             'rev-parse', 'HEAD'], capture_output=True, text=True)
    dump(OUT / 'manifest.json', dict(seed=SEED, python=sys.version, platform=platform.platform(),
         processor=platform.processor(), hardware_threads=os.cpu_count(),
         git_base=commit.stdout.strip(),
         paper_figure_file='Figs/dfa_example_2_r1.pdf',
         paper_figure_sha256=hashlib.sha256(figure.read_bytes()).hexdigest() if figure.exists() else None,
         figure_note='Optional generated figure; model inputs are independently hashed.',
         archived_paper_figure_sha256=hashlib.sha256(Path(
             '[paper]Limited Lookadhead Deadlock-free/Figs/dfa_example_2.pdf').read_bytes()).hexdigest(),
         repository='https://github.com/trigger1996/des_common',
         script='limited_lookahead_deadlock_free/examples/paper/manuscript_case_studies.py',
         source_sha256={f: hashlib.sha256(Path(f).read_bytes()).hexdigest() for f in sources}))


def main():
    global OUT
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--part', choices=('all', 'small', 'corpus', 'large'), default='all')
    parser.add_argument('--output', type=Path, default=OUT)
    args = parser.parse_args()
    OUT = args.output
    OUT.mkdir(parents=True, exist_ok=True)

    if args.part in ('all', 'small'):
        small_case()

    if args.part in ('all', 'corpus'):
        corpus_cases()

    if args.part in ('all', 'large'):
        large_cases()

    manifest()


if __name__ == '__main__':
    main()
