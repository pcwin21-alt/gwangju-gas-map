import copy
import unittest
from scripts.refresh_regions import ORDER, combine_regions, validate_combined, merge_rows


def complete_regions():
    return [dict(region=area, status='complete', checked_at=f'2026-10-24T00:{n:02d}:00+09:00', rows=[],
                 queries=[dict(region=area, status='complete', expected=0, received=0)])
            for n, area in enumerate(ORDER)]


class Regions(unittest.TestCase):
    def test_all_seventeen_in_requested_order_even_when_no_matches(self):
        snapshot = combine_regions(complete_regions())
        validate_combined(snapshot)
        self.assertEqual(snapshot['region_order'][0], '전남')
        self.assertEqual(snapshot['region_order'][-1], '서울')
        self.assertEqual(len(set(snapshot['region_order'])), 17)

    def test_partial_reordered_or_incomplete_search_is_not_publishable(self):
        good = complete_regions()
        failed = copy.deepcopy(good)
        failed[0]['queries'][0]['expected'] = 1
        for data in (good[:-1], list(reversed(good)), failed):
            with self.assertRaises(ValueError):
                combine_regions(data)

    def test_combined_province_is_split_by_actual_address(self):
        jeonnam = {'frCd': 'a', 'frcsAddr': '전남광주통합특별시 목포시 영산로 1'}
        gwangju = {'frCd': 'b', 'frcsAddr': '전남광주통합특별시 광산구 손재로 1'}
        rows = {}
        merge_rows(rows, [jeonnam, gwangju], '전남')
        self.assertEqual(list(rows), ['a'])
        invalid = complete_regions()
        invalid[0]['rows'] = [gwangju]
        with self.assertRaises(ValueError):
            combine_regions(invalid)

    def test_same_id_changed_between_queries_requires_recheck(self):
        row = {'frCd': 'a', 'frcsAddr': '전남 목포시 영산로 1', 'paperYn': 'Y'}
        rows = {}
        merge_rows(rows, [row, row], '전남')
        with self.assertRaises(ValueError):
            merge_rows(rows, [dict(row, paperYn='N')], '전남')

    def test_manifest_cannot_hide_missing_or_foreign_rows(self):
        snapshot = combine_regions(complete_regions())
        bad = copy.deepcopy(snapshot)
        bad['regions'][0]['raw_count'] = 1
        with self.assertRaises(ValueError):
            validate_combined(bad)
        snapshot['rows'] = [{'frCd': 'x', 'frcsAddr': 'unknown'}]
        with self.assertRaises(ValueError):
            validate_combined(snapshot)
