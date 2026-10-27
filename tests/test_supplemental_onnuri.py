import json
import sys
import unittest
from copy import deepcopy
from datetime import date, timedelta
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from supplemental_onnuri import apply_evidence, station_from_evidence
from discover_kb_fuel import parse_response

EVIDENCE=json.loads((ROOT/'output/supplemental_onnuri_evidence.json').read_text(encoding='utf-8'))['rows']
AS_OF=max(e['checked_at'][:10] for e in EVIDENCE)
STALE=(date.fromisoformat(AS_OF)+timedelta(days=31)).isoformat()


class SupplementalTests(unittest.TestCase):
    def test_bad_bank_point_requires_pinned_identity_and_independent_location(self):
        e=next(e for e in EVIDENCE if 'opinet_record' in e)
        s=station_from_evidence(e,AS_OF)
        self.assertEqual(s['lat'],float(e['registry_record']['LAT']))
        self.assertNotEqual(s['lat'],float(e['bank_record']['location']['lat']))
        self.assertLess(s['location_evidence']['opinet_distance_m'],10)
        for section,key,value in [('registry_record','LAT','35.1'),
                                  ('registry_record','TELNO','061-533-6761'),
                                  ('opinet_record','UNI_ID','A0020658'),
                                  ('opinet_record','NEW_ADR','전라남도 해남군 북평면 현산북평로 1138'),
                                  ('opinet_record','OS_NM','이웃주유소')]:
            wrong=deepcopy(e);wrong[section][key]=value
            with self.assertRaises(ValueError):station_from_evidence(wrong,AS_OF)
        wrong=deepcopy(e);wrong['bank_record']['content']['tel']='061-533-6761'
        with self.assertRaises(ValueError):station_from_evidence(wrong,AS_OF)

    def setUp(self):
        self.e=json.loads((ROOT/'output/supplemental_onnuri_evidence.json').read_text(encoding='utf-8'))['rows'][0]
        self.cid=self.e['annual_candidate_ids'][0]
        self.pending=[{'candidate_id':self.cid,'name':'현대주유소','region':'전남','status':'needs_review','show_pending':True}]

    def test_bank_flag_fuel_category_and_precise_identity_required(self):
        for field,value in [('onNuliGb','0'),('category','차량 정비/부품/인테리어'),('title','다른주유소'),('address','전남 나주시 매곡동')]:
            e=deepcopy(self.e);e['bank_record']['content'][field]=value
            with self.assertRaises(ValueError):station_from_evidence(e,AS_OF)
        e=deepcopy(self.e);e['bank_record']['location']['lat']='35.5'
        with self.assertRaises(ValueError):station_from_evidence(e,AS_OF)

    def test_card_scope_unknown_paper_and_idempotent_reconciliation(self):
        rows,review,meta=apply_evidence([],self.pending,[self.e],AS_OF)
        self.assertEqual(meta['confirmed_count'],1)
        self.assertFalse(review[0]['show_pending'])
        self.assertIsNone(rows[0]['onnuri_methods']['paper'])
        self.assertIsNone(rows[0]['onnuri_methods']['qr'])
        self.assertEqual(rows[0]['verification']['onnuri']['issuer_scope'],['KB국민카드'])
        again=apply_evidence(rows,review,[self.e],AS_OF)
        self.assertEqual(again,(rows,review,meta))

    def test_stale_bank_evidence_reopens_review_and_disables_routing(self):
        rows,review,_=apply_evidence([],self.pending,[self.e],STALE)
        self.assertEqual(rows[0]['verification']['onnuri']['status'],'stale')
        self.assertFalse(rows[0]['route_eligible'])
        self.assertTrue(review[0]['show_pending'])

    def test_existing_operator_confirmation_is_preserved(self):
        s=station_from_evidence(self.e,AS_OF)
        s['id']='onnuri:official';s['source']=['onnuri_place']
        s['onnuri_methods']['paper']=True
        rows,_,meta=apply_evidence([s],[],[self.e],AS_OF)
        self.assertEqual(rows,[s]);self.assertEqual(meta['confirmed_count'],0)

    def test_response_parser_rejects_wrong_filter_and_invalid_pages(self):
        bank=self.e['bank_record']
        html='총 1건 <script>var resultJson = '+json.dumps([bank])+';</script>'
        self.assertEqual(parse_response(html)[0],1)
        with self.assertRaises(ValueError):parse_response('총 0건 <script>var resultJson = '+json.dumps([bank])+';</script>')
        bank=deepcopy(bank);bank['content']['onNuliGb']='0'
        with self.assertRaises(ValueError):parse_response('총 1건 <script>var resultJson = '+json.dumps([bank])+';</script>')

    def test_reviewed_alias_and_renamed_locality_do_not_widen_other_matches(self):
        evidence=json.loads((ROOT/'output/supplemental_onnuri_evidence.json').read_text(encoding='utf-8'))['rows']
        renamed=next(e for e in evidence if e['bank_record']['content']['title']=='양북주유소')
        self.assertEqual(station_from_evidence(renamed,AS_OF)['region'],'경북')
        wrong=deepcopy(renamed);wrong['bank_record']['content']['address']='경북 다른시 양북면'
        with self.assertRaises(ValueError):station_from_evidence(wrong,AS_OF)
        alias=next(e for e in evidence if e['bank_record']['content']['franchiseNo']=='000000070023590')
        self.assertIn('명륜주유소',station_from_evidence(alias,AS_OF)['aliases'])
        wrong=deepcopy(alias);wrong['bank_record']['content']['franchiseNo']='000000070023591'
        with self.assertRaises(ValueError):station_from_evidence(wrong,AS_OF)

    def test_unlinked_same_name_historical_candidate_stays_pending(self):
        evidence=json.loads((ROOT/'output/supplemental_onnuri_evidence.json').read_text(encoding='utf-8'))['rows']
        current=next(e for e in evidence if e['bank_record']['content']['title']=='원남주유소')
        pending=[{'candidate_id':'dfea2f84be984c283e41bfe9','name':'원남주유소','region':'충북','show_pending':True}]
        stations,review,_=apply_evidence([],pending,[current],AS_OF)
        self.assertEqual(len(stations),1)
        self.assertTrue(review[0]['show_pending'])

    def test_municipal_identity_rejects_neighbor_and_wrong_phone(self):
        evidence=json.loads((ROOT/'output/supplemental_onnuri_evidence.json').read_text(encoding='utf-8'))['rows']
        e=next(e for e in evidence if e['bank_record']['content']['franchiseNo']=='000000055922363')
        station=station_from_evidence(e,AS_OF)
        self.assertEqual(station['location_evidence']['coordinate_source'],'kbcard')
        self.assertEqual(station['address'],'전라남도 목포시 영산로 668')
        self.assertIn('삼학(셀프)주유소',station['aliases'])
        changes=[('municipal_record','address','전라남도 목포시 영산로 660'),
                 ('identity_record','phone','061-283-5672'),
                 ('identity_record','source_url','https://unreviewed.example/store'),
                 ('municipal_record','category','세차장')]
        for section,key,value in changes:
            wrong=deepcopy(e);wrong[section][key]=value
            with self.assertRaises(ValueError):station_from_evidence(wrong,AS_OF)
        wrong=deepcopy(e);wrong['bank_record']['content']['franchiseNo']='000000055922364'
        with self.assertRaises(ValueError):station_from_evidence(wrong,AS_OF)

    def test_location_correction_preserves_operator_membership_and_count(self):
        evidence=json.loads((ROOT/'output/supplemental_onnuri_evidence.json').read_text(encoding='utf-8'))['rows']
        e=next(e for e in evidence if e.get('correct_existing_location'))
        original={'id':'onnuri:14077200045','name':'호남주유소','address':'전라남도 순천시 팔마로 9(장천동)',
                  'lat':34.95002,'lng':127.488458,'fuel_kind':'liquid','source':['onnuri_place'],
                  'onnuri_methods':{'paper':True,'qr':True},'verification':{'onnuri':{'checked_at':'2026-10-25','source_id':'14077200045'}}}
        rows,_,meta=apply_evidence([original],[],[e],AS_OF)
        self.assertEqual(len(rows),1);self.assertEqual(meta['confirmed_count'],0)
        self.assertEqual(rows[0]['verification'],original['verification'])
        self.assertEqual(rows[0]['onnuri_methods'],original['onnuri_methods'])
        self.assertNotEqual(rows[0]['lat'],original['lat'])
        wrong=deepcopy(e);wrong['correct_existing_location']['municipal_record']['LCTN_ROAD_NM']='전라남도 순천시 팔마로 99'
        with self.assertRaises(ValueError):apply_evidence([original],[],[wrong],AS_OF)
