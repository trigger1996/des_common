import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from examples.benchmarks.certified_benchmark import export_bts
from des_core.automata import DFA
from des_core.certified_lookahead import Limited_Lookahead_Controller, preprocess, solve_limited_lookahead, validate_policy
from des_core.offline_bts import construct_offline_bts
from des_core.closed_loop import restore_certified_result


class PairBipartiteTests(unittest.TestCase):
    def ambiguous_plant(self):
        return DFA(frozenset('0123'), '0', frozenset({'h', 'o', 'a'}), frozenset({'a'}),
                   frozenset({'o', 'a'}), {('0', 'h'): '1', ('0', 'o'): '2', ('1', 'o'): '3',
                                         ('2', 'a'): '2', ('3', 'a'): '3'})

    def test_both_methods_store_every_concrete_successor_as_a_distinct_pair(self):
        plant = self.ambiguous_plant()
        pre = preprocess(plant)

        for result in (construct_offline_bts(plant),
                       solve_limited_lookahead(pre, horizon=3, certificates=False)):
            estimate = frozenset({'2', '3'})
            self.assertIn(('2', estimate), result.decision_states)
            self.assertIn(('3', estimate), result.decision_states)
            self.assertEqual(result.decision_policy['2', estimate], result.decision_policy['3', estimate])
            self.assertEqual(result.decision_count, len(result.decision_states))
            self.assertGreater(result.decision_count, len(result.constructed_choices))
            validate_policy(pre, result)

    def test_bad_patterns_are_stored_before_pruning_and_have_recorded_steps(self):
        plant = DFA(frozenset('01'), '0', frozenset({'a', 'b'}), frozenset({'a', 'b'}),
                    frozenset({'a', 'b'}), {('0', 'a'): '0', ('0', 'b'): '1'})
        result = solve_limited_lookahead(preprocess(plant), horizon=1, record_steps=True)
        raw = result.decision_states[result.initial_decision]
        kept = result.decision_policy[result.initial_decision]
        self.assertEqual(len(raw), 4)
        self.assertEqual({c.pattern for c in kept}, {frozenset({'a'})})
        self.assertEqual(sum(s['operation'] == 'construct_pattern' for s in result.construction_steps), 4)
        self.assertTrue(any(s['operation'] == 'prune_pattern' and not s['choice'].pattern
                            for s in result.construction_steps))

    def test_serialized_decisions_and_observation_branching_are_pair_valued(self):
        plant = self.ambiguous_plant()
        pre = preprocess(plant)

        for structure, result in [('BTS', construct_offline_bts(plant)),
                                  ('LL-BTS', solve_limited_lookahead(pre, horizon=3, certificates=False))]:
            with TemporaryDirectory() as tmp:
                export_bts(pre, result, Path(tmp), structure=structure, draw=False)
                record = json.loads((Path(tmp) / ('bts.json' if structure == 'BTS' else 'll_bts.json')).read_text())

            targets = {n['id'] for n in record['D'] if set(n['estimate']) == {'2', '3'}}
            self.assertEqual(len(targets), 2)
            self.assertEqual({n['q_hat'] for n in record['D'] if n['id'] in targets}, {'2', '3'})
            self.assertTrue(all('q_hat' in n and n['state'] == [n['q_hat'], n['estimate']] for n in record['D']))
            self.assertTrue(any({target for src, target, event in record['edges'] if src == obs['id'] and event == 'o'}
                                == targets for obs in record['O']))

    def test_removing_one_concrete_observation_successor_is_detected(self):
        plant = self.ambiguous_plant()
        pre = preprocess(plant)
        result = construct_offline_bts(plant)

        with TemporaryDirectory() as tmp:
            export_bts(pre, result, Path(tmp), structure='BTS', draw=False)
            record = json.loads((Path(tmp) / 'bts.json').read_text())

        restore_certified_result(pre, record)
        edge = next(e for e in record['policy_edges'] if e[0].startswith('O') and e[2] == 'o')
        record['edges'].remove(edge)
        record['policy_edges'].remove(edge)

        with self.assertRaises(AssertionError):
            restore_certified_result(pre, record)

    def test_previous_continuation_reuses_the_updated_pair_initial_state(self):
        from examples.paper.paper_example_models import paper_small_figure

        pre = preprocess(paper_small_figure().dfa)
        controller = Limited_Lookahead_Controller(pre, horizon=5)
        result, _, _ = controller.solve()
        pattern = frozenset({'a', 'b', 'o2'})
        self.assertIn(pattern, result.maximal_patterns)
        estimate = controller.observe(pattern, 'o1')
        controller.horizon = 1
        result, fresh, reused = controller.solve()
        self.assertTrue(reused)
        self.assertEqual(fresh.status, 'inconclusive')
        self.assertEqual(result.initial_decision[1], estimate)
        self.assertIn(result.initial_decision, result.decision_policy)
        validate_policy(pre, result)


if __name__ == '__main__':
    unittest.main()
