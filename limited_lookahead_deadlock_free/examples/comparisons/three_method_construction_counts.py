"""Untimed construction/pruning replays for the 45 three-method experiments.

No solver code changes. A return hook reads the classic projection that the
actual independent solver just computed, rather than rerunning its recurrence
in a separate invented counter. Instrumentation is excluded from timing/RAM.
"""

# Allow direct execution from the project working directory.
if __package__ in (None, ""):
    import sys as _sys
    from pathlib import Path as _Path
    _sys.path.insert(0, str(_Path(__file__).resolve().parents[2]))


import argparse
from collections import deque
import hashlib
import json
from pathlib import Path
import sys

from des_core.bipartite_export import graph_record
from des_core.certified_lookahead import preprocess, solve_limited_lookahead
from des_core.classic_llp_1992 import solve_classic_llp
from des_core.warehouse_2018 import solve_warehouse, synchronous_product
from examples.comparisons.three_method_comparison import (ROOT, DEFAULT, LABELS, components_for,
                                     legal_function, input_hash, dump)


def classic_structure(plant, horizon, legal, marked):
    captured = {}
    previous = sys.getprofile()

    def capture(frame, event, arg):
        if event == 'return' and frame.f_code is solve_classic_llp.__code__:
            for name in ('physical', 'transitions', 'good'):
                captured[name] = frame.f_locals[name]

    sys.setprofile(capture)

    try:
        result = solve_classic_llp(plant, horizon=horizon, legal=legal, marked=marked)
    finally:
        sys.setprofile(previous)

    good = captured['good']
    transitions = captured['transitions']
    retained = set()
    queue = deque([0] if good[0] else [])

    while queue:
        source = queue.popleft()

        if source in retained:
            continue

        retained.add(source)
        queue.extend(target for _, target in transitions[source] if good[target])

    retained_transitions = sum(target in retained for source in retained for _, target in transitions[source])

    return result, dict(raw_states=result.stored_states, raw_transitions=result.stored_transitions,
        retained_states=len(retained), retained_transitions=retained_transitions,
        locally_admissible_states=sum(good), patterns_tested=None,
        raw_control_branches=sum(event in plant.controllable for outcomes in transitions for event, _ in outcomes),
        retained_control_branches=sum(event in plant.controllable and target in retained
                                      for source in retained for event, target in transitions[source]),
        counter_meaning='Projection transitions and controllable-event branches, not enumerated control-pattern combinations.')


def collect(row):
    method = row['method_key']
    components = components_for(row['case'])
    legal = legal_function(components)
    assert input_hash(components) == row['input_sha256']

    if method == 'cai2018':
        result = solve_warehouse(components, horizon=row['horizon'], legal=legal, interpretation='equations')
        counts = dict(raw_states=len(result.window.states), raw_transitions=result.window_transitions,
            retained_states=len(result.retained_states), retained_transitions=result.retained_transitions,
            locally_admissible_states=None, patterns_tested=None,
            raw_control_branches=sum(event in result.window.controllable for _, event in result.window.transitions),
            retained_control_branches=sum(event in result.window.controllable
                and q in result.retained_states and target in result.retained_states
                for (q, event), target in result.window.transitions.items()),
            counter_meaning='Physical-window transitions and controllable-event branches, not enumerated control-pattern combinations.')
    else:
        plant, marked = synchronous_product(components)

        if method == 'llp1992':
            result, counts = classic_structure(plant, row['horizon'], legal, marked)
        else:
            pre = preprocess(plant)
            result = solve_limited_lookahead(pre, horizon=row['horizon'])
            record, _, _ = graph_record(pre, result, 'LL-BTS')
            decisions = {item['id'] for item in record['D']}
            retained_d = sum(item['retained'] for item in record['D'])
            retained_o = sum(item['retained'] for item in record['O'])
            counts = dict(raw_states=len(record['D']) + len(record['O']), raw_transitions=len(record['edges']),
                raw_D=len(record['D']), raw_O=len(record['O']), retained_D=retained_d, retained_O=retained_o,
                retained_states=retained_d + retained_o, retained_transitions=len(record['policy_edges']),
                locally_admissible_states=None, patterns_tested=result.patterns_tested,
                raw_control_branches=sum(edge[0] in decisions for edge in record['edges']),
                retained_control_branches=sum(edge[0] in decisions for edge in record['policy_edges']),
                counter_meaning='Control branches are D-to-O control-pattern transitions; actual numerical pattern checks are separate.')

    counts['removed_states'] = counts['raw_states'] - counts['retained_states']
    counts['removed_transitions'] = counts['raw_transitions'] - counts['retained_transitions']
    counts['removed_control_branches'] = counts['raw_control_branches'] - counts['retained_control_branches']
    assert counts['raw_states'] == row['constructed_states']
    assert counts['raw_transitions'] == row['constructed_transitions']
    assert all(counts[key] >= 0 for key in ('removed_states', 'removed_transitions', 'removed_control_branches'))

    return dict(case=row['case'], horizon=row['horizon'], method=LABELS[method], method_key=method,
                input_sha256=row['input_sha256'], **counts,
                scope='Untimed independent replay; pruning counts include retained-reachability cleanup. '
                      'These are the initial finite construction counts, not the exhaustive receding closed-loop size.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=DEFAULT / 'construction_counts')
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    rows = json.loads((DEFAULT / 'summary.json').read_text(encoding='utf-8'))
    names = [Path(__file__), ROOT / 'des_core/classic_llp_1992.py', ROOT / 'des_core/warehouse_2018.py',
             ROOT / 'des_core/certified_lookahead.py', ROOT / 'des_core/bipartite_export.py']
    hashes = {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest() for path in names}
    dump(args.output / 'manifest.json', dict(source_sha256=hashes, configurations=len(rows),
        scope='Additional untimed instrumentation. Existing timings and allocation profiles unchanged.'))
    counts = [collect(row) for row in rows]
    dump(args.output / 'summary.json', counts)
    assert all(hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == digest for name, digest in hashes.items())
    print('Verified initial construction/pruning counters:', len(counts), flush=True)


if __name__ == '__main__':
    main()
