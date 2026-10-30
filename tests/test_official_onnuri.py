import unittest
from unittest.mock import Mock, patch
from scripts.official_onnuri import reconcile, parse_csv, fetch_snapshot, download_link, fuel_row, FUEL_SELECTION_VERSION
from scripts.refresh_merchants import merge, load


class OfficialOnnuri(unittest.TestCase):
    def setUp(self):
        self.row = {'가맹점명':'샘플주유소', '소속 시장명(또는 상점가)':'샘플상점가',
            '소재지':'전남광주', '취급품목':'유류', '지류형 가맹 여부':'N',
            '디지털형 가맹 여부':'Y', '가맹 등록년도':'2026'}
        self.snapshot={'rows':[self.row], 'source_date':'2026-07-31', 'retrieved_at':'2026-10-10T03:00:00+09:00'}
        self.old={'frCd':'1','frcsNm':'샘플주유소','mrktNm':'샘플상점가',
            'frcsAddr':'광주 북문대로 190','latitude':35.1852,'longitude':126.8708,
            'paperYn':'Y','cardYn':'Y','qrYn':'Y'}

    def test_match_updates_payment_not_location(self):
        rows,_=reconcile(self.snapshot,[self.old])
        self.assertEqual(rows[0]['latitude'],self.old['latitude'])
        self.assertEqual(rows[0]['paperYn'],'N')
        stations,_=merge([],rows,[],'2026-10-10')
        self.assertEqual(stations[0]['onnuri_methods'],{'paper':False,'card':None,'qr':None,'digital':True})
        self.assertEqual(stations[0]['verification']['onnuri']['source_date'],'2026-07-31')

    def test_same_name_other_market_not_promoted(self):
        rows,review=reconcile(self.snapshot,[{**self.old,'mrktNm':'다른상점가'}])
        self.assertNotIn('_verification',rows[0])
        self.assertTrue(review)

    def test_conflicting_duplicate_not_promoted(self):
        self.snapshot['rows'].append({**self.row,'디지털형 가맹 여부':'N'})
        rows,_=reconcile(self.snapshot,[self.old])
        self.assertNotIn('_verification',rows[0])

    def test_partial_or_wrong_format_csv_rejected(self):
        for content in [b'<html>error</html>', '가맹점명,소재지\nA,광주'.encode()]:
            with self.assertRaises(ValueError):parse_csv(content,'2026-07-31','today','url')

    def test_cached_file_still_checks_portal(self):
        cached=load('onnuri_official_snapshot.json')
        cached['fuel_selection_version']=FUEL_SELECTION_VERSION
        session=Mock()
        session.get.return_value.text='"contentUrl": "'+cached['download_url']+'" 전국 온누리상품권 가맹점 현황_'+cached['source_date'].replace('-','')
        result=fetch_snapshot(session,cached,cached['retrieved_at'])
        self.assertIs(result,cached)
        self.assertEqual(session.get.call_count,1)

    def test_product_search_finds_legal_names_and_vehicle_fuels(self):
        for product in ('유류 소매', '휘발유 경유', '무연', '차량용 연료', '자동차용 연료', 'LPG', '엘피지', '석유', '충전소'):
            with self.subTest(product=product):
                self.assertTrue(fuel_row({**self.row, '가맹점명':'법인상호', '취급품목':product}))
        for product in ('우유류', '섬유류', '식용유'):
            self.assertFalse(fuel_row({**self.row, '가맹점명':'일반상호', '취급품목':product}))

    def test_current_public_download_contract(self):
        html="fn_fileDataDown('3060079', 'uddi:2fec9daf-aa5a-4139-9109-e5541b4a6bae', '', '1', '2')"
        session=Mock()
        session.post.return_value.json.return_value={'status':True,'atchFileId':'FILE_000000007663918','fileDetailSn':'1'}
        url=download_link(session,html)
        self.assertIn('atchFileId=FILE_000000007663918&fileDetailSn=1',url)
        self.assertEqual(session.post.call_args.kwargs['data']['publicDataPk'],'3060079')
        for metadata in ({'status':False,'atchFileId':'FILE_123','fileDetailSn':'1'},
                         {'status':True,'atchFileId':'https://evil.invalid','fileDetailSn':'1'},
                         {'status':True,'atchFileId':'FILE_123','fileDetailSn':'1&other=2'}):
            session.post.return_value.json.return_value=metadata
            with self.assertRaises(ValueError):download_link(session,html)
        with self.assertRaises(ValueError):download_link(session,html.replace('3060079','9999999'))

    def test_old_selection_cache_is_not_reused_after_expanding_products(self):
        cached=load('onnuri_official_snapshot.json')
        cached.pop('fuel_selection_version',None)
        session=Mock()
        session.get.return_value.text='"contentUrl": "'+cached['download_url']+'" 전국 온누리상품권 가맹점 현황_'+cached['source_date'].replace('-','')
        with patch('scripts.official_onnuri.parse_csv',return_value={'new_selection':True}) as parse:
            result=fetch_snapshot(session,cached,cached['retrieved_at'])
        self.assertTrue(result['new_selection'])
        self.assertEqual(session.get.call_count,2)
        parse.assert_called_once()

    def test_published_snapshot_metadata_preserved(self):
        rows,_=reconcile(self.snapshot,[self.old])
        official,_=merge([],rows,[],'2026-10-23')
        self.assertEqual(official[0]['verification']['onnuri']['source_date'],self.snapshot['source_date'])
        self.assertEqual(official[0]['verification']['onnuri']['checked_at'],self.snapshot['retrieved_at'])
        self.assertTrue(official[0]['onnuri_methods']['digital'])
