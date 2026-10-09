import importlib.util
import json
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
        paper=next(s for s in data if s['name']=='일자석유')
        self.assertFalse(paper['onnuri_methods']['card'])
    def test_new_official_scheme_applied(self):
        a={'sn':1,'storeNm':'주공주유소','storeAddr':'광주 북문대로 190','lot':35.1852,'lalt':126.8708}
        b={'frCd':'b','frcsNm':'주공주유소','frcsAddr':'광주 북문대로 190','latitude':35.1852,'longitude':126.8708}
        rows,_=m.merge([a],[b],[],'today')
        self.assertIn('saengsaeng',rows[0]['payment_types'])

if __name__=='__main__':unittest.main()
