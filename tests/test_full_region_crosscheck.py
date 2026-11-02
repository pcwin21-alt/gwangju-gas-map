import unittest

from scripts.crosscheck_full_region import FuelIndex, county, mapped_links, phone_key, reduced_name, validate_bank_snapshot


class FullRegionCrosscheckTests(unittest.TestCase):
    def setUp(self):
        self.fuel = {'source_id': 'test:1', 'name': '(주)동행에너지',
                     'address': '전라남도 나주시 금천면 영산로 5703',
                     'phone': '061-337-0875', 'lat': 35.0355, 'lng': 126.7525,
                     'fuel_kind': 'liquid'}
        self.index = FuelIndex([self.fuel])

    def test_nonfuel_company_name_is_compared_without_keyword_filter(self):
        result = self.index.match('동행에너지', '전남 나주시 금천면', lat=35.0355, lng=126.7525)
        self.assertEqual(len(result), 1)
        self.assertIn('exact_normalized_name', result[0]['signals'])
        self.assertEqual(result[0]['status'], 'review_only_not_same_business_or_membership_proof')

    def test_shared_coordinates_do_not_prove_a_fuel_merchant(self):
        result = self.index.match('만두집', '전남 나주시 금천면', lat=35.0355, lng=126.7525)
        self.assertEqual(result[0]['signals'], ['within_100m_only'])
        self.assertIn('review_only', result[0]['status'])

    def test_reused_phone_retains_location_and_county_conflict(self):
        result = self.index.match('팥죽식당', '전남 순천시 중앙동', '061)337-0875', 34.95, 127.48)
        self.assertEqual(result[0]['signals'], ['exact_phone_only'])
        self.assertTrue(result[0]['county_conflict'])
        self.assertGreater(result[0]['distance_m'], 4000)

    def test_no_generic_or_partial_phone_match(self):
        self.assertIsNone(phone_key('337-0875'))
        self.assertIsNone(phone_key('000-000-0000'))
        self.assertEqual(phone_key('061)337-0875'), '0613370875')
        self.assertIsNone(reduced_name('SK에너지 주유소'))

    def test_region_prefix_does_not_hide_the_county(self):
        self.assertEqual(county('전남광주통합특별시 나주시 금천면 영산로 1'), '나주시')
        self.assertEqual(county('전라남도 나주시 금천면'), '나주시')

    def test_same_name_different_counties_stays_explicitly_unresolved(self):
        result = self.index.match('동행에너지', '전남 여수시')
        self.assertTrue(result[0]['county_conflict'])
        self.assertIsNone(result[0]['distance_m'])

    def test_existing_map_link_requires_fuel_kind_address_and_location(self):
        matches = self.index.match('동행에너지')
        station = {'id': 'known', 'name': '다른 법인명', 'address': self.fuel['address'],
                   'lat': self.fuel['lat'], 'lng': self.fuel['lng'], 'fuel_kind': 'liquid'}
        self.assertEqual(mapped_links(matches, [station]), ['known'])
        self.assertEqual(mapped_links(matches, [{**station, 'fuel_kind': 'lpg'}]), [])
        self.assertEqual(mapped_links(matches, [{**station, 'address': '전남 나주시 다른로 1'}]), [])

    def test_incomplete_issuer_snapshot_cannot_be_called_full_input(self):
        with self.assertRaises(ValueError):
            validate_bank_snapshot({'region': '전남', 'status': 'running'}, '전남')

    def test_wrong_region_snapshot_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_bank_snapshot({'region': '광주', 'status': 'all_listed_addresses_complete'}, '전남')

    def test_duplicate_issuer_ids_cannot_satisfy_completeness(self):
        row = {'content': {'franchiseNo': 'same', 'address': '전남 나주시'}}
        with self.assertRaises(ValueError):
            validate_bank_snapshot({'region': '전남', 'status': 'all_listed_addresses_complete',
                                    'planned_queries': 442, 'completed_queries': 442,
                                    'unique_merchants': 2, 'rows': [row, row]}, '전남')


if __name__ == '__main__':
    unittest.main()
