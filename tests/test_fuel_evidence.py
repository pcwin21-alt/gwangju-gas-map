import unittest
from scripts.live_merchants import classify, annual_aliases, prepare
from scripts.refresh_merchants import merge

class FuelEvidence(unittest.TestCase):
    def setUp(self):
        self.row = dict(frCd='a',frcsNm='에너지',mrktNm='시장',frcsAddr='광주광역시 북구 서하로 237',latitude=35.18,longitude=126.90,paperYn='Y',cardYn='Y',qrYn='Y',placeTypeNm='기타소매업')
        self.proof = dict(source_id='a',merchant_name='에너지',market='시장',address=self.row['frcsAddr'],fuel_kind='liquid',sources=['https://example.org/evidence'])
    def test_exact_evidence_unlocks_fuel_only(self):
        self.assertEqual(classify(self.row,[],{},[self.proof])[0],'located')
        self.assertEqual(classify(self.row,[],{})[0],'needs_review')
    def test_id_name_market_address_all_required(self):
        for field in ('source_id','merchant_name','market','address'):
            with self.subTest(field=field):
                self.assertEqual(classify(self.row,[],{},[{**self.proof,field:'different'}])[0],'needs_review')
    def test_no_payment_or_coordinates_cannot_be_promoted(self):
        for change in ({'paperYn':'N','cardYn':'N','qrYn':'N'},{'latitude':None}):
            self.assertEqual(classify({**self.row,**change},[],{},[self.proof])[0],'needs_review')
    def test_nonfuel_category_still_wins(self):
        self.assertEqual(classify({**self.row,'placeTypeNm':'음식점업'},[],{},[self.proof])[0],'excluded_non_vehicle_fuel')

    def test_verified_household_retail_is_excluded_without_changing_membership(self):
        proof = {**self.proof,'fuel_kind':'non_vehicle','registry_category':'가정용 연료 소매업','reason':'공식 가정용 연료 소매업 분류'}
        self.assertEqual(classify(self.row,[],{},[proof])[0],'excluded_non_vehicle_fuel')
        self.assertEqual(self.row['cardYn'],'Y')
        self.assertEqual(classify(self.row,[],{},[{**proof,'address':'different'}])[0],'needs_review')

    def test_conflicting_fuel_evidence_stays_pending(self):
        proof = {**self.proof,'fuel_kind':'non_vehicle','registry_category':'일반판매소','reason':'일반판매소'}
        self.assertEqual(classify(self.row,[],{},[proof,self.proof])[0],'needs_review')
        annual=[{'가맹점명':'에너지','취급품목':'휘발유'}]
        self.assertEqual(classify(self.row,annual,{},[proof])[0],'needs_review')

    def test_unrecognized_retail_category_does_not_exclude(self):
        proof = {**self.proof,'fuel_kind':'non_vehicle','registry_category':'unknown','reason':'unknown'}
        self.assertEqual(classify(self.row,[],{},[proof])[0],'needs_review')

    def test_legal_name_alias_requires_both_exact_identities(self):
        annual = {'가맹점명':'에너지법인(주)', '소속 시장명(또는 상점가)':'옛 시장명', '소재지':'전남광주', '취급품목':'휘발유'}
        proof = {**self.proof, 'annual_match': annual}
        self.assertEqual(annual_aliases(self.row,[annual],[proof]),[annual])
        for field in ('source_id','merchant_name','market','address'):
            self.assertEqual(annual_aliases(self.row,[annual],[{**proof,field:'different'}]),[])
        for field in annual:
            self.assertEqual(annual_aliases(self.row,[{**annual,field:'different'}],[proof]),[])
        self.assertEqual(annual_aliases(self.row,[annual],[{**proof,'sources':[]}]),[])

    def test_alias_resolves_pending_without_new_station_and_expires(self):
        annual = {'가맹점명':'에너지법인(주)', '소속 시장명(또는 상점가)':'옛 시장명', '소재지':'전남광주', '취급품목':'휘발유'}
        row = {**self.row, 'frcsNm':'에너지주유소'}
        proof = {**self.proof, 'merchant_name':row['frcsNm'], 'annual_match':annual, 'checked_at':'2026-10-25'}
        snapshot = {'status':'complete','source_url':'https://example.org','rows':[row], 'checked_at':'2026-10-25',
                    'queries':[{'status':'complete','expected':1,'received':1}]}
        current,review,ledger,_ = prepare(snapshot,{'rows':[annual]},[],[],fuel_evidence=[proof])
        stations,_ = merge([],current,[],'2026-10-25')
        self.assertEqual(len(stations),1)
        self.assertIn(annual['가맹점명'],stations[0]['aliases'])
        self.assertEqual(ledger[0]['status'],'located')
        self.assertFalse(any(r.get('show_pending') for r in review))
        _,review,ledger,_ = prepare({**snapshot,'checked_at':'2027-01-24'},{'rows':[annual]},[],[],fuel_evidence=[proof])
        self.assertEqual(ledger[0]['status'],'needs_review')
        self.assertTrue(any(r.get('show_pending') for r in review))
