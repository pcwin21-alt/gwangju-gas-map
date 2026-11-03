import importlib.util
import re
import tempfile
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
        self.assertIn("createElement('button')", result)
        self.assertNotIn('node.href=', result)
        self.assertIn('window.GasTossUI.showStationDetails(station,node)', result)
        self.assertIn('목록에서 주유소 정보를 확인하세요.', result)

    def test_candidate_registers_detail_fallback_before_results(self):
        self.assertLess(self.html.index('src="assets/information-ui.js"'), self.html.index('src="assets/nationwide-ui.js"'))
        self.assertIn('<title>온누리 주유소 지도</title>', self.html)
        self.assertNotIn('결제 가능 수단, 현재 유가', self.html)

    def test_old_trial_assets_cannot_survive_rebuild(self):
        from unittest.mock import patch
        # Use a separate output root, including a leftover from an earlier build.
        with tempfile.TemporaryDirectory() as temporary:
            here = Path(temporary)
            (here / 'src').mkdir()
            for path in (builder.HERE / 'src').glob('information-ui.*'):
                (here / 'src' / path.name).write_bytes(path.read_bytes())
            dist = here / 'dist'
            (dist / 'assets').mkdir(parents=True)
            (dist / 'assets' / 'old-trial.js').write_text('old network integration')
            with patch.object(builder, 'HERE', here):
                references = builder.copy_assets(self.html, dist)
            self.assertFalse((dist / 'assets' / 'old-trial.js').exists())
            self.assertFalse((dist / 'assets' / 'route-planner.js').exists())
            self.assertFalse((dist / 'assets' / 'theme.js').exists())
            self.assertIn('assets/information-ui.js', references)
            self.assertTrue((dist / 'assets' / 'information-ui.js').is_file())
            translation = (dist / 'assets' / 'i18n.js').read_text(encoding='utf-8')
            self.assertNotIn('전국 주유소 할인 지도', translation)
            self.assertIn('Onnuri FuelMap', translation)


if __name__ == '__main__':
    unittest.main()
