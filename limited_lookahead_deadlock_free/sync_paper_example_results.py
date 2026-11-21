"""Synchronize verified rerun evidence into the active manuscript."""

import json
from pathlib import Path
import shutil

import matplotlib

matplotlib.use('Agg')
matplotlib.rcParams['pdf.fonttype'] = 42
import matplotlib.pyplot as plt
import networkx as nx

PAPER = Path('[paper]Limited Lookadhead Deadlock-free')
RESULTS = Path('outputs/paper_examples_rerun')


def draw_certified_comparison(path):
    fig, axes = plt.subplots(2, 1, figsize=(3.5, 5.4))

    for ax, name, panel in zip(axes, ('paper_small_figure', 'paper_small_figure_u6'), ('(a) u=5', '(b) u=6')):
        data = json.loads((RESULTS/name/'ll_bts.json').read_text(encoding='utf-8'))
        graph = nx.DiGraph()
        graph.add_nodes_from(n['id'] for n in data['D']+data['O'])
        graph.add_edges_from((a, b) for a, b, e in data['edges'])
        distance = nx.single_source_shortest_path_length(graph, data['initial']);layers = {}

        for node in graph:layers.setdefault(distance.get(node, max(distance.values())+1), []).append(node)

        pos = {node:(level*2, (i-(len(nodes)-1)/2)*1.1) for level, nodes in layers.items() for i, node in enumerate(nodes)}

        for group, shape, color in ((data['D'], 's', '#d1e6f4'), (data['O'], 'o', '#f8e4b6')):
            nx.draw_networkx_nodes(graph, pos, nodelist=[n['id'] for n in group], node_shape=shape, node_color=color, node_size=260,
                edgecolors=['#253e50' if n['retained'] else '#b43c3c' for n in group], ax=ax)

        nx.draw_networkx_labels(graph, pos, font_size=7, ax=ax)
        nx.draw_networkx_edges(graph, pos, node_size=260, arrowsize=9, connectionstyle='arc3,rad=0.07', ax=ax)
        labels = {}

        for a, b, e in data['edges']:labels[a, b] = labels.get((a, b), '')+(',' if (a, b) in labels else '')+e

        nx.draw_networkx_edge_labels(graph, pos, edge_labels=labels, font_size=6, rotate=False, ax=ax)
        ax.set_title(panel+f" | D={len(data['D'])}, O={len(data['O'])}", fontsize=8)
        ax.axis('off');ax.margins(.18, .28)

    fig.tight_layout();fig.savefig(path);fig.savefig(RESULTS/'certified_ll_bts_comparison.png', dpi=170);plt.close(fig)


