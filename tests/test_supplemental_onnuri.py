import json
import sys
import unittest
from copy import deepcopy
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from supplemental_onnuri import apply_evidence, station_from_evidence
from discover_kb_fuel import parse_response


class SupplementalTests(unittest.TestCase):
    def setUp(self):
        self.e=json.loads((ROOT/'output/supplemental_onnuri_evidence.json').read_text(encoding='utf-8'))['rows'][0]
        self.cid=self.e['annual_candidate_ids'][0]
        self.pending=[{'candidate_id':self.cid,'name':'현대주유소','region':'전남','status':'needs_review','show_pending':True}]

    def test_bank_flag_fuel_category_and_precise_identity_required(self):
        for field,value in [('onNuliGb','0'),('category','차량 정비/부품/인테리어'),('title','다른주유소'),('address','전남 나주시 매곡동')]:
            e=deepcopy(self.e);e['bank_record']['content'][field]=value
            with self.assertRaises(ValueError):station_from_evidence(e,'2026-10-26')
        e=deepcopy(self.e);e['bank_record']['location']['lat']='35.5'
        with self.assertRaises(ValueError):station_from_evidence(e,'2026-10-26')

    def test_card_scope_unknown_paper_and_idempotent_reconciliation(self):
        rows,review,meta=apply_evidence([],self.pending,[self.e],'2026-10-26')
        self.assertEqual(meta['confirmed_count'],1)
        self.assertFalse(review[0]['show_pending'])
        self.assertIsNone(rows[0]['onnuri_methods']['paper'])
        self.assertIsNone(rows[0]['onnuri_methods']['qr'])
        self.assertEqual(rows[0]['verification']['onnuri']['issuer_scope'],['KB국민카드'])
        again=apply_evidence(rows,review,[self.e],'2026-10-26')
        self.assertEqual(again,(rows,review,meta))

    def test_stale_bank_evidence_reopens_review_and_disables_routing(self):
        rows,review,_=apply_evidence([],self.pending,[self.e],'2026-11-27')
        self.assertEqual(rows[0]['verification']['onnuri']['status'],'stale')
        self.assertFalse(rows[0]['route_eligible'])
        self.assertTrue(review[0]['show_pending'])

    def test_existing_operator_confirmation_is_preserved(self):
        s=station_from_evidence(self.e,'2026-10-26')
        s['id']='onnuri:official';s['source']=['onnuri_place']
        s['onnuri_methods']['paper']=True
        rows,_,meta=apply_evidence([s],[],[self.e],'2026-10-26')
        self.assertEqual(rows,[s]);self.assertEqual(meta['confirmed_count'],0)

    def test_response_parser_rejects_wrong_filter_and_invalid_pages(self):
        bank=self.e['bank_record']
        html='총 1건 <script>var resultJson = '+json.dumps([bank])+';</script>'
        self.assertEqual(parse_response(html)[0],1)
        with self.assertRaises(ValueError):parse_response('총 0건 <script>var resultJson = '+json.dumps([bank])+';</script>')
        bank=deepcopy(bank);bank['content']['onNuliGb']='0'
        with self.assertRaises(ValueError):parse_response('총 1건 <script>var resultJson = '+json.dumps([bank])+';</script>')
