"""Compact manuscript layout of the stored pair-valued Fig.1 retained LL-BTS."""

# Allow direct execution from the project working directory.
if __package__ in (None, ""):
    import sys as _sys
    from pathlib import Path as _Path
    _sys.path.insert(0, str(_Path(__file__).resolve().parents[2]))


import argparse
import json
from pathlib import Path


def render_paper_pair_bts(record, target):
    import matplotlib

    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.patches import FancyArrowPatch
    from matplotlib.path import Path as PlotPath

    def state(value):
        value = value.replace('q_', 'q')

        return 'q_{' + value[1:] + '}'

    def event(value):
        return 'o_' + value[1:] if value.startswith('o') else value

    def states(values):
        return r'\{' + ','.join(state(q) for q in sorted(values, key=lambda q: int(q.replace('q_', '').replace('q', '')))) + r'\}'

    retained = {row['id']: row for row in record['D'] + record['O'] if row['retained']}
    decisions = [row for row in record['D'] if row['retained']]
    observations = [row for row in record['O'] if row['retained']]
    assert len(decisions) == 5 and len(observations) == 7
    positions = {}

    for row in decisions:
        q = row['q_hat'].replace('q_', 'q')
        positions[row['id']] = ((.12, 1.22) if q == 'q0' else (2.03, .30)
                                if len(row['estimate']) == 1 else
                                (2.03, {'q11': .93, 'q6': 1.50, 'q8': 2.08}[q]))

    for row in observations:
        gamma = frozenset(row['pattern_controllable'])

        if any(q.replace('q_', 'q') == 'q0' for q in row['estimate']):
            level = {frozenset({'a'}): .30, frozenset({'a', 'o2'}): .94,
                     frozenset({'a', 'b'}): 1.58, frozenset({'a', 'b', 'o2'}): 2.22}[gamma]
            positions[row['id']] = (.99, level)
        else:
            positions[row['id']] = (3.14, 1.23 if len(row['estimate']) > 2 else
                                    .30 if gamma == frozenset({'a'}) else 2.18)

    fig, ax = plt.subplots(figsize=(3.65, 2.00))
    boxes = {}

    for ident, row in retained.items():
        if ident.startswith('D'):
            label = '$(' + state(row['q_hat']) + ',$\n$' + states(row['estimate']) + ')$'
            color = '#dceaf7'
            size = 6.8
        else:
            values = sorted(row['estimate'], key=lambda q: int(q.replace('q_', '').replace('q', '')))
            split = len(values) > 3
            first = r'\{' + ','.join(state(q) for q in values[:3]) + ',' if split else states(values)
            second = ','.join(state(q) for q in values[3:]) + r'\}' if split else ''
            gamma = r'\{' + ','.join(event(e) for e in row['pattern_full']) + r'\}'
            label = '$(' + first + '$\n$' + second + ',$\n$' + gamma + ')$' if split else '$(' + first + ',$\n$' + gamma + ')$'
            color = '#fff0c5'
            size = 6.1

        boxes[ident] = ax.text(*positions[ident], label, fontsize=size, ha='center', va='center',
                              linespacing=1.05, zorder=10,
                              bbox=dict(boxstyle='round,pad=.22', fc=color, ec='#444444', lw=.55))

    ax.set_xlim(-.28, 3.95)
    ax.set_ylim(-.05, 2.60)
    ax.axis('off')
    fig.subplots_adjust(left=.01, right=.99, top=.99, bottom=.01)
    fig.canvas.draw()

    for source, dest, label in record['policy_edges']:
        x1, y1 = positions[source]
        x2, y2 = positions[dest]
        outer = source.startswith('D') and len(retained[source]['estimate']) == 1 and label == 'a,o2' and y1 == .30

        if outer:
            path = PlotPath([(2.20, .20), (3.72, .03), (3.72, 2.50), (3.14, 2.50), (3.14, 2.33)])
            patch = FancyArrowPatch(path=path, arrowstyle='-|>', mutation_scale=6,
                                    lw=.45, color='#555555', zorder=1)
        else:
            patch = FancyArrowPatch((x1, y1), (x2, y2), patchA=boxes[source].get_bbox_patch(),
                                    patchB=boxes[dest].get_bbox_patch(), arrowstyle='-|>',
                                    mutation_scale=6, lw=.45, color='#555555', zorder=1,
                                    connectionstyle='arc3,rad=0.025')

        ax.add_patch(patch)
        fraction = (.42 - x1) / (x2 - x1) if source == record['initial'] else .5
        x = x1 + fraction * (x2 - x1)
        y = y1 + fraction * (y2 - y1)

        if outer:
            x, y = 3.72, 1.65

        text = ','.join(event(e) for e in label.split(','))
        ax.text(x, y, '$' + text + '$', fontsize=5.7, ha='center', va='center', zorder=4,
                bbox=dict(fc='white', ec='none', pad=.04))

    fig.savefig(target, dpi=240)
    fig.savefig(target.with_suffix('.png'), dpi=240)
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, default=Path('outputs/revision_materials/fig1_r1_20261123/u5/ll_bts.json'))
    parser.add_argument('--output', type=Path, default=Path('[paper]Limited Lookadhead Deadlock-free/Figs/ll_bts_r1_u5.pdf'))
    args = parser.parse_args()
    render_paper_pair_bts(json.loads(args.input.read_text(encoding='utf-8')), args.output)


if __name__ == '__main__':
    main()
