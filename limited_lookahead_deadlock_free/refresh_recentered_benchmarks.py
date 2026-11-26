"""Refresh all reviewed model artifacts after the recentered-window change.

python -X utf8 refresh_recentered_benchmarks.py
Uses saved reviewed plants, preserving user model edits and event attributes.
Selects the minimum tested u >= bar_u matching offline root patterns for the
canonical calibrated benchmark; manuscript corpus timing uses its separate
minimum-decisive-u experiment, without offline calibration.
"""

import json
from pathlib import Path
from time import perf_counter

from certified_benchmark import dump, export_bts
from compare_online_offline import load_plant
from des_core.certified_lookahead import preprocess, solve_limited_lookahead, validate_policy
from des_core.closed_loop import build_closed_loop
from des_core.offline_bts import construct_offline_bts
from draw_closed_loops import export_graph


def main():
    root = Path('outputs/expanded_yin_benchmark')
    models = json.loads((root / 'model_results.json').read_text(encoding='utf-8'))
    sweeps = {}

    for index, row in enumerate(models):
        folder = root / row['name']
        plant = load_plant(folder)
        pre = preprocess(plant)
        offline = construct_offline_bts(plant)
        sweep = []
        started = perf_counter()

        for horizon in range(1, max(2, len(plant.states))):
            result = solve_limited_lookahead(pre, horizon=horizon)
            validate_policy(pre, result)
            same = (result.status == offline.status and result.maximal_patterns == offline.maximal_patterns)
            sweep.append(dict(u=horizon, status=result.status, D=result.decision_count,
                              O=result.observation_count, edges=result.edge_count,
                              same_offline_root_patterns=same, seconds=result.seconds,
                              maximal_patterns=[sorted(p) for p in result.maximal_patterns]))

        selected = next(s['u'] for s in sweep if s['u'] >= max(1, pre.lookahead_lower_bound)
                        and s['same_offline_root_patterns'])
        decisive = next(s['u'] for s in sweep if s['status'] != 'inconclusive')
        matching = next(s['u'] for s in sweep if s['same_offline_root_patterns'])
        result = solve_limited_lookahead(pre, horizon=selected)
        row.update(selected_u=selected, minimal_decisive_u=decisive, minimal_matching_u=matching,
                   draft_u=pre.lookahead_lower_bound, calibration_seconds=perf_counter() - started)
        dump(folder / 'preprocessing.json', dict(Qd=sorted(pre.Q_d), Qf=sorted(pre.Q_f),
             Qe=sorted(pre.Q_e), Q_o=sorted(pre.Q_o_tilde), draft_u=pre.lookahead_lower_bound,
             bar_u=pre.lookahead_lower_bound, extended_u=pre.u,
             minimal_decisive_u=decisive, minimal_matching_u=matching, selected_u=selected,
             threshold_targets='Q_f union Q_d', window_semantics='recenter at each complete decision estimate'))
        export_bts(pre, result, folder, draw=True)
        graph = build_closed_loop(pre, result)
        graph.update(name=row['name'], u=selected, window_semantics='observation-recentered')
        dump(folder / 'closed_loop_system_online.json', graph)
        dump(folder / 'supervisor.json', dict(status=graph['status'], initial=graph['controller_initial'],
             states=graph['controller'], observable_transitions=graph['controller_edges'], source='ll_bts.json'))
        export_graph(graph, folder, row['name'], selected, mode='online')
        sweeps[row['name']] = sweep
        print(index + 1, row['name'], 'bar_u', pre.lookahead_lower_bound, 'selected', selected,
              result.status, flush=True)

    dump(root / 'model_results.json', models)
    dump(root / 'u_sweeps.json', sweeps)

    for filename in ('paper_results.json', 'structural_results.json'):
        old = json.loads((root / filename).read_text(encoding='utf-8'))
        by_name = {r['name']: r for r in models}
        dump(root / filename, [by_name[r['name']] for r in old])


if __name__ == '__main__':
    main()
