"""All six plant/language automata drawn in Yin & Lafortune, TAC 2016.

Source: https://xiangyin.sjtu.edu.cn/Paper/16TACuniform.pdf
Fig. 1(a-c), p. 2143; Fig. 3(a-c), p. 2151. Fig. 2(a-b) and
Fig. 3(d) are BTS/AES controllers, not partially-observed plant DFAs.
Dashed disabled edges in Fig. 1(b,c) are NOT plant transitions.
"""

from collections import deque
from des_core.automata import DESExample, DFA


def _dfa(states, initial, events, controllable, observable, edges):
    transitions = {(q, e): t for q, e, t in edges}
    assert len(transitions) == len(edges), 'nondeterministic transcription'

    return DFA(frozenset(states), initial, frozenset(events), frozenset(controllable),
               frozenset(observable), transitions)


def build_tac2016_uniform_examples() -> tuple[DESExample, ...]:
    events1, controls1, observed1 = ('a', 'b', 'c', 'e', 'o1', 'o2'), ('a', 'b', 'c'), ('o1', 'o2')
    edges1 = [('0', 'b', '1'), ('0', 'c', '3'), ('1', 'e', '1'), ('1', 'a', '2'),
              ('2', 'o1', '2'), ('2', 'o2', '5'), ('3', 'a', '4'), ('3', 'o1', '5'),
              ('4', 'o1', '6'), ('5', 'o1', '5'), ('6', 'o1', '6')]
    g1a = _dfa(map(str, range(7)), '0', events1, controls1, observed1, edges1)
    states1b = {'0', '3', '4', '5', '6'}
    g1b = _dfa(states1b, '0', events1, controls1, observed1,
               [edge for edge in edges1 if edge[0] in states1b and edge[2] in states1b])
    g1c = _dfa({'0', '1'}, '0', events1, controls1, observed1,
               [('0', 'b', '1'), ('1', 'e', '1')])
    events3, controls3, observed3 = ('a', 'b', 'c', 'd', 'e', 'f', 'o'), ('b', 'o'), ('a', 'c', 'd', 'o')
    edges3 = [('0', 'f', '1'), ('0', 'a', '2'), ('0', 'b', '2'), ('1', 'a', '3'),
              ('2', 'a', '4'), ('3', 'o', '3'), ('3', 'c', '5'), ('4', 'o', '4'),
              ('4', 'd', '5'), ('5', 'e', '5')]
    g3a = _dfa(map(str, range(6)), '0', events3, controls3, observed3, edges3)
    # Eq. (22), K=2: increment on EVERY event after failure; -1 before failure.
    start, seen, queue, edges = ('0', -1), {('0', -1)}, deque([('0', -1)]), []
    label = lambda pair: '%s^%d' % pair

    while queue:
        q, n = queue.popleft()

        for event, target in g3a.enabled(q):
            k = (-1 if event != 'f' else 0) if n == -1 else min(n + 1, 2)
            pair = (target, k)
            edges.append((label((q, n)), event, label(pair)))

            if pair not in seen:
                seen.add(pair)
                queue.append(pair)

    g3b = _dfa(map(label, seen), label(start), events3, controls3, observed3, edges)
    g3c = _dfa({'0', '1', '2', "2'", '3', '4', "4'", '5'}, '0',
               events3, controls3, observed3,
               [('0', 'f', '1'), ('0', 'a', '2'), ('0', 'b', "2'"),
                ('1', 'a', '3'), ('2', 'a', '4'), ("2'", 'a', "4'"),
                ('3', 'c', '5'), ('4', 'o', '4'), ('4', 'd', '5'),
                ("4'", 'd', '5'), ('5', 'e', '5')])
    items = [('1a', g1a, 'System G; opacity example'),
             ('1b', g1b, 'Controlled solution G1; disabled b edge omitted'),
             ('1c', g1c, 'Controlled solution G2; disabled a,c edges omitted'),
             ('3a', g3a, 'System G; diagnosis example'),
             ('3b', g3b, 'Unfolded GD, K=2, Eq. (22)'),
             ('3c', g3c, 'Controlled language L(S*/G); primed states retained')]

    return tuple(DESExample('16TACuniform_fig_' + name, dfa, {}, description,
                            source_name='Yin & Lafortune (2016), Fig. ' + name)
                 for name, dfa, description in items)
