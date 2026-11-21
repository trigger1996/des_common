import unittest
from itertools import product
from des_core.automata import DFA
from des_core.asynchronous_product import AsynchronousProductDFA
from des_core.implicit_product import ImplicitProductDFA
from des_core.ll_bts import construct_ll_bts
from des_core.ll_bts_synthesis import synthesize_ll_bts_controls
from examples.non_deadlock import build_small_cycle_example


class ProductEventTests(unittest.TestCase):
    def test_event_partitions_inherit_for_eight_copies(self):
        component = build_small_cycle_example().dfa
        plant = ImplicitProductDFA(component, 8)

        for i in range(8):
            for event in component.events:
                copied = f"{event}_{i}"

                for name in ('controllable', 'uncontrollable', 'observable', 'unobservable'):
                    self.assertEqual(copied in getattr(plant, name), event in getattr(component, name))

        self.assertEqual(len(plant.controllable), 24)
        self.assertEqual(plant.controllable | plant.uncontrollable, plant.events)
        self.assertFalse(plant.controllable & plant.uncontrollable)

    def test_every_transition_updates_only_its_indexed_component(self):
        component = build_small_cycle_example().dfa
        plant = ImplicitProductDFA(component, 2)

        for state in product(sorted(component.states), repeat=2):
            expected = set()

            for i in range(2):
                for event, target in component.enabled(state[i]):
                    next_state = list(state)
                    next_state[i] = target
                    expected.add((f"{event}_{i}", tuple(next_state)))

            self.assertEqual(set(plant.enabled(state)), expected)

    def test_q3_can_disable_o1_and_keep_b(self):
        plant = ImplicitProductDFA(build_small_cycle_example().dfa, 1)
        root = ('q_3',)
        result = synthesize_ll_bts_controls(plant, root, construct_ll_bts(plant, root, 4, False))
        self.assertFalse(result.empty)
        self.assertTrue(result.maximal_patterns)
        self.assertTrue(all('o1_0' not in pattern for pattern in result.maximal_patterns))
        self.assertTrue(any('b_0' in pattern for pattern in result.maximal_patterns))
        self.assertTrue(result.forward_successors)


class GenericAsynchronousProductTests(unittest.TestCase):
    def setUp(self):
        self.left = DFA(frozenset({'l0', 'l1'}), 'l0', frozenset({'tick'}),
                        frozenset({'tick'}), frozenset(), {('l0', 'tick'): 'l1'})
        self.right = DFA(frozenset({'r0', 'r1', 'r2'}), 'r0', frozenset({'tick', 'reset'}),
                         frozenset(), frozenset({'tick'}),
                         {('r0', 'tick'): 'r1', ('r1', 'reset'): 'r0'})

    def test_shared_name_keeps_owner_attributes_and_does_not_synchronize(self):
        plant = AsynchronousProductDFA((self.left, self.right))
        self.assertEqual(plant.initial, ('l0', 'r0'))
        self.assertEqual(plant.state_count, 6)
        self.assertEqual(plant.controllable, frozenset({'tick_0'}))
        self.assertEqual(plant.observable, frozenset({'tick_1'}))
        self.assertEqual(plant.uncontrollable, frozenset({'tick_1', 'reset_1'}))
        self.assertEqual(plant.unobservable, frozenset({'tick_0', 'reset_1'}))
        self.assertEqual(set(plant.enabled(plant.initial)),
                         {('tick_0', ('l1', 'r0')), ('tick_1', ('l0', 'r1'))})

    def test_one_deadlocked_component_does_not_block_another(self):
        plant = AsynchronousProductDFA((self.left, self.right))
        self.assertEqual(plant.enabled(('l1', 'r0')), (('tick_1', ('l1', 'r1')),))

    def test_repeated_component_wrapper_matches_generic_product(self):
        legacy = ImplicitProductDFA(self.left, 2)
        generic = AsynchronousProductDFA((self.left, self.left))

        for attribute in ('initial', 'state_count', 'events', 'controllable',
                          'uncontrollable', 'observable', 'unobservable'):
            self.assertEqual(getattr(legacy, attribute), getattr(generic, attribute))

        self.assertEqual(legacy.enabled(legacy.initial), generic.enabled(generic.initial))

    def test_invalid_component_count_and_state_dimension(self):
        with self.assertRaises(ValueError):
            AsynchronousProductDFA(())

        with self.assertRaises(ValueError):
            ImplicitProductDFA(self.left, 0)

        with self.assertRaises(ValueError):
            AsynchronousProductDFA((self.left, self.right)).enabled(('l0',))


if __name__ == '__main__':
    unittest.main()
