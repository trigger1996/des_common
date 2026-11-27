"""Compare Q_f and Q_f union Q_d reverse-DFS thresholds on the paper DFA.

python -X utf8 examples/comparisons/compare_deadlock_target_bound.py
This experiment leaves production preprocessing and manuscript files unchanged.
"""

# Allow direct execution from the project working directory.
if __package__ in (None, ""):
    import sys as _sys
    from pathlib import Path as _Path
    _sys.path.insert(0, str(_Path(__file__).resolve().parents[2]))


import json
from pathlib import Path

from des_core.automata import DFA
from des_core.certified_lookahead import preprocess, solve_limited_lookahead, validate_policy
from des_core.closed_loop import build_closed_loop
from des_core.offline_bts import construct_offline_bts
from examples.paper.paper_example_models import paper_small_figure_original


def reverse_bound(plant, targets):
    predecessors = {q: [] for q in plant.states}
    entries = {plant.initial}

    for (source, event), target in sorted(plant.transitions.items()):
        if event in plant.observable:
            entries.add(target)
        else:
            predecessors[target].append((source, event))

    bound, longest_path, eligible_entries = 0, [], set()

    def reverse_dfs(q, current_path, reverse_transitions):
        nonlocal bound, longest_path

        if q in entries:
            eligible_entries.add(q)

            if len(reverse_transitions) > bound:
                bound = len(reverse_transitions)
                longest_path = list(reversed(reverse_transitions))

        for source, event in predecessors[q]:
            if source not in current_path:
                reverse_dfs(source, current_path | {source},
                            reverse_transitions + [(source, event, q)])

    for target in sorted(targets):
        reverse_dfs(target, {target}, [])

    return dict(bound=bound, longest_path=longest_path, Q_o=sorted(eligible_entries))


def describe(result, pre):
    record = dict(status=result.status, root_patterns=[sorted(p) for p in result.maximal_patterns])

    if result.status == 'winning':
        record['policy_validation'] = validate_policy(pre, result)
        graph = build_closed_loop(pre, result)
        assert all(any(t['source'] == q['id'] for t in graph['edges']) for q in graph['nodes'])
        record.update(closed_states=len(graph['nodes']), closed_transitions=len(graph['edges']),
                      deadlock_free=True)

    return record


def main():
    base = paper_small_figure_original().dfa
    records = []

    for length in (0, 1, 2, 3, 4, 6):
        transitions = dict(base.transitions)
        added = [f'q_{15 + i}' for i in range(length)]

        if added:
            transitions['q_7', 'b'] = added[0]

            for source, target in zip(added, added[1:] + ['q_12']):
                transitions[source, 'u'] = target

        plant = DFA(base.states | frozenset(added), base.initial, base.events,
                    base.controllable, base.observable, transitions)
        pre = preprocess(plant)
        old = reverse_bound(plant, pre.Q_f)
        extended = reverse_bound(plant, pre.Q_f | pre.Q_d)
        assert extended['bound'] == pre.lookahead_lower_bound
        offline = construct_offline_bts(plant)
        checked = {}

        for horizon in range(1, max(6, extended['bound']) + 1):
            result = solve_limited_lookahead(pre, horizon=horizon)
            checked[horizon] = describe(result, pre)
            checked[horizon]['same_offline_root_patterns'] = result.maximal_patterns == offline.maximal_patterns

        at_bound = checked[max(1, extended['bound'])]
        winning = [u for u, r in checked.items() if r['status'] == 'winning']
        matching = [u for u, r in checked.items() if r['status'] == 'winning' and r['same_offline_root_patterns']]
        row = dict(added_states=length, Q_d=sorted(pre.Q_d), Q_f=sorted(pre.Q_f),
                   Q_f_only=old, Q_f_union_Q_d=extended,
                   at_extended_bound=at_bound, minimum_winning_u=min(winning) if winning else None,
                   minimum_matching_u=min(matching) if matching else None,
                   offline=describe(offline, pre), tested_horizons=checked)
        records.append(row)
        print(f"chain={length}: old_bound={old['bound']}, new_bound={extended['bound']}, "
              f"at_new_bound={at_bound['status']}, min_winning={row['minimum_winning_u']}, "
              f"min_matching={row['minimum_matching_u']}", flush=True)
        print('  longest unobservable path:', extended['longest_path'], flush=True)

    target = Path('outputs/revision_materials/small_failure_chain_20261123/deadlock_target_bound_comparison.json')
    target.write_text(json.dumps(dict(
        targets='Q_f union Q_d; entries include q0 and all observable-event targets; '
                'Q_o is recomputed for the expanded target set.',
        method='Exact reverse DFS over unobservable simple paths; explicit fixed-window solves, '
               'offline comparison, policy validation and closed-loop liveness checks.',
        cases=records), ensure_ascii=False, indent=2), encoding='utf-8')
    print('Saved:', target)


if __name__ == '__main__':
    main()
