"""Construct only Fig.1, merge equivalent branches immediately, and audit R1.

python -X utf8 examples/paper_fig1_r1/main.py --u 5
python -X utf8 examples/paper_fig1_r1/main.py --u 5 --no-merge
The example entry enables merge; solve_example itself defaults to False.
"""

import argparse
import hashlib
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from des_core.automata import DFA
from des_core.bipartite_export import render_record, write_dot
from des_core.certified_lookahead import preprocess, solve_limited_lookahead, validate_policy
from des_core.closed_loop import build_closed_loop, restore_certified_result
from des_core.offline_bts import construct_offline_bts
from examples.paper_fig1_r1.incremental_merge import solve_example
from examples.paper_fig1_r1.reference_audit import audit_reference


def dump(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')


def export_steps(record, history, folder):
    from PIL import Image, ImageOps

    universe = dict(record)
    decisions = {}
    observations = {}
    transitions = set()
    retained = {node['id'] for node in record['D'] + record['O'] if node['retained']}

    for step in history:
        decisions.update((node['id'], dict(node)) for node in step['D'])
        observations.update((node['id'], dict(node)) for node in step['O'])
        transitions.update(tuple(edge) for edge in step['edges'])

    for node in list(decisions.values()) + list(observations.values()):
        node['retained'] = node['id'] in retained

    universe.update(D=list(decisions.values()), O=list(observations.values()), edges=sorted(transitions))
    dump(folder / 'll_bts_generated_universe.json', universe)
    positions = render_record(universe, folder / 'layout_reference.png', title='All generated states, including merged branches')
    frames = []
    destination = folder / 'construction_steps'
    destination.mkdir(exist_ok=True)

    for index, step in enumerate(history):
        states = {node['id'] for node in step['D'] + step['O']}
        data = dict(step, visible_states=sorted(states), transitions=step['edges'])
        dump(destination / f'{index:05d}.json', data)
        picture = destination / f'{index:05d}.png'
        render_record(universe, picture, visible=states,
                      active_edges=step['edges'], positions=positions,
                      title=f"Step {index}: {step['operation']} (merge={record['merge']})")

        with Image.open(picture) as original:
            resized = ImageOps.contain(original.convert('RGB'), (1100, 800))
            frame = Image.new('RGB', (1100, 800), 'white')
            frame.paste(resized, ((1100 - resized.width) // 2, (800 - resized.height) // 2))
            frames.append(frame.quantize(colors=128))

        if index % 20 == 0:
            print('Rendered construction step', index, '/', len(history), flush=True)

    frames[0].save(folder / 'll_bts_construction.gif', save_all=True, append_images=frames[1:],
                   duration=250, loop=0, disposal=2)
    (folder / 'construction_steps.jsonl').write_text(
        '\n'.join(json.dumps(step, ensure_ascii=False) for step in history) + '\n', encoding='utf-8')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--u', type=int, default=5)
    parser.add_argument('--merge', action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument('--render-steps', action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    source = Path(__file__).with_name('plant.json')
    reference = ROOT / '[paper]Limited Lookadhead Deadlock-free/Figs/R1/ll-bts.r1.pdf'
    protected = [source, reference,
        ROOT / '[paper]Limited Lookadhead Deadlock-free/main_original.tex',
        ROOT / 'outputs/revision_materials/pair_states_final_20261123/corpus/summary.json',
        ROOT / 'outputs/revision_materials/pair_states_final_20261123/large/combined.json']
    hashes = {str(path): hashlib.sha256(path.read_bytes()).hexdigest() for path in protected}
    folder = args.output or ROOT / 'outputs/case_studies/fig1_incremental_merge' / (
        f'u{args.u}_merge_' + ('on' if args.merge else 'off'))
    folder.mkdir(parents=True, exist_ok=True)
    model = json.loads(source.read_text(encoding='utf-8'))
    plant = DFA(frozenset(model['states']), model['initial'], frozenset(model['events']),
                frozenset(model['controllable']), frozenset(model['observable']),
                {(q, event): target for q, event, target in model['transitions']})
    pre = preprocess(plant)

    # This construction performs each merge inside BFS, before pruning.
    result, record, history = solve_example(pre, args.u, merge=args.merge)
    validation = validate_policy(pre, result)
    closed = build_closed_loop(pre, result)

    # Independent unmerged reference calculations validate the result afterwards.
    ordinary = solve_limited_lookahead(pre, horizon=args.u)
    offline = construct_offline_bts(plant)
    assert result.status == ordinary.status
    assert result.maximal_patterns == ordinary.maximal_patterns
    assert set(result.decision_states) == set(ordinary.decision_states)
    assert build_closed_loop(pre, ordinary) == closed
    restore_certified_result(pre, record)
    dump(folder / 'll_bts.json', record)
    dump(folder / 'll_bts_merged.json', record)
    dump(folder / 'closed_loop_system.json', closed)
    dump(folder / 'incremental_operations.json', history)
    write_dot(record, folder / 'll_bts.dot')
    write_dot(record, folder / 'll_bts_retained.dot', retained=True)
    render_record(record, folder / 'll_bts.png')
    render_record(record, folder / 'll_bts.pdf')
    render_record(record, folder / 'll_bts_retained.png', retained=True)
    render_record(record, folder / 'll_bts_retained.pdf', retained=True)

    if args.render_steps:
        export_steps(record, history, folder)

    audit = audit_reference(pre, result, record, folder, reference, args.u)
    summary = dict(merge=args.merge, merge_count=record['merge_count'],
        u=args.u, bar_u=pre.lookahead_lower_bound, status=result.status,
        constructed_D=result.decision_count, constructed_O=result.observation_count,
        retained_D=len(result.decision_policy), retained_O=sum(node['retained'] for node in record['O']),
        constructed_transitions=result.edge_count, retained_transitions=len(record['policy_edges']),
        unmerged_D=ordinary.decision_count, unmerged_O=ordinary.observation_count,
        closed_loop_states=len(closed['nodes']), closed_loop_transitions=len(closed['edges']),
        matches_unmerged_closed_loop=True, matches_unmerged_root_patterns=True,
        matches_offline_root_patterns=result.maximal_patterns == offline.maximal_patterns,
        all_decision_pairs_preserved=True, validation=validation, steps=len(history),
        reference_verdict=audit['verdict'], protected_hashes=hashes,
        scope='Only this 17-state example was rerun. General solvers and other experiment results are unchanged.')

    for name, digest in hashes.items():
        assert hashlib.sha256(Path(name).read_bytes()).hexdigest() == digest, name

    dump(folder / 'summary.json', summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2), flush=True)


if __name__ == '__main__':
    main()
