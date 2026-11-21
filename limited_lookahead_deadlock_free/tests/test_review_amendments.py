import unittest

from examples.yin_literature import build_yin_literature_examples
from examples.review_amendments import CHANGES,REMOVED,DEFERRED


class ReviewAmendmentTests(unittest.TestCase):
    def test_variants_preserve_original_corpus_and_determinism(self):
        original={e.name:e.dfa for e in build_yin_literature_examples(amended=False)}
        revised={e.name:e.dfa for e in build_yin_literature_examples()}
        self.assertEqual(set(revised),set(original)-set(REMOVED))
        for name,p in revised.items():
            self.assertEqual(p.states,original[name].states)
            for (q,e),t in p.transitions.items():
                self.assertIn(q,p.states);self.assertIn(t,p.states);self.assertIn(e,p.events)
            if name not in CHANGES:
                self.assertEqual(p,original[name])
        self.assertEqual(DEFERRED,{})

    def test_latest_cdc_loops_keep_original_c_transition(self):
        p=next(e.dfa for e in build_yin_literature_examples() if e.name=='20CDC2_fig_2b')
        self.assertEqual(p.transitions['2','c'],'6')
        self.assertEqual(p.transitions['2','b'],'2')
        self.assertEqual(p.transitions['6','c'],'6')

    def test_corrected_c2_loops_keep_c1_exits(self):
        p=next(e.dfa for e in build_yin_literature_examples() if e.name=='16WODESmax_fig_3a_Gprime')
        for q in ('6',"6'"):
            self.assertEqual(p.transitions[q,'c1'],'7')
            self.assertEqual(p.transitions[q,'c2'],q)

    def test_changed_range_source_requires_actual_control(self):
        from des_core.certified_lookahead import preprocess,solve_certified,validate_policy
        from des_core.closed_loop import build_closed_loop
        p=next(e.dfa for e in build_yin_literature_examples() if e.name=='18TACrange_fig_3a')
        self.assertEqual(p.transitions["8'",'c1'],"9'")
        self.assertFalse(p.enabled('10'))
        pre=preprocess(p);self.assertNotIn(p.initial,pre.safe)
        result=solve_certified(pre,full=True);validate_policy(pre,result)
        self.assertEqual(result.status,'winning')
        closed=build_closed_loop(pre,result)
        self.assertNotIn('10',{n['state'] for n in closed['nodes']})


if __name__=='__main__':unittest.main()
