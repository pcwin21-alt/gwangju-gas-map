import sys
import json
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from discover_kb_addresses import area_values,validate_locality
from discover_kb_fuel import parse_response


class AddressLookupTests(unittest.TestCase):
    def test_uses_selected_area_not_default_gangwon_list(self):
        data={'area':[{'VALUE':'담양군','KEY1':'전남'}],
              'areaSgguList':[{'VALUE':'강릉시','KEY1':'강원'}]}
        self.assertEqual(area_values(data,'전남'),['담양군'])

    def test_missing_or_wrong_parent_is_not_zero_merchants(self):
        for rows in [[],[{'VALUE':'강릉시','KEY1':'강원'}]]:
            with self.assertRaises(ValueError):area_values({'area':rows},'전남')

    def test_cross_region_response_rejected(self):
        with self.assertRaises(ValueError):
            validate_locality([{'content':{'address':'광주 북구 용봉동'}}],('전남','담양군','담양읍'))

    def test_whitespace_accepted(self):
        validate_locality([{'content':{'address':'전남 담양군 담양읍 '}}],('전남','담양군','담양읍'))

    def test_address_collection_retains_blank_coordinates_but_not_wrong_membership(self):
        row={'location':{'lat':'','lng':''},'content':{'onNuliGb':'1','franchiseNo':'000000000000001','title':'좌표없는점포'}}
        def html():return '총 1건 <script>var resultJson = '+json.dumps([row])+';</script>'
        with self.assertRaises(ValueError):parse_response(html())
        self.assertEqual(parse_response(html(),require_coordinates=False)[1],[row])
        row['content']['onNuliGb']='0'
        with self.assertRaises(ValueError):parse_response(html(),require_coordinates=False)
