"""Draw certified physical closed loops for all literature and project examples.

Run: python -X utf8 scripts/reporting/draw_closed_loops.py
"""

# Allow direct execution from the project working directory.
if __package__ in (None, ""):
    import sys as _sys
    from pathlib import Path as _Path
    _sys.path.insert(0, str(_Path(__file__).resolve().parents[2]))


from collections import Counter
from dataclasses import replace
import csv
import html
import hashlib
import json
from pathlib import Path
import shutil
import zipfile

import matplotlib

matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch
from matplotlib.path import Path as MplPath
import networkx as nx

from des_core.certified_lookahead import preprocess, solve_limited_lookahead, solve_offline
from des_core.automata import DFA
from des_core.closed_loop import build_closed_loop, restore_certified_result
from examples.yin_literature import build_yin_literature_examples
from examples.structural import build_structural_examples
from examples.non_deadlock import all_examples, build_nested_cycle_deadlock_example

OUT = Path('outputs/closed_loop_systems')
BENCH = Path('outputs/expanded_yin_benchmark')


def dump(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')


def diagram(nodes, edges, initial, labels, title, path, *, hidden=(), red=()):
    graph = nx.DiGraph(); graph.add_nodes_from(nodes)

    for a, event, b in edges:
        if graph.has_edge(a, b):graph[a][b]['label'] += ', '+event
        else:graph.add_edge(a, b, label=event)

    distance = nx.single_source_shortest_path_length(graph, initial)
    layers = {}

    for node in graph:
        layers.setdefault(distance.get(node, max(distance.values(), default=0)+1), []).append(node)

    height = max(4.5, max(map(len, layers.values()), default=1)*1.2+2)
    width = max(8, (max(layers, default=0)+1)*2.2+2)
    pos = {node:(level*2.2, (i-(len(group)-1)/2)*1.5)
         for level, group in layers.items() for i, node in enumerate(group)}
    fig, ax = plt.subplots(figsize=(width, height))
    nx.draw_networkx_nodes(graph, pos, ax=ax, node_size=1800,
        node_color=['#f5c2c0' if n in red else '#bed9ed' for n in graph],
        edgecolors=['#16476b' if n == initial else '#526675' for n in graph], linewidths=1.7)
    nx.draw_networkx_labels(graph, pos, labels=labels, ax=ax, font_size=8)
    hidden = set(hidden)

    for dashed in (False, True):
        edgelist = [(a, b) for a, b in graph.edges if a != b and ((a, b) in hidden) == dashed]
        nx.draw_networkx_edges(graph, pos, ax=ax, edgelist=edgelist,
            style='dashed' if dashed else 'solid', edge_color='#73808b' if dashed else '#314451',
            arrowsize=19, node_size=1800, connectionstyle='arc3,rad=0.08')

    edge_labels = nx.get_edge_attributes(graph, 'label')
    nx.draw_networkx_edge_labels(graph, pos, {e:v for e, v in edge_labels.items() if e[0] != e[1]}, ax=ax,
        font_size=8, rotate=False, connectionstyle='arc3,rad=0.08')

    for (a, b), label in edge_labels.items():
        if a == b:
            x, y = pos[a]
            curve = MplPath([(x-.23, y+.22), (x-.8, y+1.2), (x+.8, y+1.2), (x+.23, y+.22)],
                          [MplPath.MOVETO, MplPath.CURVE4, MplPath.CURVE4, MplPath.CURVE4])
            ax.add_patch(FancyArrowPatch(path=curve, arrowstyle='-|>', mutation_scale=15,
                color='#73808b' if (a, b) in hidden else '#314451',
                linestyle='dashed' if (a, b) in hidden else 'solid', lw=1.1))
            ax.text(x, y+1.05, label, ha='center', va='bottom', fontsize=8,
                    bbox=dict(facecolor='white', edgecolor='none', pad=.4))

    x, y = pos[initial]
    ax.annotate('', xy=(x-.30, y), xytext=(x-.90, y), arrowprops=dict(arrowstyle='->', lw=1.6))
    ax.set_title(title, fontsize=12, pad=22)
    ax.set_xlim(-1.2, max(layers, default=0)*2.2+1.2)
    ys = [p[1] for p in pos.values()]
    ax.set_ylim(min(ys)-1, max(ys)+1.55)
    ax.axis('off');fig.tight_layout()
    fig.savefig(path.with_suffix('.png'), dpi=150)
    fig.savefig(path.with_suffix('.svg'))
    plt.close(fig)


def export_graph(graph, folder, name, u, *, mode='online'):
    output = folder/f'closed_loop_system_{mode}'
    scope = f'u={u}' if mode == 'online' else 'full known system; offline BTS'

    if graph['status'] != 'winning':
        for path in (output.with_suffix('.dot'), folder/'supervisor.png', folder/'supervisor.svg', folder/'supervisor_memory.csv'):
            if path.exists():path.unlink()

        fig, ax = plt.subplots(figsize=(9, 3.5));ax.axis('off')
        ax.text(.5, .76, name, ha='center', fontsize=13, transform=ax.transAxes)
        ax.text(.5, .51, 'No deadlock-free supervisor', ha='center', fontsize=19,
                color='#a63232', transform=ax.transAxes)
        ax.text(.5, .26, f'Proved losing | {scope}\nNo closed-loop transitions are fabricated.',
                ha='center', fontsize=11, transform=ax.transAxes)
        fig.tight_layout();fig.savefig(output.with_suffix('.png'), dpi=150)
        fig.savefig(output.with_suffix('.svg'));plt.close(fig)

        return

    nodes = graph['nodes'];edges = graph['edges'];memories = graph['controller']
    labels = {n['id']:n['state']+'\n'+n['memory'] for n in nodes}
    triples = [(e['source'], e['event']+(' [uo]' if not e['observable'] else '')+
              (' [uc]' if not e['controllable'] else ''), e['target'])
             for e in edges]
    diagram([n['id'] for n in nodes], triples, graph['initial'], labels,
        f'{name} | closed-loop S/G | {scope}\nNode: (DFA state, controller memory); '
        '[uo]: hidden; [uc]: uncontrollable', output,
        hidden=[(e['source'], e['target']) for e in edges if not e['observable']])
    labels = {m['id']:m['id']+'\nC={'+
            ','.join(m['controllable_pattern'])+'}' for m in memories}
    diagram([m['id'] for m in memories], graph['controller_edges'], graph['controller_initial'], labels,
        f'{name} | selected observation-feedback supervisor\nC: enabled controllable events; '
        'all uncontrollable events remain enabled; estimates in memory CSV', folder/'supervisor')
    lines = ['digraph ClosedLoop {', 'rankdir=LR;', 'node [shape=ellipse];',
           'start [shape=point];', 'start -> '+graph['initial']+';']
    lines += [n['id']+' [label='+json.dumps(labels.get(n['id'],
        n['state']+'\n'+n['memory']))+'];' for n in nodes]
    lines += [a+' -> '+b+' [label='+json.dumps(event)+'];' for a, event, b in triples]
    lines.append('}')
    output.with_suffix('.dot').write_text('\n'.join(lines), encoding='utf-8')

    with (folder/'supervisor_memory.csv').open('w', encoding='utf-8-sig', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=list(memories[0]));writer.writeheader();writer.writerows(memories)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    literature = build_yin_literature_examples()
    structural = build_structural_examples()
    projects = {e.name:(replace(e, dfa=e.original_dfa, layout=e.original_layout or {})
                     if e.original_dfa is not None else e)
              for e in all_examples()+[build_nested_cycle_deadlock_example()]}
    saved = json.loads(Path('outputs/expanded_yin_benchmark/paper_results.json').read_text(encoding='utf-8'))
    saved += json.loads((BENCH/'structural_results.json').read_text(encoding='utf-8')) if (BENCH/'structural_results.json').exists() else []
    horizons = {r['name']:r['selected_u'] for r in saved}
    rows = []

    for example in literature+structural+tuple(projects.values()):
        is_literature = example.name in horizons
        folder = (BENCH if is_literature else OUT)/example.name
        folder.mkdir(exist_ok=True)
        provenance = {}
        bts = None

        if is_literature:
            saved_plant = json.loads((folder/'plant.json').read_text(encoding='utf-8'))
            plant = DFA(frozenset(saved_plant['states']), saved_plant['initial'],
                frozenset(saved_plant['events']), frozenset(saved_plant['controllable']),
                frozenset(saved_plant['observable']), {(q, e):t for q, e, t in saved_plant['transitions']})
            example = replace(example, dfa=plant)
            bts = json.loads((folder/'ll_bts.json').read_text(encoding='utf-8'))
            provenance = {name:hashlib.sha256((folder/name).read_bytes()).hexdigest()
                        for name in ('plant.json', 'll_bts.json')}

        pre = preprocess(example.dfa, max_path_visits=2_000_000)
        offline = solve_offline(example.dfa)

        if is_literature:
            result = restore_certified_result(pre, bts)
            u = result.horizon
            assert u == horizons[example.name]
        else:
            lower = max(pre.horizon, example.lookahead_limit or 0)

            for u in range(lower, max(len(example.dfa.states), lower+1)):
                r = solve_limited_lookahead(pre, horizon=u)

                if (r.status, set(r.maximal_patterns)) == (offline.status, set(offline.maximal_patterns)):
                    break
            else:raise AssertionError(('no calibrated horizon', example.name))

            result = solve_limited_lookahead(pre, horizon=u)

        assert (result.status, set(result.maximal_patterns)) == (offline.status, set(offline.maximal_patterns))
        graph = build_closed_loop(pre, result)
        graph.update(name=example.name, u=u, source=example.source_name,
                     source_artifacts_sha256=provenance)

        if bts is not None:
            decisions = {tuple(n['estimate']):n['id'] for n in bts['D']}

            for memory in graph['controller']:
                memory['ll_bts_decision_id'] = decisions.get(tuple(memory['estimate']))
                memory['origin'] = 'Qe_enable_all_certificate' if memory['safe_continuation'] else 'retained_LL_BTS_pattern'

        dump(folder/'closed_loop_system_online.json', graph)
        dump(folder/'supervisor.json', dict(status=graph['status'],
            initial=graph['controller_initial'], states=graph['controller'],
            observable_transitions=graph['controller_edges'],
            hidden_event_rule='Controller memory remains unchanged on every hidden event.',
            source_artifacts_sha256=provenance,
            synthesis='Extracted from retained LL-BTS edges; Qe terminals expanded with enable-all continuation.'
            if is_literature else 'Extracted from certified project-example LL-BTS.'))
        export_graph(graph, folder, example.name, u)
        original = Path('outputs/expanded_yin_benchmark')/example.name/'plant.png'

        if original.exists():
            if original.resolve() != (folder/'plant.png').resolve():shutil.copy2(original, folder/'plant.png')
        else:
            plant = example.dfa
            diagram(sorted(plant.states), [(q, e, t) for (q, e), t in plant.transitions.items()],
                    plant.initial, {q:q for q in plant.states}, example.name+' | original DFA',
                    folder/'plant', red=pre.deadlocks)

        (folder/'closed_loop_README.txt').write_text(
            'Data flow: plant.json -> retained ll_bts.json -> supervisor.json -> closed_loop_system_online.json.\n'
            'A single certified maximal pattern is fixed at each controller memory.\n'
            'Closed-loop states pair a physical DFA state with controller memory.\n'
            'Hidden events preserve memory; all enabled outcomes are included.\n'
            'Safe Qe terminals use the enable-all continuation certified by the LL-BTS.\n'
            'losing means no deadlock-free supervisor/closed-loop can be extracted.\n', encoding='utf-8')

        if is_literature:
            mirror = OUT/example.name;mirror.mkdir(exist_ok=True)

            for pattern in ('closed_loop*', 'supervisor*', 'plant.png'):
                for artifact in folder.glob(pattern):
                    if artifact.is_file():shutil.copy2(artifact, mirror/artifact.name)

        row = dict(name=example.name, group='project' if example.name in projects else
                 'structural' if example.name.startswith('structural_') else 'literature',
                 status=result.status, u=u, plant_states=len(example.dfa.states),
                 closed_loop_states=len(graph['nodes']), closed_loop_transitions=len(graph['edges']),
                 controller_memories=len(graph['controller']))
        rows.append(row)
        print(row, flush=True)

    dump(OUT/'summary.json', dict(models=len(rows), statuses=dict(Counter(r['status'] for r in rows)),
         literature_models=len(literature), structural_models=len(structural), project_models=len(projects), results=rows))

    with (OUT/'summary.csv').open('w', encoding='utf-8-sig', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)

    parts = ['<!doctype html><meta charset="utf-8"><title>闭环系统图集</title>',
      '<style>body{font:16px system-ui;max-width:1200px;margin:35px auto;padding:0 25px;background:#f5f7fa;color:#172b3a}'
      'article{background:white;border:1px solid #dce3e9;border-radius:10px;padding:22px;margin:24px 0}'
      'img{max-width:100%;max-height:800px;object-fit:contain}a{color:#075eab}summary{cursor:pointer}table{border-collapse:collapse}'
      'td,th{padding:7px 12px;border-bottom:1px solid #ddd}h2{font-size:20px}nav{line-height:1.9}</style>',
      '<h1>闭环系统 S/G 图集</h1>',
      f'<p>{len(literature)}个论文模型、{len(structural)}个结构测试及{len(projects)}个项目模型。每个可解例子选取一个认证的观测反馈控制器，'
      '绘制全部可达闭环转移。节点为（实际DFA状态，控制器记忆），不可观测事件不改变记忆。'
      '不是单条运行轨迹，也不是把不同控制模式并起来。不可解例子保留原图及明确状态说明。</p>',
      '<p>控制器在每个估计处选择基数最大的认证控制模式，并以事件名排序打破平局。'
      '这是一个包含极大的可执行策略，不宣称它是全部策略的并或全局上确界。'
      'Qe证书终端采用允许全部事件的延续，并实际展开其闭环演化。</p>',
      '<p>[uo]：不可观测事件；[uc]：不可控事件。虚线边至少包含一个不可观测事件；'
      '同端点事件合并标注时，以每个事件自己的[uo]标记为准。'
      'supervisor图中的C只列允许的可控事件，不可控事件始终允许。</p>',
      '<p><a href="summary.csv">下载汇总CSV</a></p><nav>']
    parts.extend('<a href="#'+r['name']+'">'+html.escape(r['name'])+'</a> · ' for r in rows)
    parts.append('</nav>')

    for r in rows:
        name = r['name'];esc = html.escape(name)
        parts += [f'<article id="{name}"><h2>{esc}</h2>',
            f'<p>{r["status"]} · u={r["u"]} · 闭环状态{r["closed_loop_states"]} · '
            f'闭环转移{r["closed_loop_transitions"]} · 控制器记忆{r["controller_memories"]}</p>',
            f'<a href="{name}/closed_loop_system_online.svg"><img src="{name}/closed_loop_system_online.png" alt="{esc}"></a>',
            f'<p><a href="{name}/closed_loop_system_online.svg">闭环SVG</a> · '
            f'<a href="{name}/closed_loop_system_online.png">闭环PNG</a> · '
            f'<a href="{name}/closed_loop_system_online.json">完整转移JSON</a></p>']

        if r['status'] == 'winning':
            parts += [f'<details><summary>查看所选监督控制器</summary><img src="{name}/supervisor.png">'
                      f'<p><a href="{name}/supervisor_memory.csv">记忆/估计/控制模式表</a></p></details>']

        parts += [f'<details><summary>查看原自动机</summary><img src="{name}/plant.png"></details></article>']

    (OUT/'index.html').write_text('\n'.join(parts), encoding='utf-8')
    bench_rows = [r for r in rows if r['group'] != 'project']
    dump(BENCH/'closed_loop_summary.json', dict(models=len(bench_rows),
        statuses=dict(Counter(r['status'] for r in bench_rows)), results=bench_rows))

    with (BENCH/'closed_loop_summary.csv').open('w', encoding='utf-8-sig', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=list(bench_rows[0]));writer.writeheader();writer.writerows(bench_rows)

    bench_parts = ['<!doctype html><meta charset="utf-8"><title>论文例子闭环系统</title>',
        '<style>body{font:16px system-ui;max-width:1200px;margin:30px auto;padding:0 20px}'
        'article{border-top:1px solid #ccc;padding:20px 0}img{max-width:100%;max-height:650px;object-fit:contain}</style>',
        '<h1>plant → LL-BTS → supervisor → closed-loop system</h1>',
        '<p><a href="online_offline_index.html">Online LL-BTS / 传统 Offline BTS 与闭环对比</a></p>',
        '<p><a href="系统事件属性与修改意见.md">系统事件属性与修改意见</a> · <a href="运行结果.md">运行结果分析</a></p>',
        '<p>直接读取每例 plant.json 和 ll_bts.json 的保留边提取策略，未重新综合替代原始 LL-BTS。'
        f'{sum(r["status"]=="winning" for r in bench_rows)}例各提供一个可执行的观测反馈 supervisor 和对应的完整可达闭环；'
        f'{sum(r["status"]=="losing" for r in bench_rows)}例不可解。'
        'Qe安全终端使用允许全部事件的认证延续。每份JSON保存原始文件SHA256以核对来源。</p>',
        '<p><a href="closed_loop_summary.csv">汇总CSV</a></p>']

    for r in bench_rows:
        name = r['name']
        bench_parts += [f'<article><h2>{html.escape(name)}</h2><p>{r["status"]} · u={r["u"]} · '
            f'闭环状态{r["closed_loop_states"]} · 转移{r["closed_loop_transitions"]}</p>',
            f'<a href="{name}/closed_loop_system_online.svg"><img src="{name}/closed_loop_system_online.png"></a>',
            f'<p><a href="{name}/plant.png">plant</a> · <a href="{name}/ll_bts.png">LL-BTS</a> · '
            f'<a href="{name}/supervisor.json">supervisor JSON</a> · '
            f'<a href="{name}/closed_loop_system_online.json">closed-loop JSON</a></p>']

        if r['status'] == 'winning':
            bench_parts += [f'<details><summary>监督器图</summary><img src="{name}/supervisor.png"></details>']

        bench_parts.append('</article>')

    (BENCH/'closed_loop_index.html').write_text('\n'.join(bench_parts), encoding='utf-8')
    (OUT/'README.txt').write_text('打开 index.html 查看全部闭环图。\n'
        'winning：可达物理状态与观测反馈控制器记忆的乘积，包含全部允许事件的演化。\n'
        'losing：不存在认证的无死锁监督控制器，故没有伪造闭环图。\n'
        '每例 closed_loop_system_online.json 保存控制器、闭环转移、禁用事件和策略选择规则。\n'
        '此处固定执行一次求解得到的认证策略，安全终端允许全部事件；不模拟每次观测后的重新规划。\n'
        '项目部分观测封装使用 original_dfa，即实际DFA，不将绘图用observer作为被控对象。\n'
        '复现：python -X utf8 scripts/reporting/draw_closed_loops.py\n', encoding='utf-8')

    with zipfile.ZipFile(OUT.parent/'closed_loop_systems.zip', 'w', zipfile.ZIP_DEFLATED) as archive:
        for p in OUT.rglob('*'):
            if p.is_file():archive.write(p, p.relative_to(OUT.parent))

    print('FINISHED', len(rows), dict(Counter(r['status'] for r in rows)), flush=True)


if __name__ == '__main__':main()
