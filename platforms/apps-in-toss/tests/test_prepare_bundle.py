import importlib.util
import re
import unittest
from pathlib import Path

spec = importlib.util.spec_from_file_location('toss_builder', Path(__file__).resolve().parents[1] / 'prepare_bundle.py')
builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)


class PlatformBuild(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = (builder.ROOT / 'output/map.html').read_text(encoding='utf-8')
        cls.html = builder.prepare(cls.source)

    def test_public_data_is_unchanged(self):
        for key in ['STATIONS', 'PRICES', 'PRICE_INFO', 'MERCHANT_STATUS', 'NATIONAL_PENDING']:
            pattern = rf'^(?:const|let) {key} = (.+);$'
            self.assertEqual(re.search(pattern, self.source, re.M).group(1), re.search(pattern, self.html, re.M).group(1))

    def test_no_legacy_submission_or_analytics_endpoints(self):
        for token in ['X-Master-Key', 'BIN_KEY', 'formspree.io', 'qr.kakaopay.com', 'goatcounter.com', 'gc.zgo.at', 'apps.apple.com']:
            self.assertNotIn(token, self.html)
        self.assertNotIn('navigator.geolocation.getCurrentPosition(', self.html)
        self.assertNotIn('src="assets/route-planner.js"', self.html)

    def test_normal_map_and_manual_search_remain_available(self):
        for token in ['id="map"', 'id="searchInput"', 'id="regionSelect"', 'id="stationList"', 'id="myLocBtn"', 'assets/nationwide-ui.js']:
            self.assertIn(token, self.html)
        self.assertIn('window.GasToss.getCurrentPosition(', self.html)
        self.assertIn('data-theme="light"', self.html)

    def test_failed_map_fallback_does_not_send_users_to_external_navigation(self):
        js = (builder.ROOT / 'assets/nationwide-ui.js').read_text(encoding='utf-8')
        result = builder.prepare_results(js)
        self.assertIn("createElement(hasMap?'button':'div')", result)
        self.assertNotIn('node.href=', result)
        self.assertIn('목록에서 주유소 정보를 확인하세요.', result)


if __name__ == '__main__':
    unittest.main()
