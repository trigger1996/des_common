"""Explicit paper-figure variants without changing the user's current models."""

from dataclasses import replace
from des_core.automata import DFA
from examples.non_deadlock import build_nested_cycle_deadlock_example, build_small_cycle_example


def relabel(example, source, old_event, new_event, target, name):
    p = example.dfa;edges = dict(p.transitions)
    assert edges[source, old_event] == target and (source, new_event) not in edges
    del edges[source, old_event];edges[source, new_event] = target

    return replace(example, name=name, dfa=DFA(p.states, p.initial, p.events, p.controllable, p.observable, edges))


def paper_small_figure():
    # Read directly from Figs/dfa_example_2.pdf: q10 --o2--> q6.
    return relabel(build_nested_cycle_deadlock_example(), 'q_10', 'o1', 'o2', 'q_6', 'paper_small_figure')


def archived_component_figure():
    # Old Figs/example_1.pdf predates the user's q2 --a--> q0 correction.
    return relabel(build_small_cycle_example(), 'q_2', 'a', 'o1', 'q_0', 'archived_component_figure')


def u5_u6_annotation():
    """Shared clarification for the result document and paper-rerun report."""

    return '\n'.join([
        '### u=5的安全性、固定窗口与滚动重规划', '',
        '**u=5已经能保证该例子在已认证supervisor下deadlock-free。** 当前策略初始允许{a,o2}、禁用b，完整可达闭环有6个状态、7条边，逐个状态均有允许出边。保证来自这个模型和这套认证策略，不能只凭u=5就认为任意控制选择都安全。', '',
        '**u=6进一步恢复offline初始极大模式。** 在从q0开始的一次固定窗口求解中，u=5保守地排除初始允许b的模式；u=6恢复{a,b,o2}。这是宽松程度的差异，并不是u=5闭环有死锁。', '',
        '若假设初始允许b，可能出现路径：', '',
        '`q0 ─a→ q1 ─a→ q2 ─b→ q4 ─o1→ q8 ─u→ q9 ─a→ q10`', '',
        'q10距最初q0是6步，超出以q0构建的u=5窗口。这解释了当前单次固定窗口认证为何保守排除b。该路径不属于初始已经禁用b的u=5认证策略。', '',
        '**观察后要更新完整估计并重新求UR。** 在上述假设允许b的分支中，第一次观察到o1可能来自q3→q6、q4→q8或q5→q11，因此NX后的估计是{q6,q8,q11}，不能只凭o1确定实际为q8。',
        '随后选择新的控制模式：允许a、禁用b和o2，再求UR，得到{q6,q7,q8,q9,q10,q11}。若以这个新估计重新建立u=5窗口，q10已经位于窗口内；实际重新调用求解器得到winning。', '',
        '**两种调用必须区分：** solve_limited_lookahead的一次调用仅从传入的初始估计建一次窗口，同次调用中排队的后续决策估计共享该窗口。观察后再次调用求解器，才会以更新的完整估计重新建窗；Limited_Lookahead_Controller执行时采用后一种更新方式并保留认证延续。',
        '因此，“u=6才恢复offline初始极大模式”只描述当前从q0开始的单次固定窗口求解结果，不能推断滚动重规划也必须使用u=6。后续一次winning也不能单独替代跨步策略的完整安全认证。', ''])
