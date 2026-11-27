"""Render saved comparison data; no re-timing or synthesis."""

# Allow direct execution from the project working directory.
if __package__ in (None, ""):
    import sys as _sys
    from pathlib import Path as _Path
    _sys.path.insert(0, str(_Path(__file__).resolve().parents[2]))


import html
import json
from pathlib import Path

import matplotlib

matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.ticker import PercentFormatter
import networkx as nx

ROOT = Path('outputs/expanded_yin_benchmark')


def main():
    rows = json.loads((ROOT/'online_offline_comparison.json').read_text(encoding='utf-8'))
    ordered = sorted(rows, key=lambda r:r['time_saving_including_pre'])
    fig, axes = plt.subplots(1, 2, figsize=(18, 23), sharey=True)
    positions = list(range(len(ordered)))

    for ax, key, title in zip(axes, ('time_saving_including_pre', 'peak_memory_saving'),
        ('Measured time saving (preprocessing + online)', 'Measured Python allocation peak saving')):
        values = [r[key] for r in ordered]
        ax.barh(positions, values, color=['#328460' if x >= 0 else '#bd5555' for x in values])
        ax.axvline(0, color='#333333', lw=.9);ax.xaxis.set_major_formatter(PercentFormatter(1))
        ax.grid(axis='x', alpha=.2);ax.set_title(title);ax.set_axisbelow(True)

    axes[0].set_yticks(positions, [r['name'] for r in ordered], fontsize=8)
    fig.suptitle(f'{len(rows)} models | Traditional known-system BTS vs certified online LL-BTS\n'
                 '11 alternating fresh solves per model; negative values retained; ratios are not asymptotic complexity claims', fontsize=13)
    fig.tight_layout(rect=(0, 0, 1, .97));fig.savefig(ROOT/'online_offline_savings.png', dpi=130)
    fig.savefig(ROOT/'online_offline_savings.svg');plt.close(fig)

    parts = ['<!doctype html><meta charset="utf-8"><title>Online / Offline 对比</title>',
        '<style>body{font:16px system-ui;max-width:1400px;margin:30px auto;padding:0 24px}'
        'article{border-top:1px solid #ccc;margin:25px 0;padding-top:12px}.pair{display:flex;gap:15px;align-items:flex-start}'
        '.pair figure{width:49%;margin:0}img{width:100%;max-height:550px;object-fit:contain}a{color:#075eab}</style>',
        '<h1>Online LL-BTS / Offline BTS 对比</h1>',
        '<p>Offline 按完整已知系统计算 UR/NX，建立完整 BTS 后剪枝，不用前视或 Qf/Qe 证书。'
        '每例独立提取 supervisor，并生成完整可达 closed_loop_system_offline。'
        'Online 的一次性总时间计入预处理。u 的实验标定、模型读取与图形导出不计入求解计时。</p>',
        '<p><a href="ONLINE_OFFLINE_COMPARISON.md">方法、复杂度与汇总报告</a> · '
        '<a href="系统事件属性与修改意见.md">事件属性与修改意见</a> · <a href="运行结果.md">运行结果分析</a> · '
        '<a href="online_offline_comparison.csv">详细CSV</a> · '
        '<a href="large_systems/LARGE_SYSTEM_COMPARISON.md">大系统实验</a> · '
        '<a href="large_literature_supervisors.html">论文乘积千万状态运行与估算</a> · '
        '<a href="online_offline_savings.svg">节约率图</a></p>']

    for r in rows:
        name = r['name'];folder = ROOT/name
        parts += [f'<article id="{name}"><h2>{html.escape(name)}</h2>',
            f'<p>{r["status"]} · u={r["u"]} · 含预处理时间节约 {r["time_saving_including_pre"]:.1%} · '
            f'Python峰值节约 {r["peak_memory_saving"]:.1%} · '
            f'构建节点 online {r["online_nodes"]} / offline {r["offline_nodes"]}</p>',
            f'<p>可解性判定：Online {r["online_status"]} / Offline {r["offline_status"]}；'
            f'一致性：{"一致" if r["same_solvability_result"] else "不一致或未完成"}。</p>',
            '<table><tr><th>指标</th><th>Online</th><th>Offline</th><th>绝对节约（Offline−Online）</th><th>节约率（差值÷Offline）</th></tr>'
            f'<tr><td>构建信息节点D+O</td><td>{r["online_nodes"]} ({r["online_D"]}/{r["online_O"]})</td>'
            f'<td>{r["offline_nodes"]} ({r["offline_D"]}/{r["offline_O"]})</td><td>{r["nodes_saved"]}</td>'
            f'<td>{r["node_saving"]:.3%}</td></tr>'
            f'<tr><td>含预处理总时间/ms</td><td>{r["online_total_median_seconds"]*1000:.6f}</td>'
            f'<td>{r["offline_median_seconds"]*1000:.6f}</td><td>{r["time_saved_ms"]:.6f}</td>'
            f'<td>{r["time_saving_including_pre"]:.3%}</td></tr>'
            f'<tr><td>Python峰值/KiB</td><td>{r["online_peak_python_bytes"]/1024:.3f}</td>'
            f'<td>{r["offline_peak_python_bytes"]/1024:.3f}</td><td>{r["memory_saved_KiB"]:.3f}</td>'
            f'<td>{r["peak_memory_saving"]:.3%}</td></tr></table>',
            f'<p><a href="{name}/plant.png">原始系统</a> · <a href="{name}/ll_bts.png">Online LL-BTS 图</a> · '
            f'<a href="{name}/offline/bts.json">Offline BTS JSON</a> · '
            f'<a href="{name}/offline/bts.dot">Offline BTS DOT</a> · '
            f'<a href="{name}/online_offline_comparison.json">完整测量与口径</a></p>']

        if (folder/'offline/bts.png').exists():
            parts.append(f'<details><summary>Offline BTS 图</summary><img src="{name}/offline/bts.png"></details>')

        parts.append('<div class="pair">')

        for mode in ('online', 'offline'):
            directory = f'{name}/offline' if mode == 'offline' else name
            parts.append(f'<figure><figcaption>{mode} closed-loop system</figcaption>'
                f'<a href="{directory}/closed_loop_system_{mode}.svg"><img src="{directory}/closed_loop_system_{mode}.png"></a>'
                f'<p><a href="{directory}/closed_loop_system_{mode}.json">完整闭环转移</a></p></figure>')

        parts.append('</div>')

        if r['status'] == 'winning':
            parts.append(f'<details><summary>Offline supervisor</summary><img src="{name}/supervisor_offline.png">'
                f'<p><a href="{name}/supervisor_offline.json">控制器数据</a></p></details>')

        parts.append('</article>')

    (ROOT/'online_offline_index.html').write_text('\n'.join(parts), encoding='utf-8')
    render_large_overviews()


