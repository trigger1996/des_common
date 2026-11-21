"""Additional source-faithful DFA transcriptions; no invented terminal loops.

Control/observation partitions are inherited on restricted language automata.
Marked states and secrecy/legality specifications are metadata, not new edges
or a change to the deadlock-free objective. See the generated source manifest.
"""

from des_core.automata import DESExample
from examples.yin2016 import _dfa, build_yin2016_examples


def build_yin_literature_examples(*, amended=True):
    examples = list(build_yin2016_examples())

    def add(paper, fig, states, initial, events, controls, observed, edges, note=''):
        dfa = _dfa(states, initial, events, controls, observed, edges)
        examples.append(DESExample(paper + '_fig_' + fig, dfa, {}, note,
                                   source_name=paper + '.pdf, Fig. ' + fig))

        return dfa

    # ACC 2015 is NOT identical to TAC 2016: there is no e self-loop at 1.
    ev15, c15, o15 = ('a', 'b', 'c', 'o1', 'o2'), ('a', 'b', 'c'), ('o1', 'o2')
    e15 = [('0', 'b', '1'), ('0', 'c', '3'), ('1', 'a', '2'), ('2', 'o1', '2'), ('2', 'o2', '5'),
         ('3', 'a', '4'), ('3', 'o1', '5'), ('4', 'o1', '6'), ('5', 'o1', '5'), ('6', 'o1', '6')]
    add('15ACCopac', '1', map(str, range(7)), '0', ev15, c15, o15, e15,
        'p.379; differs from 16TACuniform: state 1 has no e self-loop')
    qs = {'0', '3', '4', '5', '6'}
    add('15ACCopac', '2a', qs, '0', ev15, c15, o15, [e for e in e15 if e[0] in qs and e[2] in qs],
        'Solution G1, p.379; alphabet excludes e unlike TAC 2016')
    add('15ACCopac', '2b', ('0', '1'), '0', ev15, c15, o15, [('0', 'b', '1')],
        'Solution G2; terminal state 1 retained, dashed a,c edges omitted')
    add('15ACCopac', '2c', ('0', '1', '3', '4', '5', '6'), '0', ev15, c15, o15,
        [e for e in e15 if e[0] != '1' and e[0] != '2'],
        'G3 union-language illustration; not claimed to be a realizable supervisor')

    ev16, c16, o16 = ('c1', 'c2', 'o'), ('c1', 'c2'), ('o',)
    ek16 = [('0', 'o', '1'), ('0', 'c1', '3'), ('3', 'o', '5'), ('1', 'c2', '1'), ('1', 'o', '2'),
          ('5', 'o', '6'), ('2', 'c1', '7'), ('2', 'c2', '8'), ('6', 'c1', '7'), ('6', 'c2', '8')]
    eg16 = ek16+[('5', 'c2', '9'), ('7', 'c2', '9'), ('8', 'c1', '9')]
    add('16CDC', '2a_G', ('0', '1', '2', '3', '5', '6', '7', '8', '9'), '0', ev16, c16, o16, eg16,
        'p.3926, G; numbering skips state 4; state 9 illegal')
    add('16CDC', '2a_K', ('0', '1', '2', '3', '5', '6', '7', '8'), '0', ev16, c16, o16, ek16,
        'K obtained by removing state 9 and incident transitions')
    add('16CDC', '2b', ('0', '1', '2'), '0', ev16, c16, o16,
        [('0', 'o', '1'), ('1', 'c2', '1'), ('1', 'o', '2')], 'Lower-bound R, p.3926')

    ev, c, o = ('a', 'b', 'c', 'o', 'uc'), ('a', 'b', 'c', 'o'), ('o', 'uc')
    add('14IFAC', '1', map(str, range(1, 9)), '1', ev, c, o,
        [('1', 'b', '2'), ('2', 'a', '3'), ('2', 'o', '4'), ('4', 'a', '6'),
         ('4', 'c', '1'), ('6', 'uc', '8'), ('1', 'o', '5'), ('5', 'a', '7')],
        'p.2424; safety specification is separate; states 3,7,8 have no outgoing edges')
    ev, c, o = ('a', 'b', 'c1', 'c2'), ('c1', 'c2'), ('a', 'b')
    k = [('0', 'a', '3'), ('0', 'b', '4'), ('0', 'c1', '1'), ('1', 'b', '3'), ('1', 'a', '4'),
         ('3', 'c1', '5'), ('3', 'c2', '6'), ('4', 'c1', '5'), ('4', 'c2', '6')]
    add('16WODESmax', '1a', ('0', '1', '3', '4', '5', '6'), '0', ev, c, o, k,
        'Specification K reused as a standalone DFA; terminal states retained')
    add('16WODESmax', '1b', ('0', '1', '3', '4', '5', '6', '7'), '0', ev, c, o,
        k + [('5', 'c2', '7'), ('6', 'c1', '7')], 'System G, illegal state 7 retained')
    add('16WODESmax', '2a', ('0', '3', '4', '5', '6'), '0', ev, c, o,
        [('0', 'a', '3'), ('0', 'b', '4'), ('3', 'c1', '5'), ('4', 'c2', '6')],
        'Lower-bound R reused as standalone plant; not a range-control experiment')
    # Refined G': split states carry the previous unobservable choice.
    kg = [('0', 'a', '3'), ('0', 'b', '4'), ('0', 'c1', '1'), ('1', 'b', "3'"), ('1', 'a', "4'"),
          ('3', 'c1', '5'), ('3', 'c2', '6'), ('4', 'c1', "5'"), ('4', 'c2', '6'),
          ("3'", 'c1', "5'"), ("3'", 'c2', "6'"), ("4'", 'c1', "5'"), ("4'", 'c2', "6'"),
          ('5', 'c2', '7'), ("5'", 'c2', '7'), ('6', 'c1', '7'), ("6'", 'c1', '7')]
    add('16WODESmax', '3a_Gprime', ('0', '1', '3', "3'", '4', "4'", '5', "5'", '6', "6'", '7'),
        '0', ev, c, o, kg, 'Refined G, Fig.3(a); event labels retained')
    # TAC 2017 Fig.2 is a related, distinct automaton: uncontrollable u instead
    # of c1 on the initial hidden edge, and states numbered from 1.
    ev17 = ('a', 'b', 'u', 'c1', 'c2')
    k17 = [('1', 'a', '3'), ('1', 'b', '4'), ('1', 'u', '2'), ('2', 'b', '3'), ('2', 'a', '4'),
           ('3', 'c1', '5'), ('3', 'c2', '6'), ('4', 'c1', '5'), ('4', 'c2', '6')]
    add('17TAC-Range', '2a_G', map(str, range(1, 8)), '1', ev17, c, o,
        k17+[('5', 'c2', '7'), ('6', 'c1', '7')], 'p.3918, G; illegal state 7 retained')
    add('17TAC-Range', '2a_K', map(str, range(1, 7)), '1', ev17, c, o, k17,
        'p.3918, K interpreted only as a standalone DFA')
    add('17TAC-Range', '2c', ('1', '3', '4', '5', '6'), '1', ev17, c, o,
        [('1', 'a', '3'), ('1', 'b', '4'), ('3', 'c1', '5'), ('4', 'c2', '6')], 'Lower-bound R')
    ev, c, o = ('a', 'b', 'v', 'w'), ('v', 'w'), ('a', 'b', 'v')
    add('17TAC-Range', '4a', ('1', '3'), '1', ev, c, o,
        [('1', 'a', '3'), ('3', 'v', '1')], 'R, Fig.4(a), p.3922')
    k4 = [('1', 'w', '2'), ('1', 'a', '3'), ('2', 'a', '4'), ('3', 'v', '1'), ('3', 'w', '5'),
          ('4', 'b', '6'), ('5', 'b', '6'), ('6', 'w', '5')]
    add('17TAC-Range', '4b', map(str, range(1, 7)), '1', ev, c, o, k4, 'K, Fig.4(b)')
    add('17TAC-Range', '4c', map(str, range(1, 8)), '1', ev, c, o,
        k4+[('4', 'v', '7'), ('6', 'v', '7')], 'G, Fig.4(c); state 7 has no outgoing transition')
    ev, c, o = ('c1', 'c2', 'u1', 'u2', 'o'), ('c1', 'c2'), ('o',)
    e18 = [('1', 'o', '3'), ('1', 'c1', '2'), ('2', 'o', '4'), ('3', 'c2', '5'), ('4', 'c2', '12'),
           ('5', 'u1', '6'), ('5', 'u2', '7'), ('6', 'o', '8'), ('7', 'o', '9'), ('8', 'o', '8'),
           ('8', 'c2', '10'), ('10', 'o', '8'), ('10', 'c1', '13'), ('9', 'o', '9'),
           ('9', 'c1', '11'), ('11', 'o', '9'), ('11', 'c2', '13')]
    add('18TACrange', '1a', map(str, range(1, 14)), '1', ev, c, o, e18,
        'p.4437, G; marked states are not automatically deadlock-free')
    add('18TACrange', '1b', ('1', '3', '5'), '1', ev, c, o,
        [('1', 'o', '3'), ('3', 'c2', '5')], 'R; original terminal state 5 preserved')
    es = [('1', 'o', '3'), ('3', 'c2', '5'), ('5', 'u1', '6'), ('5', 'u2', '7'), ('6', 'o', '8'),
          ('7', 'o', '9'), ('8', 'o', "8'"), ("8'", 'o', '8'), ("8'", 'c2', '10'), ('10', 'o', '8'),
          ('9', 'o', "9'"), ("9'", 'o', '9'), ('9', 'c1', '11'), ('11', 'o', "9'")]
    add('18TACrange', '3a', ('1', '3', '5', '6', '7', '8', "8'", '9', "9'", '10', '11'),
        '1', ev, c, o, es, 'p.4438, closed-loop language; primed states retained')
    add('18TACrange', '3b', ('1', '2', '3', '4'), '1', ev, c, o,
        [('1', 'o', '3'), ('1', 'c1', '2'), ('2', 'o', '4')], 'Closed-loop language L(S/G)')
    ev, c, o = ('a1', 'a2', 'b1', 'b2', 'c1', 'c2', 'o'), ('c1', 'c2'), ('o',)
    add('16TACNB', '7a', map(str, range(11)), '0', ev, c, o,
        [('0', 'a1', '1'), ('0', 'a2', '2'), ('1', 'o', '3'), ('2', 'o', '4'),
         ('3', 'o', '3'), ('4', 'o', '4'), ('7', 'o', '3'), ('8', 'o', '4'),
         ('3', 'c1', '5'), ('4', 'c2', '6'), ('5', 'b1', '7'), ('6', 'b2', '8'),
         ('5', 'c2', '9'), ('6', 'c1', '10')], 'p.1252; marks 7,8 ignored for deadlock objective')
    ev, c, o = ('c1', 'c2', 'o1', 'o2', 'o3'), ('c1', 'c2'), ('o1', 'o2', 'o3')
    add('22TACopaque', '1', map(str, range(12)), '0', ev, c, o,
        [('0', 'c1', '1'), ('0', 'c2', '3'), ('1', 'c2', '2'), ('3', 'c1', '2'), ('2', 'o3', '4'),
         ('1', 'o1', '4'), ('3', 'o2', '4'), ('1', 'o2', '5'), ('3', 'o1', '5'),
         ('5', 'c1', '6'), ('5', 'c2', '7'), ('6', 'c2', '8'), ('7', 'c1', '8'),
         ('6', 'o1', '9'), ('6', 'o2', '10'), ('7', 'o1', '10'), ('7', 'o2', '11')],
        'p.6569; no invented self-loops on terminal states 4,8,9,10,11')
    ev, c, o = ('a', 'b', 'c', 'o1', 'o2'), ('a', 'b', 'c'), ('o1', 'o2')
    e24 = [('0', 'a', '1'), ('0', 'b', '4'), ('1', 'b', '2'), ('2', 'b', '3'), ('2', 'o1', '5'),
           ('3', 'o1', '6'), ('4', 'c', '5'), ('5', 'o2', '6'), ('4', 'b', '7'),
           ('7', 'o2', '8'), ('8', 'o1', '6')]
    add('24TACopa', '1a', map(str, range(9)), '0', ev, c, o, e24, 'p.4960, G')
    add('24TACopa', '1b', ('0', '1'), '0', ev, c, o, [('0', 'a', '1')],
        'G1; dashed disabled b edge omitted')
    qs = {'0', '4', '5', '6', '7', '8'}
    add('24TACopa', '1c', qs, '0', ev, c, o, [e for e in e24 if e[0] in qs and e[2] in qs],
        'G2; dashed disabled a edge omitted')
    add('24TACopa', '4', map(str, range(9)), '0', ('a', 'o1', 'o2'), ('a',), ('o1', 'o2'),
        [('0', 'a', '1'), ('0', 'o1', '2'), ('1', 'o1', '3'), ('3', 'a', '5'), ('2', 'o2', '4'),
         ('4', 'a', '5'), ('4', 'o1', '6'), ('5', 'o2', '7'), ('6', 'o2', '8'), ('7', 'o1', '8')],
        'p.4967, quantitative-opacity plant reused with deadlock-free objective')
    from examples.yin_extended import build_yin_extended_examples

    corpus = tuple(examples) + build_yin_extended_examples()

    if amended:
        from examples.review_amendments import apply_review_amendments

        return apply_review_amendments(corpus)

    return corpus
