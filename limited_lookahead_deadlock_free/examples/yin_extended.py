"""Figure-audited additions from the 2026-11-21 literature search.

Only transition topology is reused: weights, marks, attacks, delays, and secrecy
are not objectives in this deadlock-free benchmark. The few verification-only
examples explicitly introduce a control partition; they are not reproductions
of a control experiment in the source paper.
"""

from des_core.automata import DESExample
from examples.tac2016_uniform import _dfa


def build_yin_extended_examples():
    examples = []

    def add(paper, fig, page, initial, controls, observed, edges, note='', states=None):
        events = set(controls) | set(observed) | {e for _, e, _ in edges}
        states = states or ({q for q, _, _ in edges} | {t for _, _, t in edges})
        plant = _dfa(states, initial, events, controls, observed, edges)
        examples.append(DESExample(paper+'_fig_'+fig, plant, {}, note,
            source_name=f'{paper}.pdf, Fig. {fig}, PDF p.{page}'))

    # epsilon in this transformation is an explicit unobservable output-symbol
    # event in Delta_epsilon, not an invented self-loop or an epsilon-elimination.
    mealy = [('0', 's1', '0_s1'), ('0', 's2', '0_s2'),
             ('0_s1', 'd1', '1'), ('0_s1', 'd2', '1'), ('0_s2', 'd1', '2'),
             ('1', 's1', '1_s1'), ('1', 's2', '1_s2'), ('1_s2', 'd1', '2'),
             ('1_s1', 'd1', '3'), ('1_s1', 'eps', '3')]
    note = ('s1,s2=source sigma1,sigma2; d1,d2=delta1,delta2; eps is the '
            'explicit hidden symbol in Delta_epsilon. Marked terminal states retained.')
    add('17Mealy', '2a', 4, '0', ('s1', 's2'), ('d1', 'd2'),
        mealy+[('2', 's2', '2_s2'), ('2_s2', 'd2', '4')], note)
    add('17Mealy', '2b', 4, '0', ('s1', 's2'), ('d1', 'd2'), mealy, note)
    split = [edge for edge in mealy if edge != ('0_s1', 'd1', '1')]
    split += [('0_s1', 'd1', "1'"), ("1'", 's1', '1_s1')]
    add('17Mealy', '3a', 5, '0', ('s1', 's2'), ('d1', 'd2'), split, note)
    add('17Mealy', '3b', 5, '0', ('s1', 's2'), ('d1', 'd2'),
        [edge for edge in mealy if edge[0] != '0_s2' and edge != ('0', 's2', '0_s2')], note)

    add('22TAConline', '2', 5, '1', ('a', 'b', 'u1', 'u2', 'u3'), ('a', 'b'),
        [('1', 'a', '2'), ('2', 'u3', '3'), ('3', 'u2', '5'), ('5', 'a', '8'),
         ('8', 'b', '16'), ('8', 'a', '10'), ('2', 'u1', '4'), ('4', 'u2', '15'),
         ('4', 'a', '6'), ('6', 'b', '7'), ('6', 'a', '9'), ('9', 'u1', '11'),
         ('9', 'u2', '12'), ('11', 'a', '13'), ('12', 'b', '14'),
         ('13', 'b', '17'), ('14', 'a', '17')],
        'Plant topology and partitions only; control-channel delay Nc=1 is not simulated.')
    add('22TAClocal', '2', 4, 'x0', tuple('abcdef'),
        tuple('abcdef')+tuple('u%d'%i for i in range(1, 7)),
        [('x0', 'u1', 'x1'), ('x1', 'a', 'x2'), ('x2', 'd', 'x1'),
         ('x1', 'b', 'x3'), ('x3', 'c', 'x4'), ('x4', 'u4', 'x5'), ('x5', 'u6', 'x1'),
         ('x1', 'u2', 'x6'), ('x6', 'e', 'x7'), ('x7', 'u3', 'x1'),
         ('x7', 'f', 'x8'), ('x8', 'u5', 'x1')],
        'Full observation as stated on PDF p.3; weights ignored. Unsafe x8 is NOT '
        'a deadlock: its original u5 return edge is preserved.')

    add('24AutoOpt', '1', 4, 'q0', ('a', 'b', 'c'), ('a', 'b', 'c'),
        [('q0', 'a', 'q1'), ('q0', 'b', 'q1'), ('q1', 'c', 'q1')],
        'Fully observed optimal cyclic-task source; costs and marks ignored.')
    add('24AutoOpt', '2', 5, 'q0', ('a',), ('a', 'd', 'e'),
        [('q0', 'a', 'q1'), ('q1', 'd', 'q0'), ('q0', 'e', 'q2'), ('q2', 'a', 'q0'),
         ('q1', 'a', 'q3'), ('q1', 'e', 'q2'), ('q2', 'e', 'q1'), ('q3', 'e', 'q3'), ('q3', 'd', 'q4'),
         ('q4', 'd', 'q4')], 'Full observation; costs/marked states ignored.')
    ugv = [('q0', 'S', 'q1'), ('q12', 'E', 'q0'), ('q4', 'B', 'q4')]

    for a, b in [(1, 2), (2, 3), (5, 6), (7, 8), (9, 10), (10, 11), (11, 12)]:
        ugv += [('q%d'%a, 'E', 'q%d'%b), ('q%d'%b, 'W', 'q%d'%a)]

    for a, b in [(1, 5), (2, 6), (3, 7), (5, 9), (6, 10), (7, 11), (8, 12)]:
        ugv += [('q%d'%a, 'S', 'q%d'%b), ('q%d'%b, 'N', 'q%d'%a)]

    ugv += [('q8', 'N', 'q4')]
    add('24AutoOpt', '6b', 11, 'q0', ('N', 'S', 'E', 'W'), ('N', 'S', 'E', 'W', 'B'), ugv,
        'UGV component only; B uncontrollable. One-way q8 -> q4 and q12 -> q0 retained.')
    add('24AutoOpt', '6d', 11, 'q0', (), ('Wbar', 'Ebar', 'H'),
        [('q0', 'Wbar', 'q8'), ('q8', 'Wbar', 'q7'), ('q7', 'Wbar', 'q6'),
         ('q6', 'Ebar', 'q7'), ('q7', 'Ebar', 'q8'),
         ('q6', 'H', 'q6'), ('q7', 'H', 'q7'), ('q8', 'H', 'q8')],
        'UAV component only; movement and hovering uncontrollable; overbars renamed.')

    add('21AutomaticaOptimal', '2', 7, 'x0', ('c1', 'c2', 'c3', 'c4', 'c5'),
        ('o1', 'o2', 'o3', 'o4'),
        [('x0', 'a1', 'x1'), ('x0', 'a3', 'x1'), ('x0', 'a2', 'x2'), ('x0', 'a4', 'x2'),
         ('x1', 'o1', 'x3'), ('x2', 'o1', 'x4'), ('x3', 'o1', 'x3'), ('x4', 'o1', 'x4'),
         ('x3', 'c1', 'x5'), ('x4', 'c2', 'x6'), ('x5', 'b1', 'x7'), ('x7', 'o1', 'x3'),
         ('x6', 'b2', 'x8'), ('x8', 'o1', 'x4'), ('x5', 'c2', 'x9'), ('x6', 'c1', 'x10'),
         ('x9', 'o2', 'x12'), ('x12', 'o4', 'x12'), ('x12', 'c3', 'x14'), ('x14', 'c5', 'x9'),
         ('x10', 'o3', 'x13'), ('x13', 'o4', 'x13'), ('x13', 'c4', 'x15'), ('x15', 'b2', 'x10')],
        'Mean payoff weights ignored; inherited Ec and Eo from Example 2, PDF p.7.',
        states={'x%d'%i for i in range(16) if i != 11})

    small = [('1', 'a', '2'), ('2', 'b', '3'), ('3', 'd', '3'),
             ('2', 'c', '4'), ('4', 'd', '5'), ('5', 'b', '6')]
    add('20CDC2', '1a', 3, '1', ('c', 'd'), ('a', 'b', 'd'), small,
        'Nominal G. Attack models and safety objective are not simulated.')
    add('20CDC2', '1b', 3, '1', ('c', 'd'), ('a', 'b', 'd'),
        [(q, 'c_attack' if e == 'c' else e, t) for q, e, t in small],
        'Attacked G_a: c^a renamed c_attack, unobservable and uncontrollable; '
        'partition of nominal c,d inherited only for surviving nominal events.')
    large = [('1', 'a', '2'), ('1', 'b', '3'), ('3', 'a', '5'), ('2', 'a', '4'),
             ('2', 'c', '6'), ('4', 'c', '7'), ('6', 'd', '9'), ('9', 'e', '10'),
             ('6', 'a', '8'), ('8', 'e', '11'), ('7', 'a', '12'), ('12', 'd', '13')]
    add('20CDC2', '2a', 6, '1', ('a', 'b', 'd', 'e'), ('c',), large,
        'All original terminal states retained; no implicit accepting-state loops.')
    keep = {'1', '2', '4', '6', '7', '9', '10'}
    add('20CDC2', '2b', 6, '1', ('a', 'b', 'd', 'e'), ('c',),
        [edge for edge in large if edge[0] in keep and edge[2] in keep],
        'Controlled language Sp/G used as standalone DFA.')
    add('20IFAC1', '1', 2, '0', ('c1', 'c2'), ('o1', 'o2', 'o3'),
        [('0', 'c1', '1'), ('0', 'c2', '3'), ('1', 'c2', '2'), ('3', 'c1', '2'),
         ('2', 'o3', '5'), ('1', 'o1', '5'), ('1', 'o2', '6'), ('3', 'o2', '5'), ('3', 'o1', '6')],
        'Original six-state opacity example; terminal 5,6 retained. Number 4 absent.')

    # A centralized pooled-observation benchmark, explicitly different from the
    # decentralized intersection architecture in the source.
    pooled = 'Centralized union of local partitions: Sigma_c={c}, Sigma_o={a,b,o,c}; '
    pooled += 'not a decentralized-control reproduction. Terminal states retained.'
    sei1 = [('1', 'a', '3'), ('1', 'b', '2'), ('3', 'o', '4'), ('1', 'o', '5'), ('2', 'o', '6'),
          ('4', 'c', '7'), ('5', 'c', '8'), ('6', 'c', '9')]
    add('16SEI', '1a', 3, '1', ('c',), ('a', 'b', 'o', 'c'), sei1, pooled)
    add('16SEI', '1b', 3, '1', ('c',), ('a', 'b', 'o', 'c'),
        [edge for edge in sei1 if edge not in [('4', 'c', '7'), ('6', 'c', '9')]], pooled)
    sei4 = [('1', 'a', '4'), ('1', 'b', '2'), ('2', 'a', '3'), ('4', 'o', '6'),
          ('1', 'o', '5'), ('2', 'o', '7'), ('3', 'o', '8'), ('6', 'c', '9'),
          ('5', 'c', '11'), ('7', 'c', '10'), ('8', 'c', '12')]
    add('16SEI', '4a', 6, '1', ('c',), ('a', 'b', 'o', 'c'), sei4, pooled)
    add('16SEI', '4b', 6, '1', ('c',), ('a', 'b', 'o', 'c'),
        [edge for edge in sei4 if edge not in [('5', 'c', '11'), ('8', 'c', '12')]], pooled)

    introduced = ('Verification source has no control partition. For this deadlock-free '
                'test only, all events are declared controllable; observation partition '
                'and transitions are inherited. No claim of source control reproduction.')
    add('17AutomaticaTW', '1a', 3, '0', ('a', 'b', 'u1', 'u2'), ('a', 'b'),
        [('0', 'u1', '1'), ('0', 'u2', '2'), ('1', 'a', '3'), ('2', 'a', '4'),
         ('3', 'a', '5'), ('4', 'b', '5'), ('5', 'a', '5')], introduced)
    secure = [('0', 'a', '2'), ('0', 'u', '1'), ('1', 'a', '3'), ('2', 'b', '4'),
            ('3', 'b', '5'), ('4', 'c', '6'), ('5', 'c', '7'), ('7', 'b', '6'), ('6', 'a', '6')]
    add('23TACsecure', '2a', 3, '0', ('a', 'b', 'c', 'u'), ('a', 'b', 'c'), secure, introduced)
    add('23TACsecure', '2b', 3, '0', ('a', 'b', 'c', 'u'), ('a', 'b', 'c'),
        secure+[('0', 'c', '2'), ('1', 'c', '5')], introduced)
    add('23TACsecure', '3', 5, '0', ('a', 'u'), ('a',),
        [('0', 'a', '1'), ('1', 'u', '2'), ('2', 'a', '2')], introduced)

    add('23IFAC-attack', '1', 4, 'x0', ('b', 'c', 'd', 'e'), tuple('abcde'),
        [('x0', 'a', 'x1'), ('x1', 'b', 'x2'), ('x2', 'c', 'x3'),
         ('x1', 'd', 'x3'), ('x3', 'e', 'x4')],
        'Full observation from source; attack budget/weights ignored, terminal x4 retained.')
    add('23IFAC-attack', '2b', 5, 'x0', ('a', 'c', 'd'), tuple('abcd'),
        [('x0', 'b', 'x2'), ('x2', 'b', 'x3'), ('x2', 'd', 'x4'), ('x3', 'b', 'x1'),
         ('x1', 'a', 'x3'), ('x3', 'c', 'x4'), ('x4', 'a', 'x5'), ('x4', 'd', 'x6'), ('x5', 'c', 'x6')],
        'Robot topology only, full observation; original terminal x6 retained.')
    add('25LCSSattack', '1', 3, '0', ('a', 'b'), ('a', 'b', 'c'),
        [('0', 'c', '0'), ('0', 'a', '1'), ('0', 'b', '2'), ('1', 'c', '2'),
         ('4', 'b', '1'), ('1', 'b', '4'), ('2', 'a', '3'), ('4', 'a', '3')],
        'Full observation; protection, vulnerability, and attacks ignored for this objective.')

    return tuple(examples)
