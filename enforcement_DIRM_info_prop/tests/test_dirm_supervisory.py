import unittest
from dataclasses import fields

from dirm import (
    IState,
    JState,
    LState,
    build_example_3_bts,
    build_example_4_bts,
    build_example_5_bts,
    build_example_6_bts,
    build_simplified_example_2_bts,
    build_untimed_iwa_bts,
)


class SupervisoryDIRMTripartiteTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.bts = build_untimed_iwa_bts()

    def test_required_transition_types_are_present(self):
        counts = self.bts.state_counts()
        self.assertGreater(counts["I"], 0)
        self.assertGreater(counts["J"], 0)
        self.assertGreater(counts["L"], 0)
        for source, edges in self.bts.graph.items():
            if isinstance(source, IState):
                self.assertTrue(all(isinstance(edge.target, JState) for edge in edges))
                self.assertTrue(all(edge.kind == "IJ" for edge in edges))
            elif isinstance(source, JState):
                self.assertTrue(all(isinstance(edge.target, (IState, LState)) for edge in edges))
                self.assertTrue(all(edge.kind in {"JI", "JL"} for edge in edges))
            else:
                self.assertEqual(len(edges), 1)
                self.assertIsInstance(edges[0].target, IState)
                self.assertEqual(edges[0].kind, "LI")

    def test_i_and_j_have_no_exact_state(self):
        for state in self.bts.graph:
            if isinstance(state, (IState, JState)):
                self.assertFalse(hasattr(state, "actual"))
                self.assertIsInstance(state.q_hat, frozenset)
                self.assertIsInstance(state.q, frozenset)
                if isinstance(state, JState):
                    self.assertEqual(
                        tuple(field.name for field in fields(state)),
                        ("q_hat", "q", "gamma"),
                    )

    def test_control_is_selected_only_on_i_to_j(self):
        for source, edges in self.bts.graph.items():
            for edge in edges:
                if isinstance(source, IState):
                    self.assertIsNotNone(edge.gamma)
                    self.assertEqual(edge.gamma, edge.target.gamma)
                else:
                    self.assertIsNone(edge.gamma)

    def test_j_states_have_no_microstate_level_self_transitions(self):
        j_edges = [
            edge
            for source, edges in self.bts.graph.items()
            if isinstance(source, JState)
            for edge in edges
        ]
        self.assertTrue(j_edges)
        self.assertTrue(all(edge.kind in {"JI", "JL"} for edge in j_edges))
        self.assertFalse(any(isinstance(edge.target, JState) for edge in j_edges))

    def test_only_sigma_o_labels_od_transitions(self):
        for source, edges in self.bts.graph.items():
            if not isinstance(source, JState):
                continue
            for edge in edges:
                if edge.kind == "JI":
                    self.assertIn(edge.sigma, self.bts.system.observable)
                    self.assertNotIn(edge.sigma, self.bts.system.releasable)

    def test_release_goes_through_l_and_fuses_estimates(self):
        release_edges = [
            edge
            for state, edges in self.bts.graph.items()
            if isinstance(state, JState)
            for edge in edges
            if isinstance(edge.target, LState)
        ]
        self.assertTrue(release_edges)
        for edge in release_edges:
            update = self.bts.graph[edge.target][0]
            self.assertIsNotNone(edge.sigma)
            self.assertEqual(edge.target.q_mid, update.target.q_hat)
            self.assertEqual(edge.target.q_mid, update.target.q)

    def test_control_patterns_include_every_uncontrollable_event(self):
        patterns = self.bts.control_patterns()
        self.assertEqual(len(patterns), 2 ** len(self.bts.controllable))
        self.assertTrue(all(self.bts.uncontrollable <= pattern for pattern in patterns))

    def test_both_requested_examples_construct_and_synthesize(self):
        for bts in (
            self.bts,
            build_simplified_example_2_bts(),
            build_example_3_bts(),
            build_example_4_bts(),
            build_example_5_bts(),
            build_example_6_bts(),
        ):
            result = bts.synthesize()
            self.assertEqual(result.initial_winning, bts.initial in result.winning_states)
            if result.initial_winning:
                self.assertTrue(result.policy[bts.initial])

    def test_example_2_is_compact_with_release_at_2_and_5(self):
        bts = build_simplified_example_2_bts()
        self.assertEqual(dict(bts.state_counts()), {"I": 7, "J": 29, "L": 5})
        self.assertLessEqual(sum(bts.state_counts().values()), 41)
        self.assertEqual(bts.plant.initial, "0")
        self.assertTrue({("2", True), ("5", True)} <= bts.system.states)
        self.assertEqual(bts.system.release_states, frozenset({"2", "5"}))
        self.assertEqual(bts.controllable, frozenset({"a", "b", "h"}))
        self.assertEqual(bts.uncontrollable, frozenset({"o", "uc"}))
        self.assertEqual(bts.system.observable, frozenset({"o"}))
        self.assertEqual(bts.system.unobservable, frozenset({"a", "b", "uc"}))
        self.assertEqual(bts.system.releasable, frozenset({"h"}))

    def test_example_2_release_prefix_uses_fixed_low_level_subgraph(self):
        bts = build_simplified_example_2_bts()
        root = next(
            edge.target for edge in bts.graph[bts.initial]
            if edge.gamma == bts.plant.alphabet
        )
        after_one_h = bts._release_prefix_step(root, "h")
        self.assertIsNotNone(after_one_h)
        self.assertEqual(after_one_h.q, root.q)
        self.assertEqual(
            after_one_h.q_hat,
            frozenset({("1", True), ("3", True), ("4", True), ("6", True)}),
        )
        after_one_targets = bts._release_targets(after_one_h)
        self.assertEqual(
            after_one_targets["a"], frozenset({("2", True), ("5", True)})
        )
        self.assertEqual(
            after_one_targets["b"], frozenset({("2", True), ("5", True)})
        )

        after_two_h = bts._release_prefix_step(after_one_h, "h")
        self.assertIsNotNone(after_two_h)
        self.assertEqual(after_two_h.q, root.q)
        self.assertEqual(
            after_two_h.q_hat,
            frozenset({("4", True), ("6", True)}),
        )
        self.assertEqual(
            bts._release_targets(after_two_h)["b"], frozenset({("5", True)})
        )

    def test_example_2_i_estimates_include_multistate_high_and_low(self):
        bts = build_simplified_example_2_bts()
        estimates = {
            (state.q_hat, state.q) for state in bts.graph
            if isinstance(state, IState)
        }
        shared = frozenset({("2", False), ("3", False)})
        self.assertIn((shared, shared), estimates)
        self.assertTrue(any(
            isinstance(state, IState)
            and state.q_hat == shared and state.q == shared
            and state in bts.synthesize().winning_states
            for state in bts.graph
        ))
        self.assertTrue(any(len(high) > 1 for high, _ in estimates))
        self.assertTrue(any(len(low) > 1 for _, low in estimates))

    def test_example_2_uncontrolled_plant_is_not_dirm_opaque(self):
        from dirm.dfa_tac2025_example import build_simplified_example_2_augmented
        from dirm.observer import DIRMObserver

        bts = build_simplified_example_2_bts()
        system = build_simplified_example_2_augmented()
        self.assertEqual(system.release_states, bts.system.release_states)
        self.assertFalse(system.is_true_release(system.step(("6", False), "h")))
        self.assertTrue(system.is_true_release(system.step(("4", True), "b")))
        observer = DIRMObserver(
            bts.plant,
            observable={"o"}, unobservable={"a", "b", "uc"},
            releasable={"h"}, release_states={"2", "5"},
        )
        result = observer.check_current_state_opacity()
        self.assertFalse(result.opaque)
        self.assertEqual(result.witness, ("uc", "h", "a", "h", "b"))
        self.assertEqual(result.violating_state.q, frozenset({("5", True)}))
        self.assertTrue(bts.synthesize().initial_winning)

    def test_example_3_keeps_multistate_estimate_at_control_point(self):
        bts = build_example_3_bts()
        winning = bts.synthesize().winning_states
        self.assertLessEqual(sum(bts.state_counts().values()), 30)
        self.assertTrue(any(
            isinstance(state, IState)
            and len(state.q_hat) > 1 and len(state.q) > 1
            for state in winning
        ))

    def test_example_3_uncontrolled_plant_is_not_dirm_opaque(self):
        from dirm.observer import DIRMObserver

        bts = build_example_3_bts()
        observer = DIRMObserver(
            bts.plant, observable={"a", "b"}, unobservable={"u"},
            releasable={"h"}, release_states={5, 9},
        )
        result = observer.check_current_state_opacity()
        self.assertFalse(result.opaque)
        self.assertEqual(result.witness, ("u", "h", "u", "a"))
        self.assertEqual(result.violating_state.q, frozenset({(7, False)}))
        self.assertTrue(bts.synthesize().initial_winning)

    def test_example_5_same_static_observation_splits_on_release(self):
        bts = build_example_5_bts()
        system = bts.system
        self.assertEqual(bts.controllable, frozenset({"a"}))
        self.assertEqual(bts.uncontrollable, frozenset({"h", "o", "u"}))
        self.assertEqual(set(bts.control_patterns()), {
            frozenset({"h", "o", "u"}),
            frozenset({"a", "h", "o", "u"}),
        })
        self.assertTrue(all(
            "o" in state.gamma for state in bts.graph
            if isinstance(state, (JState, LState))
        ))
        self.assertEqual(system.observable, frozenset({"o"}))
        self.assertEqual(system.unobservable, frozenset({"a", "u"}))
        self.assertEqual(system.releasable, frozenset({"h"}))
        self.assertEqual(system.release_states, frozenset({1, 4, 8}))
        endpoints = []
        histories = []
        for word in ("haho", "uhaho"):
            state = system.initial
            released_prefix_length = 0
            history = {""}
            prefix = ""
            for event in word:
                prefix += event
                state = system.step(state, event)
                self.assertIsNotNone(state)
                if system.is_true_release(state):
                    released_prefix_length = len(prefix)
                history.add("".join(
                    letter for index, letter in enumerate(prefix)
                    if letter in system.observable
                    or (index < released_prefix_length and letter in system.releasable)
                ))
            endpoints.append(state)
            histories.append(history)
            self.assertEqual("".join(e for e in word if e in system.observable), "o")
        self.assertEqual(endpoints, [(4, True), (9, False)])
        self.assertEqual(histories, [{"", "h", "hho"}, {"", "hh", "hho"}])
        self.assertTrue(system.is_true_release(endpoints[0]))
        self.assertFalse(system.is_true_release(endpoints[1]))
        self.assertEqual(system.step((8, True), "o"), (9, False))
        # The original Fig. 1 also releases h immediately at state 1.
        self.assertTrue(system.is_true_release(system.step(system.initial, "h")))
        # The two o-labeled continuations have different release semantics.
        o_edges = [
            edge for state, edges in bts.graph.items() if isinstance(state, JState)
            for edge in edges if edge.sigma == "o"
        ]
        self.assertEqual({edge.kind for edge in o_edges}, {"JI", "JL"})
        release_edge = next(edge for edge in o_edges if edge.kind == "JL")
        self.assertEqual(release_edge.target.q_mid, frozenset({(4, True)}))
        self.assertNotIn(release_edge.target, bts.synthesize().winning_states)

    def test_example_4_independent_variant(self):
        bts = build_example_4_bts()
        self.assertEqual(bts.plant.states, frozenset(range(7)))
        self.assertEqual(bts.plant.transitions[(3, "h")], 5)
        self.assertEqual(bts.plant.transitions[(6, "a")], 3)
        self.assertNotIn((3, "a"), bts.plant.transitions)
        self.assertEqual(bts.plant.transitions[(6, "u")], 6)
        self.assertNotIn((6, "b"), bts.plant.transitions)
        self.assertEqual(bts.system.release_states, frozenset({3, 6}))
        self.assertTrue({(3, True), (6, True)} <= bts.system.states)
        self.assertEqual(dict(bts.state_counts()), {"I": 5, "J": 10, "L": 4})

    def test_dominated_control_choices_are_merged(self):
        for bts in (build_example_3_bts(), self.bts):
            self.assertGreater(bts.reduction_stats["control_edges"], 0)
            for source, edges in bts.graph.items():
                if not isinstance(source, IState):
                    continue
                choices = [edge.target for edge in edges]
                for smaller in choices:
                    for larger in choices:
                        if not smaller.gamma < larger.gamma:
                            continue
                        if (smaller.q_hat, smaller.q) != (larger.q_hat, larger.q):
                            continue
                        self.assertNotEqual(
                            bts._z_successor_signature(smaller, bts.graph),
                            bts._z_successor_signature(larger, bts.graph),
                            "a behaviorally identical proper-subset control remains",
                        )

    def test_same_predecessor_and_estimates_are_not_enough_to_merge(self):
        for bts in (build_example_3_bts(), self.bts):
            retained_because_successors_differ = 0
            for source, edges in bts.graph.items():
                if not isinstance(source, IState):
                    continue
                choices = [edge.target for edge in edges]
                for smaller in choices:
                    for larger in choices:
                        if (
                            smaller.gamma < larger.gamma
                            and (smaller.q_hat, smaller.q)
                            == (larger.q_hat, larger.q)
                            and bts._z_successor_signature(smaller, bts.graph)
                            != bts._z_successor_signature(larger, bts.graph)
                        ):
                            retained_because_successors_differ += 1
            self.assertGreater(retained_because_successors_differ, 0)

    def test_figure_2_initial_j_is_one_high_low_control_triple(self):
        bts = build_example_3_bts()
        full_control = bts.plant.alphabet
        j_state = next(
            edge.target
            for edge in bts.graph[bts.initial]
            if edge.gamma == full_control
        )
        self.assertEqual(j_state.q_hat, frozenset({(0, False), (1, False)}))
        self.assertEqual(
            j_state.q,
            frozenset({
                (0, False), (1, False), (2, True),
                (3, True), (4, True),
            }),
        )
        self.assertEqual(j_state.gamma, full_control)

    def test_pending_release_augmentation_is_not_projected_away(self):
        found_both = False
        for state in self.bts.graph:
            estimate = state.q_mid if isinstance(state, LState) else state.q
            by_plant = {}
            for plant_state, pending in estimate:
                by_plant.setdefault(plant_state, set()).add(pending)
            found_both |= any(flags == {False, True} for flags in by_plant.values())
        self.assertTrue(found_both)


if __name__ == "__main__":
    unittest.main()