def main():
    summary = json.loads((RESULTS/'summary.json').read_text(encoding='utf-8'))
    rows = {r['name']:r for r in summary['small_models']}
    assert rows['paper_small_figure']['status'] == 'winning' and not rows['paper_small_figure']['same_root_patterns']
    assert rows['paper_small_figure_u6']['same_root_patterns']
    product = summary['products']['product_current'];candidate = product['verified_controller']
    assert candidate['states'] == 6561 and candidate['edges'] == 52488
    assert all(not r['complete'] for r in product['certified_attempts'])
    original = (PAPER/'main.tex').read_text(encoding='utf-8')
    backup = Path('tmp/paper_examples_before_sync');backup.mkdir(parents=True, exist_ok=True)

    for relative in ('main.tex', 'Figs/example_1.pdf', 'Figs/ll_bts_example_2.pdf', 'Figs/visited_states_example_1.pdf'):
        target = backup/relative;target.parent.mkdir(parents=True, exist_ok=True)

        if not target.exists():shutil.copy2(PAPER/relative, target)

    draw_certified_comparison(PAPER/'Figs/ll_bts_example_2_rerun.pdf')
    shutil.copy2(RESULTS/'component_current_code/component_current.pdf', PAPER/'Figs/example_1_rerun.pdf')
    shutil.copy2(RESULTS/'product_current/visited_states_rerun.pdf', PAPER/'Figs/visited_states_example_1_rerun.pdf')
    small_start = ('We first reconsider the DFA shown in Fig.~' if 'We first reconsider the DFA shown in Fig.~' in original
                 else 'We first consider the DFA shown in Fig.~')
    start = original.index(small_start)
    end = original.index('% \\subsection{Large-Scale Product Example}', start)
    small_text = r"""We first reconsider the DFA shown in Fig.~\ref{fig:case_1_dfa},
using exactly the labels in that figure, including
$q_{10}\mathrel{\mathop{\longrightarrow}^{o_2}}q_6$.
The updated implementation retains complete observation estimates and checks
complete $\operatorname{UR}$ and $\operatorname{NX}$ successors.
At $u=5$, the certified LL-BTS contains $3$ decision nodes and $6$ observation
nodes and yields a deadlock-free supervisor; the selected reachable closed loop
has $6$ states and $7$ transitions. However, its initial maximal pattern is
$\{a,o_2\}$, whereas the complete offline BTS admits $\{a,b,o_2\}$.
Thus feasibility agreement at this depth does not imply agreement of maximal
control patterns.

This comparison concerns one call of the certified solver: its window is
built once around the initial estimate at $q_0$ and is shared by subsequent
decision estimates explored within that call. If $b$ were initially enabled,
one possible path would be
\[
\begin{aligned}
q_0&\xrightarrow{a}q_1\xrightarrow{a}q_2\xrightarrow{b}q_4\\
   &\xrightarrow{o_1}q_8\xrightarrow{u}q_9\xrightarrow{a}q_{10}.
\end{aligned}
\]
State $q_{10}$ is six transitions from $q_0$, outside this initial $u=5$
window. Without an applicable safety certificate for that boundary, the
initial mode enabling $b$ is conservatively excluded. At $u=6$, $q_{10}$
is included and that branch can be certified. The selected $u=5$ supervisor
already guarantees deadlock-freeness by initially disabling $b$; its verified
closed loop therefore does not traverse the hypothetical branch above.

Replanning after an actual observation is a different call. If $b$ had been
allowed initially, observing $o_1$ would give the full estimate
$E=\{q_6,q_8,q_{11}\}$, not the known physical state $q_8$.
With the next controllable pattern $\{a\}$ (disabling $b$ and $o_2$),
the new unobservable reach is
$\operatorname{UR}(E)=\{q_6,q_7,q_8,q_9,q_{10},q_{11}\}$.
A new window centered on $E$ with $u=5$ includes $q_{10}$; our separate
recentered solve returns winning. Thus the initial fixed-window result
does not imply that receding-window replanning requires $u=6$.
The guarantee applies to a certified control policy, not to arbitrary
choices made solely because the horizon equals five; a later winning
solve alone is not a certificate for an entire cross-step policy.

Increasing the depth to $u=6$ restores the offline initial maximal patterns.
The LL-BTS then has $4$ decision nodes and $8$ observation nodes; the selected
reachable closed loop has $14$ states and $19$ transitions.
Figure~\ref{fig:case_1_ll_bts} compares the two certified constructions.
These closed-loop counts include the controller memory and all permitted event
evolutions, rather than a single selected physical trajectory.

%
"""
    updated = original[:start]+small_text+original[end:]
    updated = updated.replace('{Figs/ll_bts_example_2.pdf}', '{Figs/ll_bts_example_2_rerun.pdf}')
    old_caption = r'\caption{(a)--(c) LL-BTSs constructed in three consecutive online iterations with $u=5$. The initial state in (b) and (c) is the selected successor reached in the preceding iteration shown in (a) and (b), respectively.}'
    new_caption = r'\caption{Certified LL-BTS constructions for the DFA in Fig.~\ref{fig:case_1_dfa}: (a) $u=5$ and (b) $u=6$. Boxes denote decision nodes and circles observation/control nodes. IDs refer to the complete estimates and control patterns recorded in the accompanying JSON exports; red borders denote pruned nodes.}'
    assert old_caption in updated or new_caption in updated
    updated = updated.replace(old_caption, new_caption)
    updated = updated.replace('{Figs/example_1.pdf}', '{Figs/example_1_rerun.pdf}')
    large_start = ('For the product experiment, the component in Fig.~' if 'For the product experiment, the component in Fig.~' in updated
                 else 'To demonstrate the scalability of our method,')
    start = updated.index(large_start)
    end = updated.index(r'\begin{figure}[t]', start)
    large_text = r"""For the product experiment, the component in Fig.~\ref{fig:case_2}
uses the corrected return transition
$q_2\mathrel{\mathop{\longrightarrow}^{a}}q_0$.
Eight independent asynchronous copies yield
$|Q_{\mathrm{product}}|=6^8=1679616$ reachable plant states.
Each indexed event updates only its owning coordinate and retains the
component's controllability and observability.

We reran the historical physical-root window implementation at $u=3$ for
$50$ queries with cross-query caching disabled.
"""
    large_text += 'The queries completed in '+str(round(product['legacy']['elapsed_seconds'], 6))+' seconds. '
    large_text += r"""This is a reproduction of its search workload, not a certificate
for a partially observed global supervisor: the historical implementation
starts each query from a selected physical state rather than carrying the
complete observation estimate. Figure~\ref{fig:case_product_visited} therefore
reports query-state coverage only.

The current estimate-based certified solver was tested separately at $u=3$
and at the compositional preprocessing threshold $u=7$.
With a budget of $5000$ control-mode checks, $25000$ materialized window states,
and $3$ seconds, both online attempts and the independent traditional BTS
attempt stopped at the mode-check budget. This truncation is neither a proof
of infeasibility nor a completed maximal-supervisor synthesis.

A feasible supervisor can nevertheless be verified completely for this
corrected product: disable every $o_{1,i}$ and allow all remaining events.
Each coordinate then stays on the cycle
$q_0\mathrel{\mathop{\longrightarrow}^{o_2}}q_1
\mathrel{\mathop{\longrightarrow}^{b}}q_2
\mathrel{\mathop{\longrightarrow}^{a}}q_0$.
The reachable closed loop has $3^8=6561$ states and $8\cdot3^8=52488$
transitions. We enumerated all these states and transitions, verified that
each state has an allowed successor, and checked that no uncontrollable event
is disabled. This proves feasibility of the stated constant supervisor;
global maximal permissiveness is not claimed.

"""
    composition = product.get('compositional_supervisor')

    if composition:
        large_text += r"""We additionally synthesized a factored observation-feedback supervisor by
composing independently certified component supervisors.
Its reachable physical plant states number $4^8=65536$.
Including controller memory, the exact factored closed loop has
$8^8=16777216$ state--memory pairs and $150994944$ transitions.
Every reachable component state--memory pair and allowed event was checked.
Disjoint indexed alphabets then imply that every global tuple has an allowed
successor and all uncontrollable events remain enabled. We also checked
one-, two-, and three-copy products exhaustively and executed $100000$
steps with the exported eight-copy controller. This is a compositional
certificate for the whole product, not an explicit construction of its
complete global BTS or a proof of globally maximal permissiveness.

"""

    updated = updated[:start]+large_text+updated[end:]
    updated = updated.replace('{Figs/visited_states_example_1.pdf}', '{Figs/visited_states_example_1_rerun.pdf}')
    updated = updated.replace(r'\caption{Local and cumulative numbers of product states visited during the online computation for the large-scale system.}',
        r'\caption{Local and cumulative concrete states visited by the rerun historical physical-root window queries ($u=3$, $50$ queries). These coverage counts are not the size of a certified global LL-BTS or closed loop.}')
    assert (PAPER/'main.tex').read_text(encoding='utf-8') == original, 'Manuscript changed during synchronization'
    (PAPER/'main.tex').write_text(updated, encoding='utf-8')
    (RESULTS/'MANUSCRIPT_SYNC.md').write_text(
        '# 论文结果同步\n\n已更新活动主文 '+str(PAPER/'main.tex')+' 的两项case study。原主文与旧图备份在 tmp/paper_examples_before_sync/。\n\n'
        '小例子采用论文图的o2标签，分别报告u=5认证策略的无死锁保证与u=6的初始根极大模式一致性，并区分一次固定窗口求解和观察后围绕完整新估计重新建窗；后者u=5也可认证。乘积分量图同步为用户此前修正的a返回边。\n\n'
        '八副本50次历史查询明确为工作量复现；认证求解预算截断与独立可行常量策略分开说明。未改动main_original.tex或__paper归档。\n',
        encoding='utf-8')
    print('Synchronized', PAPER/'main.tex')


if __name__ == '__main__':main()
