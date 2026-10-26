import unittest
from scripts.pending_evidence import annotate_pending


class PendingEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.row = dict(candidate_id='a', name='현대주유소', market='웃장', region='전남',
                        status='needs_review', show_pending=True, reason='기존 사유')
        self.evidence = dict(candidate_id='a', name='현대주유소', market='웃장', region='전남',
                             scope='historical_physical_identity_only', address='순천시 중앙로 172',
                             sources=['https://www.data.go.kr/data/15091227/fileData.do'],
                             historical_source_date='2021-09-28', commercial_source_date='2026-06-30')

    def test_annotation_never_confirms_payment_or_creates_navigation(self):
        result = annotate_pending([self.row], [self.evidence])[0]
        self.assertEqual(result['status'], 'needs_review')
        self.assertTrue(result['show_pending'])
        self.assertNotIn('lat', result)
        self.assertNotIn('onnuri_methods', result)
        self.assertIn('2021-09-28', result['reason'])
        self.assertIn('현재 온누리 가맹 재확인 필요', result['reason'])
        self.assertEqual(self.row['reason'], '기존 사유')

    def test_same_name_different_identity_and_conflicting_evidence_not_applied(self):
        for field in ('candidate_id', 'market', 'region', 'name'):
            self.assertEqual(annotate_pending([self.row], [{**self.evidence, field:'다름'}]), [self.row])
        self.assertEqual(annotate_pending([self.row], [self.evidence, self.evidence]), [self.row])

    def test_confirmed_and_incomplete_evidence_not_changed(self):
        confirmed = {**self.row, 'status':'confirmed'}
        self.assertEqual(annotate_pending([confirmed], [self.evidence]), [confirmed])
        self.assertEqual(annotate_pending([self.row], [{**self.evidence, 'sources':[]}]), [self.row])


if __name__ == '__main__':
    unittest.main()
