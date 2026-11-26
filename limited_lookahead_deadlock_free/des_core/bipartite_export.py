"""Pair-valued BTS/LL-BTS exports and recorded incremental graph rendering."""

from collections import deque
import json
from pathlib import Path

from des_core.bipartite_graph import choice_variants, observation_key


def state_text(value):
    if isinstance(value, tuple):
        return '(' + ','.join(state_text(q) for q in value) + ')'

    return str(value).replace('q_', 'q')


def estimate_text(values):
    return '{' + ','.join(state_text(q) for q in sorted(values)) + '}'


def graph_record(pre, result, structure):
    pairs = sorted(result.decision_states, key=lambda p: (len(p[1]), sorted(p[1]), p[0]))
    ids = {pair: f'D{i}' for i, pair in enumerate(pairs)}
    observations = sorted(result.observation_states, key=lambda p: (sorted(p[0]), sorted(p[1])))
    oids = {key: f'O{i}' for i, key in enumerate(observations)}
    kept_obs = {observation_key(c) for cs in result.decision_policy.values() for c in cs}
    decisions = [dict(id=ids[p], q_hat=p[0], estimate=sorted(p[1]),
                      state=[p[0], sorted(p[1])], retained=p in result.decision_policy,
                      safe_terminal=p[1] in result.safe_terminals) for p in pairs]
    obs = [dict(id=oids[key], estimate=sorted(key[0]), pattern_controllable=sorted(key[1]),
                pattern_full=sorted(key[1] | pre.plant.uncontrollable), retained=key in kept_obs)
           for key in observations]
    edges = set()
    policy_edges = set()

    for pair, choices in result.decision_states.items():
        for choice in choices:
            oid = oids[observation_key(choice)]
            transition = (ids[pair], oid, ','.join(sorted(choice.pattern)) or '{}')
            edges.add(transition)
            keep = pair in result.decision_policy and choice in result.decision_policy[pair]

            if keep:
                policy_edges.add(transition)

            for event, estimate in choice.successors:
                for q_hat in estimate:
                    transition = (oid, ids[q_hat, estimate], event)
                    edges.add(transition)

                    if keep:
                        policy_edges.add(transition)

    assert len(decisions) == result.decision_count
    assert len(obs) == result.observation_count
    assert len(edges) == result.edge_count

    return dict(schema_version=2, structure=structure, representation=result.representation,
                status=result.status, u=result.horizon, window=sorted(result.window),
                initial=ids[result.initial_decision], D=decisions, O=obs,
                edges=sorted(edges), policy_edges=sorted(policy_edges),
                boundary_choices=result.boundary_choices, patterns_tested=result.patterns_tested,
                maximal_root_patterns=[sorted(p) for p in result.maximal_patterns],
                window_semantics='One window per complete estimate; q_hat indices are distinct decision states.',
                terminal_semantics='Safe estimates have an implicit all-events continuation.'), ids, oids


def write_dot(record, path, *, retained=False):
    nodes = [n for n in record['D'] + record['O'] if not retained or n['retained']]
    allowed = {n['id'] for n in nodes}
    lines = ['digraph BTS {', 'rankdir=LR;', 'node [fontname="Times New Roman"];']

    for n in nodes:
        label = ('(' + state_text(n['q_hat']) + ',' + estimate_text(n['estimate']) + ')'
                 if n['id'].startswith('D') else
                 '(' + estimate_text(n['estimate']) + ',{' + ','.join(n['pattern_full']) + '})')
        color = 'black' if n['retained'] else 'red'
        lines.append(n['id'] + ' [shape=' + ('box' if n['id'].startswith('D') else 'ellipse')
                     + ',color=' + color + ',label=' + json.dumps(label) + '];')

    for source, target, event in record['policy_edges'] if retained else record['edges']:
        if source in allowed and target in allowed:
            lines.append(f'{source} -> {target} [label={json.dumps(event)}];')

    lines.append('}')
    path.write_text('\n'.join(lines), encoding='utf-8')


