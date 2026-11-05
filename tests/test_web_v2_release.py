import importlib.util
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('promote_web_v2', ROOT / 'scripts/promote_web_v2.py')
ui = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ui)


class WebReleaseTests(unittest.TestCase):
    def test_promotion_preserves_live_data_and_is_repeatable(self):
        original = '''<html><head></head><body><div class="app">
<button id="toolsOpenBtn">더보기</button><nav class="search-modes"></nav>
<section id="mapFilters"></section><button id="languageBtn">EN</button>
<div class="map-area"></div><script src="assets/i18n.js"></script><script>
const STATIONS = [{"id":"new-live-id","checked_at":"2026-11-06"}];
const PRICES = {"new-live-id":{"휘발유":1850}};
const PRICE_INFO = {"new-live-id":{"source_dates":["20261106"]}};
const MERCHANT_STATUS = {"new-live-id":{"issuer":"kb"}};
const NATIONAL_PENDING = [{"id":"unconfirmed","status":"review"}];
</script></div></body></html>'''
        result = ui.promote(original)
        self.assertEqual(ui.datasets(original), ui.datasets(result))
        self.assertEqual(ui.promote(result), result)
        self.assertNotIn('id="languageBtn"', result)
        self.assertNotIn('src="assets/i18n.js', result)
        self.assertIn('endpoint:"",externalNavigationEnabled:true', result)
        self.assertNotIn('127.0.0.1', result)
        self.assertNotIn('BIN_KEY', result)

    def test_release_references_exist_and_match_design_sources(self):
        html = (ROOT / 'output/map.html').read_text(encoding='utf-8')
        for relative in re.findall(r'(?:src|href)="(assets/[^"?#]+)', html):
            self.assertTrue((ROOT / relative).is_file(), relative)
        for name in ['reference.css', 'reference.js', 'journey.css', 'journey.js']:
            self.assertEqual((ROOT / 'design/onnuri-fuel-v2' / name).read_bytes(), (ROOT / 'assets/fuel-ui' / name).read_bytes())


if __name__ == '__main__':
    unittest.main()
