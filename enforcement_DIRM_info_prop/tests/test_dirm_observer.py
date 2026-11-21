import unittest

from dirm import DFA, DIRMObserver
from dirm.observer import ObserverState


def plant(secret=False):
    return DFA.build(
        states={"q0", "safe", "secret", "safe_release", "secret_release"},
        alphabet={"h", "a", "u"},
        initial="q0",
        transitions={
            ("q0", "h"): "secret",
            ("q0", "a"): "safe",
            ("secret", "u"): "secret_release",
            ("safe", "u"): "safe_release",
        },
        secret_states={"secret", "secret_release"} if secret else set(),
    )


class DIRMObserverTests(unittest.TestCase):
    def test_ur_and_nx_keep_release_observations_out_of_closures(self):
        observer = DIRMObserver(
            plant(), observable={"a"}, unobservable={"u"}, releasable={"h"}, release_states={"safe_release", "secret_release"}
        )
        start = observer.initial_state()
        self.assertIn(("secret", True), start.q)
        self.assertEqual(observer.nx_release({("secret", True)}), frozenset({("secret_release", True)}))

    def test_ur_tilde_uses_the_papers_state_dependent_observation_sets(self):
        observer = DIRMObserver(
            plant(), observable={"a"}, unobservable={"u"}, releasable={"h"},
            release_states={"safe_release", "secret_release"},
        )
        system = observer.system

        # The same event u belongs to Sigma_uo.  It is nevertheless in O(x)
        # at secretY because its successor is a true release state.
        self.assertIn("u", system.observable_events(("secret", True)))
        self.assertNotIn(("secret_release", True), system.ur_tilde({("secret", True)}))

        # Without pending releasable information, the successor is not in
        # X_tilde_r, so u is outside O(x) and belongs to UR_tilde.
        self.assertNotIn("u", system.observable_events(("secret", False)))
        self.assertIn(("secret_release", False), system.ur_tilde({("secret", False)}))

    def test_ur_tilde_always_contains_its_seed_set(self):
        observer = DIRMObserver(
            plant(), observable={"a"}, unobservable={"u"}, releasable={"h"},
            release_states={"safe_release", "secret_release"},
        )
        seeds = frozenset({("safe_release", True), ("secret_release", True)})

        self.assertTrue(seeds <= observer.system.ur_tilde(seeds))
        self.assertTrue(seeds <= observer.system.ur_tilde_low(seeds))

    def test_three_nx_tilde_operators_have_disjoint_paper_domains(self):
        nx_plant = DFA.build(
            states={"0", "p", "r"},
            alphabet={"h", "a", "u"},
            initial="0",
            transitions={
                ("0", "h"): "p",
                ("p", "a"): "r",
                ("p", "u"): "r",
            },
        )
        system = DIRMObserver(
            nx_plant,
            observable={"a"},
            unobservable={"u"},
            releasable={"h"},
            release_states={"r"},
        ).system

        # No pending release: a reaches rN, which is not in X_tilde_r.
        self.assertEqual(
            system.nx_tilde_sigma({("p", False)}, "a"),
            frozenset({("r", False)}),
        )
        # Pending release: the same visible event now belongs to sigma,r.
        self.assertEqual(
            system.nx_tilde_sigma_r({("p", True)}, "a"),
            frozenset({("r", True)}),
        )
        # Anonymous release is generated only by Sigma_uo.
        self.assertEqual(
            system.nx_tilde_r({("p", True)}),
            frozenset({("r", True)}),
        )
        self.assertEqual(system.nx_tilde_sigma({("p", True)}, "u"), frozenset())
        self.assertEqual(system.nx_tilde_sigma_r({("p", True)}, "u"), frozenset())

    def test_observer_detects_secret_revealed_after_release(self):
        observer = DIRMObserver(
            plant(secret=True), observable={"a"}, unobservable={"u"}, releasable={"h"}, release_states={"safe_release", "secret_release"}
        )
        result = observer.check_current_state_opacity()
        self.assertFalse(result.opaque)
        self.assertEqual(result.witness, ("h", "u"))
        self.assertEqual(result.violating_state.q, frozenset({("secret_release", True)}))

    def test_observer_accepts_a_nonsecret_history_equivalent_run(self):
        observer = DIRMObserver(
            plant(secret=False), observable={"a"}, unobservable={"u"}, releasable={"h"}, release_states={"safe_release", "secret_release"}
        )
        self.assertTrue(observer.check_current_state_opacity().opaque)

    def test_true_release_fuses_the_high_level_estimate(self):
        """Eq. (4) switches the low-level component to q_mid at release."""
        observer = DIRMObserver(
            plant(), observable={"a"}, unobservable={"u"}, releasable={"h"},
            release_states={"safe_release", "secret_release"},
        )
        before_release = ObserverState(
            x_tilde=("secret", True),
            q_hat=frozenset({("secret", True), ("safe", True)}),
            q=frozenset({("secret", True)}),
        )
        after_release = observer.successor(before_release, "u")
        self.assertIsNotNone(after_release)
        self.assertEqual(
            after_release.q,
            frozenset({("secret_release", True), ("safe_release", True)}),
        )

    def test_reachable_observer_is_the_expected_five_state_structure(self):
        observer = DIRMObserver(
            plant(secret=True), observable={"a"}, unobservable={"u"}, releasable={"h"}, release_states={"safe_release", "secret_release"}
        )
        graph, _ = observer.reachable()
        self.assertEqual(len(graph), 5)
