"""Rebuild the page-9 DFA and compare its LL-BTS with reference page 10.

python -X utf8 examples/paper/rebuild_fig1_r1.py
Input: examples/paper_fig1_r1/plant.json. Only q14-a-q15-b-q16 is added.
The provided reference PDF and main_original.tex are never modified.
"""

# Allow direct execution from the project working directory.
if __package__ in (None, ""):
    import sys as _sys
    from pathlib import Path as _Path
    _sys.path.insert(0, str(_Path(__file__).resolve().parents[2]))


import argparse
import hashlib
from itertools import combinations
import json
from pathlib import Path
import shutil

from examples.benchmarks.certified_benchmark import export_bts
from des_core.automata import DFA
from des_core.certified_lookahead import preprocess, solve_limited_lookahead, validate_policy
from des_core.closed_loop import build_closed_loop
from des_core.offline_bts import construct_offline_bts, traditional_ur_nx
from examples.paper.manuscript_case_studies import plant_record, plot_small_ll_bts
from examples.paper.paper_example_models import paper_small_figure_original, paper_small_figure_r1


INPUT = Path('examples/paper_fig1_r1/plant.json')
REFERENCE = Path('[paper]Limited Lookadhead Deadlock-free/Figs/on-the-fly_nb_case.R1.pdf')
OUTPUT = Path('outputs/revision_materials/fig1_r1_20261123')


