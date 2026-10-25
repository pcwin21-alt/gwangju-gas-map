import unittest
from scripts.live_merchants import classify

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