def render_record(record, path, *, retained=False, visible=None, active_edges=None, title=None, positions=None):
    import matplotlib

    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import networkx as nx

    nodes = {n['id']: n for n in record['D'] + record['O']}
    allowed = (set(nodes) if visible is None else visible) & (
        {key for key, n in nodes.items() if n['retained']} if retained else set(nodes))
    edge_list = record['policy_edges'] if retained else record['edges']

    if active_edges is not None:
        edge_list = active_edges

    graph = nx.DiGraph()
    graph.add_nodes_from(allowed)

    for source, target, label in edge_list:
        if source in allowed and target in allowed:
            if graph.has_edge(source, target):
                graph[source][target]['label'] += ',' + label
            else:
                graph.add_edge(source, target, label=label)

    if positions is None:
        distances = nx.single_source_shortest_path_length(graph, record['initial']) if record['initial'] in graph else {}
        layers = {}

        for node in sorted(graph):
            layers.setdefault(distances.get(node, max(distances.values(), default=0) + 1), []).append(node)

        positions = {node: (level * 4., (i - (len(layer) - 1) / 2) * 1.5)
                     for level, layer in layers.items() for i, node in enumerate(layer)}

    xs = [p[0] for p in positions.values()] or [0.]
    ys = [p[1] for p in positions.values()] or [0.]
    width = max(9., max(xs) + 4.)
    height = max(6., (max(ys) - min(ys)) * .65 + 2.)
    fig, ax = plt.subplots(figsize=(width, height))
    nx.draw_networkx_edges(graph, positions, ax=ax, arrowsize=10, width=.6,
                           connectionstyle='arc3,rad=.04', node_size=1800)

    for key in allowed:
        n = nodes[key]

        if key.startswith('D'):
            label = key + '\n(' + state_text(n['q_hat']) + ', ' + estimate_text(n['estimate']) + ')'
            fill = '#dceaf7'
        else:
            label = key + '\nx=' + estimate_text(n['estimate']) + '\ngamma={' + ','.join(n['pattern_full']) + '}'
            fill = '#fff0c5'

        ax.text(*positions[key], label, ha='center', va='center', fontsize=8,
                bbox=dict(boxstyle='round,pad=.35', facecolor=fill,
                          edgecolor='#333333' if n['retained'] else '#bd3939'), zorder=5)

    nx.draw_networkx_edge_labels(graph, positions, nx.get_edge_attributes(graph, 'label'), ax=ax, font_size=7)
    ax.set_xlim(min(xs) - 2.2, max(xs) + 2.2)
    ax.set_ylim(min(ys) - 1.2, max(ys) + 1.2)
    ax.set_title(title or (record['structure'] + ': decision states (q_hat, x_hat)'), fontsize=11)
    ax.axis('off')
    fig.tight_layout()
    fig.savefig(path, dpi=105)
    plt.close(fig)

    return positions


def export_recorded_steps(result, record, ids, oids, folder):
    """Save every actual pair-graph insertion/deletion step and combine frames."""

    from PIL import Image, ImageOps

    steps_folder = folder / 'construction_steps'
    steps_folder.mkdir(parents=True, exist_ok=True)
    visible = {record['initial']}
    edges = set()
    snapshots = []
    events = []
    positions = render_record(record, folder / 'll_bts.png')
    kept_edges = {tuple(e) for e in record['policy_edges']}
    kept_nodes = {n['id'] for n in record['D'] + record['O'] if n['retained']}

    def save(operation, details):
        index = len(events)
        data = dict(step=index, operation=operation, details=details,
                    visible_states=sorted(visible), transitions=sorted(edges))
        json_path = steps_folder / f'{index:05d}.json'
        json_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
        png = json_path.with_suffix('.png')
        render_record(record, png, visible=set(visible), active_edges=set(edges),
                      positions=positions, title=f'LL-BTS step {index}: {operation}')

        with Image.open(png) as source:
            frame = ImageOps.contain(source.convert('RGB'), (1100, 800))
            canvas = Image.new('RGB', (1100, 800), 'white')
            canvas.paste(frame, ((1100 - frame.width) // 2, (800 - frame.height) // 2))
            snapshots.append(canvas.quantize(colors=128))

        events.append(data)

    save('initial_decision', record['initial'])

    for event in result.construction_steps:
        decision = event['decision']
        did = ids[decision]

        if event['operation'] == 'construct_pattern':
            choice = event['choice']
            oid = oids[observation_key(choice)]
            visible.update((did, oid))
            edges.add((did, oid, ','.join(sorted(choice.pattern)) or '{}'))

            for label, target in event['targets']:
                visible.add(ids[target])
                edges.add((oid, ids[target], label))

            save('construct_pattern', dict(decision=did, observation=oid,
                 gamma_c=sorted(choice.pattern), UR=sorted(choice.closure)))
        elif event['operation'] == 'prune_pattern':
            choice = event['choice']
            oid = oids[observation_key(choice)]
            edges.discard((did, oid, ','.join(sorted(choice.pattern)) or '{}'))

            if not any(target == oid for _, target, _ in edges):
                visible.discard(oid)
                edges = {e for e in edges if e[0] != oid}

            save('prune_pattern', dict(decision=did, observation=oid))
        else:
            visible.discard(did)
            edges = {e for e in edges if did not in e[:2]}
            save('prune_decision', did)

    visible = kept_nodes
    edges = kept_edges
    save('retained_graph', 'Final retained pair-valued LL-BTS')
    (folder / 'construction_steps.jsonl').write_text(
        '\n'.join(json.dumps(e, ensure_ascii=False) for e in events) + '\n', encoding='utf-8')
    snapshots[0].save(folder / 'll_bts_construction.gif', save_all=True,
                      append_images=snapshots[1:], duration=250, loop=0, disposal=2)

    return len(events)