def dump(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')


def ordered(states):
    return sorted(states, key=lambda q: int(q.split('_')[-1]))


def show(states):
    return '{' + ','.join(q.replace('_', '') for q in ordered(states)) + '}'


def retained_count(result):
    return len(result.decision_policy), len({(c.closure, c.pattern) for cs in result.policy.values() for c in cs})


def fragments(pre, estimate, horizon):
    plant = pre.plant
    result = solve_limited_lookahead(pre, estimate=estimate, horizon=horizon)
    controls = sorted(plant.controllable)
    rows = []

    for size in range(len(controls) + 1):
        for enabled in combinations(controls, size):
            pattern = frozenset(enabled)
            choice = traditional_ur_nx(plant, estimate, pattern)
            gamma = pattern | plant.uncontrollable
            dead = choice.closure & pre.Q_d
            failure = choice.closure & pre.Q_f
            blocked = {q for q in choice.closure if not any(e in gamma for e, _ in plant.enabled(q))}
            bad_successors = [(e, x) for e, x in choice.successors if x & (pre.Q_d | pre.Q_f)]
            retained = any(c.pattern == pattern for c in result.policy.get(estimate, ()))
            reasons = []

            if dead:
                reasons.append('UR reaches deadlock ' + show(dead))

            if failure:
                reasons.append('UR reaches Q_f ' + show(failure))

            if blocked:
                reasons.append('no enabled event at ' + show(blocked))

            if bad_successors:
                reasons.append('observable successor intersects Q_f or Q_d')

            if not reasons and not retained:
                reasons.append('excluded by finite-window completeness or backward consistency checks')

            rows.append(dict(pattern_controllable=sorted(pattern), pattern_full=sorted(gamma),
                             UR=ordered(choice.closure),
                             NX={e: ordered(x) for e, x in choice.successors},
                             retained=retained, reasons=reasons))

    return rows


def plot_reference_panels(panels, path):
    import matplotlib

    matplotlib.use('Agg')
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(3, 1, figsize=(11., 15.))

    for ax, (title, estimate, rows) in zip(axes, panels):
        ax.set_xlim(0., 11.)
        ax.set_ylim(-.8, 8.5)
        ax.axis('off')
        ax.set_title(title + ' — complete UR/NX, local u=4', fontsize=11)
        ax.text(.65, 3.5, show(estimate), ha='center', va='center', fontsize=10,
                bbox=dict(boxstyle='round', facecolor='#e7f0fa', edgecolor='#305d8a'))

        for index, row in enumerate(reversed(rows)):
            y = index
            certain_bad = any(not reason.startswith('excluded') for reason in row['reasons'])
            color = '#d9efdc' if row['retained'] else ('#f6d5d2' if certain_bad else '#fff0c0')
            label = show(row['UR']) + '\n' + 'gamma={' + ','.join(row['pattern_full']) + '}'
            ax.text(4.9, y, label, ha='center', va='center', fontsize=8,
                    bbox=dict(boxstyle='round', facecolor=color, edgecolor='#555555'))
            ax.annotate('', xy=(3., y), xytext=(1.45, 3.5),
                        arrowprops=dict(arrowstyle='->', lw=.6, color='#555555'))
            successor = '; '.join(e + ': ' + show(x) for e, x in row['NX'].items())
            ax.text(8.5, y, successor or 'no observable successor', ha='center', va='center', fontsize=8)

    fig.text(.5, .015, 'Green: retained; red: deadlock/liveness or bad-successor violation; '
             'yellow: excluded by the limited window/consistency checks.\n'
             'Panels (b) and (c) are separate local queries, not substitutes for the complete post-observation estimate.',
             ha='center', fontsize=8)
    fig.tight_layout(rect=(0., .04, 1., 1.))
    fig.savefig(path)
    fig.savefig(path.with_suffix('.png'), dpi=160)
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=OUTPUT)
    args = parser.parse_args()
    out = args.output
    out.mkdir(parents=True, exist_ok=True)
    record = json.loads(INPUT.read_text(encoding='utf-8'))
    plant = DFA(frozenset(record['states']), record['initial'], frozenset(record['events']),
                frozenset(record['controllable']), frozenset(record['observable']),
                {(q, e): target for q, e, target in record['transitions']})
    original = paper_small_figure_original().dfa
    assert plant.states - original.states == {'q_15', 'q_16'}
    assert all(plant.transitions[key] == value for key, value in original.transitions.items())
    assert set(plant.transitions) - set(original.transitions) == {('q_14', 'a'), ('q_15', 'b')}
    assert plant.controllable == original.controllable and plant.observable == original.observable
    assert plant_record(plant) == plant_record(paper_small_figure_r1().dfa)
    pre = preprocess(plant)
    original_pre = preprocess(original)
    full = construct_offline_bts(plant)
    (out / 'offline').mkdir(parents=True, exist_ok=True)
    export_bts(pre, full, out / 'offline', structure='BTS', draw=False)
    dump(out / 'plant.json', record)
    sweep = []

    for horizon in range(1, 7):
        result = solve_limited_lookahead(pre, horizon=horizon)
        validation = validate_policy(pre, result)
        d, o = retained_count(result)
        row = dict(u=horizon, status=result.status, D=result.decision_count,
                   O=result.observation_count, retained_D=d, retained_O=o,
                   root_patterns=[sorted(p) for p in result.maximal_patterns],
                   same_offline_patterns=result.maximal_patterns == full.maximal_patterns,
                   same_offline_policy=result.policy == full.policy,
                   validation=validation)

        if horizon in (4, 5):
            folder = out / ('u' + str(horizon))
            folder.mkdir(parents=True, exist_ok=True)
            export_bts(pre, result, folder, draw=True)
            graph = build_closed_loop(pre, result)
            sources = {e['source'] for e in graph['edges']}
            assert graph['nodes'] and all(q['id'] in sources for q in graph['nodes'])
            dump(folder / 'closed_loop_system.json', graph)
            row.update(closed_loop_states=len(graph['nodes']), closed_loop_transitions=len(graph['edges']))
            previous = solve_limited_lookahead(original_pre, horizon=horizon)
            validate_policy(original_pre, previous)
            previous_graph = build_closed_loop(original_pre, previous)
            row['versus_original_15_state'] = dict(
                same_constructed_fragments=result.constructed_choices == previous.constructed_choices,
                same_retained_policy=result.policy == previous.policy,
                same_selected_closed_loop=graph == previous_graph,
                original_retained_D_O=list(retained_count(previous)))
            assert all(row['versus_original_15_state'][key] for key in (
                'same_constructed_fragments', 'same_retained_policy', 'same_selected_closed_loop'))
            plot_small_ll_bts(result, folder / 'll_bts_retained.pdf', pre)

        sweep.append(row)

    panels = [(name, frozenset({q}), fragments(pre, frozenset({q}), 4))
              for name, q in [('(a) initial estimate', 'q_0'), ('(b) local estimate q8', 'q_8'),
                             ('(c) local estimate q6', 'q_6')]]
    dump(out / 'reference_fragments_recomputed.json', {name: rows for name, _, rows in panels})
    plot_reference_panels(panels, out / 'page10_recomputed.pdf')
    full_first = traditional_ur_nx(plant, frozenset({plant.initial}), plant.controllable)
    assert dict(full_first.successors)['o1'] == frozenset({'q_6', 'q_8', 'q_11'})
    dump(out / 'complete_observation_estimate.json', dict(
        estimate=['q_6', 'q_8', 'q_11'],
        rows=fragments(pre, frozenset({'q_6', 'q_8', 'q_11'}), 5)))
    import pymupdf

    doc = pymupdf.open(REFERENCE)
    crop = pymupdf.open()
    page = crop.new_page(width=645., height=305.)
    page.show_pdf_page(page.rect, doc, 8, clip=pymupdf.Rect(0., 115., 645., 420.))
    crop.save(out / 'dfa_reference_page9.pdf')
    crop.close()
    doc.close()
    dump(out / 'result.json', dict(states=len(plant.states), transitions=len(plant.transitions),
        Q_d=ordered(pre.Q_d), Q_f=ordered(pre.Q_f), Q_e=ordered(pre.Q_e),
        Q_o=ordered(pre.Q_o_tilde), bar_u=pre.lookahead_lower_bound, sweep=sweep,
        offline_D=full.decision_count, offline_O=full.observation_count,
        reference_pdf=str(REFERENCE), reference_pages=[9, 10],
        reference_sha256=hashlib.sha256(REFERENCE.read_bytes()).hexdigest(),
        input_sha256=hashlib.sha256(INPUT.read_bytes()).hexdigest()))
    dump(out / 'added_chain_comparison.json', dict(
        original_Q_d=ordered(original_pre.Q_d), original_Q_f=ordered(original_pre.Q_f),
        revised_Q_d=ordered(pre.Q_d), revised_Q_f=ordered(pre.Q_f),
        original_bar_u=original_pre.lookahead_lower_bound, revised_bar_u=pre.lookahead_lower_bound,
        comparisons=[dict(u=row['u'], **row['versus_original_15_state'])
                     for row in sweep if 'versus_original_15_state' in row],
        conclusion='Under the same horizon and current construction/pruning rules, the added '
                   'q14-a-q15-b-q16 chain changes bad-state classification but not the retained '
                   'LL-BTS or selected closed loop at u=4 and u=5.'))
    shutil.copy2(INPUT.parent / 'README.md', out / '对照说明.md')
    print('Fig.1 R1:', len(plant.states), 'states,', len(plant.transitions),
          'transitions; bar_u =', pre.lookahead_lower_bound)
    print('u=4 retained D/O:', sweep[3]['retained_D'], sweep[3]['retained_O'])
    print('u=5 retained D/O:', sweep[4]['retained_D'], sweep[4]['retained_O'])


if __name__ == '__main__':
    main()
