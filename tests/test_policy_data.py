import importlib.util
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('policy_builder', ROOT / 'scripts/build_policy_data.py')
builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)


class PolicyData(unittest.TestCase):
    def test_published_json_and_offline_fallback_are_identical(self):
        data = json.loads((ROOT / 'assets/onnuri-policy.json').read_text(encoding='utf-8'))
        self.assertEqual(builder.browser_script(data), (ROOT / 'assets/onnuri-policy-data.js').read_text(encoding='utf-8'))

    def test_toss_fallback_retains_policy_evidence_without_app_market_links(self):
        source = (ROOT / 'assets/onnuri-policy-data.js').read_text(encoding='utf-8')
        result = builder.platform_script(source)
        self.assertNotIn('apps.apple.com', result)
        self.assertNotIn('play.google.com', result)
        self.assertIn('156783869', result)
        self.assertIn('156786628', result)

    def test_announcement_clock_and_limits_validate_consistently(self):
        data = json.loads((ROOT / 'assets/onnuri-policy.json').read_text(encoding='utf-8'))
        self.assertEqual(builder.validate(data)['notices'][0]['endsAt'], '2026-11-06T23:30:00+09:00')
        for key, value in [('endsAt', '2026-11-07T23:30:00+09:00'), ('endsAt', '2026-11-06T14:30:00Z'), ('purchaseLimitKRW', -1)]:
            changed = json.loads(json.dumps(data))
            changed['notices'][0][key] = value
            with self.assertRaises(ValueError):
                builder.validate(changed)


if __name__ == '__main__':
    unittest.main()
