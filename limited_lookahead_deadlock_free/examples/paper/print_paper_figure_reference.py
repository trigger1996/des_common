"""Print the current paper DFA and retained LL-BTS as state/event triples."""

# Allow direct execution from the project working directory.
if __package__ in (None, ""):
    import sys as _sys
    from pathlib import Path as _Path
    _sys.path.insert(0, str(_Path(__file__).resolve().parents[2]))


import argparse
from pathlib import Path

from des_core.certified_lookahead import preprocess, solve_limited_lookahead, validate_policy
from des_core.bipartite_export import graph_record
from des_core.offline_bts import construct_offline_bts
from examples.paper.paper_example_models import paper_small_figure


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--u', type=int, default=5)
    parser.add_argument('--full', action='store_true')
    args = parser.parse_args()
    plant = paper_small_figure().dfa
    pre = preprocess(plant)
    result = construct_offline_bts(plant) if args.full else solve_limited_lookahead(pre, horizon=args.u)
    validate_policy(pre, result)
    order = lambda states: sorted(states, key=lambda q: int(q.split('_')[-1]))
    show = lambda states: '{' + ','.join(q.replace('_', '') for q in order(states)) + '}'
    lines = [f'当前 DFA：{len(plant.states)} 个状态、{len(plant.transitions)} 条转移；事件属性保持原稿。',
             'Sigma_c={a,b,o2}; Sigma_o={o1,o2}', 'bar_u=' + str(pre.lookahead_lower_bound), '']

    for q in order(plant.states):
        transitions = '; '.join(f'{e} -> {t.replace("_", "")}' for e, t in plant.enabled(q))
        lines.append(q.replace('_', '') + ': ' + (transitions or '无后继状态'))

    structure = 'BTS' if args.full else 'LL-BTS'
    record, _, _ = graph_record(pre, result, structure)
    decisions = [state for state in record['D'] if state['retained']]
    observations = [state for state in record['O'] if state['retained']]
    lines += ['', f'剪枝后 {structure}，实际 u={result.horizon}；gamma_c 仅列可控事件。']
    lines += [f"{state['id']} = ({state['q_hat'].replace('_', '')}, {show(state['estimate'])})"
              for state in decisions]
    lines += [f"{state['id']} = ({show(state['estimate'])}, gamma_c={state['pattern_controllable']})"
              for state in observations]
    lines += [f'{source} --{event}--> {target}' for source, target, event in record['policy_edges']]
    lines += [f'合计：{len(decisions)} 个决策状态、{len(observations)} 个观测状态。']
    folder = Path('outputs/revision_materials/fig1_r1_20261123')
    output = folder / ('figure_state_transition_full.txt' if args.full else
                       f'figure_state_transition_u{args.u}.txt')
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text('\n'.join(lines) + '\n', encoding='utf-8')

    if not args.full and args.u == 5:
        (folder / 'figure_state_transition_reference.txt').write_text('\n'.join(lines) + '\n', encoding='utf-8')

    print('\n'.join(lines))


if __name__ == '__main__':
    main()
