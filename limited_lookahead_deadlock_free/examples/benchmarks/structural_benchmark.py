"""Calibrate and export the three requested structural examples.

Run after examples/benchmarks/expanded_yin_benchmark.py, then run scripts/reporting/draw_closed_loops.py.
"""

# Allow direct execution from the project working directory.
if __package__ in (None, ""):
    import sys as _sys
    from pathlib import Path as _Path
    _sys.path.insert(0, str(_Path(__file__).resolve().parents[2]))


import json
from collections import Counter
from pathlib import Path
from time import perf_counter

from examples.benchmarks.certified_benchmark import dump, export_plant, export_bts, summary_row, trajectory
from des_core.certified_lookahead import preprocess, solve_offline, solve_limited_lookahead, validate_policy
from examples.structural import build_structural_examples

OUT = Path('outputs/expanded_yin_benchmark')


def render_plant(example, pre, folder):
    from des_core.plot_automaton import render_plant as render

    render(example.dfa, folder, example.name, pre.deadlocks, pre.safe)


def main():
    OUT.mkdir(exist_ok=True, parents=True)
    rows = [];sweeps = {};traces = {}

    for example in build_structural_examples():
        folder = OUT/example.name;folder.mkdir(exist_ok=True)
        export_plant(example, folder)
        pre = preprocess(example.dfa, max_path_visits=2_000_000)
        offline = solve_offline(example.dfa);validate_policy(pre, offline)
        sweep = [];started = perf_counter()

        for u in range(1, max(2, len(example.dfa.states))):
            result = solve_limited_lookahead(pre, horizon=u);validate_policy(pre, result)

            if result.status != 'inconclusive':assert result.status == offline.status

            same = (result.status, set(result.maximal_patterns)) == (offline.status, set(offline.maximal_patterns))
            sweep.append(dict(u=u, status=result.status, D=result.decision_count, O=result.observation_count,
                edges=result.edge_count, seconds=result.seconds, same_offline_root_patterns=same,
                maximal_patterns=[sorted(p) for p in result.maximal_patterns]))

        elapsed = perf_counter()-started
        decisive = next(r['u'] for r in sweep if r['status'] != 'inconclusive')
        matching = next(r['u'] for r in sweep if r['same_offline_root_patterns'])
        selected = next(r['u'] for r in sweep if r['u'] >= pre.horizon and r['same_offline_root_patterns'])
        result = solve_limited_lookahead(pre, horizon=selected);validate_policy(pre, result)
        row = summary_row(example.name, pre, result, offline, selected, elapsed)
        row.update(minimal_decisive_u=decisive, minimal_matching_u=matching,
            source=example.source_name, notes=example.description, group='structural')
        rows.append(row);sweeps[example.name] = sweep;traces[example.name] = trajectory(pre, selected, steps=20)
        dump(folder/'preprocessing.json', dict(Qd=sorted(pre.deadlocks), Qf=sorted(pre.failure),
            Qe=sorted(pre.safe), draft_u=pre.horizon, minimal_decisive_u=decisive,
            minimal_matching_u=matching, selected_u=selected))
        export_bts(pre, result, folder)
        baseline = folder/'offline';baseline.mkdir(exist_ok=True)
        export_bts(pre, offline, baseline, draw=offline.decision_count+offline.observation_count <= 65, structure='BTS')
        render_plant(example, pre, folder)
        print(example.name, 'u=', selected, result.status, 'D/O', result.decision_count, result.observation_count, flush=True)

    dump(OUT/'structural_results.json', rows)
    dump(OUT/'structural_u_sweeps.json', sweeps)
    dump(OUT/'structural_trajectories.json', traces)
    paper = json.loads((OUT/'paper_results.json').read_text(encoding='utf-8'))
    dump(OUT/'model_results.json', paper+rows)
    dump(OUT/'model_summary.json', dict(literature_models=len(paper), structural_models=len(rows),
        total_models=len(paper)+len(rows), statuses=dict(Counter(r['status'] for r in paper+rows))))


if __name__ == '__main__':main()
