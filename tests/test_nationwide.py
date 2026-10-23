import unittest
from scripts.nationwide import resolve, region, valid_coords
from scripts.fetch_prices import parse_prices, same_station

class Nationwide(unittest.TestCase):
    def setUp(self):
        self.row={'가맹점명':'현리주유소','소속 시장명(또는 상점가)':'조종시장','소재지':'경기',
                  '취급품목':'주유소','지류형 가맹 여부':'Y','디지털형 가맹 여부':'Y'}
        self.snap={'rows':[self.row],'retrieved_at':'2026-10-23T12:00:00+09:00',
                   'source_date':'2026-07-31','source_url':'official'}
        self.loc={'CONM_NM':'현리주유소','CTPV_NM':'경기도','LCTN_ROAD_NM':'경기도 가평군 조종면 현창로 64',
                  'LAT':'37.818','LOT':'127.348','DATA_CRTR_YMD':'2026-08-01'}

    def test_exact_regional_location_and_payment_evidence(self):
        rows,review=resolve(self.snap,[],[self.loc])
        self.assertFalse(review)
        self.assertEqual(rows[0]['frcsAddr'],self.loc['LCTN_ROAD_NM'])
        self.assertEqual(rows[0]['digitalYn'],'Y')
        self.assertEqual(rows[0]['cardYn'],'')

    def test_same_name_two_addresses_requires_review(self):
        other={**self.loc,'LCTN_ROAD_NM':'경기도 파주시 문산읍 문산로 1','LAT':'37.85'}
        rows,review=resolve(self.snap,[],[self.loc,other])
        self.assertFalse(rows)
        self.assertEqual(review[0]['status'],'needs_review')

    def test_other_province_not_substituted(self):
        rows,review=resolve(self.snap,[],[{**self.loc,'CTPV_NM':'충청북도'}])
        self.assertFalse(rows)
        self.assertTrue(review)

    def test_no_market_centre_or_nan_coordinates(self):
        rows,review=resolve(self.snap,[],[{**self.loc,'LAT':'NaN'}])
        self.assertFalse(rows)
        self.assertFalse(valid_coords(None,None))
        self.assertTrue(review)

    def test_integrated_region_does_not_turn_haenam_into_gwangju(self):
        self.assertEqual(region('전남광주통합특별시 해남군 화산면 해남화산로 1045'),'전남')
        self.assertEqual(region('전남광주통합특별시 광산구 고봉로 21'),'광주')

    def test_official_product_codes_not_old_mislabels(self):
        prices=parse_prices({'OIL_PRICE':[
            {'PRODCD':'B034','PRICE':1900,'TRADE_DT':'20261023'},
            {'PRODCD':'D047','PRICE':1500,'TRADE_DT':'20261023'},
            {'PRODCD':'K015','PRICE':1000,'TRADE_DT':'20261023'}]})
        self.assertEqual(prices['고급휘발유']['price'],1900)
        self.assertEqual(prices['경유']['price'],1500)
        self.assertEqual(prices['LPG']['price'],1000)

    def test_same_name_wrong_address_cannot_receive_price(self):
        station={'name':'현리주유소','address':'경기도 가평군 조종면 현창로 64'}
        self.assertTrue(same_station(station,{'OS_NM':'현리주유소','NEW_ADR':station['address']}))
        self.assertFalse(same_station(station,{'OS_NM':'현리주유소','NEW_ADR':'경기도 파주시 현창로 65'}))
        self.assertFalse(same_station(station,{'OS_NM':'현리주유소','NEW_ADR':'경기도 파주시 현창로 64'}))
        self.assertFalse(same_station(station,{'OS_NM':'현리주유소','NEW_ADR':'충청북도 청주시 현창로 64'}))

    def test_bad_or_undated_prices_are_not_published(self):
        self.assertEqual(parse_prices({'OIL_PRICE':[{'PRODCD':'D047','PRICE':True,'TRADE_DT':'20261023'},
                         {'PRODCD':'B027','PRICE':-1,'TRADE_DT':'20261023'},
                         {'PRODCD':'K015','PRICE':1100}]}),{})