def render_large_overviews():
    root = ROOT/'large_systems'

    for folder in root.glob('large_*'):
        if not (folder/'comparison.json').exists():continue

        row = json.loads((folder/'comparison.json').read_text(encoding='utf-8'));n = row['states']
        graph = nx.DiGraph()

        if row['status'] == 'losing':
            labels = {'a':'q0', 'b':f'chain of {n-2:,} intermediate states', 'c':f'q{n-1}\nterminal'}
            graph.add_edges_from([('a', 'b'), ('b', 'c')]);pos = {'a':(0, 0), 'b':(2.5, 0), 'c':(5, 0)}
        else:
            labels = {'a':'q0', 'b':f'chain of {n-4:,} intermediate states', 'c':f'q{n-3}',
                    'd':f'q{n-2}', 'e':f'q{n-1}'}
            graph.add_edges_from([('a', 'b'), ('b', 'c'), ('c', 'd'), ('d', 'e'), ('e', 'c')])
            pos = {'a':(0, 0), 'b':(2.8, 0), 'c':(5.6, 0), 'd':(7, 1.4), 'e':(8.4, 0)}

        fig, ax = plt.subplots(figsize=(15, 4.3))
        nx.draw_networkx(graph, pos, labels=labels, node_shape='s', node_size=3100, font_size=9,
                         ax=ax, node_color='#d9e8f2', arrowsize=20)
        ax.set_title(f'{row["name"]} | {n:,} reachable states\nStructural overview, not a full unrolled graph; complete tables and BTS arrays are stored alongside')
        ax.margins(.15, .3);ax.axis('off');fig.tight_layout()
        fig.savefig(folder/'structural_overview.png', dpi=150);fig.savefig(folder/'structural_overview.svg')
        plt.close(fig)


if __name__ == '__main__':main()
