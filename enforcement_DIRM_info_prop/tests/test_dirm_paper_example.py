"""Observer regression checks for the independent project Example 3."""

import unittest

from dirm import DIRMObserver, example_3_plant


class DIRMObserverPaperExampleTests(unittest.TestCase):
    def setUp(self):
        self.observer = DIRMObserver(
            example_3_plant(),
            observable={"a", "b"},
            unobservable={"u"},
            releasable={"h"},
            release_states={5, 9},
        )

    def test_example_3_prefix_states(self):
        initial = self.observer.initial_state()
        self.assertEqual(initial.x_tilde, (0, False))
        self.assertIn((0, False), initial.q_hat)
        self.assertIn((0, False), initial.q)

        after_u = self.observer.successor(initial, "u")
        after_uh = self.observer.successor(after_u, "h")
        self.assertEqual(after_uh.x_tilde, (3, True))
        self.assertEqual(after_uh.q, initial.q)

        after_uhu = self.observer.successor(after_uh, "u")
        self.assertEqual(after_uhu.x_tilde, (5, True))
        self.assertEqual(after_uhu.q_hat, frozenset({(5, True)}))
        self.assertEqual(after_uhu.q, after_uhu.q_hat)

    def test_revised_a_edge_returns_from_9_to_3(self):
        plant = example_3_plant()
        self.assertEqual(plant.transitions[(9, "a")], 3)
        self.assertNotIn((3, "a"), plant.transitions)
        self.assertEqual(plant.transitions[(3, "u")], 5)
        self.assertNotIn((3, "h"), plant.transitions)
        self.assertNotIn((7, "u"), plant.transitions)


if __name__ == "__main__":
    unittest.main()
