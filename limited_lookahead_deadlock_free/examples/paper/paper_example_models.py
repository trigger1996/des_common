"""Explicit paper-figure variants without changing the user's current models."""

# Allow direct execution from the project working directory.
if __package__ in (None, ""):
    import sys as _sys
    from pathlib import Path as _Path
    _sys.path.insert(0, str(_Path(__file__).resolve().parents[2]))


from dataclasses import replace
from des_core.automata import DFA
from examples.non_deadlock import build_nested_cycle_deadlock_example, build_small_cycle_example


def relabel(example, source, old_event, new_event, target, name):
    p = example.dfa;edges = dict(p.transitions)
    assert edges[source, old_event] == target and (source, new_event) not in edges
    del edges[source, old_event];edges[source, new_event] = target

    return replace(example, name=name, dfa=DFA(p.states, p.initial, p.events, p.controllable, p.observable, edges))


def paper_small_figure_original():
    # Read directly from Figs/dfa_example_2.pdf: q10 --o2--> q6.
    return relabel(build_nested_cycle_deadlock_example(), 'q_10', 'o1', 'o2', 'q_6', 'paper_small_figure')


def paper_small_figure_r1():
    """Page 9 of on-the-fly_nb_case.R1.pdf: only add q14-a-q15-b-q16."""

    example = paper_small_figure_original()
    plant = example.dfa
    transitions = dict(plant.transitions)
    transitions['q_14', 'a'] = 'q_15'
    transitions['q_15', 'b'] = 'q_16'
    states = plant.states | frozenset({'q_15', 'q_16'})
    layout = {f'q_{i}': position for i, position in {
        0: (0., 2.), 1: (2., 2.), 2: (4., 2.), 3: (6., 2.),
        4: (2., 0.), 5: (4., 0.), 11: (6., 0.), 6: (8., 0.),
        7: (10., 0.), 12: (12., 0.), 16: (0., 0.),
        15: (0., -2.), 14: (2., -2.), 8: (4., -2.),
        9: (6., -2.), 10: (8., -2.), 13: (10., -2.)}.items()}

    return replace(example, name='paper_fig1_r1',
        dfa=DFA(states, plant.initial, plant.events, plant.controllable, plant.observable, transitions),
        layout=layout,
        description='Original paper DFA with q14--a-->q15--b-->q16; all other transitions unchanged.')


def paper_small_figure_hidden_chain_archive():
    """Extend q7--b-->q12 by four hidden failure-chain states.

    The original cycles and event partitions are preserved. The observable
    entry q6 reaches the last failure state q18 in five hidden transitions,
    making Qf nonempty. Covering Qf union Qd includes q12 one step later,
    so the structural threshold is six under the revised definition.
    """

    example = paper_small_figure_original()
    plant = example.dfa
    transitions = dict(plant.transitions)
    transitions['q_7', 'b'] = 'q_15'

    for index in range(15, 18):
        transitions[f'q_{index}', 'u'] = f'q_{index + 1}'

    transitions['q_18', 'u'] = 'q_12'
    states = plant.states | frozenset(f'q_{index}' for index in range(15, 19))
    layout = dict(example.layout)
    layout.update({f'q_{index}': (10. + 2. * (index - 15), 1.8) for index in range(15, 19)})
    layout['q_12'] = (16., -.8)

    return replace(example, dfa=DFA(states, plant.initial, plant.events,
        plant.controllable, plant.observable, transitions), layout=layout,
        description=example.description + ' Four hidden failure-chain states subdivide q7--b-->q12.')


def paper_small_figure():
    """Current Fig.1, matching reference page 9 and its q14-a-q15-b-q16 addition."""

    return paper_small_figure_r1()


def archived_component_figure():
    # Old Figs/example_1.pdf predates the user's q2 --a--> q0 correction.
    return relabel(build_small_cycle_example(), 'q_2', 'a', 'o1', 'q_0', 'archived_component_figure')


def u5_u6_annotation():
    """Compatibility entry point for the revised window/threshold explanation."""

    return '\n'.join([
        '### 前视阈值、观察后重新建窗与无死锁保证', '',
        '当前实现从Q_f并Q_d执行反向DFS求检测阈值，并在每个完整决策估计处重新建窗。'
        'Q_f仍只包含非死锁的单后继链状态，不将Q_d混入Q_f。', '',
        '原始15状态系统的Q_f为空，但Q_d非空，新阈值bar_u=4；u=4返回winning。'
        '初始选择允许{a,o2}、禁用b，UR={q0,q1,q2,q3}，观察o1后NX={q6}，'
        '随后从{q6}重新建窗，保留q6-a-q7-u-q6的安全循环。', '',
        '当前Fig.1按参考PDF第9页只增加q14-a-q15-b-q16，共17状态，Q_f={q14,q15}，'
        'bar_u=4；u=4得到六状态七转移的无死锁闭环，u=5恢复Full根极大模式。', '',
        '历史四状态长链的19状态版本得到bar_u=6：'
        'q6-a-q7-b-q15-u-q16-u-q17-u-q18-u-q12共六步。'
        '该版本u=4已可得到安全但较保守的初始模式{a,o2}，'
        'u=5恢复offline初始极大模式{a,b,o2}；该历史版本默认从bar_u开始时采用u=6。', '',
        '旧实现所有内部后继共用初始窗口，因此曾记录u=5/6的差异；'
        '这些旧数值不能继续描述重新建窗后的实现。'
        '当前每个保留模式都通过完整UR/NX、逐状态活性及后继一致性检查，'
        '不是先执行模式、再假定下一次重新求解必然成功。', '',
        'bar_u是危险状态检测的充分阈值，不单独等于最小成功前视，也不单独证明综合可解。'
        '即使覆盖Q_f并Q_d，安全不可观测环的完整UR仍可能需要更大的窗口；'
        '程序在尚不能建立完整延续时返回inconclusive并增大实际u。', ''])
