import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('refresh', ROOT/'scripts'/'refresh_merchants.py')
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

class Merchants(unittest.TestCase):
    def test_complete_pages_required(self):
        first = {'error':'N','dataMap':{'totalCnt':2,'pageCnt':2,'list':[{'sn':1,'storeNm':'A','storeAddr':'도로 1'}]}}
        second = {'error':'N','dataMap':{'list':[]}}
        with patch.object(m,'request',side_effect=[first,second]), patch.object(m.time,'sleep'):
            with self.assertRaises(ValueError):m.fetch_sangsaeng(None)

    def test_repeat_pages_rejected(self):
        row={'sn':1,'storeNm':'A','storeAddr':'도로 1'}
        first={'error':'N','dataMap':{'totalCnt':2,'pageCnt':2,'list':[row]}}
        with patch.object(m,'request',side_effect=[first,{'error':'N','dataMap':{'list':[row]}}]),patch.object(m.time,'sleep'):
            with self.assertRaises(ValueError):m.fetch_sangsaeng(None)

    def test_neighbor_not_merged_and_methods_preserved(self):
        a={'sn':1,'storeNm':'A주유소','storeAddr':'광주 북문대로 190','lot':35.1852,'lalt':126.8708}
        b={'frCd':'b','frcsNm':'B주유소','frcsAddr':'광주 북문대로 192','latitude':35.1852,'longitude':126.8708,'paperYn':'Y','cardYn':'N','qrYn':'N'}
        rows,_=m.merge([a],[b],[],'2026-10-09')
        self.assertEqual(len(rows),2)
        self.assertFalse(rows[1]['onnuri_methods']['card'])
        self.assertEqual(rows[1]['verification']['onnuri']['status'],'stale')

    def test_same_road_merge(self):
        a={'sn':1,'storeNm':'새이름주유소','storeAddr':'새행정구역 북문대로 190','lot':35.1852,'lalt':126.8708}
        b={'frCd':'b','frcsNm':'옛이름주유소','frcsAddr':'광주 북문대로 190 (운암동)','latitude':35.18521,'longitude':126.87081,'paperYn':'Y','cardYn':'Y','qrYn':'Y'}
        rows,_=m.merge([a],[b],[],'2026-10-09')
        self.assertEqual(rows[0]['payment_types'],['saengsaeng','onnuri'])
        self.assertIn('옛이름주유소',rows[0]['aliases'])

    def test_same_place_duplicate_source_keeps_ids(self):
        row={'frCd':'a','frcsNm':'A주유소','frcsAddr':'광주 북문대로 190','latitude':35.1852,'longitude':126.8708,'paperYn':'Y','cardYn':'Y','qrYn':'Y'}
        rows,_=m.merge([], [row,{**row,'frCd':'b','cardYn':'N'}],[],'today')
        self.assertEqual(rows[0]['payment_types'],['onnuri'])
        self.assertEqual(rows[0]['verification']['onnuri']['source_ids'],['a','b'])
        self.assertFalse(rows[0]['onnuri_methods']['card'])

    def test_false_positive_excluded(self):
        rows,review=m.merge([], [{'frCd':'x','frcsNm':'메가커피 광주유촌점'}],[], 'today')
        self.assertFalse(rows)
        self.assertTrue(review)

    def test_published_data(self):
        data=json.loads((ROOT/'output/gas_stations.json').read_text(encoding='utf-8'))
        self.assertEqual(len({s['id'] for s in data}),len(data))
        self.assertTrue(all(s.get('verification') for s in data))
        self.assertTrue(all(len(s['payment_types']) == len(set(s['payment_types'])) for s in data))
        self.assertTrue(all(s['lat'] is not None and s['lng'] is not None for s in data if s['route_eligible']))
        for station in data:
            methods=station.get('onnuri_methods')
            if methods:
                if station.get('verification',{}).get('onnuri',{}).get('provider')=='kbcard':
                    self.assertIsNone(methods['paper'])
                    self.assertIsNone(methods['qr'])
                    self.assertTrue(methods['card'])
                else:
                    self.assertIn(methods['paper'],(True,False))
                self.assertIn(methods['digital'],(True,False))
    def test_new_official_scheme_applied(self):
        a={'sn':1,'storeNm':'주공주유소','storeAddr':'광주 북문대로 190','lot':35.1852,'lalt':126.8708}
        b={'frCd':'b','frcsNm':'주공주유소','frcsAddr':'광주 북문대로 190','latitude':35.1852,'longitude':126.8708}
        rows,_=m.merge([a],[b],[],'today')
        self.assertIn('saengsaeng',rows[0]['payment_types'])

    def test_failed_annual_or_live_request_preserves_data_and_last_success(self):
        for stage in ('annual_snapshot', 'public_search'):
            with self.subTest(stage=stage), tempfile.TemporaryDirectory() as directory:
                out = Path(directory)
                old = [{'id': 'existing', 'name': '기존주유소'}]
                status = {'onnuri': {'checked_at': '2026-10-23T23:00:00+09:00',
                                    'refresh_run_url': 'https://github.com/old/run/1'},
                          'saengsaeng': {'checked_at': '2026-10-23T22:00:00+09:00'}}
                now = m.datetime.now(m.KST).isoformat()
                files = {'gas_stations.json': old, 'merchant_status.json': status,
                         'station_locations.json': {'retrieved_at': now, 'complete_registry': True, 'rows': []},
                         'lpg_locations.json': {'retrieved_at': now, 'rows': []},
                         'onnuri_live_snapshot.json': {'rows': [], 'checked_at': status['onnuri']['checked_at']}}
                for name, content in files.items():
                    (out/name).write_text(json.dumps(content), encoding='utf-8')
                (out/'map.html').write_text('const STATIONS = [];\n', encoding='utf-8')
                original = (out/'gas_stations.json').read_bytes()
                snapshot = (out/'onnuri_live_snapshot.json').read_bytes()
                with (patch.object(m, 'OUT', out), patch('sys.argv', ['refresh_merchants.py']),
                      patch.object(m, 'fetch_sangsaeng', return_value=[{}]*30),
                      patch.object(m, 'fetch_snapshot', return_value={'rows': []},
                                   side_effect=m.requests.ConnectTimeout() if stage == 'annual_snapshot' else None),
                      patch.object(m, 'collect', side_effect=m.requests.ConnectTimeout()),
                      patch.dict(m.os.environ, {'GITHUB_ACTIONS': 'true', 'GITHUB_REPOSITORY': 'owner/repo',
                                                'GITHUB_RUN_ID': '123'}, clear=True)):
                    with self.assertRaises(m.requests.ConnectTimeout):
                        m.main()
                current = json.loads((out/'merchant_status.json').read_text(encoding='utf-8'))
                self.assertEqual(current['onnuri']['checked_at'], status['onnuri']['checked_at'])
                self.assertEqual(current['saengsaeng'], status['saengsaeng'])
                self.assertEqual(current['onnuri']['refresh_stage'], stage)
                self.assertEqual(current['onnuri']['refresh_run_url'], 'https://github.com/owner/repo/actions/runs/123')
                self.assertEqual((out/'gas_stations.json').read_bytes(), original)
                self.assertEqual((out/'onnuri_live_snapshot.json').read_bytes(), snapshot)
                self.assertIn('기존주유소', (out/'map.html').read_text(encoding='utf-8'))
                self.assertIn('ConnectTimeout', (out/'map.html').read_text(encoding='utf-8'))

    def test_local_attempt_clears_previous_hosted_run_link(self):
        with patch.dict(m.os.environ, {}, clear=True):
            self.assertEqual(m.refresh_context(), {'refresh_environment': 'local', 'refresh_run_url': None})

if __name__=='__main__':unittest.main()
