import unittest
from scripts.market_regions import resolve_pending_regions


class MarketRegionTests(unittest.TestCase):
    def candidate(self):
        return dict(name='현대주유소', market='웃장', region='전남광주', status='needs_review')

    def evidence(self, address, kind='official_market_registry', source_id=None, market='웃장'):
        return dict(market=market, reference_address=address, source_kind=kind, source_id=source_id)

    def test_market_address_resolves_only_province(self):
        before = self.candidate()
        got = resolve_pending_regions([before], [self.evidence('전라남도 순천시 북문길 40')])[0]
        self.assertEqual(got['region'], '전남')
        self.assertEqual(got['source_region'], '전남광주')
        self.assertEqual(got['status'], 'needs_review')
        self.assertEqual(before['region'], '전남광주')
        self.assertFalse(any(key in got for key in ('address', 'lat', 'lng', 'payment_types')))

    def test_conflicting_and_unrelated_markets_stay_unresolved(self):
        for evidence in [[], [self.evidence('광주광역시 서구 내방로 1', market='웃장상가')],
                         [self.evidence('전라남도 순천시 북문길 40'), self.evidence('광주광역시 북구 북문대로 2')]]:
            self.assertEqual(resolve_pending_regions([self.candidate()], evidence)[0]['region'], '지역 미확정')

    def test_place_evidence_requires_two_distinct_merchants(self):
        one = self.evidence('전라남도 순천시 북문길 40', 'official_place_search', 'a')
        two = self.evidence('전라남도 순천시 중앙로 100', 'official_place_search', 'b')
        self.assertEqual(resolve_pending_regions([self.candidate()], [one, one])[0]['region'], '지역 미확정')
        self.assertEqual(resolve_pending_regions([self.candidate()], [one, two])[0]['region'], '전남')

    def test_existing_explicit_region_is_not_overridden(self):
        row = dict(self.candidate(), region='서울')
        self.assertEqual(resolve_pending_regions([row], [self.evidence('전라남도 순천시 북문길 40')]), [row])

    def test_resolution_is_idempotent(self):
        evidence = [self.evidence('전라남도 순천시 북문길 40')]
        once = resolve_pending_regions([self.candidate()], evidence)
        self.assertEqual(resolve_pending_regions(once, evidence), once)


if __name__ == '__main__':
    unittest.main()
