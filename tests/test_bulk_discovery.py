import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from discover_bulk_candidates import vehicle_fuel
from discover_address_candidates import address_key
from plan_fuel_centers import cover


class BulkDiscoveryTests(unittest.TestCase):
    def test_real_lpg_label_is_not_dropped(self):
        self.assertTrue(vehicle_fuel({'상권업종소분류코드':'G21402', '상권업종소분류명':'가스 충전소'}))
        self.assertTrue(vehicle_fuel({'상권업종소분류코드':'G21401', '상권업종소분류명':'주유소'}))

    def test_household_gas_is_not_vehicle_lpg(self):
        self.assertFalse(vehicle_fuel({'상권업종소분류코드':'G21403', '표준산업분류명':'가정용 가스 연료 소매업'}))
        self.assertFalse(vehicle_fuel({'상권업종소분류명':'가스 충전소'}))

    def test_spaced_branch_road_is_not_main_road_number(self):
        self.assertEqual(address_key('경남 거제시 거제중앙로 19길 13'),
                         address_key('경상남도 거제시 거제중앙로19길 13'))
        self.assertNotEqual(address_key('경남 거제시 거제중앙로 19길 13'),
                            address_key('경남 거제시 동부면 거제중앙로 19'))

    def test_city_district_is_not_dropped(self):
        self.assertNotEqual(address_key('충북 청주시 상당구 중앙로 26'),
                            address_key('충북 청주시 청원구 북이면 중앙로 26'))

    def test_station_sampling_reuses_cache_and_covers_every_remaining_point(self):
        points = [(35.0,126.0),(35.005,126.0),(35.1,126.0),(35.105,126.0)]
        reused, queries = cover(points, [points[0]])
        self.assertEqual(reused, 2)
        self.assertEqual(len(queries), 1)
        self.assertEqual(queries[0]['covered_point_indices'], [2,3])

    def test_sampling_keeps_margin_and_handles_empty_inventory(self):
        self.assertEqual(cover([], []), (0, []))
        with self.assertRaises(ValueError):
            cover([(35,126)], [], radius=2)
