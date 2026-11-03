import copy
import json
import unittest
from pathlib import Path
from unittest.mock import Mock

from scripts.independent_place import URL, validate
from scripts.incremental_collector import initial_state, merge_sources, request_for, run
from scripts.collector_limits import limits
from tests.test_incremental_collector import Clock, response


def place_job(i=0):
    return {'id': 'place-' + str(i), 'kind': 'kakao_place_identity', 'source': 'kakao_local',
            'region': '전남', 'purpose': 'independent_premise_identity',
            'review_station_id': 'existing-station', 'discovery_only': True,
            'target': {'name': '샘플주유소', 'query': '샘플주유소 나주'}}


def payload():
    return {'meta': {'total_count': 1, 'is_end': True}, 'documents': [
        {'id': 'sample-place', 'place_name': '샘플주유소', 'phone': '061-123-4567',
         'road_address_name': '전남 나주시 검증로 1', 'address_name': '전남 나주시 검증동 1',
         'category_group_code': 'OL7', 'category_name': '교통,수송 > 주유소',
         'x': '126.7', 'y': '35.0'}]}


class IndependentPlaceTests(unittest.TestCase):
    def setUp(self):
        self.policy = json.loads((Path(__file__).resolve().parents[1] / 'config/collector-policy.json').read_text(encoding='utf-8'))
        self.clock = Clock(); self.session = Mock(); self.store = Mock()
        self.set_response(payload())

    def set_response(self, data, status=200):
        r = response(status, text=json.dumps(data, ensure_ascii=False))
        r.json.return_value = data
        self.session.request.return_value = r

    def state(self, count=1):
        return initial_state({'id': 'place-test', 'scope': 'identity only',
                              'jobs': [place_job(i) for i in range(count)]}, self.policy)

    def execute(self, state, maximum=4):
        return run(state, self.store, self.policy, self.session, [], {},
                   clock=self.clock, sleeper=self.clock.sleep, max_requests=maximum)

    def test_named_request_has_fixed_transport_and_single_bounded_page(self):
        j = place_job(); j.update(url='https://untrusted.test', headers={'Authorization': 'ignored'})
        method, url, options = request_for(j)
        self.assertEqual((method, url), ('GET', URL))
        self.assertEqual(options, {'params': {'q': '샘플주유소 나주', 'page': 1, 'size': 15, 'sort': 'accuracy'}})
        for query in ('', 'x' * 121, None):
            j['target']['query'] = query
            with self.assertRaises(ValueError): request_for(j)
        j = place_job(); j['source'] = 'onnuri'
        with self.assertRaises(ValueError): request_for(j)

    def test_place_and_even_fuel_category_never_renew_membership_or_annual_identity(self):
        state = self.state(); state['membership_rechecks'] = {'existing-station': {'status': 'needs_review_not_found'}}
        state['candidate_resolutions'] = {'candidate': {'status': 'pending'}}
        before = copy.deepcopy(state)
        self.execute(state)
        self.assertEqual(self.session.request.call_count, 1)
        for field in ('evidence', 'membership_rechecks', 'candidate_resolutions', 'source_gaps', 'review'):
            self.assertEqual(state[field], before[field])
        saved = state['independent_place_checks']['place-0']
        self.assertEqual(saved['payload']['documents'][0]['category_group_code'], 'OL7')
        self.assertIn('not membership', saved['scope'])
        self.assertTrue(any(len(call.args) > 1 and call.args[1] for call in self.store.save.call_args_list))

    def test_source_specific_one_per_run_two_per_rolling_day_without_raising_kb_limits(self):
        state = self.state(3)
        self.execute(state); self.assertEqual(self.session.request.call_count, 1)
        self.clock.value += 10800; self.execute(state)
        self.assertEqual(self.session.request.call_count, 2)
        self.clock.value += 10800; self.execute(state)
        self.assertEqual(self.session.request.call_count, 2)
        self.assertEqual(limits(state, self.policy, 'kbcard', self.clock())['requests_per_run'], 3)
        self.assertEqual(limits(state, self.policy, 'kbcard', self.clock())['requests_per_24h'], 24)
        self.assertEqual(limits(state, self.policy, 'datagov', self.clock())['requests_per_24h'], 20)

    def test_explicit_rejection_stays_blocked_and_never_uses_another_transport(self):
        self.set_response({'error': 'forbidden'}, 403)
        state = self.state(2); self.execute(state)
        self.clock.value += 86400; self.execute(state)
        self.assertEqual(self.session.request.call_count, 1)
        self.assertEqual(state['sources']['kakao_local']['status'], 'blocked')
        self.assertEqual(state['sources']['onnuri']['status'], 'blocked')
        self.assertEqual(self.session.request.call_args.args[:2], ('GET', URL))

    def test_contract_or_relay_error_is_preserved_and_pauses_source(self):
        for status, data in [(200, {'unexpected': []}), (503, {'error': 'upstream_not_configured'})]:
            with self.subTest(status=status):
                self.session.reset_mock(); self.store.reset_mock(); self.set_response(data, status)
                state = self.state(2); self.execute(state)
                self.clock.value += 86400; self.execute(state)
                self.assertEqual(self.session.request.call_count, 1)
                self.assertEqual(state['sources']['kakao_local']['status'], 'needs_review')
                self.assertNotIn('independent_place_checks', state)
                self.assertTrue(any(len(call.args) > 1 and call.args[1] for call in self.store.save.call_args_list))

    def test_bad_coordinates_duplicates_and_bad_metadata_fail_closed(self):
        variants = []
        for field, value in [('y', '0'), ('id', ''), ('phone', None)]:
            data = payload(); data['documents'][0][field] = value; variants.append(data)
        data = payload(); data['documents'] *= 2; data['meta']['total_count'] = 2; variants.append(data)
        data = payload(); data['meta']['is_end'] = 'true'; variants.append(data)
        for data in variants:
            with self.subTest(data=data):
                with self.assertRaises(ValueError): validate(data)

    def test_installing_source_preserves_prior_rejections_timers_and_requests(self):
        state = self.state(); state['sources'].pop('kakao_local')
        state['sources']['kbcard'].update(status='blocked', next_allowed_at=12345, reason='prior rejection')
        state['attempts'] = [{'source': 'kbcard', 'status': 'blocked', 'at': 1}]
        before = copy.deepcopy(state)
        merge_sources(state, self.policy)
        for name, settings in before['sources'].items(): self.assertEqual(state['sources'][name], settings)
        self.assertEqual(state['attempts'], before['attempts'])
        state['sources']['kakao_local'].update(status='blocked', next_allowed_at=98765)
        merge_sources(state, self.policy)
        self.assertEqual(state['sources']['kakao_local']['status'], 'blocked')
        self.assertEqual(state['sources']['kakao_local']['next_allowed_at'], 98765)


if __name__ == '__main__':
    unittest.main()
