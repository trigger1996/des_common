import unittest
import json
from pathlib import Path
from tempfile import TemporaryDirectory

from des_core.automata import DFA
from des_core.certified_lookahead import preprocess, solve_limited_lookahead
from des_core.closed_loop import build_closed_loop, restore_certified_result


class ClosedLoopTests(unittest.TestCase):
    def test_saved_ll_bts_roundtrip_and_missing_observation_rejected(self):
        from examples.benchmarks.certified_benchmark import export_bts

        plant = DFA(frozenset('012'), '0', frozenset(('a', 'b', 'o')), frozenset(('b',)),
                  frozenset(('a', 'b', 'o')), {('0', 'o'):'1', ('1', 'a'):'1', ('1', 'b'):'2'})
        pre = preprocess(plant)
        original = solve_limited_lookahead(pre, full=True)

        with TemporaryDirectory() as tmp:
            export_bts(pre, original, Path(tmp), draw=False)
            saved = json.loads((Path(tmp)/'ll_bts.json').read_text(encoding='utf-8'))

        restored = restore_certified_result(pre, saved)
        self.assertEqual(build_closed_loop(pre, original), build_closed_loop(pre, restored))
        edge = next(e for e in saved['edges'] if e[0].startswith('O'))
        saved['edges'].remove(edge)
        saved['policy_edges'] = [e for e in saved['policy_edges'] if e != edge]

        with self.assertRaises(AssertionError):restore_certified_result(pre, saved)

    def test_hidden_events_preserve_memory_and_ambiguous_outcomes(self):
        plant = DFA(frozenset('0123'), '0', frozenset(('h', 'o', 'a')), frozenset(('a',)),
                  frozenset(('o', 'a')), {('0', 'h'):'1', ('0', 'o'):'2', ('1', 'o'):'3',
                                         ('2', 'a'):'2', ('3', 'a'):'3'})
        pre = preprocess(plant)
        graph = build_closed_loop(pre, solve_limited_lookahead(pre, full=True))
        nodes = {n['id']:n for n in graph['nodes']}
        hidden = next(e for e in graph['edges'] if e['event'] == 'h')
        self.assertEqual(nodes[hidden['source']]['memory'], nodes[hidden['target']]['memory'])
        observed = [nodes[e['target']] for e in graph['edges'] if e['event'] == 'o']
        self.assertEqual({n['state'] for n in observed}, {'2', '3'})
        self.assertEqual(len({n['memory'] for n in observed}), 1)
        self.assertEqual(len(graph['nodes']), 4)  # expands the one-node Qe certificate

    def test_controlled_deadlock_branch_is_excluded(self):
        plant = DFA(frozenset('012'), '0', frozenset(('a', 'b', 'o')), frozenset(('b',)),
                  frozenset(('a', 'b', 'o')), {('0', 'o'):'1', ('1', 'a'):'1', ('1', 'b'):'2'})
        pre = preprocess(plant)
        graph = build_closed_loop(pre, solve_limited_lookahead(pre, full=True))
        self.assertEqual({n['state'] for n in graph['nodes']}, {'0', '1'})
        self.assertTrue(any(e[1] == 'b' for e in graph['disabled']))

    def test_losing_model_does_not_fabricate_a_closed_loop(self):
        plant = DFA(frozenset('01'), '0', frozenset(('a',)), frozenset(),
                  frozenset(('a',)), {('0', 'a'):'1'})
        pre = preprocess(plant)
        graph = build_closed_loop(pre, solve_limited_lookahead(pre, full=True))
        self.assertEqual(graph['status'], 'losing')
        self.assertEqual(graph['nodes'], [])


if __name__ == '__main__': unittest.main()
