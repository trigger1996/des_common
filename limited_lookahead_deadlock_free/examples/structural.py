"""User-requested synthetic topologies, kept separate from literature models."""

from des_core.automata import DESExample
from examples.tac2016_uniform import _dfa


def build_structural_examples():
    def make(name, n, edges, controls, observed, note, layout=None):
        events = {e for _, e, _ in edges}
        plant = _dfa(('q%d'%i for i in range(n)), 'q0', events, controls, observed, edges)

        return DESExample(name, plant, layout or {}, note, source_name='User-requested synthetic topology')

    chain = make('structural_01_long_chain_16', 16,
        [('q%d'%i, 'o' if i%3 == 2 else 'h', 'q%d'%(i+1)) for i in range(15)],
        ('h',), ('o',),
        '16-state finite single chain q0 -> ... -> q15. q15 has no outgoing edge. '
        'No invented terminal self-loop: deadlock-free supervision is impossible.',
        {f'q{i}':(i*1.3, 0) for i in range(16)})

    edges = [('q%d'%i, 'h', 'q%d'%(i+1)) for i in range(5)]
    edges += [('q5', 'h', 'q6'), ('q6', 'o', 'q7'), ('q7', 'h', 'q8'), ('q8', 'o', 'q5'),
              ('q6', 'x', 'q9'), ('q9', 'h', 'q10'), ('q10', 'h', 'q11'),
              ('q8', 'y', 'q12'), ('q12', 'h', 'q13'), ('q13', 'h', 'q14')]
    tails = make('structural_02_chain_cycle_two_tails_15', 15, edges,
        ('h', 'x', 'y'), ('o', 'x', 'y'),
        'Prefix q0 -> ... -> q5; cycle q5 -> q6 -> q7 -> q8 -> q5; '
        'two exit chains q6 -x-> q9 -> q10 -> q11 and q8 -y-> q12 -> q13 -> q14. '
        'Terminal q11,q14 are deadlocks; x,y can be disabled to retain the cycle.',
        {**{f'q{i}':(i*1.3, 0) for i in range(6)},
         'q6':(9, 0), 'q7':(9, 3), 'q8':(6.5, 3),
         'q9':(10.8, -.4), 'q10':(12.3, -.4), 'q11':(13.8, -.4),
         'q12':(6.5, 5), 'q13':(8.5, 5), 'q14':(10.5, 5)})

    edges = [('q%d'%i, 'h', 'q%d'%(i+1)) for i in range(5)]
    edges += [('q5', 'h', 'q6'), ('q6', 'o', 'q7'), ('q7', 'h', 'q8'), ('q8', 'o', 'q5'),
              ('q6', 'j', 'q9'), ('q9', 'h', 'q10'), ('q10', 'j', 'q6')]
    nested = make('structural_03_chain_nested_cycles_11', 11, edges,
        ('h', 'j'), ('o',),
        'Prefix q0 -> ... -> q5; outer cycle q5 -> q6 -> q7 -> q8 -> q5; '
        'inner cycle q6 -> q9 -> q10 -> q6. Both cycles share q6. '
        'Hidden inner cycling is permitted by the deadlock-free objective; '
        'no fairness, eventual observation or nonblocking objective is imposed.',
        {**{f'q{i}':(i*1.3, 0) for i in range(6)},
         'q6':(10.5, 0), 'q7':(10.5, 5), 'q8':(6.5, 5),
         'q9':(7.5, 1.2), 'q10':(7.8, 3.4)})

    return chain, tails, nested
