"""Regression baselines for the two non-equivalent maintained IWA engines."""

from contextlib import redirect_stdout
from io import StringIO
import unittest

from opacity_iwa import WeightedAIC, t_bts


EVENT_C = ["a", "b", "o3"]
EVENT_O = ["o1", "o2", "o3"]
EVENT_UC = ["o1", "o2", "uc"]
EVENT_UO = ["a", "b", "uc"]


class IWARegressionTests(unittest.TestCase):
    def test_original_iwa_43_baseline(self):
        machine = t_bts("opacity_iwa/iwa/IWA_4.3.yaml", ["1"], EVENT_C, EVENT_O, EVENT_UC, EVENT_UO)
        with redirect_stdout(StringIO()):
            machine.construct_T_BTS()
            supervisors = machine.find_all_supervisor(is_print=False)
        self.assertEqual(machine.t_bts.number_of_nodes(), 34)
        self.assertEqual(len(supervisors), 307)

    def test_endpoint_aware_example_4_baseline(self):
        machine = WeightedAIC(
            "opacity_iwa/iwa/IWA_4.3.r1_w_urcycles.yaml", ["1"], EVENT_C, EVENT_O, EVENT_UC, EVENT_UO
        )
        with redirect_stdout(StringIO()):
            machine.construct_W_AIC(t_cutoff=10)
            machine.remove_all_revealing_states(is_print_state_to_remove=False)
            supervisors = machine.find_all_supervisor(is_print=False)
        self.assertEqual(machine.w_aic.number_of_nodes(), 31)
        self.assertEqual(len(supervisors), 600)

    def test_enforcement_iwa_example_4_initial_estimates(self):
        machine = WeightedAIC(
            "opacity_iwa/iwa/IWA_4.3.r1_w_urcycles.yaml", ["1"], EVENT_C, EVENT_O, EVENT_UC, EVENT_UO
        )
        with redirect_stdout(StringIO()):
            machine.construct_W_AIC(t_cutoff=10)

        observed = set()
        intervals = {(2, 3), (3, 5.5), (5.5, 6)}
        for node in machine.w_aic.nodes:
            if len(node) != 2 or not isinstance(node[1], tuple):
                continue
            policy = dict(node[1])
            if node[0] != ("1", "2") or policy.get("a", ())[:2] != (1, 2):
                continue
            interval = policy.get("o3", ())[:2]
            if interval not in intervals:
                continue
            for _, target, data in machine.w_aic.out_edges(node, data=True):
                if data.get("observation", (None,))[0] == "o3":
                    observed.add((interval, target))

        self.assertEqual(
            observed,
            {((2, 3), ("3",)), ((3, 5.5), ("3", "7")), ((5.5, 6), ("7",))},
        )
