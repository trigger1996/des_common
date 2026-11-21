import unittest
from pathlib import Path
from unittest.mock import patch

from benchmark_review_results import enrich_review,root_rejections


class ReviewResultsTests(unittest.TestCase):
    def test_note_and_unrelated_text_preserved_on_repeated_enrichment(self):
        original=('# 原始系统事件属性与修改意见\n\n手写总说明。\n\n## 快速索引\n\n索引。\n\n'
            '## demo\n\n手写模型说明。\n\n### 修改意见（请填写）\n\n'
            '<!-- USER-NOTES: demo -->\n我的修改：保持这段文字。\n<!-- END-USER-NOTES: demo -->\n')
        notes={'demo':'我的修改：保持这段文字。'}
        models=[({'name':'demo'},{},{},{})]
        with patch('benchmark_review_results.overview',return_value='总览分析'),\
             patch('benchmark_review_results.model_analysis',return_value='逐例分析'),\
             patch('benchmark_review_results.large_analyses',return_value=''):
            once=enrich_review(original,Path('.'),models,notes)
            twice=enrich_review(once,Path('.'),models,notes)
        self.assertEqual(once,twice)
        self.assertIn('手写总说明。',once)
        self.assertIn('手写模型说明。',once)
        self.assertIn('我的修改：保持这段文字。',once)
        self.assertEqual(once.count('<!-- RUN-RESULTS: demo -->'),1)

    def test_root_pattern_rejections_are_exclusive(self):
        plant=dict(states=['0','1','2'],events=['a','b'],controllable=['a','b'],
                   transitions=[['0','a','1'],['0','b','2'],['1','a','1']])
        bts=dict(initial='D0',O=[dict(id='O'+str(i),estimate=['0'],pattern_controllable=p)
             for i,p in enumerate([[],['a'],['b'],['a','b']])],
             edges=[['D0','O'+str(i),str(i)] for i in range(4)],policy_edges=[['D0','O1','1']])
        self.assertEqual(root_rejections(plant,bts),dict(plant_deadlock=0,control_deadlock=1,
                                                       successor_loss=2,retained=1))


if __name__=='__main__':unittest.main()
