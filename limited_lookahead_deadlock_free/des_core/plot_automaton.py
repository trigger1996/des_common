"""Plant diagrams whose edges route around unrelated state nodes."""

import json
from math import hypot


def render_plant(plant, folder, name, deadlocks=(), safe=(), *, subtitle=''):
    import matplotlib

    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.patches import FancyArrowPatch
    import networkx as nx

    graph = nx.DiGraph();graph.add_nodes_from(sorted(plant.states))

    for (q, e), t in sorted(plant.transitions.items()):
        if graph.has_edge(q, t):graph[q][t]['label'] += ', '+e
        else:graph.add_edge(q, t, label=e)

    distance = nx.single_source_shortest_path_length(graph, plant.initial)
    levels = {}

    for q in graph:
        level = distance.get(q, max(distance.values(), default=0)+1)
        levels.setdefault(level, []).append(q)

    pos = {q:(depth*2.8, (i-(len(nodes)-1)/2)*2.3)
         for depth, nodes in levels.items() for i, q in enumerate(nodes)}
    fig, ax = plt.subplots(figsize=(max(10, len(levels)*2.2), max(6, max(map(len, levels.values()))*1.7+2)))
    nx.draw_networkx_nodes(graph, pos, ax=ax, node_size=1050,
        node_color=['#edb4ae' if q in deadlocks else '#b5dfc2' if q in safe else '#b9d5ed' for q in graph])
    nx.draw_networkx_labels(graph, pos, ax=ax, font_size=10)
    label_positions = []
    routes = []

    for q, t, data in graph.edges(data=True):
        x, y = pos[q];xx, yy = pos[t]

        if q == t:
            patch = FancyArrowPatch((x-.15, y+.22), (x+.15, y+.22),
                connectionstyle='arc3,rad=-2.5', arrowstyle='-|>', mutation_scale=16, color='#333')
            lx, ly = x, y+.95;rad = None
        else:
            dx, dy = xx-x, yy-y
            preferred = .20 if graph.has_edge(t, q) else 0.
            candidates = [preferred, .22, -.22, .4, -.4, .65, -.65, 1., -1., 1.4, -1.4]

            def score(rad):
                cx, cy = (x+xx)/2+rad*dy, (y+yy)/2-rad*dx
                clearance = min((hypot((1-v)**2*x+2*(1-v)*v*cx+v*v*xx-px,
                    (1-v)**2*y+2*(1-v)*v*cy+v*v*yy-py)
                    for n, (px, py) in pos.items() if n not in (q, t)
                    for v in (i/40 for i in range(1, 40))), default=10.)
                v = .35 if rad else .5
                lx = (1-v)**2*x+2*(1-v)*v*cx+v*v*xx
                ly = (1-v)**2*y+2*(1-v)*v*cy+v*v*yy
                label_clearance = min((hypot(lx-px, ly-py) for px, py in label_positions), default=10.)

                return (max(0, .60-clearance)*100+max(0, .40-label_clearance)*20+abs(rad-preferred), lx, ly)

            rad = min(candidates, key=lambda r:score(r)[0]);_, lx, ly = score(rad)
            patch = FancyArrowPatch((x, y), (xx, yy), connectionstyle=f'arc3,rad={rad}',
                arrowstyle='-|>', shrinkA=20, shrinkB=20, mutation_scale=17, color='#333')

        ax.add_patch(patch);label_positions.append((lx, ly))
        ax.text(lx, ly, data['label'], ha='center', va='center', fontsize=9,
            bbox=dict(facecolor='white', edgecolor='none', pad=2))
        routes.append(dict(source=q, target=t, label=data['label'], curvature=rad))

    x, y = pos[plant.initial]
    ax.annotate('', xy=(x-.25, y), xytext=(x-.95, y), arrowprops=dict(arrowstyle='->', lw=1.4))
    ax.set_title(name+' | initial='+plant.initial+'\nControllable={'+','.join(sorted(plant.controllable))+
        '}; Observable={'+','.join(sorted(plant.observable))+'}\n'+
        (subtitle or 'Red: plant deadlock; green: Qe; blue: other states'))
    ax.update_datalim(list(pos.values())+label_positions);ax.autoscale_view();ax.margins(.12, .2)
    ax.axis('off');fig.tight_layout()
    fig.savefig(folder/'plant.png', dpi=145);fig.savefig(folder/'plant.svg');plt.close(fig)
    (folder/'plant_routes.json').write_text(json.dumps(routes, ensure_ascii=False, indent=2), encoding='utf-8')
