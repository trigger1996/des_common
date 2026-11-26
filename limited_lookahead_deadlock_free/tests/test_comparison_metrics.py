import unittest

from compare_online_offline import absolute_metrics, savings
from des_core.automata import DFA
from des_core.certified_lookahead import preprocess, solve_limited_lookahead


class ComparisonMetricsTests(unittest.TestCase):
    def test_absolute_values_ratios_and_units(self):
        row = dict(offline_median_seconds=1., online_total_median_seconds=.25,
            offline_peak_python_bytes=4096, online_peak_python_bytes=1024,
            offline_nodes=10, online_nodes=3, offline_edges=20, online_edges=4)
        result = absolute_metrics(row)
        self.assertEqual(result['time_saved_seconds'], .75)
        self.assertEqual(result['time_saved_ms'], 750)
        self.assertEqual(result['time_speedup'], 4)
        self.assertEqual(result['memory_saved_bytes'], 3072)
        self.assertEqual(result['memory_saved_KiB'], 3)
        self.assertEqual(savings(.25, 1), .75)
        self.assertEqual(savings(2, 1), -1)

    def test_safe_root_certificate_precedes_window_construction(self):
        plant = DFA(frozenset(('0', '1', '2')), '0', frozenset(('o',)), frozenset(),
            frozenset(('o',)), {('0', 'o'):'1', ('1', 'o'):'1'})
        pre = preprocess(plant)
        self.assertEqual(pre.safe, frozenset(('0', '1')))
        result = solve_limited_lookahead(pre, horizon=100, max_window_states=1)
        self.assertEqual(result.status, 'winning')
        self.assertEqual(result.window, frozenset(('0',)))
        self.assertEqual((result.decision_count, result.observation_count), (1, 0))

    def test_literature_product_certificate_keeps_original_partitions(self):
        from literature_product_forecast import compositional_context, verify_composition_small
        from examples.yin_extended import build_yin_extended_examples
        from des_core.asynchronous_product import ImplicitProductDFA

        component = next(e.dfa for e in build_yin_extended_examples() if e.name == '21AutomaticaOptimal_fig_2')
        verify_composition_small(component)
        product = ImplicitProductDFA(component, 6)
        pre = compositional_context(component, product)
        result = solve_limited_lookahead(pre, horizon=max(1, pre.horizon), max_window_states=1)
        self.assertEqual(product.state_count, 15**6)
        self.assertEqual(len(product.controllable), 30)
        self.assertEqual(len(product.observable), 24)
        self.assertEqual(pre.horizon, 0)
        self.assertEqual(pre.u, 12)
        self.assertEqual(result.maximal_patterns, (product.controllable,))

    def test_product_certificate_export_roundtrip(self):
        import json
        from pathlib import Path
        from tempfile import TemporaryDirectory
        from literature_product_forecast import compositional_context
        from examples.yin_extended import build_yin_extended_examples
        from des_core.asynchronous_product import ImplicitProductDFA
        from des_core.closed_loop import restore_certified_result
        from certified_benchmark import export_bts

        component = next(e.dfa for e in build_yin_extended_examples() if e.name == '21AutomaticaOptimal_fig_2')
        product = ImplicitProductDFA(component, 2);pre = compositional_context(component, product)
        result = solve_limited_lookahead(pre, horizon=max(1, pre.horizon))

        with TemporaryDirectory() as tmp:
            export_bts(pre, result, Path(tmp), draw=False)
            restored = restore_certified_result(pre, json.loads((Path(tmp)/'ll_bts.json').read_text(encoding='utf-8')))

        self.assertEqual(restored.initial, result.initial)
        self.assertEqual(restored.maximal_patterns, result.maximal_patterns)


if __name__ == '__main__':unittest.main()
