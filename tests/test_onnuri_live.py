import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, Mock

from scripts import onnuri_live as live
from scripts.live_merchants import classify, prepare
from scripts.refresh_merchants import merge


def merchant(**changes):
    return dict(frCd='a', frcsNm='A주유소', frcsAddr='광주광역시 북구 서하로 77',
                mrktNm='시장', latitude=35.19, longitude=126.88,
                paperYn='Y', cardYn='Y', qrYn='N', placeTypeNm='기타소매업', **changes)


class LiveSearch(unittest.TestCase):
    def test_explicit_request_block_is_not_retried_as_transient_400(self):
        session = Mock()
        session.post.return_value = Mock(status_code=400, text='<H1>Request Blocked</H1>')
        with patch.object(live.time, 'sleep') as sleep:
            with self.assertRaises(PermissionError):
                live.post(session, '/place/search', {})
        self.assertEqual(session.post.call_count, 1)
        sleep.assert_not_called()

    def test_area_code_without_real_anchor_is_rejected(self):
        with patch.object(live, 'post') as request:
            with self.assertRaises(ValueError):
                live.search(None, '현대', '12150', pause=0)
            request.assert_not_called()

    def test_nearby_probe_sends_registry_anchor_not_default_seoul(self):
        with patch.object(live, 'post', return_value=dict(totalCnt=0, totalPage=0, currPage=1, list=[])) as request:
            _, query = live.search(None, '', pause=0, center=(34.96097252,127.4847157), radius=2)
            sent = request.call_args.args[2]
            self.assertEqual(sent['latitude'], '34.96097252')
            self.assertEqual(sent['longitude'], '127.4847157')
            self.assertEqual(sent['baseRange'], 2)
            self.assertEqual(query['center'], [34.96097252,127.4847157])

    def test_missing_page_and_repeated_page_fail(self):
        first = dict(totalCnt=2, totalPage=2, currPage=1, list=[merchant()])
        for batch in ([], [merchant()]):
            with patch.object(live, 'post', side_effect=[first, dict(first, currPage=2, list=batch)]):
                with self.assertRaises(ValueError):
                    live.search(None, '주유소', pause=0)

    def test_count_mismatch_fails(self):
        with patch.object(live, 'post', return_value=dict(totalCnt=2, totalPage=1, currPage=1, list=[merchant()])):
            with self.assertRaises(ValueError):
                live.search(None, '주유소', pause=0)

    def test_empty_result_is_success_not_collection_failure(self):
        with patch.object(live, 'post', return_value=dict(totalCnt=0, totalPage=0, currPage=1, list=[])):
            rows, status = live.search(None, '없는주유소', pause=0)
        self.assertEqual(rows, [])
        self.assertEqual(status['status'], 'complete')

    def test_partial_snapshot_cannot_overwrite_previous(self):
        with tempfile.TemporaryDirectory() as folder:
            p = Path(folder) / 'snapshot.json'
            p.write_text('previous', encoding='utf-8')
            with self.assertRaises(ValueError):
                live.write_snapshot(p, {'status': 'partial'})
            self.assertEqual(p.read_text(), 'previous')

    def test_corporate_name_and_lpg_recognized_by_official_items(self):
        row = merchant()
        row['frcsNm'] = '주식회사 아승클린'
        self.assertEqual(classify(row, [{'가맹점명': row['frcsNm'], '취급품목': '휘발유 경유'}], set())[0], 'located')
        row['frcsNm'] = '반디가스 송암점'
        result = classify(row, [{'가맹점명': row['frcsNm'], '취급품목': '차량용 엘피지충전'}], set())
        self.assertEqual((result[0], result[2]), ('located', 'lpg'))

    def test_food_and_heating_oil_are_not_filling_stations(self):
        row = merchant()
        row.update(frcsNm='주유소기사식당', placeTypeNm='음식점업')
        self.assertEqual(classify(row, [], set())[0], 'excluded_non_vehicle_fuel')
        row.update(frcsNm='대한에너지석유등유배달', placeTypeNm='기타소매업')
        self.assertEqual(classify(row, [], set())[0], 'needs_review')

    def test_same_address_aliases_merge_and_preserve_current_flags(self):
        s = dict(sn=1, storeNm='77번가주유소', storeAddr='광주광역시 북구 서하로 77', lot=35.19, lalt=126.88)
        row = merchant()
        row['_fuel_kind'] = 'liquid'
        row['_verification'] = {'status': 'confirmed', 'checked_at': '2026-10-23', 'source_id': 'a'}
        old = {**merchant(), 'frCd': 'old', 'cardYn': 'N'}
        stations, _ = merge([s, {**s, 'sn': 2, 'storeNm': 'SK코끼리주유소'}], [row, old], [], '2026-10-23')
        self.assertEqual(len(stations), 1)
        self.assertEqual(stations[0]['verification']['saengsaeng']['source_ids'], ['1', '2'])
        self.assertEqual(stations[0]['verification']['onnuri']['status'], 'confirmed')
        self.assertTrue(stations[0]['onnuri_methods']['card'])

    def test_annual_name_never_invents_a_location(self):
        annual = {'rows': [{'가맹점명': '부흥주유소', '소속 시장명(또는 상점가)': '공산성골목형상점가',
                           '소재지': '충남', '취급품목': '주유소'}]}
        snapshot = {'status': 'complete', 'queries': [{'status': 'complete', 'expected': 0, 'received': 0}],
                    'rows': [], 'checked_at': '2026-10-23', 'source_url': live.SOURCE}
        wrong = {'CONM_NM': '부흥주유소', 'LCTN_ROAD_NM': '충남 홍성군 광천로 329번길 11'}
        selected, _, ledger, _ = prepare(snapshot, annual, [], [], [wrong])
        self.assertEqual(selected, [])
        self.assertEqual(ledger[0]['status'], 'needs_review')

    def test_missing_previously_verified_place_retains_its_date_as_stale(self):
        old = merchant()
        old['_verification'] = {'status': 'confirmed', 'checked_at': '2026-10-22', 'source_id': 'a'}
        snapshot = {'status': 'complete', 'queries': [{'status': 'complete', 'expected': 0, 'received': 0}],
                    'rows': [], 'checked_at': '2026-10-23', 'source_url': live.SOURCE}
        selected, *_ = prepare(snapshot, {'rows': []}, [old], [])
        stations, _ = merge([], selected, [], '2026-10-23')
        self.assertEqual(stations[0]['verification']['onnuri']['status'], 'stale')
        self.assertEqual(stations[0]['verification']['onnuri']['checked_at'], '2026-10-22')

    def test_live_address_fills_missing_coordinates_in_first_pass(self):
        s = dict(sn=1, storeNm='A주유소', storeAddr='광주광역시 북구 서하로 77', lot=None, lalt=None)
        row = merchant()
        row['_verification'] = {'status': 'confirmed', 'checked_at': '2026-10-23', 'source_id': 'a'}
        stations, _ = merge([s], [row], [], '2026-10-23')
        self.assertEqual(len(stations), 1)
        self.assertEqual(stations[0]['payment_types'], ['saengsaeng', 'onnuri'])

    def test_petrol_and_lpg_at_same_address_remain_separate(self):
        row = merchant()
        row['_fuel_kind'] = 'liquid'
        lpg = {**merchant(), 'frCd': 'lpg', '_fuel_kind': 'lpg'}
        stations, _ = merge([], [row, lpg], [], 'today')
        self.assertEqual(len(stations), 2)
